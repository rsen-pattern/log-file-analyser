"""Visual theme for the Streamlit app.

Mirrors the "Editorial Tech" design system used at https://pattern.com —
near-black surfaces, neon-lime accent, JetBrains Mono / Space Grotesk
/ Inter typography. Streamlit's primary/background/text colors are
already wired up via the ``--theme.*`` CLI flags in ``cli.py``; this
module layers on the typography, the section markers, the brand
header, and the author credit footer that Streamlit's built-in theme
config can't express.

Public API:

* :func:`setup_page(section)` — call once at the top of every page to
  inject the design-system CSS and render the brand header. Pass a
  ``section`` string like ``"01 / crawl budget"`` to also render the
  ◇-prefixed section marker.
* :func:`add_footer()` — call at the bottom of every page. Renders the
  credit line linking to https://pattern.com and the GitHub repo.
* :data:`PLOTLY_TEMPLATE` — a Plotly layout dict that matches the
  dark/lime palette. Pass it as ``template=PLOTLY_TEMPLATE`` (or use
  :func:`apply_plotly_template` for a one-shot).
"""

from __future__ import annotations

import streamlit as st

# --------------------------------------------------------------------------- #
# CSS  (kept inline so the package has no extra asset files to ship)
# --------------------------------------------------------------------------- #

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@400;500;600;700"
    "&family=Space+Grotesk:wght@500;600;700"
    "&family=JetBrains+Mono:wght@400;500"
    "&display=swap"
)

_CSS = """
<style>
@import url("__FONTS__");

:root {
  --bg-0: #09090b;
  --bg-1: #0d0d10;
  --bg-2: #131318;
  --bg-3: #1a1a20;
  --line: #26262d;
  --line-2: #32323a;
  --text-hi: #f5f5f7;
  --text-md: #b4b4ba;
  --text-lo: #707078;
  --text-xlo: #4b4b52;
  --accent: #b4ff39;
  --accent-soft: rgba(180, 255, 57, 0.12);
  --accent-2: #ff6b4a;
  --ff-display: "Space Grotesk", ui-sans-serif, system-ui, sans-serif;
  --ff-body: "Inter", ui-sans-serif, system-ui, sans-serif;
  --ff-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background: var(--bg-0) !important;
  font-family: var(--ff-body) !important;
  color: var(--text-md) !important;
  letter-spacing: -0.005em;
}

/* Headings */
h1, h2, h3, h4,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
  font-family: var(--ff-display) !important;
  color: var(--text-hi) !important;
  letter-spacing: -0.02em !important;
  font-weight: 600 !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"] {
  font-family: var(--ff-body) !important;
  color: var(--text-md) !important;
}

/* Code-style elements — captions look like terminal text */
.stCaption, [data-testid="stCaptionContainer"] {
  font-family: var(--ff-mono) !important;
  font-size: 0.78rem !important;
  color: var(--text-lo) !important;
}

/* ---------- Brand header at top of each page ---------- */
.brand-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0 1rem 0;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1.25rem;
  font-family: var(--ff-mono);
  font-size: 0.82rem;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--accent);
  color: var(--bg-0);
  border-radius: 9px;
  font-family: var(--ff-display);
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: -0.02em;
}
.brand-name { color: var(--text-hi); font-weight: 500; }
.brand-tag { color: var(--text-lo); }
.brand-spacer { flex: 1; }
.brand-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-lo);
}
.brand-status::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
}

/* ---------- Section marker (renders above page titles) ---------- */
.section-marker {
  font-family: var(--ff-mono);
  font-size: 0.78rem;
  color: var(--text-lo);
  text-transform: lowercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.35rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.section-marker::before {
  content: "\\25C7";
  color: var(--accent);
  font-size: 0.9rem;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: var(--bg-1) !important;
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  font-family: var(--ff-display) !important;
  color: var(--text-hi) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label {
  font-family: var(--ff-body) !important;
  color: var(--text-md) !important;
}
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] span {
  font-family: var(--ff-mono) !important;
  font-size: 0.85rem !important;
}

/* ---------- Metric cards (KPI tiles) ---------- */
[data-testid="stMetric"] {
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1rem 1.1rem;
}
[data-testid="stMetricLabel"] {
  color: var(--text-lo) !important;
  font-family: var(--ff-mono) !important;
  font-size: 0.72rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] {
  color: var(--text-hi) !important;
  font-family: var(--ff-display) !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
}

/* ---------- Buttons ---------- */
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  color: var(--bg-0) !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  letter-spacing: -0.005em;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  filter: brightness(1.05);
}
.stButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--line-2) !important;
  background: var(--bg-2) !important;
  color: var(--text-hi) !important;
  font-weight: 500 !important;
}

/* ---------- Inputs ---------- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
  background: var(--bg-2) !important;
  border: 1px solid var(--line) !important;
  color: var(--text-hi) !important;
  font-family: var(--ff-mono) !important;
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"],
section[data-testid="stFileUploaderDropzone"] {
  background: var(--bg-2) !important;
  border: 1px dashed var(--line-2) !important;
  border-radius: 12px;
}

/* ---------- Tabs / Dataframe headers ---------- */
.stDataFrame, [data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 10px;
}

/* ---------- Code blocks ---------- */
code, pre {
  font-family: var(--ff-mono) !important;
  background: var(--bg-2) !important;
}

/* ---------- Alerts ---------- */
[data-testid="stAlert"] {
  border-radius: 10px;
  border-left: 2px solid var(--accent);
  background: var(--bg-2) !important;
}

/* ---------- Footer ---------- */
.app-footer {
  margin-top: 3rem;
  padding: 1.25rem 0 0.5rem 0;
  border-top: 1px solid var(--line);
  font-family: var(--ff-mono);
  font-size: 0.76rem;
  color: var(--text-lo);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.app-footer a {
  color: var(--accent);
  text-decoration: none;
}
.app-footer a:hover { text-decoration: underline; }
.app-footer-prompt::before {
  content: "~/seo-log-auditor ";
  color: var(--text-xlo);
}
.app-footer-prompt::after {
  content: " \\276F";
  color: var(--accent);
  margin-left: 0.35rem;
}

/* ---------- Hide Streamlit's default top-right hamburger/share noise ---------- */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }

/* ---------- Accessibility: focus indicators + shape differentiation ---------- */
*:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}
.stMultiSelect [data-baseweb="tag"] {
  border: 2px solid var(--bg-0) !important;
  font-weight: 600 !important;
}
.section-marker {
  font-size: 0.85rem !important;
}
</style>
""".replace(
    "__FONTS__", _FONTS
)

