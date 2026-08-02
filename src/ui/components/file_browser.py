"""File browser component — searchable list of exported markdown files."""

from __future__ import annotations

from typing import Callable

import flet as ft
from pathlib import Path


def build_file_item(
    path: Path,
    display_path: str,
    is_selected: bool,
    on_select: Callable[[Path], None],
) -> ft.Container:
    """Build a single file item container."""
    return ft.Container(
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
        on_click=lambda _, p=path: on_select(p),
    )


def build_file_browser(
    files: list[Path],
    selected_path: Path | None,
    output_dir: str,
    search_value: str,
    on_select: Callable[[Path], None],
    on_search: Callable[[ft.ControlEvent], None],
    on_refresh: Callable[[], None],
    search_field_ref: ft.TextField | None = None,
    file_list: ft.ListView | None = None,
) -> ft.Container:
    """Build the file browser with search and refresh.

    If search_field_ref is provided, it is used instead of creating a new TextField.
    This allows the caller to hold a reference for programmatic access.

    Returns a Container with the file list and toolbar.
    """
    search_field = search_field_ref or ft.TextField(
        label="Search files",
        hint_text="Filter by name or content...",
        value=search_value,
        prefix_icon=ft.Icons.SEARCH,
        on_change=on_search,
        dense=True,
    )

    # Build file list
    if files:
        output_path = Path(output_dir)
        controls = []
        for path in files:
            try:
                display_path = str(path.relative_to(output_path))
            except ValueError:
                display_path = str(path)
            controls.append(
                build_file_item(path, display_path, path == selected_path, on_select)
            )
    else:
        controls = [
            ft.Container(
                content=ft.Text(
                    "No exported Markdown files found.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                ),
                padding=ft.padding.only(top=8),
            )
        ]

    # Build file list — use shared list if provided, otherwise create new
    if file_list is not None:
        file_list.controls = controls
    else:
        file_list = ft.ListView(controls=controls, expand=True, spacing=2, padding=0)

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Exported Markdown files", weight=ft.FontWeight.BOLD),
                search_field,
                file_list,
            ],
            spacing=8,
            expand=True,
        ),
        width=300,
        padding=12,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        expand=False,
    )
