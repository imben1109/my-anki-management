"""Image Generation dialog component — provider/model selection and preview.

Replaces the old image_gen.py mixin dialog.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import flet as ft

# Providers
PROVIDER_POLLINATIONS = "pollinations"
PROVIDER_OPENROUTER = "openrouter"

# Available OpenRouter image models
OPENROUTER_IMAGE_MODELS = [
    "black-forest-labs/flux.2-flex",
    "black-forest-labs/flux.2-pro",
    "bytedance-seed/seedream-4.5",
    "openai/gpt-image-2",
]


def open_image_gen_dialog(
    page: ft.Page,
    initial_prompt: str = "",
    on_generate_pollinations: Callable[
        [str, ft.Image, ft.Text, ft.ProgressRing, ft.TextButton | None], None
    ] | None = None,
    on_generate_openrouter: Callable[
        [str, str, ft.Image, ft.Text, ft.ProgressRing, ft.TextButton | None], None
    ] | None = None,
    on_attach: Callable[[ft.Text | None], None] | None = None,
) -> ft.AlertDialog:
    """Open the image generation dialog.

    Args:
        page: The Flet page.
        initial_prompt: Pre-filled prompt (e.g., from note front content).
        on_generate_pollinations: Called for Pollinations.ai generation.
        on_generate_openrouter: Called for OpenRouter generation.
        on_attach: Called when user clicks "Attach to card".

    Returns the dialog for reference.
    """
    provider_dd = ft.Dropdown(
        label="Provider",
        options=[
            ft.dropdown.Option(PROVIDER_POLLINATIONS, "Pollinations.ai (free)"),
            ft.dropdown.Option(PROVIDER_OPENROUTER, "OpenRouter"),
        ],
        value=PROVIDER_POLLINATIONS,
    )
    model_dd = ft.Dropdown(
        label="Model",
        options=[ft.dropdown.Option(m) for m in OPENROUTER_IMAGE_MODELS],
        value=OPENROUTER_IMAGE_MODELS[0],
        visible=False,
    )

    def on_provider_change(e: ft.ControlEvent) -> None:
        model_dd.visible = provider_dd.value == PROVIDER_OPENROUTER
        page.update()

    provider_dd.on_change = on_provider_change

    prompt_field = ft.TextField(
        label="Image description",
        hint_text="e.g. a cute cat wearing a wizard hat",
        value=initial_prompt,
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
    )
    image_display = ft.Image(
        src="",
        fit=ft.ImageFit.CONTAIN,
        width=480,
        height=360,
        visible=False,
    )
    status_text = ft.Text(
        "Enter a prompt and click Generate.",
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    ring = ft.ProgressRing(width=16, height=16, visible=False)

    placeholder = ft.Container(
        content=ft.Icon(ft.Icons.IMAGE, size=64, color=ft.Colors.OUTLINE),
        width=480,
        height=360,
        alignment=ft.alignment.center,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
    )
    image_stack = ft.Stack(
        controls=[placeholder, image_display],
        width=480,
        height=360,
    )

    save_btn = ft.TextButton(
        "Attach to card",
        icon=ft.Icons.ATTACH_FILE,
        visible=False,
        on_click=lambda e: on_attach(status_text) if on_attach else None,
    )

    def _generate(e: ft.ControlEvent) -> None:
        prompt = prompt_field.value.strip()
        if not prompt:
            status_text.value = "Enter a prompt first."
            status_text.color = ft.Colors.RED_700
            page.update()
            return

        status_text.value = "Generating..."
        status_text.color = ft.Colors.BLUE_700
        ring.visible = True
        page.update()

        if provider_dd.value == PROVIDER_OPENROUTER:
            if on_generate_openrouter:
                model = model_dd.value or OPENROUTER_IMAGE_MODELS[0]
                on_generate_openrouter(prompt, model, image_display, status_text, ring, save_btn)
        else:
            if on_generate_pollinations:
                on_generate_pollinations(prompt, image_display, status_text, ring, save_btn)

    dialog = ft.AlertDialog(
        title=ft.Text("AI Image Generation", size=20, weight=ft.FontWeight.BOLD),
        content=ft.Column(
            controls=[
                ft.Row(controls=[provider_dd, model_dd], spacing=10),
                prompt_field,
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Generate",
                            icon=ft.Icons.AUTO_AWESOME,
                            on_click=_generate,
                        ),
                        ring,
                        status_text,
                    ],
                    spacing=10,
                ),
                image_stack,
                ft.Row(
                    controls=[
                        save_btn,
                        ft.TextButton("Close", on_click=lambda e: page.close(dialog)),
                    ],
                    spacing=10,
                ),
            ],
            spacing=12,
            width=520,
        ),
    )

    page.open(dialog)
    return dialog