# --------------------------------------------------------------------------- #
# Plotly template
# --------------------------------------------------------------------------- #

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": "#09090b",
        "plot_bgcolor": "#09090b",
        "font": {
            "family": "Inter, system-ui, sans-serif",
            "color": "#b4b4ba",
            "size": 12,
        },
        "title": {"font": {"family": "Space Grotesk, sans-serif", "color": "#f5f5f7"}},
        "colorway": [
            "#b4ff39",  # signature lime
            "#ff6b4a",  # coral
            "#4a7bff",  # blue
            "#ffd166",  # amber
            "#9b8cff",  # lavender
            "#6affc0",  # mint
            "#ff7ad9",  # pink
        ],
        "xaxis": {
            "gridcolor": "#1a1a20",
            "zerolinecolor": "#26262d",
            "linecolor": "#26262d",
            "tickfont": {"color": "#707078", "family": "JetBrains Mono, monospace", "size": 11},
            "title": {"font": {"color": "#b4b4ba"}},
        },
        "yaxis": {
            "gridcolor": "#1a1a20",
            "zerolinecolor": "#26262d",
            "linecolor": "#26262d",
            "tickfont": {"color": "#707078", "family": "JetBrains Mono, monospace", "size": 11},
            "title": {"font": {"color": "#b4b4ba"}},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#b4b4ba", "size": 11},
            "bordercolor": "#26262d",
        },
        "hoverlabel": {
            "bgcolor": "#131318",
            "bordercolor": "#26262d",
            "font": {"color": "#f5f5f7", "family": "JetBrains Mono, monospace"},
        },
    }
}


def apply_plotly_template() -> None:
    """Register the Editorial Tech template as the default for Plotly."""
    try:
        import plotly.io as pio

        pio.templates["editorial_tech"] = PLOTLY_TEMPLATE
        pio.templates.default = "editorial_tech"
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #


