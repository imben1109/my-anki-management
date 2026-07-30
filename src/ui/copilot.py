"""Copilot CLI dialog — chat with GitHub Copilot inside a popup."""

from __future__ import annotations

import subprocess
import threading
import uuid

import flet as ft


class _CopilotMixin:
    """Mixin providing the Copilot CLI dialog and inline copilot methods."""

    def _open_copilot_dialog(self, _event: ft.ControlEvent | None = None) -> None:
        """Open GitHub Copilot as a popup dialog."""
        dialog_prompt = ft.TextField(
            label="Ask GitHub Copilot",
            hint_text="e.g. list all decks, create a study plan...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            on_submit=lambda e: self._send_copilot_dialog(dialog_prompt, dialog_output, dialog_status, dialog_ring),
        )
        dialog_output = ft.TextField(
            value="\n".join(self.copilot_log_lines),
            read_only=True,
            multiline=True,
            min_lines=12,
            max_lines=20,
            expand=True,
            text_style=ft.TextStyle(font_family="monospace", size=13),
        )
        dialog_status = ft.Text("Ready.", color=ft.Colors.ON_SURFACE_VARIANT)
        dialog_ring = ft.ProgressRing(width=16, height=16, visible=False)

        def send_from_dialog(e: ft.ControlEvent) -> None:
            self._send_copilot_dialog(dialog_prompt, dialog_output, dialog_status, dialog_ring)

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Text("GitHub Copilot CLI", size=20, weight=ft.FontWeight.BOLD),
                    ft.TextButton(
                        "New conversation",
                        on_click=lambda e: self._reset_copilot_dialog(dialog_output, dialog_status),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Column(
                controls=[
                    dialog_prompt,
                    ft.Row(
                        controls=[
                            ft.FilledButton("Send", icon=ft.Icons.SEND, on_click=send_from_dialog),
                            ft.Row(
                                controls=[dialog_ring, dialog_status],
                                spacing=8,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    dialog_output,
                ],
                spacing=12,
                width=700,
                height=550,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
            on_dismiss=lambda e: self._on_copilot_dialog_dismiss(dialog_output),
        )

        self._copilot_dialog = dialog
        self.page.open(dialog)

    def _send_copilot_dialog(
        self,
        prompt_field: ft.TextField,
        output_field: ft.TextField,
        status_text: ft.Text,
        progress_ring: ft.ProgressRing,
    ) -> None:
        """Send a prompt from the copilot dialog."""
        prompt = prompt_field.value.strip()
        if not prompt:
            status_text.value = "Enter a prompt first."
            status_text.color = ft.Colors.RED_700
            self.page.update()
            return

        cmd = [
            "copilot",
            "--prompt", prompt,
            "--session-id", self.copilot_session_id,
            "--allow-all",
            "--silent",
            "--no-color",
        ]
        prompt_field.value = ""
        status_text.value = "Processing..."
        status_text.color = ft.Colors.BLUE_700
        progress_ring.visible = True
        self.page.update()

        def _run() -> None:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(self.base_dir),
                    timeout=300,
                )
                output = result.stdout.strip() or result.stderr.strip() or "(no output)"
                self.copilot_log_lines.append(f"> {prompt}")
                self.copilot_log_lines.append(output)
                self.copilot_log_lines.append("")
                output_field.value = "\n".join(self.copilot_log_lines)
                status_text.value = "Done."
                status_text.color = ft.Colors.GREEN_700
            except subprocess.TimeoutExpired:
                self.copilot_log_lines.append(f"> {prompt}")
                self.copilot_log_lines.append("(timed out after 5 minutes)")
                self.copilot_log_lines.append("")
                output_field.value = "\n".join(self.copilot_log_lines)
                status_text.value = "Timed out."
                status_text.color = ft.Colors.RED_700
            except Exception as exc:
                self.copilot_log_lines.append(f"> {prompt}")
                self.copilot_log_lines.append(f"Error: {exc}")
                self.copilot_log_lines.append("")
                output_field.value = "\n".join(self.copilot_log_lines)
                status_text.value = f"Error: {exc}"
                status_text.color = ft.Colors.RED_700
            finally:
                progress_ring.visible = False
                self.page.update()

        threading.Thread(target=_run, daemon=True).start()

    def _reset_copilot_dialog(
        self, output_field: ft.TextField, status_text: ft.Text
    ) -> None:
        """Reset the copilot conversation from the dialog."""
        self.copilot_session_id = str(uuid.uuid4())
        self.copilot_log_lines = ["Started a new GitHub Copilot conversation.", ""]
        output_field.value = "\n".join(self.copilot_log_lines)
        status_text.value = "New conversation started."
        status_text.color = ft.Colors.GREEN_700
        self.page.update()

    def _on_copilot_dialog_dismiss(self, output_field: ft.TextField) -> None:
        """Sync dialog state back to main copilot log."""
        self._copilot_dialog = None
        self.copilot_log_field.value = output_field.value

    def reset_copilot_conversation(
        self, _event: ft.ControlEvent | None = None
    ) -> None:
        self.copilot_session_id = str(uuid.uuid4())
        self.copilot_prompt_field.value = ""
        self._append_copilot_log("Started a new GitHub Copilot conversation.")
        self._set_copilot_status(
            "Started a new GitHub Copilot conversation.", ft.Colors.GREEN_700
        )

    def ask_copilot(self, _event: ft.ControlEvent | None = None) -> None:
        prompt = self.copilot_prompt_field.value.strip()
        if not prompt:
            self._report_copilot_issue("Enter a prompt for GitHub Copilot first.")
            return

        cmd = [
            "copilot",
            "--prompt",
            prompt,
            "--session-id",
            self.copilot_session_id,
            "--allow-all",
            "--silent",
            "--no-color",
        ]
        self.copilot_prompt_field.value = ""
        self.page.update()
        self._run_in_thread(
            "GitHub Copilot",
            cmd,
            append_log=self._append_copilot_log,
            set_status=self._set_copilot_status,
            set_busy=self._set_copilot_busy,
            report_issue=self._report_copilot_issue,
        )
