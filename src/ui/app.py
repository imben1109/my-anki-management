#!/usr/bin/env python3
"""Flet UI for Anki deck listing, export, and update workflows."""

from __future__ import annotations

import uuid
from pathlib import Path

import flet as ft

from src.ui.helpers import _HelpersMixin, parse_decks
from src.ui.copilot import _CopilotMixin
from src.ui.image_gen import _ImageGenMixin
from src.ui.decks import _DecksMixin


class AnkiManagerUI(_HelpersMixin, _CopilotMixin, _ImageGenMixin, _DecksMixin):
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "Anki Manager UI"
        self.page.padding = 16
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.window_width = 1180
        self.page.window_height = 760
        self.page.window_min_width = 900
        self.page.window_min_height = 620

        # Project root is 3 levels up from app/ui/app.py
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.export_script = self.base_dir / "src" / "api" / "export.py"
        self.update_script = self.base_dir / "src" / "api" / "update.py"

        self.decks: list[str] = []
        self.selected_deck: str | None = None
        self.selected_preview_path: Path | None = None
        self.preview_files: list[Path] = []
        self._md_cache: dict[Path, str] = {}
        self._preview_row_map: dict[Path, ft.Container] = {}
        self.preview_load_request = 0
        self.log_lines: list[str] = []
        self.copilot_log_lines: list[str] = []
        self.active_jobs = 0
        self.copilot_active_jobs = 0
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
        self.preview_search_field = ft.TextField(
            label="Search files",
            hint_text="Filter by name or content...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_preview_search,
            dense=True,
        )
        self.markdown_preview = ft.Markdown(
            value="",
            selectable=True,
            expand=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
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
        self.copilot_status_text = ft.Text(
            "Ready.", color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.copilot_progress_ring = ft.ProgressRing(
            width=16, height=16, visible=False
        )
        self.copilot_log_field = ft.TextField(
            value="",
            multiline=True,
            min_lines=8,
            max_lines=20,
            read_only=True,
            expand=True,
            text_style=ft.TextStyle(font_family="monospace", size=13),
        )
        self._copilot_dialog: ft.AlertDialog | None = None

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
            "Send",
            icon=ft.Icons.SEND,
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
                                "Generate image",
                                icon=ft.Icons.IMAGE,
                                on_click=self._generate_image_from_front,
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
                                        self.preview_search_field,
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
            controls=[export_card, update_card, logs_card],
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
        # Start on manage decks — preview hidden until user switches via hamburger menu
        self.preview_workspace.visible = False

        # Hamburger menu instead of button row
        app_bar = ft.AppBar(
            leading=ft.PopupMenuButton(
                icon=ft.Icons.MENU,
                items=[
                    ft.PopupMenuItem(
                        text="Manage notes",
                        icon=ft.Icons.DASHBOARD,
                        on_click=self.show_manage_workspace,
                    ),
                    ft.PopupMenuItem(
                        text="Markdown preview",
                        icon=ft.Icons.PREVIEW,
                        on_click=self.show_preview_workspace,
                    ),
                    ft.PopupMenuItem(
                        text="GitHub Copilot",
                        icon=ft.Icons.SMART_TOY,
                        on_click=self._open_copilot_dialog,
                    ),
                    ft.PopupMenuItem(
                        text="Generate image",
                        icon=ft.Icons.IMAGE,
                        on_click=self._open_image_gen_dialog,
                    ),
                ],
            ),
            title=ft.Text("Anki Manager", size=20, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        self.page.appbar = app_bar
        self.page.add(
            ft.Column(
                controls=[
                    self.manage_workspace,
                    self.preview_workspace,
                ],
                spacing=12,
                expand=True,
            )
        )



def main(page: ft.Page) -> None:
    AnkiManagerUI(page)


if __name__ == "__main__":
    ft.app(target=main)
