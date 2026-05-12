# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- Initial public release.
- `seo-log-auditor` console script that launches the Streamlit dashboard.
- `seo-log-auditor init-config` to drop a starter `page_patterns.yaml` into
  the user's working directory.
- Seven analysis pages: Crawl Budget, Orphan Pages, Status Waste,
  Stale Pages, Performance, Bot Verification, Parameter Traps.
- Multi-format log parser: Loki JSON, NDJSON / JSONL (objects *and*
  JSON-encoded strings), Grafana Explore CSV, plain nginx access-log text.
- Default upload cap raised to 300 MB so a 30-day Loki export fits.
- Forward-confirmed reverse-DNS Googlebot verification with cached results.
- Sitemap-index aware crawler.
