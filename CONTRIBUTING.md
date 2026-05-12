# Contributing to seo-log-auditor

Thanks for your interest. This is a small, opinionated project built by an SEO engineer for SEO engineers and SREs. The bar for contributions is "is this useful to people running technical SEO audits in production?" — that's it.

## Quickest path to a contribution

The most-wanted contributions, in rough priority order:

1. **Parsers for other log formats.** Cloudflare, AWS ALB / CloudFront, Apache combined log, Caddy. The existing nginx + Loki parser in [`src/seo_log_auditor/parsers.py`](src/seo_log_auditor/parsers.py) is a good template.
2. **Starter `page_patterns.yaml` files** for common stacks: Shopify, WordPress, Webflow, headless e-commerce, publishers, SaaS marketing sites. Drop them in `src/seo_log_auditor/_data/` as `page_patterns.shopify.yaml` etc.
3. **A `--demo` mode** that loads bundled synthetic data so first-time users can explore without their own logs.
4. **Bug reports with reproduction logs.** A 100-line snippet of an unusual log format that breaks the parser is more valuable than 10 vague issues.
5. **Documentation improvements.** README, this file, docstrings — anything that makes onboarding smoother.

## Codebase tour

```
src/seo_log_auditor/
├── cli.py                 Console-script entry. Launches Streamlit.
├── parsers.py             Log-format auto-detection + parsing.
├── classify.py            URL → page_type classifier (regex YAML).
├── sitemap.py             Sitemap / sitemap-index fetcher + parser.
├── verify_bot.py          Google IP-range fetch + reverse-DNS verification.
├── ui_state.py            Streamlit session-state helpers + caching.
├── analysis/              One module per analysis technique:
│   ├── budget.py          Crawl budget distribution.
│   ├── orphans.py         Sitemap-vs-actual orphan detection.
│   ├── status_waste.py    Non-200 ratio breakdown.
│   ├── frequency.py       Stale-page detection.
│   ├── performance.py     Size / latency / hit-frequency correlation.
│   ├── masquerade.py      Real Googlebot vs. spoofers.
│   └── param_traps.py     Query-string explosion detection.
├── _app/                  Streamlit entry script + multipage UI.
│   ├── app.py             Main page (sidebar + KPI overview).
│   ├── _theme.py          Dark "Editorial Tech" theme + Plotly template.
│   └── pages/             One file per analysis page (Streamlit auto-discovers).
└── _data/                 Bundled assets (page_patterns.example.yaml).
```

The `analysis/` modules are pure functions — they take a parsed DataFrame and return a DataFrame or summary. They have no Streamlit dependency. This is intentional: it lets you import them in a notebook or a script if you want.

## Local development

```bash
git clone https://github.com/hitensangani/seo-log-auditor.git
cd seo-log-auditor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest                    # all 31 tests should pass
seo-log-auditor           # launch the app
```

Streamlit hot-reloads on save, so edits to any file under `src/` are reflected immediately in the running app.

## Running tests

```bash
pytest -q                # quiet
pytest -v                # verbose
pytest tests/test_parsers.py  # one file
```

Add a test for any new parser format, any new analysis module, and any bug fix. Aim for the test to fail without your change and pass with it.

## Pull request guidelines

- **Branch name**: `feature/short-description`, `fix/short-description`, or `docs/short-description`.
- **Commit messages**: keep them imperative and short ("add cloudflare log parser", not "added cloudflare log parser"). Reference issues with `#123`.
- **One concern per PR**. Easier to review, easier to merge, easier to revert if needed.
- **Update [`CHANGELOG.md`](CHANGELOG.md)** under `## [Unreleased]` if your change is user-visible.
- **Run `pytest` locally** before pushing. CI will run it again on every push.
- **Add a screenshot** if you change the UI.

## Code style

- Format with [`ruff format`](https://docs.astral.sh/ruff/) — no separate Black setup.
- Type hints on public functions are encouraged, optional on internals.
- Prefer pandas vectorised operations over Python loops in the analysis modules — these run on millions of rows.
- Streamlit pages should stay thin. Heavy lifting belongs in `analysis/`, not in `pages/*.py`.

## What I'll likely *not* merge

- Adding heavy dependencies (more than a couple MB) without a clear reason — keep `pip install` fast.
- Hosted-mode features that require a backend service. The local-first model is a feature, not a limitation.
- Authentication, multi-tenancy, role-based access control. This is a single-user local tool by design.
- Cosmetic-only PRs that change formatting across the codebase without user-facing benefit.

If you're unsure whether a contribution fits, **open an issue first** describing the idea. Easier than rebuilding a rejected PR.

## Code of conduct

Be kind, be curious, assume good intent. If someone's PR confuses you, ask before assuming the worst. If a discussion starts to spiral, walk away and come back later.

I reserve the right to close issues / PRs that don't follow these basics — but in practice this almost never happens.

## Recognising contributors

Every merged PR gets:
- An entry in [`CHANGELOG.md`](CHANGELOG.md) crediting the contributor.
- A mention in the v-release GitHub Release notes.
- The author listed in the repo contributors graph (automatically).

## Questions?

Open a [Discussion](https://github.com/hitensangani/seo-log-auditor/discussions) or ping me via [hiten.eu](https://hiten.eu). I read everything.

— Hiten
