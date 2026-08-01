"""AI image generation dialog — Pollinations.ai (free) and Qwen Image (via OpenRouter)."""

from __future__ import annotations

import os
import threading
import urllib.parse
from pathlib import Path

import flet as ft


# Available providers
PROVIDER_POLLINATIONS = "pollinations"
PROVIDER_OPENROUTER = "openrouter"

OPENROUTER_IMAGE_MODELS = [
    "black-forest-labs/flux.2-flex",
    "black-forest-labs/flux.2-pro",
    "bytedance-seed/seedream-4.5",
    "openai/gpt-image-2",
]


class _ImageGenMixin:
    """Mixin providing the AI image generation dialog."""

    def _open_image_gen_dialog(self, _event: ft.ControlEvent | None = None, initial_prompt: str = "") -> None:
        """Open the image generation dialog with provider + model selection."""
        # Track generated image for attach-to-card
        self._gen_image_url: str | None = None
        self._gen_image_path: Path | None = None

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
            self.page.update()

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
        status_text = ft.Text("Enter a prompt and click Generate.", color=ft.Colors.ON_SURFACE_VARIANT)
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
            on_click=lambda e: self._save_image_to_note(status_text),
        )
        button_row = ft.Row(
            controls=[
                save_btn,
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
            spacing=10,
        )

        dialog = ft.AlertDialog(
            title=ft.Text("AI Image Generation", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[provider_dd, model_dd],
                        spacing=10,
                    ),
                    prompt_field,
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Generate",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=lambda e: self._generate_image(
                                    provider_dd, model_dd, prompt_field,
                                    image_display, status_text, ring, button_row,
                                ),
                            ),
                            ring,
                            status_text,
                        ],
                        spacing=10,
                    ),
                    image_stack,
                    button_row,
                ],
                spacing=12,
                width=520,
            ),
        )
        self.page.open(dialog)

    # ------------------------------------------------------------------
    # Image generation dispatch
    # ------------------------------------------------------------------
    def _generate_image(
        self,
        provider_dd: ft.Dropdown,
        model_dd: ft.Dropdown,
        prompt_field: ft.TextField,
        image_display: ft.Image,
        status_text: ft.Text,
        ring: ft.ProgressRing,
        button_row: ft.Row,
    ) -> None:
        """Dispatch to the correct image generation backend."""
        prompt = prompt_field.value.strip()
        if not prompt:
            status_text.value = "Enter a prompt first."
            status_text.color = ft.Colors.RED_700
            self.page.update()
            return

        status_text.value = "Generating..."
        status_text.color = ft.Colors.BLUE_700
        ring.visible = True
        self.page.update()

        save_btn = button_row.controls[0] if button_row.controls else None

        if provider_dd.value == PROVIDER_OPENROUTER:
            self._generate_openrouter(prompt, model_dd.value or OPENROUTER_IMAGE_MODELS[0],
                                image_display, status_text, ring, save_btn)
        else:
            self._generate_pollinations(prompt, image_display, status_text, ring, save_btn)

    # ------------------------------------------------------------------
    # Pollinations.ai backend (free)
    # ------------------------------------------------------------------
    def _generate_pollinations(
        self,
        prompt: str,
        image_display: ft.Image,
        status_text: ft.Text,
        ring: ft.ProgressRing,
        save_btn: ft.TextButton | None,
    ) -> None:
        """Generate via Pollinations.ai (GET request, no API key)."""
        encoded = urllib.parse.quote(prompt, safe="")
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=576&nologo=true"

        def _worker() -> None:
            import base64
            import requests

            try:
                r = requests.get(image_url, timeout=120)
                if r.status_code == 200 and len(r.content) > 100:
                    b64 = base64.b64encode(r.content).decode()
                    image_display.src_base64 = b64
                    image_display.visible = True
                    self._gen_image_url = image_url
                    self._gen_image_data = r.content
                    self._gen_image_path = getattr(self, "selected_preview_path", None)
                    if save_btn:
                        save_btn.visible = True
                    status_text.value = f"Generated: {prompt[:50]}..."
                    status_text.color = ft.Colors.GREEN_700
                else:
                    status_text.value = f"Generation failed (HTTP {r.status_code})"
                    status_text.color = ft.Colors.RED_700
            except Exception as exc:
                status_text.value = f"Error: {exc}"
                status_text.color = ft.Colors.RED_700
            finally:
                ring.visible = False
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # OpenRouter backend
    # ------------------------------------------------------------------
    def _generate_openrouter(
        self,
        prompt: str,
        model: str,
        image_display: ft.Image,
        status_text: ft.Text,
        ring: ft.ProgressRing,
        save_btn: ft.TextButton | None,
    ) -> None:
        """Generate via Qwen Image on OpenRouter."""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            ring.visible = False
            status_text.value = "Set OPENROUTER_API_KEY environment variable."
            status_text.color = ft.Colors.RED_700
            self.page.update()
            return

        def _worker() -> None:
            import base64
            import json
            import requests

            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/images",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "prompt": prompt,
                        "response_format": "b64_json",
                    },
                    timeout=180,
                )
                if r.status_code == 200:
                    data = r.json()
                    img_data = data.get("data", [])
                    if isinstance(img_data, list) and len(img_data) > 0:
                        img_b64 = img_data[0].get("b64_json", "")
                    elif isinstance(img_data, str):
                        img_b64 = img_data
                    else:
                        img_b64 = ""
                    if img_b64:
                        image_display.src_base64 = img_b64
                        image_display.visible = True
                        self._gen_image_url = f"openrouter:{model}:{prompt[:30]}"
                        self._gen_image_data = base64.b64decode(img_b64)
                        self._gen_image_path = getattr(self, "selected_preview_path", None)
                        if save_btn:
                            save_btn.visible = True
                        status_text.value = f"Generated: {prompt[:50]}..."
                        status_text.color = ft.Colors.GREEN_700
                    else:
                        status_text.value = f"No image in response: {data.get('error', data)}"
                        status_text.color = ft.Colors.RED_700
                else:
                    err = r.text[:300]
                    status_text.value = f"OpenRouter error ({r.status_code}): {err}"
                    status_text.color = ft.Colors.RED_700
            except Exception as exc:
                status_text.value = f"Error: {exc}"
                status_text.color = ft.Colors.RED_700
            finally:
                ring.visible = False
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()
