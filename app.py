"""Flask entry point for the SEO log auditor."""

from __future__ import annotations

import os
import sys
import uuid
from io import BytesIO

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from snowflake.connector import connect

# Make src package importable when running locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import plotly.express as px

from seo_log_auditor.analysis.budget import crawl_budget_distribution, hits_over_time
from seo_log_auditor.analysis.frequency import crawl_depth_distribution, stale_pages
from seo_log_auditor.analysis.masquerade import hits_by_verdict, top_spoofers, verification_summary
from seo_log_auditor.analysis.orphans import find_orphans
from seo_log_auditor.analysis.param_traps import parameter_frequency, trap_candidates
from seo_log_auditor.analysis.performance import hits_by_size_decile, latency_summary, size_vs_latency
from seo_log_auditor.analysis.status_waste import (
    four_oh_four_forensics,
    status_class_breakdown,
    waste_by_page_type,
    waste_overview,
    worst_offenders,
)
from seo_log_auditor.insights import generate_insights
from seo_log_auditor.plotly_theme import fig_to_json
from seo_log_auditor.web_state import (
    clear_caches,
    clear_session,
    dataframe_records,
    filter_to_googlebot,
    get_preferences,
    get_state,
    load_data,
    summary_for_insights,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")


@app.before_request
def reload_env():
    if app.debug:
        load_dotenv(override=True)


def _session_id() -> str:
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def _require_state():
    state = get_state(_session_id())
    if state is None:
        flash("Upload a log export from the home page first.", "warning")
        return None
    return state


def get_private_key():
    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    private_key_content = os.getenv("SNOWFLAKE_PRIVATE_KEY")
    passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

    if passphrase:
        passphrase = passphrase.strip().strip('"').strip("'")

    if private_key_path:
        private_key_path = private_key_path.strip().strip('"').strip("'")
        if "\r" in private_key_path and "\r" != os.linesep:
            private_key_path = private_key_path.replace("\r", "\\r")
        private_key_path = os.path.normpath(private_key_path)
        if not os.path.isfile(private_key_path):
            raise Exception(f"Private key file not found at path: {private_key_path}")
        with open(private_key_path, "rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=passphrase.encode() if passphrase else None,
                backend=default_backend(),
            )
    elif private_key_content:
        key_content = private_key_content.strip().strip('"').strip("'").replace("\\n", "\n")
        p_key = serialization.load_pem_private_key(
            key_content.encode(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )
    else:
        raise Exception("Either SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PRIVATE_KEY must be set")

    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_snowflake_connection():
    private_key = get_private_key()
    user = os.getenv("SNOWFLAKE_USERNAME")
    if not user:
        raise Exception("SNOWFLAKE_USERNAME must be set")
    conn_params = {
        "user": user,
        "private_key": private_key,
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    }
    role = os.getenv("SNOWFLAKE_ROLE")
    if role:
        conn_params["role"] = role
    return connect(**conn_params)


NAV = [
    ("index", "00 / overview", "Overview"),
    ("crawl_budget", "01 / crawl budget", "Crawl Budget"),
    ("orphan_pages", "02 / orphans", "Orphan Pages"),
    ("status_waste", "03 / status waste", "Status Waste"),
    ("stale_pages_view", "04 / stale", "Stale Pages"),
    ("performance", "05 / performance", "Performance"),
    ("bot_verification", "06 / bot verification", "Bot Verification"),
    ("parameter_traps", "07 / parameter traps", "Parameter Traps"),
]


@app.context_processor
def inject_nav():
    return {"nav_items": NAV, "prefs": get_preferences(_session_id())}


@app.route("/")
def index():
    state = get_state(_session_id())
    context = {
        "section": "00 / overview",
        "state": state,
        "metrics": None,
        "chart_json": None,
        "time_span": "",
        "insights": session.pop("insights_text", None),
    }
    if state is not None:
        bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
        waste = waste_overview(bot_df)
        context["metrics"] = {
            "bot_hits": f"{waste['total']:,}",
            "unique_urls": f"{bot_df['path'].nunique():,}",
            "unique_ips": f"{bot_df['ip'].nunique():,}",
            "waste_ratio": f"{waste['waste_ratio']:.1%}",
            "verified_share": f"{bot_df['is_verified_googlebot'].fillna(False).mean():.0%}"
            if not bot_df.empty
            else "0%",
        }
        if bot_df["timestamp"].notna().any():
            first = bot_df["timestamp"].min()
            last = bot_df["timestamp"].max()
            context["time_span"] = f"{first:%Y-%m-%d %H:%M} -> {last:%Y-%m-%d %H:%M} UTC"
            ts_df = (
                bot_df.dropna(subset=["timestamp"])
                .assign(bucket=lambda d: d["timestamp"].dt.floor("1h"))
                .groupby(["bucket", "page_type"])
                .size()
                .rename("hits")
                .reset_index()
            )
            if not ts_df.empty:
                context["chart_json"] = fig_to_json(
                    px.area(ts_df, x="bucket", y="hits", color="page_type")
                )
    return render_template("index.html", **context)


@app.route("/load", methods=["POST"])
def load_logs():
    uploads = request.files.getlist("log_files")
    files = [(f.filename, f.read()) for f in uploads if f.filename]
    patterns = request.files.get("patterns_file")
    patterns_bytes = patterns.read() if patterns and patterns.filename else None
    sitemap_url = request.form.get("sitemap_url", "")
    verify_bots = request.form.get("verify_bots") == "on"
    only_verified = request.form.get("only_verified") == "on"

    _, errors = load_data(
        _session_id(),
        files,
        sitemap_url,
        patterns_bytes,
        verify_bots,
        only_verified,
    )
    for err in errors:
        flash(err, "error" if "Could not" in err or "Failed" in err else "warning")
    if not errors or get_state(_session_id()) is not None:
        flash("Log data loaded successfully.", "success")
    return redirect(url_for("index"))


@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    clear_caches()
    flash("Cleared cached parses and fetches. Click Load / refresh to re-run.", "success")
    return redirect(url_for("index"))


@app.route("/clear-data", methods=["POST"])
def clear_data():
    clear_session(_session_id())
    session.pop("insights_text", None)
    flash("Cleared all loaded data.", "success")
    return redirect(url_for("index"))


@app.route("/insights", methods=["POST"])
def insights():
    page = request.form.get("page", "overview")
    summary = summary_for_insights(_session_id())
    session["insights_text"] = generate_insights(summary, page=page)
    return redirect(request.referrer or url_for("index"))


@app.route("/crawl-budget")
def crawl_budget():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    dist = crawl_budget_distribution(
        bot_df,
        sitemap_page_types=state.sitemap_page_types if not state.sitemap_page_types.empty else None,
    )
    charts = {}
    if not dist.empty:
        charts["pie"] = fig_to_json(
            px.pie(dist.reset_index(), names="page_type", values="hits", hole=0.4)
        )
        cmp = dist.reset_index()[["page_type", "hit_share", "url_share"]].melt(
            id_vars="page_type", var_name="series", value_name="share"
        )
        charts["bar"] = fig_to_json(px.bar(cmp, x="page_type", y="share", color="series", barmode="group"))
        ts = hits_over_time(bot_df, freq="1h")
        if not ts.empty:
            charts["area"] = fig_to_json(px.area(ts, x="bucket", y="hits", color="page_type"))
    return render_template(
        "analysis.html",
        section="01 / crawl budget",
        title="Where Google is spending its crawl.",
        caption=(
            "How Googlebot is actually spending its budget vs. how your URLs are "
            "structured. A large positive delta means a page type is over-crawled."
        ),
        table=dist,
        charts=charts,
        page_key="crawl_budget",
    )


@app.route("/orphan-pages")
def orphan_pages():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    if not state.sitemap_paths:
        flash("No sitemap loaded. Add a sitemap URL and click Load / refresh.", "warning")
        return redirect(url_for("index"))
    include_non_200 = request.args.get("include_non_200") == "1"
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    orphans = find_orphans(bot_df, state.sitemap_paths, only_200=not include_non_200)
    return render_template(
        "analysis.html",
        section="02 / orphans",
        title="URLs Googlebot finds that your sitemap doesn't list.",
        caption="Pages crawled (200 OK) that aren't in your sitemap.",
        table=orphans,
        charts={},
        page_key="orphan_pages",
        metric_label="Orphan URLs",
        metric_value=f"{len(orphans):,}",
        download_name="orphans.csv",
        controls={"include_non_200": include_non_200},
    )


@app.route("/status-waste")
def status_waste():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    overview = waste_overview(bot_df)
    top_n = int(request.args.get("top_n", 100))
    selected = request.args.getlist("status_class") or ["3xx", "4xx", "5xx"]
    scope = request.args.get("scope", "googlebot")
    forensics_classes = request.args.getlist("forensics_class") or ["4xx"]
    forensics_df = bot_df if scope == "googlebot" else state.log_df
    offenders = worst_offenders(bot_df, status_classes=tuple(selected), top_n=top_n)
    forensics = four_oh_four_forensics(
        forensics_df,
        sitemap_paths=state.sitemap_paths or None,
        status_classes=tuple(forensics_classes) or ("4xx",),
        top_n=200,
    )
    charts = {}
    classes = status_class_breakdown(bot_df)
    if not classes.empty:
        charts["status"] = fig_to_json(px.bar(classes, x="status_class", y="hits", text="hits"))
    by_type = waste_by_page_type(bot_df)
    if not by_type.empty:
        charts["waste_type"] = fig_to_json(px.bar(by_type, x="page_type", y="waste_ratio", text="non_200"))
    return render_template(
        "status_waste.html",
        section="03 / status waste",
        title="Crawl spent on redirects and errors.",
        overview=overview,
        offenders=offenders,
        forensics=forensics,
        by_type=by_type,
        charts=charts,
        top_n=top_n,
        selected=selected,
        scope=scope,
        forensics_classes=forensics_classes,
        page_key="status_waste",
    )


@app.route("/stale-pages")
def stale_pages_view():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    if not state.sitemap_paths:
        flash("No sitemap loaded. Add a sitemap URL and click Load / refresh.", "warning")
        return redirect(url_for("index"))
    stale_days = int(request.args.get("stale_days", 7))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    stale = stale_pages(bot_df, state.sitemap_paths, stale_days=stale_days)
    never = int((stale["status"] == "never").sum())
    old = int((stale["status"] == "stale").sum())
    charts = {}
    depth = crawl_depth_distribution(bot_df)
    if not depth.empty:
        charts["depth"] = fig_to_json(px.bar(depth, x="depth", y="hits", text="hits"))
    return render_template(
        "analysis.html",
        section="04 / stale",
        title="Sitemap URLs Google hasn't visited recently.",
        caption="Sitemap URLs that Googlebot hasn't visited in N days, or never.",
        table=stale,
        charts=charts,
        page_key="stale_pages",
        metrics=[("Never crawled", f"{never:,}"), (f"Crawled but >{stale_days}d old", f"{old:,}")],
        download_name="stale_pages.csv",
        controls={"stale_days": stale_days},
    )


@app.route("/performance")
def performance():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    stats = latency_summary(bot_df)
    scatter = size_vs_latency(bot_df)
    deciles = hits_by_size_decile(bot_df)
    charts = {}
    if not scatter.empty:
        charts["scatter"] = fig_to_json(
            px.scatter(
                scatter,
                x="median_bytes",
                y="median_latency_ms",
                size="hits",
                color="page_type",
                hover_data=["path", "hits"],
                log_x=True,
            )
        )
    if not deciles.empty:
        deciles_display = deciles.assign(
            bucket=lambda d: d.apply(
                lambda r: f"{int(r['lower_bytes']):,} - {int(r['upper_bytes']):,} B", axis=1
            )
        )
        charts["deciles"] = fig_to_json(
            px.bar(deciles_display, x="bucket", y="avg_hits_per_url", text="urls")
        )
    else:
        deciles_display = deciles
    return render_template(
        "performance.html",
        section="05 / performance",
        stats=stats,
        deciles=deciles_display,
        charts=charts,
        page_key="performance",
    )


@app.route("/bot-verification")
def bot_verification():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    summary = verification_summary(state.log_df)
    verdicts = hits_by_verdict(state.log_df)
    spoofers = top_spoofers(state.log_df, top_n=100)
    charts = {}
    if not verdicts.empty:
        charts["verdicts"] = fig_to_json(px.bar(verdicts, x="verdict", y="hits", text="hits"))
    return render_template(
        "bot_verification.html",
        section="06 / bot verification",
        summary=summary,
        spoofers=spoofers,
        charts=charts,
        verification_enabled=state.verification_enabled,
        page_key="bot_verification",
        download_name="spoofers.csv" if not spoofers.empty else None,
    )


@app.route("/parameter-traps")
def parameter_traps():
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    threshold = int(request.args.get("threshold", 50))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    traps = trap_candidates(bot_df, min_variants=threshold)
    freq = parameter_frequency(bot_df, top_n=30)
    charts = {}
    if not freq.empty:
        charts["freq"] = fig_to_json(px.bar(freq, x="param", y="hits", text="paths_seen"))
    return render_template(
        "analysis.html",
        section="07 / parameter traps",
        title="Query-string explosions eating budget.",
        caption="Paths whose query strings have exploded into too many variants.",
        table=traps,
        charts=charts,
        page_key="parameter_traps",
        metric_label="Trap candidates",
        metric_value=f"{len(traps):,}",
        download_name="param_traps.csv" if not traps.empty else None,
        controls={"threshold": threshold},
        extra_chart_title="Most common query parameters across all hits",
    )


@app.route("/download/<name>")
def download_csv(name: str):
    state = _require_state()
    if state is None:
        return redirect(url_for("index"))
    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    mapping = {
        "orphans.csv": lambda: find_orphans(
            bot_df, state.sitemap_paths, only_200=request.args.get("include_non_200") != "1"
        ),
        "stale_pages.csv": lambda: stale_pages(
            bot_df, state.sitemap_paths, stale_days=int(request.args.get("stale_days", 7))
        ),
        "spoofers.csv": lambda: top_spoofers(state.log_df, top_n=100),
        "param_traps.csv": lambda: trap_candidates(
            bot_df, min_variants=int(request.args.get("threshold", 50))
        ),
        "404_forensics.csv": lambda: four_oh_four_forensics(
            bot_df if request.args.get("scope", "googlebot") == "googlebot" else state.log_df,
            sitemap_paths=state.sitemap_paths or None,
            status_classes=tuple(request.args.getlist("forensics_class") or ["4xx"]),
            top_n=200,
        ),
    }
    if name not in mapping:
        flash("Unknown download.", "error")
        return redirect(url_for("index"))
    df = mapping[name]()
    return Response(
        df.to_csv(index=False),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )


@app.route("/test-connection", methods=["POST"])
def test_connection():
    conn = None
    cursor = None
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()")
        current_db, current_schema = cursor.fetchone()
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        current_user, current_role, current_warehouse = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify(
            {
                "success": True,
                "message": "Successfully connected to Snowflake and verified data access!",
                "version": version,
                "database": current_db,
                "schema": current_schema,
                "user": current_user,
                "role": current_role,
                "warehouse": current_warehouse,
            }
        )
    except Exception as exc:  # noqa: BLE001
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return jsonify({"success": False, "message": f"Connection test failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)
