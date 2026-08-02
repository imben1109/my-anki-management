"""Deck management, export/update workflows, file pickers, and markdown preview."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import flet as ft
import requests

from src.ui.helpers import parse_decks


MACOS_FOLDER_PICKER_SCRIPT = """
on run argv
    set promptText to item 1 of argv
    set startFolder to POSIX file (item 2 of argv) as alias
    set pickedFolder to choose folder with prompt promptText default location startFolder
    return POSIX path of pickedFolder
end run
"""


def _extract_section(name: str, text: str) -> str:
    """Extract the content of a ## section from markdown text."""
    pattern = rf"^## {re.escape(name)}(?:\s+\(markdown\))?\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


class _DecksMixin:
    """Mixin providing deck listing, export/update, file pickers, and preview."""

    def refresh_decks(self, _event: ft.ControlEvent | None = None) -> None:
        previous_deck = self.selected_deck
        self._append_log("$ apy info")
        self._set_status("Loading decks...", ft.Colors.BLUE_700)
        self._set_busy(True)

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["apy", "info"],
                    cwd=str(self.base_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                self._report_issue("Failed to load decks: could not find 'apy' on PATH.")
                self._set_busy(False)
                return
            except Exception as exc:
                self._report_issue(f"Failed to load decks: {exc}")
                self._set_busy(False)
                return

            if result.stdout.strip():
                self._append_log(result.stdout.rstrip())
            if result.stderr.strip():
                self._append_log(result.stderr.rstrip())

            if result.returncode != 0:
                self._append_log(f"Deck refresh failed with exit code {result.returncode}.")
                self._set_status(
                    f"Deck refresh failed with exit code {result.returncode}.",
                    ft.Colors.RED_700,
                )
                self._set_busy(False)
                return

            decks = parse_decks(result.stdout)
            self.decks = decks
            if previous_deck in decks:
                self.selected_deck = previous_deck
            elif self.selected_deck in decks:
                pass
            else:
                self.selected_deck = decks[0] if decks else None
            self._render_decks()
            self._append_log(f"Loaded {len(decks)} deck(s).")
            self._set_status(f"Loaded {len(decks)} deck(s).", ft.Colors.GREEN_700)
            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()


    def _render_decks(self) -> None:
        from src.ui.components.deck_list import render_deck_list

        render_deck_list(self.deck_list, self.decks, self.selected_deck, self._select_deck)
        self.deck_count_text.value = f"Decks: {len(self.decks)}"
        self.page.update()


    def _select_deck(self, deck_name: str) -> None:
        self.selected_deck = deck_name
        self._render_decks()


    def _deck_query(self, deck_name: str) -> str:
        escaped = deck_name.replace('"', r"\"")
        return f'deck:"{escaped}"'


    def export_selected_deck(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return
        if not self.selected_deck:
            self._set_status("Select a deck first!", ft.Colors.RED_700)
            self.page.open(ft.AlertDialog(
                title=ft.Text("No deck selected"),
                content=ft.Text("Click a deck name in the list first, then try export again."),
            ))
            return
        if not self.decks:
            self._set_status("No decks loaded. Click 'Refresh decks'.", ft.Colors.RED_700)
            return

        query = self._deck_query(self.selected_deck)
        self.query_field.value = query
        self.page.update()
        self._run_export(query)


    def export_custom_query(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return

        query = self.query_field.value.strip()
        if not query:
            self._report_issue("Missing query. Enter an Anki query first.")
            return

        self._run_export(query)


    def _run_export(self, query: str) -> None:
        output_dir = self.output_field.value.strip()
        if not output_dir:
            self._set_status("Choose an output folder first!", ft.Colors.RED_700)
            return

        output_path = Path(output_dir)
        # Compute the deck-specific subfolder using same sanitization as export.py
        deck_name = self.selected_deck or "Default"
        safe_deck = re.sub(r"[^\w\s\-]", "", deck_name)
        safe_deck = re.sub(r"\s+", " ", safe_deck).strip() or "Default"
        deck_folder = output_path / safe_deck

        # If deck folder already exists, prompt for confirmation
        if deck_folder.exists() and any(deck_folder.iterdir()):
            self._show_export_confirm_dialog(query, output_dir, output_path, deck_folder)
        else:
            self._do_export(query, output_dir, output_path)


    def _show_export_confirm_dialog(
        self, query: str, output_dir: str, output_path: Path, deck_folder: Path
    ) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Deck folder already exists"),
            content=ft.Text(
                f'The folder "{deck_folder.name}" already exists in the export directory. '
                f"Delete it and re-export?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dialog)),
                ft.FilledButton(
                    "Delete & Export",
                    on_click=lambda e: self._confirm_export_delete(
                        e, dialog, query, output_dir, output_path, deck_folder
                    ),
                ),
            ],
        )
        self.page.open(dialog)

    def _confirm_export_delete(
        self,
        e: ft.ControlEvent,
        dialog: ft.AlertDialog,
        query: str,
        output_dir: str,
        output_path: Path,
        deck_folder: Path,
    ) -> None:
        self.page.close(dialog)
        shutil.rmtree(deck_folder)
        self._append_log(f"Deleted: {deck_folder}")
        self._do_export(query, output_dir, output_path)


    def _do_export(self, query: str, output_dir: str, output_path: Path) -> None:
        cmd = [sys.executable, str(self.export_script), query, output_dir]

        def on_success() -> None:
            if not self.update_target_field.value.strip():
                self.update_target_field.value = output_dir
            self._refresh_preview_files()
            exported_files = sorted(output_path.rglob("*.md"), key=lambda p: p.stat().st_mtime)
            if exported_files:
                self._preview_markdown_file(exported_files[-1])
            else:
                self.page.update()

        self._run_in_thread("Export", cmd, on_success=on_success)


    def update_notes(self, _event: ft.ControlEvent | None = None) -> None:
        if not self._ensure_scripts():
            return

        target = self.update_target_field.value.strip()
        if not target:
            self._report_issue(
                "Missing target. Choose a markdown file or directory to update."
            )
            return

        target_path = Path(target)
        if not target_path.exists():
            self._report_issue(f"Target path does not exist: {target}")
            return

        cmd = [sys.executable, str(self.update_script), str(target_path)]
        self._run_in_thread("Update", cmd)


    def _ensure_scripts(self) -> bool:
        missing = [
            str(path.name)
            for path in (self.export_script, self.update_script)
            if not path.exists()
        ]
        if missing:
            self._report_issue(
                "Missing script(s): "
                + ", ".join(missing)
                + ". Expected them next to anki_ui.py."
            )
            return False
        return True


    def _refresh_preview_files(self) -> None:
        output_path = Path(self.output_field.value.strip())
        files: list[tuple[float, Path]] = []
        if output_path.is_dir():
            try:
                for path in output_path.rglob("*.md"):
                    try:
                        files.append((path.stat().st_mtime, path))
                    except OSError:
                        continue
            except OSError as exc:
                self._report_copilot_issue(f"Could not list exported Markdown files: {exc}")
                return

        self.preview_files = [
            path for _, path in sorted(files, key=lambda item: item[0], reverse=True)
        ]
        if self.selected_preview_path not in self.preview_files:
            self.selected_preview_path = None
        self._render_preview_file_list()
        # Don't auto-switch to preview during startup — only when user clicks "Markdown preview"


    def _on_preview_search(self, _event: ft.ControlEvent) -> None:
        """Filter preview files by search text in name, then content."""
        query = self.preview_search_field.value.strip().lower()
        if not query:
            self._render_preview_file_list()
            return

        # Phase 1: filter by filename (fast, no disk I/O)
        name_matches = [p for p in self.preview_files if query in p.name.lower()]
        name_set = set(name_matches)
        remaining = [p for p in self.preview_files if p not in name_set]

        # Phase 2: for remaining, check cached content
        content_matches = []
        for p in remaining:
            cached = self._md_cache.get(p)
            if cached is not None:
                if query in cached.lower():
                    content_matches.append(p)
                    continue
            # If not cached, only read on enter (not on every keystroke)

        filtered = name_matches + content_matches
        self._render_preview_file_list(files=filtered)


    def _render_preview_file_list(self, files: list[Path] | None = None) -> None:
        """Build the full file list once. Subsequent selection changes use _update_preview_selection."""
        controls: list[ft.Control] = []
        output_path = Path(self.output_field.value.strip())
        new_row_map: dict[Path, ft.Container] = {}

        source_files = files if files is not None else self.preview_files
        for path in source_files:
            is_selected = path == self.selected_preview_path
            try:
                display_path = str(path.relative_to(output_path))
            except ValueError:
                display_path = str(path)
            container = ft.Container(
                content=ft.ListTile(
                    title=ft.Text(
                        display_path,
                        weight=ft.FontWeight.W_600 if is_selected else None,
                    ),
                    dense=True,
                ),
                bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.SURFACE,
                border=ft.border.all(
                    1,
                    ft.Colors.BLUE_300 if is_selected else ft.Colors.OUTLINE_VARIANT,
                ),
                border_radius=8,
                on_click=lambda _, p=path: self._preview_markdown_file(p),
            )
            controls.append(container)
            new_row_map[path] = container

        if not controls:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        "No exported Markdown files found.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.padding.only(top=8),
                )
            )

        self._preview_row_map = new_row_map
        self.preview_file_list.controls = controls
        self.page.update()

    def _update_preview_selection(self, new_path: Path, old_path: Path | None) -> None:
        """Update only the highlight on two rows — no rebuild of 6,000 controls."""
        row_map = getattr(self, '_preview_row_map', {})
        if not row_map:
            return  # not yet rendered

        selected_style = (
            ft.Colors.BLUE_50,
            ft.border.all(1, ft.Colors.BLUE_300),
            ft.FontWeight.W_600,
        )
        normal_style = (
            ft.Colors.SURFACE,
            ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            None,
        )

        def _apply(container: ft.Container, bgcolor, border, weight):
            container.bgcolor = bgcolor
            container.border = border
            container.content.title.weight = weight

        # Deselect old
        if old_path and old_path in row_map:
            _apply(row_map[old_path], *normal_style)
        # Select new
        if new_path in row_map:
            _apply(row_map[new_path], *selected_style)

        self.page.update()


    def _preview_markdown_file(self, path: Path) -> None:
        old_path = self.selected_preview_path
        self.selected_preview_path = path
        self.preview_load_request += 1
        request = self.preview_load_request
        self.preview_path_text.value = str(path)

        # Batch all main-thread updates into a single page.update()
        self.manage_workspace.visible = False
        self.preview_workspace.visible = True
        self._update_preview_selection(path, old_path)
        self.copilot_status_text.value = f"Loading {path.name}..."
        self.copilot_status_text.color = ft.Colors.BLUE_700
        self.page.update()  # single roundtrip for all main-thread changes

        def worker() -> None:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                if request == self.preview_load_request:
                    self._report_copilot_issue(f"Could not preview Markdown file {path}: {exc}")
                return

            if request != self.preview_load_request:
                return

            # Parse sections: header (title + metadata), ## Front, ## Back, ## Image
            title_match = re.match(r"^# (.+)", text)
            title = title_match.group(1) if title_match else path.stem

            # Extract metadata lines between title and first ## section
            meta_lines: list[str] = []
            front_content = ""
            back_content = ""
            image_content = ""

            # Split by ## headers
            sections = re.split(r"^## ", text, flags=re.MULTILINE)
            for i, section in enumerate(sections):
                section = section.strip()
                if i == 0:
                    # First "section" is the header block (title + metadata)
                    lines = section.splitlines()
                    for line in lines[1:]:  # skip the # title line
                        line = line.strip()
                        if line and not line.startswith("##"):
                            meta_lines.append(line)
                elif section.startswith("Front"):
                    front_content = section[len("Front"):].strip()
                elif section.startswith("Back"):
                    back_content = section[len("Back"):].strip()
                elif section.startswith("Image"):
                    image_content = section[len("Image"):].strip()

            header_parts = [title]
            for line in meta_lines:
                if line.startswith("model:") or line.startswith("deck:"):
                    header_parts.append(line)
            header_text = "  ·  ".join(header_parts)

            # Resolve image path for preview
            image_src = ""
            img_match = re.search(r"!\[.*?\]\((images/[^)]+)\)", image_content)
            if img_match:
                output_dir = Path(self.output_field.value.strip()).resolve()
                try:
                    rel_dir = path.resolve().parent.relative_to(output_dir)
                    image_src = f"http://localhost:8551/{rel_dir}/{img_match.group(1)}"
                except ValueError:
                    pass

            # Batch all worker updates
            self.editable_header.value = header_text
            self.editable_front.value = front_content
            self.editable_back.value = back_content
            self.editable_image.value = image_content
            if image_src:
                self.editable_image_preview.src = image_src
                self.editable_image_preview.visible = True
            else:
                self.editable_image_preview.visible = False
            self.editable_save_button.visible = True

            source_label = "disk"
            self.copilot_status_text.value = f"Previewing {path.name} ({source_label})."
            self.copilot_status_text.color = ft.Colors.GREEN_700

            self.page.update()

        threading.Thread(target=worker, daemon=True).start()


    def refresh_preview_files(self, _event: ft.ControlEvent | None = None) -> None:
        self._refresh_preview_files()

    def update_current_note(self, _event: ft.ControlEvent | None = None) -> None:
        """Update the currently previewed markdown file back to Anki."""
        path = self.selected_preview_path
        if path is None:
            self._report_issue("No markdown file selected for preview.")
            return
        if not self._ensure_scripts():
            return
        cmd = [sys.executable, str(self.update_script), str(path)]

        def _update_status(msg: str, color: str = ft.Colors.ON_SURFACE_VARIANT) -> None:
            self.copilot_status_text.value = msg
            self.copilot_status_text.color = color
            self.page.update()

        def _update_log(_msg: str) -> None:
            pass  # log is hidden; status bar is one line

        def _update_busy(busy: bool) -> None:
            self.copilot_progress_ring.visible = busy
            self.page.update()

        self._run_in_thread(
            f"Update {path.name}", cmd,
            set_status=_update_status,
            append_log=_update_log,
            set_busy=_update_busy,
        )

    def _save_editable_preview(self, _event: ft.ControlEvent | None = None) -> None:
        """Save the editable preview fields back to the .md file."""
        path = self.selected_preview_path
        if path is None:
            self._report_issue("No file selected for preview.")
            return

        # Reconstruct markdown from the original file header + edited fields
        try:
            original = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._report_copilot_issue(f"Cannot read file: {exc}")
            return

        # Extract the original header (everything before ## Front)
        header_end = original.find("\n## Front")
        if header_end == -1:
            header_end = original.find("\n## Front")
        if header_end == -1:
            self._report_copilot_issue("Cannot find ## Front section in file.")
            return
        header = original[:header_end]

        front = self.editable_front.value.strip()
        back = self.editable_back.value.strip()
        image = self.editable_image.value.strip()

        new_md = f"{header}\n## Front\n{front}\n\n## Back\n{back}\n"
        if image:
            new_md += f"## Image\n{image}\n"
        else:
            new_md += "## Image\n"

        try:
            path.write_text(new_md, encoding="utf-8")
        except OSError as exc:
            self._report_copilot_issue(f"Cannot write file: {exc}")
            return

        self.copilot_status_text.value = f"Saved {path.name}."
        self.copilot_status_text.color = ft.Colors.GREEN_700
        self.page.update()

    def _batch_generate_images(self, _event: ft.ControlEvent | None = None) -> None:
        """Batch process all preview cards: AI description → OpenRouter seedream image → attach → update to Anki."""
        if not self.preview_files:
            self._report_copilot_issue("No exported markdown files found. Export a deck first.")
            return

        # Pre-scan: count cards without images
        to_process: list[Path] = []
        for path in self.preview_files:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            front = _extract_section("Front", content)
            image = _extract_section("Image", content)
            if front and not image:
                to_process.append(path)

        if not to_process:
            self._report_copilot_issue("All cards already have images. Nothing to do.")
            return

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        ai_key = os.environ.get("AI_CHAT_API_KEY", "")
        if not api_key:
            self._report_copilot_issue("Set OPENROUTER_API_KEY environment variable.")
            return
        if not ai_key:
            self._report_copilot_issue("Set AI_CHAT_API_KEY environment variable.")
            return

        total = len(to_process)
        self.copilot_status_text.value = f"Batch: 0/{total} cards..."
        self.copilot_status_text.color = ft.Colors.BLUE_700
        self.copilot_progress_ring.visible = True
        self.page.update()

        def _worker() -> None:
            import asyncio
            import base64
            import re as _re

            success = 0
            failed = 0

            for i, path in enumerate(to_process):
                name = path.name
                try:
                    content = path.read_text(encoding="utf-8")
                    front = _extract_section("Front", content)
                    if not front:
                        failed += 1
                        continue

                    # Step 1: AI description
                    desc_prompt = (
                        "You are a language learning assistant using the comprehensible input method. "
                        "Given a vocabulary word or phrase, create a single-sentence, vivid image description "
                        "that clearly illustrates its meaning in a natural scene. "
                        "Focus on the core meaning — avoid abstract metaphors. "
                        "Keep it under 80 words. Do NOT include any explanation, just the description.\n\n"
                        f"Vocabulary: {front}"
                    )
                    try:
                        description = asyncio.run(self._run_agent(desc_prompt)).strip()
                    except Exception as exc:
                        self._log_batch_progress(i, total, name, f"AI error: {exc}", False)
                        failed += 1
                        continue

                    # Step 2: Generate image via OpenRouter seedream
                    try:
                        r = requests.post(
                            "https://openrouter.ai/api/v1/images",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": "bytedance-seed/seedream-4.5",
                                "prompt": description,
                                "response_format": "b64_json",
                            },
                            timeout=180,
                        )
                        if r.status_code != 200:
                            self._log_batch_progress(i, total, name, f"Image HTTP {r.status_code}", False)
                            failed += 1
                            continue

                        data = r.json()
                        img_data = data.get("data", [])
                        if isinstance(img_data, list) and len(img_data) > 0:
                            img_b64 = img_data[0].get("b64_json", "")
                        elif isinstance(img_data, str):
                            img_b64 = img_data
                        else:
                            self._log_batch_progress(i, total, name, "No image in response", False)
                            failed += 1
                            continue

                        img_bytes = base64.b64decode(img_b64)
                    except Exception as exc:
                        self._log_batch_progress(i, total, name, f"Image error: {exc}", False)
                        failed += 1
                        continue

                    # Step 3: Save image
                    images_dir = path.parent / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = _re.sub(r"[^\w\-]", "_", front)[:40]
                    img_filename = f"batch-{safe_name}.png"
                    img_path = images_dir / img_filename
                    img_path.write_bytes(img_bytes)

                    # Step 4: Update markdown
                    content = _re.sub(r"\n*## Image\n.*?(?=\n#|\Z)", "", content, flags=_re.DOTALL)
                    md_ref = f"![image](images/{img_filename})"
                    content = content.rstrip() + f"\n\n## Image\n{md_ref}\n"
                    path.write_text(content, encoding="utf-8")

                    success += 1
                    self._log_batch_progress(i, total, name, "✓", True)

                except Exception as exc:
                    failed += 1
                    self._log_batch_progress(i, total, name, f"Error: {exc}", False)

            # Step 5: Update all to Anki
            final_msg = f"Batch done: {success} updated, {failed} failed."
            if success > 0:
                final_msg += " Updating Anki..."
                self.copilot_status_text.value = final_msg
                self.copilot_status_text.color = ft.Colors.BLUE_700
                self.page.update()

                output_path = Path(self.output_field.value.strip())
                if self._ensure_scripts():
                    cmd = [sys.executable, str(self.update_script), str(output_path)]
                    import subprocess
                    subprocess.run(cmd, capture_output=True, timeout=300)
                    final_msg = f"Batch done: {success} cards updated to Anki, {failed} failed."

            self.copilot_status_text.value = final_msg
            self.copilot_status_text.color = ft.Colors.GREEN_700 if failed == 0 else ft.Colors.ORANGE_700
            self.copilot_progress_ring.visible = False
            self.page.update()
            self._refresh_preview_files()

        threading.Thread(target=_worker, daemon=True).start()

    def _log_batch_progress(self, i: int, total: int, name: str, detail: str, ok: bool) -> None:
        """Update status bar with batch progress."""
        self.copilot_status_text.value = f"Batch: {i+1}/{total} — {name} {detail}"
        self.copilot_status_text.color = ft.Colors.BLUE_700 if ok else ft.Colors.ORANGE_700
        self.page.update()

    def _generate_image_description(self, _event: ft.ControlEvent | None = None) -> None:
        """Use AI to generate a vivid image description from the Front field,
        then open the image gen dialog with that description."""
        path = self.selected_preview_path
        if path is None:
            self._report_copilot_issue("No markdown file selected for preview.")
            return

        # Use the editable front content (already parsed and loaded)
        front = self.editable_front.value.strip() if self.editable_front.value else ""
        if not front:
            self._report_copilot_issue("No Front field found in the current note.")
            return

        self.copilot_status_text.value = "Generating image description..."
        self.copilot_status_text.color = ft.Colors.BLUE_700
        self.page.update()

        prompt = (
            "You are a language learning assistant using the comprehensible input method. "
            "Given a vocabulary word or phrase, create a single-sentence, vivid image description "
            "that clearly illustrates its meaning in a natural scene. "
            "Focus on the core meaning — avoid abstract metaphors. "
            "Keep it under 80 words. Do NOT include any explanation, just the description.\n\n"
            f"Vocabulary: {front}"
        )

        def _worker() -> None:
            import asyncio
            try:
                description = asyncio.run(self._run_agent(prompt)).strip()
            except Exception as exc:
                description = f"Error: {exc}"

            # Open image gen dialog with the generated description
            self._open_image_gen_dialog(initial_prompt=description)
            self.copilot_status_text.value = "Description ready."
            self.copilot_status_text.color = ft.Colors.GREEN_700
            self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _generate_image_from_front(self, _event: ft.ControlEvent | None = None) -> None:
        """Open image gen dialog pre-filled with the Front section of the current note."""
        path = self.selected_preview_path
        if path is None:
            self._report_copilot_issue("No markdown file selected for preview.")
            return

        markdown = self._md_cache.get(path)
        if markdown is None:
            try:
                markdown = path.read_text(encoding="utf-8")
                self._md_cache[path] = markdown
            except (OSError, UnicodeDecodeError) as exc:
                self._report_copilot_issue(f"Could not read {path.name}: {exc}")
                return

        # Extract ## Front section
        front_content = ""
        in_front = False
        for line in markdown.splitlines():
            if line.startswith("## Front"):
                in_front = True
                continue
            if in_front:
                if line.startswith("## ") or line.startswith("# "):
                    break
                stripped = line.strip()
                if stripped:
                    front_content = stripped
                    break

        if not front_content:
            self._report_copilot_issue("No Front field found in the current note.")
            return

        self._open_image_gen_dialog(initial_prompt=front_content)


    def _save_image_to_note(self, status_text: ft.Text | None = None) -> None:
        """Save the generated image to images/ folder and attach to the note's ## Image field."""
        url = getattr(self, '_gen_image_url', None)
        image_data = getattr(self, '_gen_image_data', None)
        path = getattr(self, '_gen_image_path', None)

        if not path:
            if status_text:
                status_text.value = "No generated image to attach."
                status_text.color = ft.Colors.RED_700
                self.page.update()
            return
        if not url and not image_data:
            if status_text:
                status_text.value = "No generated image data available."
                status_text.color = ft.Colors.RED_700
                self.page.update()
            return

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            if status_text:
                status_text.value = f"Could not read note: {exc}"
                status_text.color = ft.Colors.RED_700
                self.page.update()
            return

        # Determine images/ folder: same directory as the .md file
        images_dir = path.parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Generate a filename from the front content (sanitized)
        front_content = self.editable_front.value.strip() if self.editable_front.value else ""
        safe_name = re.sub(r"[^\w\-]", "_", front_content)[:40] if front_content else "image"
        ext = ".jpg"
        image_filename = f"gen-{safe_name}{ext}"

        # Download the image
        import requests

        if status_text:
            status_text.value = "Saving image..."
            status_text.color = ft.Colors.BLUE_700
            self.page.update()

        try:
            image_path = images_dir / image_filename
            if image_data:
                image_path.write_bytes(image_data)
            else:
                import requests
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                image_path.write_bytes(r.content)
        except Exception as exc:
            if status_text:
                status_text.value = f"Download failed: {exc}"
                status_text.color = ft.Colors.RED_700
                self.page.update()
            return

        # Remove existing ## Image section, then append new one with markdown reference
        content = re.sub(r"\n*## Image\n.*?(?=\n#|\Z)", "", content, flags=re.DOTALL)
        md_ref = f"![image](images/{image_filename})"
        content = content.rstrip() + f"\n\n## Image\n{md_ref}\n"

        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            if status_text:
                status_text.value = f"Could not write note: {exc}"
                status_text.color = ft.Colors.RED_700
                self.page.update()
            return

        # Update cache and editable preview fields
        self._md_cache[path] = content
        self.editable_image.value = md_ref
        # Show image preview via localhost server
        output_dir = Path(self.output_field.value.strip()).resolve()
        try:
            rel_dir = path.resolve().parent.relative_to(output_dir)
            self.editable_image_preview.src = f"http://localhost:8551/{rel_dir}/images/{image_filename}"
            self.editable_image_preview.visible = True
        except ValueError:
            pass

        self._append_log(f"Attached image to note: {path.name}")

        # Sync back to Anki
        _path = path
        _st = status_text

        def _on_anki_sync() -> None:
            self._append_log(f"Synced image to Anki: {_path.name}")
            if _st:
                _st.value = f"Attached to {_path.name} ✓ (synced to Anki)"
                _st.color = ft.Colors.GREEN_700
                self.page.update()

        cmd = [sys.executable, str(self.update_script), str(path)]
        self._run_in_thread("Save to Anki", cmd, on_success=_on_anki_sync)

        if status_text:
            status_text.value = f"Attached image to {path.name} ✓"
            status_text.color = ft.Colors.GREEN_700
            self.page.update()

        # Clear saved image ref
        self._gen_image_url = None
        self._gen_image_path = None


    def show_manage_workspace(self, _event: ft.ControlEvent | None = None) -> None:
        self.manage_workspace.visible = True
        self.preview_workspace.visible = False
        self.page.update()


    def show_preview_workspace(self, _event: ft.ControlEvent | None = None) -> None:
        # Auto-load file when user opens preview
        if self.selected_preview_path in self.preview_files:
            self._preview_markdown_file(self.selected_preview_path)
        elif self.preview_files:
            self._preview_markdown_file(self.preview_files[0])
        else:
            self.manage_workspace.visible = False
            self.preview_workspace.visible = True
            self.page.update()


    def _handle_output_dir_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.path:
            return
        self._set_output_directory(event.path)


    def _set_output_directory(self, path: str) -> None:
        self.output_field.value = path
        if not self.update_target_field.value.strip():
            self.update_target_field.value = path
        self._refresh_preview_files()


    def _handle_update_dir_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.path:
            return
        self._set_update_directory(event.path)


    def _set_update_directory(self, path: str) -> None:
        self.update_target_field.value = path
        self.page.update()


    def _handle_update_file_picked(self, event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            return
        self.update_target_field.value = event.files[0].path
        self.page.update()


    def choose_output_folder(self, _event: ft.ControlEvent) -> None:
        initial_directory = self._existing_directory(self.output_field.value)
        if sys.platform == "darwin":
            self._choose_macos_folder(
                "Choose export folder",
                initial_directory,
                self._set_output_directory,
            )
            return
        self.output_dir_picker.get_directory_path(
            dialog_title="Choose export folder",
            initial_directory=initial_directory,
        )


    def choose_update_folder(self, _event: ft.ControlEvent) -> None:
        initial_directory = self._existing_directory(
            self.update_target_field.value,
            self.output_field.value,
        )
        if sys.platform == "darwin":
            self._choose_macos_folder(
                "Choose notes folder to update",
                initial_directory,
                self._set_update_directory,
            )
            return
        self.update_dir_picker.get_directory_path(
            dialog_title="Choose notes folder to update",
            initial_directory=initial_directory,
        )


    def _choose_macos_folder(
        self,
        prompt: str,
        initial_directory: str,
        on_selected: Callable[[str], None],
    ) -> None:
        self._set_status("Opening macOS folder picker...", ft.Colors.BLUE_700)
        self._set_busy(True)

        def worker() -> None:
            try:
                result = subprocess.run(
                    [
                        "osascript",
                        "-e",
                        MACOS_FOLDER_PICKER_SCRIPT,
                        "--",
                        prompt,
                        initial_directory,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                self._report_issue("Could not open the macOS folder picker: osascript is missing.")
                self._set_busy(False)
                return
            except OSError as exc:
                self._report_issue(f"Could not open the macOS folder picker: {exc}")
                self._set_busy(False)
                return

            if result.returncode != 0:
                if "-128" in result.stderr:
                    self._set_status("Folder selection canceled.")
                else:
                    detail = result.stderr.strip() or "unknown error"
                    self._report_issue(f"Could not open the macOS folder picker: {detail}")
                self._set_busy(False)
                return

            selected_path = result.stdout.strip()
            if not selected_path or not Path(selected_path).is_dir():
                self._report_issue("The macOS folder picker returned an invalid folder.")
                self._set_busy(False)
                return

            on_selected(selected_path)
            self._set_status("Folder selected.", ft.Colors.GREEN_700)
            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()


    def choose_update_file(self, _event: ft.ControlEvent) -> None:
        self.update_file_picker.pick_files(
            dialog_title="Choose a Markdown note to update",
            allow_multiple=False,
            allowed_extensions=["md"],
            file_type=ft.FilePickerFileType.CUSTOM,
            initial_directory=self._existing_directory(
                self.update_target_field.value,
                self.output_field.value,
            ),
        )

