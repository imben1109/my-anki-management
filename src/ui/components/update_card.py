"""Update card component — target field, folder/file pickers, update button."""

from __future__ import annotations

from typing import Callable

import flet as ft


def build_update_card(
    target_value: str,
    on_target_change: Callable[[ft.ControlEvent], None] | None,
    on_pick_folder: Callable[[], None],
    on_pick_file: Callable[[], None],
    on_update: Callable[[], None],
    target_field_ref: ft.TextField | None = None,
) -> ft.Container:
    """Build the update card with target path picker and update button."""
    target_field = target_field_ref or ft.TextField(
        label="Update target (.md file or directory)",
        value=target_value,
        expand=True,
    )
    if on_target_change:
        target_field.on_change = on_target_change

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Update", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        target_field,
                        ft.OutlinedButton(
                            "Pick folder",
                            icon=ft.Icons.FOLDER,
                            on_click=lambda e: on_pick_folder(),
                        ),
                        ft.OutlinedButton(
                            "Pick file",
                            icon=ft.Icons.DESCRIPTION,
                            on_click=lambda e: on_pick_file(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Update notes",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=lambda e: on_update(),
                        ),
                    ],
                    wrap=True,
                ),
            ],
            spacing=12,
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=14,
    )
