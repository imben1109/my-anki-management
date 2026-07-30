"""Entry point for the Anki Manager desktop application."""

from __future__ import annotations

import flet as ft

from src.ui.app import main


if __name__ == "__main__":
    ft.app(target=main)
