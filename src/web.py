"""Entry point for the Anki Manager web application."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flet as ft

from src.ui.app import main


if __name__ == "__main__":
    ft.app(target=main, port=8550)
