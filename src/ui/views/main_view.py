"""Main workspace view — decks, export, update, and logs.

Composes deck_list, export_card, update_card, and log panel components.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.ui.components.deck_list import build_deck_item, build_deck_list, render_deck_list
from src.ui.components.export_card import build_export_card
from src.ui.components.update_card import build_update_card


def build_main_view(
    # --- Deck list state ---
    decks: list[str],
    selected_deck: str | None,
    deck_count: int,
    deck_list_view: ft.ListView | None = None,
    deck_count_text: ft.Text | None = None,
    on_refresh: Callable[[ft.ControlEvent], None] | None = None,
    on_select_deck: Callable[[str], None] | None = None,
    on_export_selected: Callable[[ft.ControlEvent], None] | None = None,
    # --- Export card ---
    output_field: ft.TextField | None = None,
    query_field: ft.TextField | None = None,
    on_choose_output_folder: Callable[[], None] | None = None,
    on_export_query: Callable[[ft.ControlEvent], None] | None = None,
    # --- Update card ---
    update_target_field: ft.TextField | None = None,
    on_choose_update_folder: Callable[[], None] | None = None,
    on_choose_update_file: Callable[[], None] | None = None,
    on_update: Callable[[ft.ControlEvent], None] | None = None,
    # --- Logs ---
    log_field: ft.TextField | None = None,
    status_text: ft.Text | None = None,
    progress_ring: ft.ProgressRing | None = None,
    # --- Responsive ---
    is_mobile: bool = False,
) -> ft.Row:
    """Build the main manage-decors workspace."""

    # --- Left panel: deck list ---
    if deck_list_view is None:
        deck_list_view = build_deck_list(decks, selected_deck, on_select_deck)
    else:
        render_deck_list(deck_list_view, decks, selected_deck, on_select_deck)

    if deck_count_text is None:
        deck_count_text = ft.Text(f"Decks: {deck_count}", color=ft.Colors.ON_SURFACE_VARIANT)

    left_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Decks", size=20, weight=ft.FontWeight.BOLD),
                        deck_count_text,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Refresh decks", on_click=on_refresh),
                        ft.ElevatedButton("Export selected deck", on_click=on_export_selected),
                    ],
                    wrap=True,
                ),
                ft.Container(content=deck_list_view, expand=True),
            ],
            spacing=12,
            expand=True,
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=14,
        expand=1,
    )

    # --- Right panel cards ---
    export_card = build_export_card(
        output_value=output_field.value or "",
        query_value=query_field.value or "",
        on_output_change=None,
        on_query_change=None,
        on_choose_folder=on_choose_output_folder,
        on_export_query=on_export_query,
        output_field_ref=output_field,
        query_field_ref=query_field,
    )

    update_card = build_update_card(
        target_value=update_target_field.value or "",
        on_target_change=None,
        on_pick_folder=on_choose_update_folder,
        on_pick_file=on_choose_update_file,
        on_update=on_update,
        target_field_ref=update_target_field,
    )

    logs_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Status & logs", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row(controls=[progress_ring, status_text], spacing=10),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                log_field,
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

    if is_mobile:
        return ft.Column(
            controls=[left_panel, right_panel],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
    return ft.Row(
        controls=[left_panel, right_panel],
        spacing=16,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
