#!/usr/bin/env python3
"""Flet UI for Anki deck listing, update, and preview workflows.

Architecture:
  - src/api/       — Business logic (no Flet imports)
  - src/ui/components/ — Reusable Flet widgets
  - src/ui/views/  — Full-page compositions of components
  - app.py         — App shell that wires views together
"""

from __future__ import annotations

import uuid
from pathlib import Path

import flet as ft

from src.ui.helpers import _HelpersMixin
from src.ui.agent_chat import _AgentChatMixin
from src.ui.image_gen import _ImageGenMixin
from src.ui.decks import _DecksMixin
from src.ui.views.main_view import build_main_view
from src.ui.views.preview_view import build_preview_view


class AnkiManagerUI(_HelpersMixin, _AgentChatMixin, _ImageGenMixin, _DecksMixin):
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "Anki Manager UI"
        self.page.padding = 16
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.window_width = 1180
        self.page.window_height = 760
        self.page.window_min_width = 320
        self.page.window_min_height = 480
        self.page.on_resize = self._on_resize
        self._last_is_mobile: bool | None = None

        # Project root is 3 levels up from src/ui/app.py
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.export_script = self.base_dir / "src" / "api" / "export.py"
        self.update_script = self.base_dir / "src" / "api" / "update.py"

        # --- Application state ---
        self.decks: list[str] = []
        self.selected_deck: str | None = None
        self.selected_preview_path: Path | None = None
        self.preview_files: list[Path] = []
        self._deck_filter_active: str | None = None
        self._md_cache: dict[Path, str] = {}
        self._preview_row_map: dict[Path, ft.Container] = {}
        self.preview_load_request = 0
        self.log_lines: list[str] = []
        self.copilot_log_lines: list[str] = []
        self.active_jobs = 0
        self.copilot_active_jobs = 0
        self.copilot_session_id = str(uuid.uuid4())

        default_output = str(self.base_dir / "anki-export")

        # --- Shared control references used across views ---
        self.output_field = ft.TextField(
            label="Output folder", value=default_output, expand=True,
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
        self.editable_header = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.editable_front = ft.TextField(
            label="Front", multiline=True, min_lines=2, max_lines=8, expand=True,
            text_style=ft.TextStyle(size=14), border=ft.InputBorder.OUTLINE,
        )
        self.editable_back = ft.TextField(
            label="Back", multiline=True, min_lines=2, max_lines=12, expand=True,
            text_style=ft.TextStyle(size=14), border=ft.InputBorder.OUTLINE,
        )
        self.editable_image = ft.TextField(
            label="Image", hint_text="![image](images/filename.jpg)",
            multiline=True, min_lines=1, max_lines=3,
            text_style=ft.TextStyle(size=13), border=ft.InputBorder.OUTLINE,
        )
        self.editable_image_preview = ft.Image(
            src="", width=200, fit=ft.ImageFit.CONTAIN, visible=False,
        )
        self.editable_save_button = ft.ElevatedButton(
            "Save changes", icon=ft.Icons.SAVE,
            on_click=self._save_editable_preview, visible=False,
        )

        self.status_text = ft.Text("Ready.", color=ft.Colors.ON_SURFACE_VARIANT)
        self.progress_ring = ft.ProgressRing(width=16, height=16, visible=False)
        self.log_field = ft.TextField(
            value="", multiline=True, min_lines=16, max_lines=24,
            read_only=True, expand=True, text_size=13,
        )
        self.copilot_status_text = ft.Text(
            "Ready.", color=ft.Colors.ON_SURFACE_VARIANT, size=12,
        )
        self.copilot_progress_ring = ft.ProgressRing(width=16, height=16, visible=False)
        self.copilot_log_field = ft.TextField(
            value="", multiline=True, min_lines=8, max_lines=20,
            read_only=True, expand=True,
            text_style=ft.TextStyle(font_family="monospace", size=13),
        )
        self.deck_filter_dropdown = ft.Dropdown(
            label="Deck filter",
            hint_text="All decks",
            options=[ft.dropdown.Option("__all__", "All decks")],
            value="__all__",
            on_change=self._on_deck_filter_change,
            dense=True,
        )
        self._copilot_dialog: ft.AlertDialog | None = None

        # --- File pickers ---
        self.output_dir_picker = ft.FilePicker(on_result=self._handle_output_dir_picked)
        self.page.overlay.append(self.output_dir_picker)

        self._refresh_preview_files()
        self._build_ui()
        self.refresh_decks()

    # ------------------------------------------------------------------
    # UI construction (composed from views)
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Build the UI by composing views from src/ui/views/. Each view is a
        pure function that takes callbacks and control references — no more
        inline widget construction."""

        is_mobile = self.page.width < 768 if self.page.width else False
        self._last_is_mobile = is_mobile

        # Pre-create deck controls that the mixin methods need to update
        if not hasattr(self, "deck_list"):
            self.deck_list = ft.ListView(expand=True, spacing=8, padding=0)
        if not hasattr(self, "deck_count_text"):
            self.deck_count_text = ft.Text(
                f"Decks: {len(self.decks)}", color=ft.Colors.ON_SURFACE_VARIANT,
            )

        self.manage_workspace = build_main_view(
            is_mobile=is_mobile,
            decks=self.decks,
            selected_deck=self.selected_deck,
            deck_count=len(self.decks),
            deck_list_view=self.deck_list,
            deck_count_text=self.deck_count_text,
            on_refresh=self.refresh_decks,
            on_select_deck=self._select_deck,
            on_export_selected=self.export_selected_deck,
            output_field=self.output_field,
            on_choose_output_folder=self.choose_output_folder,
            on_update=self.update_notes,
            log_field=self.log_field,
            status_text=self.status_text,
            progress_ring=self.progress_ring,
        )

        self.preview_workspace = build_preview_view(
            is_mobile=is_mobile,
            preview_files=self.preview_files,
            selected_preview_path=self.selected_preview_path,
            output_dir=self.output_field.value or "",
            file_list_view=self.preview_file_list,
            deck_filter_dropdown=self.deck_filter_dropdown,
            preview_search_value=self.preview_search_field.value or "",
            preview_search_field=self.preview_search_field,
            on_select_file=self._preview_markdown_file,
            on_search_files=self._on_preview_search,
            on_refresh_files=self._refresh_preview_files,
            preview_path_text=self.preview_path_text,
            editable_header=self.editable_header,
            editable_front=self.editable_front,
            editable_back=self.editable_back,
            editable_image=self.editable_image,
            editable_image_preview=self.editable_image_preview,
            editable_save_button=self.editable_save_button,
            on_save_editable=self._save_editable_preview,
            on_batch_gen=self._batch_generate_images,
            on_gen_description=self._generate_image_description,
            on_gen_image=self._generate_image_from_front,
            on_update_current=self.update_current_note,
            on_refresh_list=self.refresh_preview_files,
            copilot_status_text=self.copilot_status_text,
            copilot_progress_ring=self.copilot_progress_ring,
        )
        self.preview_workspace.visible = False

        # --- App bar with hamburger menu ---
        app_bar = ft.AppBar(
            leading=ft.PopupMenuButton(
                icon=ft.Icons.MENU,
                items=[
                    ft.PopupMenuItem(
                        text="Manage notes", icon=ft.Icons.DASHBOARD,
                        on_click=self.show_manage_workspace,
                    ),
                    ft.PopupMenuItem(
                        text="Markdown preview", icon=ft.Icons.PREVIEW,
                        on_click=self.show_preview_workspace,
                    ),
                    ft.PopupMenuItem(
                        text="AI Chat", icon=ft.Icons.SMART_TOY,
                        on_click=self._open_agent_chat_dialog,
                    ),
                    ft.PopupMenuItem(
                        text="Generate image", icon=ft.Icons.IMAGE,
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
                controls=[self.manage_workspace, self.preview_workspace],
                spacing=12,
                expand=True,
            )
        )

    def _on_resize(self, _event: ft.ControlEvent) -> None:
        """Rebuild UI when crossing the mobile/desktop breakpoint."""
        is_mobile = self.page.width < 768 if self.page.width else False
        if is_mobile == self._last_is_mobile:
            return
        self.page.controls.clear()
        self._build_ui()
        self.page.update()



def main(page: ft.Page) -> None:
    AnkiManagerUI(page)


if __name__ == "__main__":
    ft.app(target=main)
