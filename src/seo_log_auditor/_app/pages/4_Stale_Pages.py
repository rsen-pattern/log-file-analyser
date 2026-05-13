from __future__ import annotations

import plotly.express as px
import streamlit as st

from seo_log_auditor.analysis.frequency import crawl_depth_distribution, stale_pages
from seo_log_auditor.ui_state import filter_to_googlebot, require_state
from seo_log_auditor._app._theme import (
    add_footer,
    render_dataframe,
    render_plotly,
    setup_page,
)

st.set_page_config(page_title="Stale Pages", layout="wide")
setup_page("04 / stale")
state = require_state()

st.title("Sitemap URLs Google hasn't visited recently.")
st.caption(
    "Sitemap URLs that Googlebot hasn't visited in N days, or never. "
    "These are the prime candidates for the 'Deep Crawl Leakage' you described."
)

if not state.sitemap_paths:
    st.warning(
        "No sitemap loaded. Add a sitemap URL in the sidebar and click **Load / refresh**."
    )
    st.stop()

only_verified = st.session_state.get("only_verified_default", False)
bot_df = filter_to_googlebot(state.log_df, only_verified=only_verified)

stale_days = st.slider("Stale threshold (days)", 1, 30, value=7)

stale = stale_pages(bot_df, state.sitemap_paths, stale_days=stale_days)

never = (stale["status"] == "never").sum()
old = (stale["status"] == "stale").sum()
c1, c2 = st.columns(2)
c1.metric("Never crawled", f"{never:,}")
c2.metric(f"Crawled but >{stale_days}d old", f"{old:,}")

render_dataframe(
    stale,
    empty_message=(
        "No stale pages at this threshold. Try lowering the slider, or every "
        "sitemap URL has been crawled recently."
    ),
)

st.download_button(
    "Download stale list as CSV",
    data=stale.to_csv(index=False).encode(),
    file_name="stale_pages.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Crawl depth distribution")
st.caption(
    "Approximate depth based on path segments. Upload a Screaming Frog / "
    "Sitebulb crawl for precise shortest-path data."
)
depth = crawl_depth_distribution(bot_df)
if depth.empty:
    st.info("No depth data to show yet.")
else:
    fig = px.bar(depth, x="depth", y="hits", text="hits")
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
    render_plotly(fig)

add_footer()