def setup_page(section: str | None = None) -> None:
    """Inject CSS, render the brand header, and (optionally) a section marker.

    Call this once at the top of every Streamlit page (after
    ``st.set_page_config`` if used). The ``section`` parameter is a short
    label like ``"01 / crawl budget"`` that's rendered above the page
    title in the JetBrains-Mono "section marker" style.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="brand-header" role="banner" aria-label="seo-log-auditor by Rahul Sengupta and Pattern">
          <span class="brand-mark" aria-hidden="true">RS</span>
          <span class="brand-name">seo-log-auditor</span>
          <span class="brand-tag">· by Rahul Sengupta · Pattern</span>
          <span class="brand-spacer"></span>
          <span class="brand-status">runs locally</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if section:
        st.markdown(
            f'<div class="section-marker">{section}</div>',
            unsafe_allow_html=True,
        )
    apply_plotly_template()


# --------------------------------------------------------------------------- #
# Dataframe display helpers
# --------------------------------------------------------------------------- #

COLUMN_LABELS = {
    "path": "Path",
    "hits": "Hits",
    "status": "Status",
    "page_type": "Page Type",
    "hit_share": "Hit Share %",
    "url_share": "URL Share %",
    "sitemap_urls": "Sitemap URLs",
    "delta": "Delta %",
    "last_crawled": "Last Crawled",
    "days_since": "Days Since Crawl",
    "status_mix": "Status Codes",
    "avg_hits_per_url": "Avg Hits / URL",
    "lower_bytes": "Size (Min)",
    "upper_bytes": "Size (Max)",
    "total_hits": "Total Hits",
    "user_agent": "User Agent",
    "non_200": "Non-200 Hits",
    "waste_ratio": "Waste Ratio %",
    "sample_query": "Sample Query",
    "top_param": "Top Parameter",
    "paths_seen": "Paths Seen",
    "ip": "IP",
    "param": "Parameter",
    "variants": "Variants",
    "depth": "Depth",
    "decile": "Decile",
    "urls": "URLs",
    "bucket": "Bucket",
    "median_bytes": "Median Bytes",
    "median_latency_ms": "Median Latency (ms)",
    "status_class": "Status Class",
    "share": "Share %",
    "verdict": "Verdict",
    "total": "Total",
    "referer": "Referer",
    "referer_hits": "Referer Hits",
    "in_sitemap": "In Sitemap",
}

_PERCENT_COLS = {"hit_share", "url_share", "delta", "waste_ratio", "share"}
_LARGE_COLS = {"path", "sample_query", "user_agent", "referer", "last_crawled", "bucket"}
_SMALL_COLS = {
    "hits", "status", "depth", "decile", "variants", "non_200",
    "urls", "total_hits", "paths_seen", "in_sitemap", "days_since",
    "referer_hits", "status_class",
}


def clean_dataframe(df):
    """Replace None/NaN display values with readable alternatives."""
    import pandas as pd

    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
        elif pd.api.types.is_bool_dtype(df[col]):
            df[col] = df[col].fillna(False)
        else:
            df[col] = df[col].astype("object").fillna("—")
    return df


def _build_column_config(df):
    """Build a st.column_config dict that renames snake_case columns and sizes them sanely."""
    from streamlit import column_config as cc

    cfg = {}
    for col in df.columns:
        label = COLUMN_LABELS.get(col, str(col).replace("_", " ").title())
        if col in _PERCENT_COLS:
            cfg[col] = cc.NumberColumn(label, format="%.1f%%", width="small")
        elif col in _LARGE_COLS:
            cfg[col] = cc.TextColumn(label, width="large")
        elif col in _SMALL_COLS:
            cfg[col] = cc.NumberColumn(label, width="small") if str(df[col].dtype).startswith(("int", "float", "bool")) else cc.TextColumn(label, width="small")
        else:
            cfg[col] = cc.Column(label)
    return cfg


def render_dataframe(
    df,
    *,
    empty_message: str = "No results to display.",
    column_overrides: dict | None = None,
    height: int | None = None,
) -> None:
    """Render a DataFrame with empty-state, NaN cleanup, and human-readable headers."""
    import pandas as pd

    if df is None or len(df) == 0:
        st.info(empty_message)
        return

    df = clean_dataframe(df)

    # Scale 0-1 ratio columns into 0-100 for the "%" format string.
    for col in df.columns:
        if col in _PERCENT_COLS and pd.api.types.is_numeric_dtype(df[col]):
            try:
                m = df[col].abs().max()
                if pd.notna(m) and m <= 1.5:
                    df[col] = df[col] * 100
            except Exception:
                pass

    cfg = _build_column_config(df)
    if column_overrides:
        cfg.update(column_overrides)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=cfg,
        height=height,
    )


PLOTLY_CONFIG = {"displayModeBar": False}


def render_plotly(fig, **kwargs) -> None:
    """Render a Plotly figure with the floating toolbar hidden."""
    config = kwargs.pop("config", None) or {}
    config = {**PLOTLY_CONFIG, **config}
    st.plotly_chart(fig, use_container_width=kwargs.pop("use_container_width", True), config=config, **kwargs)


def add_footer() -> None:
    """Render the credit footer linking to pattern.com and the GitHub repo."""
    st.markdown(
        """
        <div class="app-footer">
          <span class="app-footer-prompt">v0.1.0 · MIT · runs entirely on your machine</span>
          <span>
            Built by
            <a href="https://pattern.com" target="_blank" rel="noopener noreferrer">Rahul Sengupta · Pattern</a>
            ·
            <a href="https://github.com/rsen-pattern/log-file-analyser" target="_blank" rel="noopener noreferrer">GitHub</a>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
