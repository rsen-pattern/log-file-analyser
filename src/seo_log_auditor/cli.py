"""Console-script entry point.

Installed as ``seo-log-auditor`` via the ``[project.scripts]`` table in
``pyproject.toml``. Two subcommands:

* ``seo-log-auditor`` (no args) -- launches the Streamlit dashboard. This
  is the primary user flow.
* ``seo-log-auditor init-config`` -- writes a copy of the bundled example
  ``page_patterns.yaml`` into the user's current working directory so they
  can edit it and re-upload it via the sidebar.

The launch path uses :mod:`importlib.resources` so the bundled
``_app/app.py`` works whether the package is installed normally
(site-packages) or run from a wheel via ``uvx``.
"""

from __future__ import annotations

import argparse
import importlib.resources as resources
import shutil
import subprocess
import sys
from pathlib import Path


def _resource_path(*parts: str) -> Path:
    """Return an absolute path to a packaged resource.

    ``importlib.resources.files`` returns a ``Traversable`` that may live
    inside a zip; we cast through ``str`` so callers always get a real
    filesystem ``Path`` (Streamlit needs a real path for multipage
    discovery).
    """
    res = resources.files("seo_log_auditor").joinpath(*parts)
    return Path(str(res))


def _run_app(args: argparse.Namespace) -> int:
    app_path = _resource_path("_app", "app.py")
    if not app_path.is_file():
        sys.stderr.write(
            f"Cannot locate bundled Streamlit app at {app_path}.\n"
            "This is a packaging bug -- please file an issue.\n"
        )
        return 2

    cmd: list[str] = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
        "--server.maxUploadSize",
        str(args.max_upload_mb),
        "--browser.gatherUsageStats",
        "false",
        # ----- "Editorial Tech" theme (mirrors hiten.eu) -----
        "--theme.base",
        "dark",
        "--theme.primaryColor",
        "#b4ff39",
        "--theme.backgroundColor",
        "#09090b",
        "--theme.secondaryBackgroundColor",
        "#131318",
        "--theme.textColor",
        "#f5f5f7",
    ]
    if args.no_browser:
        cmd += ["--server.headless", "true"]

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


def _init_config(args: argparse.Namespace) -> int:
    src = _resource_path("_data", "page_patterns.example.yaml")
    dst = Path(args.dest).resolve()
    if dst.exists() and not args.force:
        sys.stderr.write(
            f"{dst} already exists. Pass --force to overwrite.\n"
        )
        return 1
    shutil.copyfile(src, dst)
    print(f"Wrote {dst}")
    print(
        "Edit it for your URL structure, then upload it via the "
        "'Page-pattern rules' field in the sidebar."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="seo-log-auditor",
        description=(
            "Audit Googlebot crawl behaviour from raw nginx access logs. "
            "Runs entirely on your machine."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    # `seo-log-auditor` with no subcommand launches the app. Implemented by
    # making the parser default to the `run` action when no subcommand is
    # given (handled below) but also exposing it as an explicit `run`
    # subcommand for clarity.
    p_run = sub.add_parser("run", help="Launch the dashboard (default).")
    p_run.add_argument("--port", type=int, default=8501)
    p_run.add_argument(
        "--max-upload-mb",
        type=int,
        default=300,
        help="Streamlit upload cap in MB. Default 300, enough for ~30 days of nginx Googlebot logs.",
    )
    p_run.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open a browser tab (useful when running over SSH).",
    )
    p_run.set_defaults(func=_run_app)

    p_init = sub.add_parser(
        "init-config",
        help="Drop a starter page_patterns.yaml in the current directory.",
    )
    p_init.add_argument(
        "--dest",
        default="page_patterns.yaml",
        help="Output path (default: ./page_patterns.yaml).",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if the destination already exists.",
    )
    p_init.set_defaults(func=_init_config)

    # Default to the `run` subcommand if the user didn't pick one. We have
    # to do this BEFORE argparse sees the args, because otherwise unknown
    # top-level flags like `--no-browser` make argparse exit with usage.
    raw = list(argv) if argv is not None else sys.argv[1:]
    known_subcommands = {"run", "init-config"}
    help_flags = {"-h", "--help"}
    needs_run_default = not raw or (
        raw[0] not in known_subcommands and raw[0] not in help_flags
    )
    if needs_run_default:
        raw = ["run", *raw]

    args = parser.parse_args(raw)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
