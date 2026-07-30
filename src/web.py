"""Entry point for the Anki Manager web application."""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flet as ft

from src.ui.app import main

IMAGE_PORT = 8551


def _start_image_server(export_dir: str) -> None:
    """Serve image files from the export directory on IMAGE_PORT."""

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=export_dir, **kwargs)

        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()

        def log_message(self, format, *args):
            pass  # suppress logs

    server = socketserver.TCPServer(("", IMAGE_PORT), _Handler)
    server.allow_reuse_address = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    export_dir = str(base_dir / "anki-export")
    _start_image_server(export_dir)
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
