"""AI Chat dialog component — chat popup powered by OpenAI Agents SDK.

Replaces the old agent_chat.py and copilot.py mixin dialogs.
"""

from __future__ import annotations

import threading
import uuid
from typing import Callable

import flet as ft


def open_chat_dialog(
    page: ft.Page,
    log_lines: list[str],
    on_send: Callable[[str, ft.Text, ft.Text, ft.ProgressRing], None],
    on_reset: Callable[[ft.Text, ft.Text], None],
) -> ft.AlertDialog:
    """Open the AI Chat dialog as a popup.

    on_send(prompt, output_field, status_text, progress_ring) — called when the user presses Send.
    on_reset(output_field, status_text) — called when the user starts a new conversation.
    """

    dialog_output = ft.Text(
        value="\n".join(log_lines) if log_lines else "",
        size=13,
        font_family="monospace",
        selectable=True,
    )
    output_container = ft.Container(
        content=ft.Column(
            controls=[dialog_output],
            scroll=ft.ScrollMode.AUTO,
        ),
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=8,
        padding=10,
        expand=True,
        height=300,
    )

    dialog_status = ft.Text("Ready.", color=ft.Colors.ON_SURFACE_VARIANT)
    dialog_ring = ft.ProgressRing(width=16, height=16, visible=False)

    prompt_field = ft.TextField(
        label="Ask AI Assistant",
        hint_text="e.g. list all decks, create a study plan...",
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
        on_submit=lambda e: _handle_send(
            prompt_field, dialog_output, dialog_status, dialog_ring, on_send
        ),
    )

    def _send(e: ft.ControlEvent) -> None:
        _handle_send(prompt_field, dialog_output, dialog_status, dialog_ring, on_send)

    dialog = ft.AlertDialog(
        title=ft.Row(
            controls=[
                ft.Text("AI Assistant", size=20, weight=ft.FontWeight.BOLD),
                ft.TextButton(
                    "New conversation",
                    on_click=lambda e: on_reset(dialog_output, dialog_status),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        content=ft.Column(
            controls=[
                prompt_field,
                ft.Row(
                    controls=[
                        ft.FilledButton("Send", icon=ft.Icons.SEND, on_click=_send),
                        ft.Row(controls=[dialog_ring, dialog_status], spacing=8),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                output_container,
            ],
            spacing=12,
            width=700,
            height=550,
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda e: page.close(dialog)),
        ],
    )

    page.open(dialog)
    return dialog


def _handle_send(
    prompt_field: ft.TextField,
    output_field: ft.Text,
    status_text: ft.Text,
    progress_ring: ft.ProgressRing,
    on_send: Callable[[str, ft.Text, ft.Text, ft.ProgressRing], None],
) -> None:
    """Extract prompt and delegate to the on_send callback."""
    prompt = prompt_field.value.strip()
    if not prompt:
        status_text.value = "Enter a prompt first."
        status_text.color = ft.Colors.RED_700
        page = prompt_field.page
        if page:
            page.update()
        return

    prompt_field.value = ""
    on_send(prompt, output_field, status_text, progress_ring)
