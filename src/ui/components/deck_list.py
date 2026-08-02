"""Deck list component — selectable list of Anki deck names."""

from __future__ import annotations

from typing import Callable

import flet as ft


def build_deck_item(
    deck_name: str,
    is_selected: bool,
    on_select: Callable[[str], None],
) -> ft.Container:
    """Build a single deck item container."""
    return ft.Container(
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
        on_click=lambda _, d=deck_name: on_select(d),
    )


def build_deck_list(
    decks: list[str],
    selected_deck: str | None,
    on_select: Callable[[str], None],
) -> ft.ListView:
    """Build a ListView of deck items."""
    if decks:
        controls = [
            build_deck_item(d, d == selected_deck, on_select) for d in decks
        ]
    else:
        controls = [
            ft.Container(
                content=ft.Text(
                    "No decks loaded yet.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                ),
                padding=ft.padding.only(top=8),
            )
        ]

    return ft.ListView(controls=controls, expand=True, spacing=8, padding=0)


def render_deck_list(
    list_view: ft.ListView,
    decks: list[str],
    selected_deck: str | None,
    on_select: Callable[[str], None],
) -> None:
    """Re-render an existing deck list view with updated decks/selection."""
    if decks:
        list_view.controls = [
            build_deck_item(d, d == selected_deck, on_select) for d in decks
        ]
    else:
        list_view.controls = [
            ft.Container(
                content=ft.Text(
                    "No decks loaded yet.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                ),
                padding=ft.padding.only(top=8),
            )
        ]
