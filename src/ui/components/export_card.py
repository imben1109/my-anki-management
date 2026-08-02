"""Export card component — query field, output folder, export buttons."""

from __future__ import annotations

from typing import Callable

import flet as ft


def build_export_card(
    output_value: str,
    query_value: str,
    on_output_change: Callable[[ft.ControlEvent], None] | None,
    on_query_change: Callable[[ft.ControlEvent], None] | None,
    on_choose_folder: Callable[[], None],
    on_export_query: Callable[[], None],
    output_field_ref: ft.TextField | None = None,
    query_field_ref: ft.TextField | None = None,
) -> ft.Container:
    """Build the export card with output folder picker and query field.

    Optionally takes external TextField references to allow the caller to
    hold references for programmatic updates.
    """
    output_field = output_field_ref or ft.TextField(
        label="Output folder",
        value=output_value,
        expand=True,
    )
    if on_output_change:
        output_field.on_change = on_output_change

    query_field = query_field_ref or ft.TextField(
        label="Custom query",
        hint_text='Example: deck:"My Deck"',
        value=query_value,
        expand=True,
    )
    if on_query_change:
        query_field.on_change = on_query_change

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Export", size=18, weight=ft.FontWeight.BOLD),
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
                        query_field,
                        ft.FilledButton(
                            "Export query",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=lambda e: on_export_query(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=12,
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=14,
    )
