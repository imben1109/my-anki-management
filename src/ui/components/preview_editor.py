"""Preview editor component — editable Front/Back/Image fields with save."""

from __future__ import annotations

from typing import Callable

import flet as ft


def build_preview_editor(
    path_text: str,
    header_text: str,
    front_value: str,
    back_value: str,
    image_value: str,
    image_src: str,
    on_front_change: Callable[[ft.ControlEvent], None] | None,
    on_back_change: Callable[[ft.ControlEvent], None] | None,
    on_image_change: Callable[[ft.ControlEvent], None] | None,
    on_save: Callable[[ft.ControlEvent], None],
    save_visible: bool = False,
    front_field_ref: ft.TextField | None = None,
    back_field_ref: ft.TextField | None = None,
    image_field_ref: ft.TextField | None = None,
    image_preview_ref: ft.Image | None = None,
) -> ft.Container:
    """Build the preview editor with editable fields.

    Optionally takes external control references so the caller can
    hold references for programmatic updates.
    """
    preview_path = ft.Text(
        path_text or "Select an exported Markdown file to preview it.",
        color=ft.Colors.ON_SURFACE_VARIANT,
        selectable=True,
    )

    header = ft.Text(
        header_text or "",
        size=12,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    front_field = front_field_ref or ft.TextField(
        label="Front",
        value=front_value,
        multiline=True,
        min_lines=2,
        max_lines=8,
        expand=True,
        text_style=ft.TextStyle(size=14),
        border=ft.InputBorder.OUTLINE,
    )
    if on_front_change:
        front_field.on_change = on_front_change

    back_field = back_field_ref or ft.TextField(
        label="Back",
        value=back_value,
        multiline=True,
        min_lines=2,
        max_lines=12,
        expand=True,
        text_style=ft.TextStyle(size=14),
        border=ft.InputBorder.OUTLINE,
    )
    if on_back_change:
        back_field.on_change = on_back_change

    image_field = image_field_ref or ft.TextField(
        label="Image",
        hint_text="![image](images/filename.jpg)",
        value=image_value,
        multiline=True,
        min_lines=1,
        max_lines=3,
        text_style=ft.TextStyle(size=13),
        border=ft.InputBorder.OUTLINE,
    )
    if on_image_change:
        image_field.on_change = on_image_change

    image_preview = image_preview_ref or ft.Image(
        src=image_src or "",
        width=200,
        fit=ft.ImageFit.CONTAIN,
        visible=bool(image_src),
    )

    save_button = ft.ElevatedButton(
        "Save changes",
        icon=ft.Icons.SAVE,
        on_click=on_save,
        visible=save_visible,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                preview_path,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            header,
                            front_field,
                            back_field,
                            image_field,
                            image_preview,
                            save_button,
                        ],
                        scroll=ft.ScrollMode.AUTO,
                        spacing=8,
                        expand=True,
                    ),
                    padding=ft.padding.only(right=12),
                    expand=True,
                ),
            ],
            spacing=8,
            expand=True,
        ),
        padding=12,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        expand=True,
    )
