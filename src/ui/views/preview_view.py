"""Preview workspace view — file browser + editable preview editor.

Composes file_browser, preview_editor, and toolbar components.
"""

from __future__ import annotations

from typing import Callable

import flet as ft
from pathlib import Path

from src.ui.components.file_browser import build_file_browser
from src.ui.components.preview_editor import build_preview_editor


def build_preview_view(
    # --- File browser ---
    preview_files: list[Path],
    selected_preview_path: Path | None,
    output_dir: str,
    preview_search_field: ft.TextField,
    file_list_view: ft.ListView,
    deck_filter_dropdown: ft.Dropdown,
    preview_search_value: str,
    on_select_file: Callable[[Path], None],
    on_search_files: Callable[[ft.ControlEvent], None],
    on_refresh_files: Callable[[], None],
    # --- Preview editor ---
    preview_path_text: ft.Text,
    editable_header: ft.Text,
    editable_front: ft.TextField,
    editable_back: ft.TextField,
    editable_image: ft.TextField,
    editable_image_preview: ft.Image,
    editable_save_button: ft.ElevatedButton,
    on_save_editable: Callable[[ft.ControlEvent], None],
    # --- Toolbar actions ---
    on_batch_gen: Callable[[], None],
    on_gen_description: Callable[[], None],
    on_gen_image: Callable[[], None],
    on_update_current: Callable[[], None],
    on_refresh_list: Callable[[], None],
    # --- Status ---
    copilot_status_text: ft.Text,
    copilot_progress_ring: ft.ProgressRing,
    # --- Responsive ---
    is_mobile: bool = False,
) -> ft.Container:
    """Build the preview workspace with file browser and editable editor."""

    file_browser = build_file_browser(
        files=preview_files,
        selected_path=selected_preview_path,
        output_dir=output_dir,
        file_list=file_list_view,
        deck_filter=deck_filter_dropdown,
        search_value=preview_search_value,
        search_field_ref=preview_search_field,
        on_select=on_select_file,
        on_search=on_search_files,
        on_refresh=on_refresh_list,
    )
    # Note: search_field is managed externally (preview_search_field) and
    # is wired via on_search_files callback. The file_browser creates its
    # own internal search field but we use the external one for state access.

    preview_editor = build_preview_editor(
        path_text=preview_path_text.value or "",
        header_text=editable_header.value or "",
        front_value=editable_front.value or "",
        back_value=editable_back.value or "",
        image_value=editable_image.value or "",
        image_src=editable_image_preview.src or "",
        on_front_change=None,
        on_back_change=None,
        on_image_change=None,
        on_save=on_save_editable,
        save_visible=editable_save_button.visible,
        front_field_ref=editable_front,
        back_field_ref=editable_back,
        image_field_ref=editable_image,
        image_preview_ref=editable_image_preview,
    )

    toolbar = ft.Row(
        controls=[
            ft.Text("Markdown preview", size=18, weight=ft.FontWeight.BOLD),
            ft.OutlinedButton(
                "Batch image gen",
                icon=ft.Icons.AUTO_AWESOME,
                on_click=lambda e: on_batch_gen(),
            ),
            ft.OutlinedButton(
                "Gen image description",
                icon=ft.Icons.AUTO_AWESOME,
                on_click=lambda e: on_gen_description(),
            ),
            ft.OutlinedButton(
                "Generate image",
                icon=ft.Icons.IMAGE,
                on_click=lambda e: on_gen_image(),
            ),
            ft.OutlinedButton(
                "Update note",
                icon=ft.Icons.UPLOAD,
                on_click=lambda e: on_update_current(),
            ),
            ft.OutlinedButton(
                "Refresh list",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: on_refresh_list(),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        wrap=True,
    )

    # Stack vertically on mobile, side-by-side on desktop
    if is_mobile:
        content_row = ft.Column(
            controls=[file_browser, preview_editor],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
    else:
        content_row = ft.Row(
            controls=[file_browser, preview_editor],
            spacing=12,
            expand=True,
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                toolbar,
                content_row,
                # Compact status bar
                ft.Container(
                    content=ft.Row(
                        controls=[
                            copilot_progress_ring,
                            copilot_status_text,
                        ],
                        spacing=8,
                    ),
                    padding=ft.padding.only(top=8),
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
