"""Helper utilities for the Anki Manager UI — logging, status, threading."""

from __future__ import annotations

import shlex
import subprocess
import threading
from pathlib import Path
from typing import Callable

import flet as ft

from src.api.parsing import parse_decks  # re-exported for convenience



class _HelpersMixin:
    """Mixin providing logging, status, and threading helpers."""

    def _existing_directory(self, *raw_values: str | None) -> str:
        for raw_value in raw_values:
            value = (raw_value or "").strip()
            if not value:
                continue
            path = Path(value)
            if path.exists() and path.is_dir():
                return str(path)
            if path.exists() and path.is_file():
                return str(path.parent)
        return str(self.base_dir)


    def _set_status(self, message: str, color: str = ft.Colors.ON_SURFACE_VARIANT) -> None:
        self.status_text.value = message
        self.status_text.color = color
        self.page.update()


    def _append_log(self, text: str) -> None:
        self.log_lines.append(text)
        self.log_field.value = "\n".join(self.log_lines)
        self.page.update()


    def _set_copilot_status(
        self, message: str, color: str = ft.Colors.ON_SURFACE_VARIANT
    ) -> None:
        self.copilot_status_text.value = message
        self.copilot_status_text.color = color
        self.page.update()


    def _append_copilot_log(self, text: str) -> None:
        self.copilot_log_lines.append(text)
        self.copilot_log_field.value = "\n".join(self.copilot_log_lines)
        self.page.update()


    def _set_busy(self, busy: bool) -> None:
        self.active_jobs += 1 if busy else -1
        if self.active_jobs < 0:
            self.active_jobs = 0
        self.progress_ring.visible = self.active_jobs > 0
        self.page.update()


    def _set_copilot_busy(self, busy: bool) -> None:
        self.copilot_active_jobs += 1 if busy else -1
        if self.copilot_active_jobs < 0:
            self.copilot_active_jobs = 0
        self.copilot_progress_ring.visible = self.copilot_active_jobs > 0
        self.page.update()


    def _report_issue(self, message: str) -> None:
        self._append_log(message)
        self._set_status(message, ft.Colors.RED_700)


    def _report_copilot_issue(self, message: str) -> None:
        self._append_copilot_log(message)
        self._set_copilot_status(message, ft.Colors.RED_700)


    def _run_in_thread(
        self,
        title: str,
        argv: list[str],
        on_success: Callable[[], None] | None = None,
        append_log: Callable[[str], None] | None = None,
        set_status: Callable[[str, str], None] | None = None,
        set_busy: Callable[[bool], None] | None = None,
        report_issue: Callable[[str], None] | None = None,
    ) -> None:
        append_log = append_log or self._append_log
        set_status = set_status or self._set_status
        set_busy = set_busy or self._set_busy
        report_issue = report_issue or self._report_issue
        append_log(f"$ {shlex.join(argv)}")
        set_status(f"{title} running...", ft.Colors.BLUE_700)
        set_busy(True)

        def worker() -> None:
            try:
                result = subprocess.run(
                    argv,
                    cwd=str(self.base_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError as exc:
                report_issue(f"{title} failed: {exc}")
                set_busy(False)
                return
            except Exception as exc:
                report_issue(f"{title} failed unexpectedly: {exc}")
                set_busy(False)
                return

            if result.stdout.strip():
                append_log(result.stdout.rstrip())
            if result.stderr.strip():
                append_log(result.stderr.rstrip())

            if result.returncode == 0:
                append_log(f"{title} completed successfully.")
                set_status(f"{title} completed successfully.", ft.Colors.GREEN_700)
                if on_success:
                    on_success()
            else:
                append_log(f"{title} failed with exit code {result.returncode}.")
                set_status(
                    f"{title} failed with exit code {result.returncode}.",
                    ft.Colors.RED_700,
                )

            set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

