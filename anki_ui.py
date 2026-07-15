#!/usr/bin/env python3
"""Flet UI for Anki deck listing, export, and update workflows."""

from __future__ import annotations

import shlex
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Callable

import flet as ft


MACOS_FOLDER_PICKER_SCRIPT = """
on run argv
    set promptText to item 1 of argv
    set startFolder to POSIX file (item 2 of argv) as alias
    set pickedFolder to choose folder with prompt promptText default location startFolder
    return POSIX path of pickedFolder
end run
"""


def parse_decks(apy_info: str) -> list[str]:
    decks: list[str] = []
    in_decks = False
    for raw_line in apy_info.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("Decks:"):
            in_decks = True
            continue
        if in_decks and line.startswith("Model"):
            break
        if in_decks and line.startswith("  - "):
            decks.append(line.replace("  - ", "", 1).strip())
    return decks


class AnkiManagerUI:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "Anki Manager UI"
        self.page.padding = 16
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.window_width = 1180
        self.page.window_height = 760
        self.page.window_min_width = 900
        self.page.window_min_height = 620

        self.base_dir = Path(__file__).resolve().parent
        self.export_script = self.base_dir / "export_anki_notes.py"
        self.update_script = self.base_dir / "update_anki_notes.py"

        self.decks: list[str] = []
        self.selected_deck: str | None = None
        self.selected_preview_path: Path | None = None
        self.preview_files: list[Path] = []
        self.preview_load_request = 0
        self.log_lines: list[str] = []
        self.active_jobs = 0
        self.copilot_session_id = str(uuid.uuid4())

        default_output = str(self.base_dir / "anki-export")

        self.output_field = ft.TextField(
            label="Output folder",
            value=default_output,
            expand=True,
        )
        self.query_field = ft.TextField(
            label="Custom query",
            hint_text='Example: deck:"My Deck"',
            expand=True,
        )
        self.update_target_field = ft.TextField(
            label="Update target (.md file or directory)",
            value=default_output,
            expand=True,
        )
        self.preview_path_text = ft.Text(
            "Select an exported Markdown file to preview it.",
            color=ft.Colors.ON_SURFACE_VARIANT,
            selectable=True,
        )
        self.preview_file_list = ft.ListView(expand=True, spacing=2, padding=0)
        self.markdown_preview = ft.Markdown(
            value="",
            selectable=True,
            expand=True,
            shrink_wrap=False,
            fit_content=False,
        )
        self.copilot_prompt_field = ft.TextField(
            label="Ask GitHub Copilot",
            hint_text="Ask about this Anki collection or request a change in this project.",
            multiline=True,
            min_lines=3,
            max_lines=6,
            expand=True,
        )

        self.status_text = ft.Text("Ready.", color=ft.Colors.ON_SURFACE_VARIANT)
        self.progress_ring = ft.ProgressRing(width=16, height=16, visible=False)
        self.deck_count_text = ft.Text("Decks: 0", color=ft.Colors.ON_SURFACE_VARIANT)
        self.deck_list = ft.ListView(expand=True, spacing=8, padding=0)
        self.log_field = ft.TextField(
            value="",
            multiline=True,
            min_lines=16,
            max_lines=24,
            read_only=True,
            expand=True,
            text_size=13,
        )

        self.refresh_button = ft.ElevatedButton("Refresh decks", on_click=self.refresh_decks)
        self.export_deck_button = ft.ElevatedButton(
            "Export selected deck",
            on_click=self.export_selected_deck,
        )
        self.export_query_button = ft.FilledButton(
            "Export query",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.export_custom_query,
        )
        self.update_button = ft.FilledButton(
            "Update notes",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self.update_notes,
        )
        self.copilot_button = ft.FilledButton(
            "Send to Copilot",
            icon=ft.Icons.SMART_TOY,
            on_click=self.ask_copilot,
        )

        self.output_dir_picker = ft.FilePicker(on_result=self._handle_output_dir_picked)
        self.update_dir_picker = ft.FilePicker(on_result=self._handle_update_dir_picked)
        self.update_file_picker = ft.FilePicker(on_result=self._handle_update_file_picked)
        self.page.overlay.append(self.output_dir_picker)
        self.page.overlay.append(self.update_dir_picker)
        self.page.overlay.append(self.update_file_picker)

        self._build_ui()
        self._refresh_preview_files()
        self.refresh_decks()

    def _build_ui(self) -> None:
        left_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Decks", size=20, weight=ft.FontWeight.BOLD),
                            self.deck_count_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[self.refresh_button, self.export_deck_button],
                        wrap=True,
                    ),
                    ft.Container(content=self.deck_list, expand=True),
                ],
                spacing=12,
                expand=True,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
            expand=1,
        )

        export_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Export", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            self.output_field,
                            ft.OutlinedButton(
                                "Choose folder",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=self.choose_output_folder,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Row(
                        controls=[self.query_field, self.export_query_button],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=12,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
        )

        update_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Update", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            self.update_target_field,
                            ft.OutlinedButton(
                                "Pick folder",
                                icon=ft.Icons.FOLDER,
                                on_click=self.choose_update_folder,
                            ),
                            ft.OutlinedButton(
                                "Pick file",
                                icon=ft.Icons.DESCRIPTION,
                                on_click=self.choose_update_file,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Row(controls=[self.update_button], wrap=True),
                ],
                spacing=12,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
        )

        preview_workspace = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Markdown preview",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.OutlinedButton(
                                "Refresh list",
                                icon=ft.Icons.REFRESH,
                                on_click=self.refresh_preview_files,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Exported Markdown files",
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        self.preview_file_list,
                                    ],
                                    spacing=8,
                                    expand=True,
                                ),
                                width=300,
                                padding=12,
                                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                                border_radius=10,
                                expand=False,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        self.preview_path_text,
                                        ft.Container(
                                            content=ft.Column(
                                                controls=[self.markdown_preview],
                                                scroll=ft.ScrollMode.AUTO,
                                                expand=True,
                                            ),
                                            padding=ft.padding.only(right=12),
                                            expand=True,
                                        ),
                                    ],
                                    spacing=8,
                                    expand=True,
                                ),
                                padding=12,
                                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                                border_radius=10,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        expand=True,
                    ),
                ],
                spacing=12,
                expand=True,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
            expand=True,
        )

        copilot_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "GitHub Copilot CLI",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.TextButton(
                                "New conversation",
                                on_click=self.reset_copilot_conversation,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.copilot_prompt_field,
                    ft.Row(
                        controls=[
                            self.copilot_button,
                            ft.Text(
                                "Responses appear in Status & logs.",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
        )

        logs_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Status & logs", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[self.progress_ring, self.status_text],
                                spacing=10,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.log_field,
                ],
                spacing=12,
                expand=True,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
            expand=True,
        )

        right_panel = ft.Column(
            controls=[export_card, update_card, copilot_card, logs_card],
            spacing=12,
            expand=2,
        )

        manage_workspace = ft.Row(
            controls=[left_panel, right_panel],
            spacing=16,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        self.manage_workspace = manage_workspace
        self.preview_workspace = preview_workspace
        self.preview_workspace.visible = False
        workspace_navigation = ft.Row(
            controls=[
                ft.FilledButton(
                    "Manage notes",
                    icon=ft.Icons.DASHBOARD,
                    on_click=self.show_manage_workspace,
                ),
                ft.OutlinedButton(
                    "Markdown preview",
                    icon=ft.Icons.PREVIEW,
                    on_click=self.show_preview_workspace,
                ),
            ],
            spacing=8,
        )
        self.page.add(
            ft.Column(
                controls=[
                    workspace_navigation,
                    self.manage_workspace,
                    self.preview_workspace,
                ],
                spacing=12,
                expand=True,
            )
        )

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

    def _set_busy(self, busy: bool) -> None:
        self.active_jobs += 1 if busy else -1
        if self.active_jobs < 0:
            self.active_jobs = 0
        self.progress_ring.visible = self.active_jobs > 0
        self.page.update()

    def _report_issue(self, message: str) -> None:
        self._append_log(message)
        self._set_status(message, ft.Colors.RED_700)

    def _run_in_thread(
        self,
        title: str,
        argv: list[str],
        on_success: Callable[[], None] | None = None,
    ) -> None:
        self._append_log(f"$ {shlex.join(argv)}")
        self._set_status(f"{title} running...", ft.Colors.BLUE_700)
        self._set_busy(True)

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
                self._report_issue(f"{title} failed: {exc}")
                self._set_busy(False)
                return
            except Exception as exc:
                self._report_issue(f"{title} failed unexpectedly: {exc}")
                self._set_busy(False)
                return

            if result.stdout.strip():
                self._append_log(result.stdout.rstrip())
            if result.stderr.strip():
                self._append_log(result.stderr.rstrip())

            if result.returncode == 0:
                self._append_log(f"{title} completed successfully.")
                self._set_status(f"{title} completed successfully.", ft.Colors.GREEN_700)
                if on_success:
                    on_success()
            else:
                self._append_log(f"{title} failed with exit code {result.returncode}.")
                self._set_status(
                    f"{title} failed with exit code {result.returncode}.",
                    ft.Colors.RED_700,
                )

            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_output_dir_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.path:
            return
        self._set_output_directory(event.path)

    def _set_output_directory(self, path: str) -> None:
        self.output_field.value = path
        if not self.update_target_field.value.strip():
            self.update_target_field.value = path
        self._refresh_preview_files()

    def _handle_update_dir_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.path:
            return
        self._set_update_directory(event.path)

    def _set_update_directory(self, path: str) -> None:
        self.update_target_field.value = path
        self.page.update()

    def _handle_update_file_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            return
        self.update_target_field.value = event.files[0].path
        self.page.update()

    def choose_output_folder(self, _event: ft.ControlEvent) -> None:
        initial_directory = self._existing_directory(self.output_field.value)
        if sys.platform == "darwin":
            self._choose_macos_folder(
                "Choose export folder",
                initial_directory,
                self._set_output_directory,
            )
            return
        self.output_dir_picker.get_directory_path(
            dialog_title="Choose export folder",
            initial_directory=initial_directory,
        )

    def choose_update_folder(self, _event: ft.ControlEvent) -> None:
        initial_directory = self._existing_directory(
            self.update_target_field.value,
            self.output_field.value,
        )
        if sys.platform == "darwin":
            self._choose_macos_folder(
                "Choose notes folder to update",
                initial_directory,
                self._set_update_directory,
            )
            return
        self.update_dir_picker.get_directory_path(
            dialog_title="Choose notes folder to update",
            initial_directory=initial_directory,
        )

    def _choose_macos_folder(
        self,
        prompt: str,
        initial_directory: str,
        on_selected: Callable[[str], None],
    ) -> None:
        self._set_status("Opening macOS folder picker...", ft.Colors.BLUE_700)
        self._set_busy(True)

        def worker() -> None:
            try:
                result = subprocess.run(
                    [
                        "osascript",
                        "-e",
                        MACOS_FOLDER_PICKER_SCRIPT,
                        "--",
                        prompt,
                        initial_directory,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                self._report_issue("Could not open the macOS folder picker: osascript is missing.")
                self._set_busy(False)
                return
            except OSError as exc:
                self._report_issue(f"Could not open the macOS folder picker: {exc}")
                self._set_busy(False)
                return

            if result.returncode != 0:
                if "-128" in result.stderr:
                    self._set_status("Folder selection canceled.")
                else:
                    detail = result.stderr.strip() or "unknown error"
                    self._report_issue(f"Could not open the macOS folder picker: {detail}")
                self._set_busy(False)
                return

            selected_path = result.stdout.strip()
            if not selected_path or not Path(selected_path).is_dir():
                self._report_issue("The macOS folder picker returned an invalid folder.")
                self._set_busy(False)
                return

            on_selected(selected_path)
            self._set_status("Folder selected.", ft.Colors.GREEN_700)
            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def choose_update_file(self, _event: ft.ControlEvent) -> None:
        self.update_file_picker.pick_files(
            dialog_title="Choose a Markdown note to update",
            allow_multiple=False,
            allowed_extensions=["md"],
            file_type=ft.FilePickerFileType.CUSTOM,
            initial_directory=self._existing_directory(
                self.update_target_field.value,
                self.output_field.value,
            ),
        )

    def refresh_preview_files(self, _event: ft.ControlEvent | None = None) -> None:
        self._refresh_preview_files()

    def show_manage_workspace(self, _event: ft.ControlEvent | None = None) -> None:
        self.manage_workspace.visible = True
        self.preview_workspace.visible = False
        self.page.update()

    def show_preview_workspace(self, _event: ft.ControlEvent | None = None) -> None:
        self.manage_workspace.visible = False
        self.preview_workspace.visible = True
        self.page.update()

    def _refresh_preview_files(self) -> None:
        output_path = Path(self.output_field.value.strip())
        files: list[tuple[float, Path]] = []
        if output_path.is_dir():
            try:
                for path in output_path.rglob("*.md"):
                    try:
                        files.append((path.stat().st_mtime, path))
                    except OSError:
                        continue
            except OSError as exc:
                self._report_issue(f"Could not list exported Markdown files: {exc}")
                return

        self.preview_files = [
            path for _, path in sorted(files, key=lambda item: item[0], reverse=True)
        ]
        if self.selected_preview_path not in self.preview_files:
            self.selected_preview_path = None
        self._render_preview_file_list()

    def _render_preview_file_list(self) -> None:
        controls: list[ft.Control] = []
        output_path = Path(self.output_field.value.strip())
        for path in self.preview_files:
            is_selected = path == self.selected_preview_path
            try:
                display_path = str(path.relative_to(output_path))
            except ValueError:
                display_path = str(path)
            controls.append(
                ft.Container(
                    content=ft.ListTile(
                        title=ft.Text(
                            display_path,
                            weight=ft.FontWeight.W_600 if is_selected else None,
                        ),
                        dense=True,
                    ),
                    bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.SURFACE,
                    border=ft.border.all(
                        1,
                        ft.Colors.BLUE_300 if is_selected else ft.Colors.OUTLINE_VARIANT,
                    ),
                    border_radius=8,
                    on_click=lambda _, selected=path: self._preview_markdown_file(selected),
                )
            )

        if not controls:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        "No exported Markdown files found.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.padding.only(top=8),
                )
            )

        self.preview_file_list.controls = controls
        self.page.update()

    def _preview_markdown_file(self, path: Path) -> None:
        self.selected_preview_path = path
        self.preview_load_request += 1
        request = self.preview_load_request
        self.preview_path_text.value = str(path)
        self.show_preview_workspace()
        self._render_preview_file_list()
        self._set_status(f"Loading {path.name}...", ft.Colors.BLUE_700)

        def worker() -> None:
            try:
                markdown = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                if request == self.preview_load_request:
                    self._report_issue(f"Could not preview Markdown file {path}: {exc}")
                return

            if request != self.preview_load_request:
                return

            self.markdown_preview.value = markdown
            self._append_log(f"Previewing Markdown file: {path}")
            self._set_status(f"Previewing {path.name}.", ft.Colors.GREEN_700)

        threading.Thread(target=worker, daemon=True).start()

    def _render_decks(self) -> None:
        deck_controls: list[ft.Control] = []
        for deck_name in self.decks:
            is_selected = deck_name == self.selected_deck
            deck_controls.append(
                ft.Container(
                    content=ft.ListTile(
                        title=ft.Text(
                            deck_name,
                            weight=ft.FontWeight.W_600 if is_selected else None,
                        ),
                        dense=True,
                    ),
                    bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.SURFACE,
                    border=ft.border.all(
                        1,
                        ft.Colors.BLUE_300 if is_selected else ft.Colors.OUTLINE_VARIANT,
                    ),
                    border_radius=10,
                    on_click=lambda _, selected=deck_name: self._select_deck(selected),
                )
            )

        if not deck_controls:
            deck_controls.append(
                ft.Container(
                    content=ft.Text(
                        "No decks loaded yet.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.padding.only(top=8),
                )
            )

        self.deck_list.controls = deck_controls
        self.deck_count_text.value = f"Decks: {len(self.decks)}"
        self.page.update()

    def _select_deck(self, deck_name: str) -> None:
        self.selected_deck = deck_name
        self._render_decks()

    def refresh_decks(self, _event: ft.ControlEvent | None = None) -> None:
        previous_deck = self.selected_deck
        self._append_log("$ apy info")
        self._set_status("Loading decks...", ft.Colors.BLUE_700)
        self._set_busy(True)

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["apy", "info"],
                    cwd=str(self.base_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                self._report_issue("Failed to load decks: could not find 'apy' on PATH.")
                self._set_busy(False)
                return
            except Exception as exc:
                self._report_issue(f"Failed to load decks: {exc}")
                self._set_busy(False)
                return

            if result.stdout.strip():
                self._append_log(result.stdout.rstrip())
            if result.stderr.strip():
                self._append_log(result.stderr.rstrip())

            if result.returncode != 0:
                self._append_log(f"Deck refresh failed with exit code {result.returncode}.")
                self._set_status(
                    f"Deck refresh failed with exit code {result.returncode}.",
                    ft.Colors.RED_700,
                )
                self._set_busy(False)
                return

            decks = parse_decks(result.stdout)
            self.decks = decks
            if previous_deck in decks:
                self.selected_deck = previous_deck
            elif self.selected_deck in decks:
                pass
            else:
                self.selected_deck = decks[0] if decks else None
            self._render_decks()
            self._append_log(f"Loaded {len(decks)} deck(s).")
            self._set_status(f"Loaded {len(decks)} deck(s).", ft.Colors.GREEN_700)
            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_scripts(self) -> bool:
        missing = [
            str(path.name)
            for path in (self.export_script, self.update_script)
            if not path.exists()
        ]
        if missing:
            self._report_issue(
                "Missing script(s): "
                + ", ".join(missing)
                + ". Expected them next to anki_ui.py."
            )
            return False
        return True

    def _deck_query(self, deck_name: str) -> str:
        escaped = deck_name.replace('"', r"\"")
        return f'deck:"{escaped}"'

    def export_selected_deck(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return
        if not self.selected_deck:
            self._report_issue("No deck selected. Select a deck first.")
            return

        query = self._deck_query(self.selected_deck)
        self.query_field.value = query
        self.page.update()
        self._run_export(query)

    def export_custom_query(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return

        query = self.query_field.value.strip()
        if not query:
            self._report_issue("Missing query. Enter an Anki query first.")
            return

        self._run_export(query)

    def _run_export(self, query: str) -> None:
        output_dir = self.output_field.value.strip()
        if not output_dir:
            self._report_issue("Missing output folder. Choose an output folder first.")
            return

        output_path = Path(output_dir)
        existing_files = set(output_path.rglob("*.md")) if output_path.exists() else set()
        cmd = [sys.executable, str(self.export_script), query, output_dir]

        def on_success() -> None:
            if not self.update_target_field.value.strip():
                self.update_target_field.value = output_dir
            exported_files = set(output_path.rglob("*.md")) - existing_files
            self._refresh_preview_files()
            if exported_files:
                newest_file = max(exported_files, key=lambda path: path.stat().st_mtime)
                self._preview_markdown_file(newest_file)
            else:
                self.page.update()

        self._run_in_thread("Export", cmd, on_success=on_success)

    def update_notes(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return

        target = self.update_target_field.value.strip()
        if not target:
            self._report_issue(
                "Missing target. Choose a markdown file or directory to update."
            )
            return

        target_path = Path(target)
        if not target_path.exists():
            self._report_issue(f"Target path does not exist: {target}")
            return

        cmd = [sys.executable, str(self.update_script), str(target_path)]
        self._run_in_thread("Update", cmd)

    def reset_copilot_conversation(
        self, _event: ft.ControlEvent | None = None
    ) -> None:
        self.copilot_session_id = str(uuid.uuid4())
        self.copilot_prompt_field.value = ""
        self._append_log("Started a new GitHub Copilot conversation.")
        self._set_status("Started a new GitHub Copilot conversation.", ft.Colors.GREEN_700)

    def ask_copilot(self, _event: ft.ControlEvent | None = None) -> None:
        prompt = self.copilot_prompt_field.value.strip()
        if not prompt:
            self._report_issue("Enter a prompt for GitHub Copilot first.")
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
        self._run_in_thread("GitHub Copilot", cmd)


def main(page: ft.Page) -> None:
    AnkiManagerUI(page)


if __name__ == "__main__":
    ft.app(target=main)
