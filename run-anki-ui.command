#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run anki_ui.py." >&2
  exit 1
fi

if ! python3 -c "import flet" >/dev/null 2>&1; then
  if [ ! -f requirements.txt ]; then
    echo "requirements.txt was not found next to run-anki-ui.command." >&2
    exit 1
  fi

  echo "Installing desktop UI dependencies from requirements.txt..." >&2
  if ! python3 -m pip install -r requirements.txt; then
    echo "Failed to install requirements.txt for anki_ui.py." >&2
    exit 1
  fi
fi

exec python3 anki_ui.py
