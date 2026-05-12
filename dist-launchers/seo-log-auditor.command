#!/usr/bin/env bash
# seo-log-auditor launcher (macOS)
#
# Double-click this file in Finder. It will:
#   1. Install `uv` (~30 MB, one-time) if you don't already have it.
#   2. Run `uvx seo-log-auditor`, which downloads and launches the app.
#   3. Open http://localhost:8501 in your browser.
#
# The Terminal window stays open so you can close the app cleanly with
# Ctrl-C. To uninstall later: `uv tool uninstall seo-log-auditor`.

set -e

echo "==> seo-log-auditor launcher"
echo

if ! command -v uv >/dev/null 2>&1; then
  echo "==> 'uv' not found. Installing it now (one-time, no admin password needed)."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # The installer drops uv into ~/.local/bin or ~/.cargo/bin; make sure
  # it's on PATH for this shell.
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

  if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "ERROR: uv was installed but isn't on PATH."
    echo "Open a new Terminal window and run this launcher again."
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
  fi
fi

echo "==> Launching seo-log-auditor (this may take a minute on first run)..."
echo "    A browser tab will open at http://localhost:8501."
echo "    Press Ctrl-C in this window to stop the app."
echo

uvx seo-log-auditor

echo
read -n 1 -s -r -p "App stopped. Press any key to close this window..."
