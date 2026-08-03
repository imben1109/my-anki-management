"""Update card component — output folder display and update button."""

from __future__ import annotations

from typing import Callable

import flet as ft


def build_update_card(
    output_value: str,
    on_choose_folder: Callable[[], None],
    on_update: Callable[[], None],
    output_field_ref: ft.TextField | None = None,
) -> ft.Container:
    """Build the update card with output folder display and update button."""
    output_field = output_field_ref or ft.TextField(
        label="Output folder",
        value=output_value,
        expand=True,
        read_only=True,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Notes folder", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        output_field,
                        ft.OutlinedButton(
                            "Choose folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: on_choose_folder(),
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
