"""AI image generation dialog using Pollinations.ai (free, no API key needed)."""

from __future__ import annotations

import threading
import urllib.parse

import flet as ft


class _ImageGenMixin:
    """Mixin providing the AI image generation dialog method."""

    def _open_image_gen_dialog(self, _event: ft.ControlEvent | None = None, initial_prompt: str = "") -> None:
        """Open an AI image generation dialog using Pollinations.ai (free, no key needed)."""
        # Track generated image for save-to-note
        self._gen_image_b64: str | None = None
        self._gen_image_path: Path | None = None

        prompt_field = ft.TextField(
            label="Image description",
            hint_text="e.g. a cute cat wearing a wizard hat",
            value=initial_prompt,
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            on_submit=lambda e: self._generate_image(prompt_field, image_display, status_text, ring, save_btn),
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
            "Save to note",
            icon=ft.Icons.SAVE,
            visible=False,
            on_click=lambda e: self._save_image_to_note(status_text),
        )

        dialog = ft.AlertDialog(
            title=ft.Text("AI Image Generation", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                controls=[
                    prompt_field,
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Generate",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=lambda e: self._generate_image(
                                    prompt_field, image_display, status_text, ring, save_btn
                                ),
                            ),
                            ring,
                            status_text,
                        ],
                        spacing=10,
                    ),
                    image_stack,
                ],
                spacing=12,
                width=520,
            ),
            actions=[
                save_btn,
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
        )
        self.page.open(dialog)

    def _generate_image(
        self,
        prompt_field: ft.TextField,
        image_display: ft.Image,
        status_text: ft.Text,
        ring: ft.ProgressRing,
        save_btn: ft.TextButton | None = None,
    ) -> None:
        """Call Pollinations.ai to generate an image from the prompt."""
        prompt = prompt_field.value.strip()
        if not prompt:
            status_text.value = "Enter a prompt first."
            status_text.color = ft.Colors.RED_700
            self.page.update()
            return

        encoded = urllib.parse.quote(prompt, safe="")
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=576&nologo=true"

        status_text.value = "Generating..."
        status_text.color = ft.Colors.BLUE_700
        ring.visible = True
        self.page.update()

        def _worker() -> None:
            import requests

            try:
                r = requests.get(image_url, timeout=120)
                if r.status_code == 200 and len(r.content) > 100:
                    import base64

                    b64 = base64.b64encode(r.content).decode()
                    image_display.src_base64 = b64
                    image_display.visible = True
                    # Store for potential save-to-note
                    self._gen_image_b64 = b64
                    self._gen_image_path = getattr(self, 'selected_preview_path', None)
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
