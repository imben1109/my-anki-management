#!/usr/bin/env python3
"""Export Anki notes to individual markdown files using apy CLI.

Usage:
  python3 export_anki_notes.py "<query>" [output_dir]

Examples:
  python3 export_anki_notes.py 'deck:"My Deck"'
  python3 export_anki_notes.py 'deck:"My Deck"' ./my-notes
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def usage() -> None:
    script = Path(sys.argv[0]).name
    print(f"Usage: {script} <query> [output_dir]")
    print("")
    print("Examples:")
    print(f"  {script} 'deck:\"My Deck\"'")
    print(f"  {script} 'deck:\"My Deck\"' ./my-notes")


def html_to_md(text: str) -> str:
    text = re.sub(r"<ul>", "", text)
    text = re.sub(r"</ul>", "", text)
    text = re.sub(r"<ol>", "", text)
    text = re.sub(r"</ol>", "", text)
    text = re.sub(r"<li>(.*?)</li>", r"- \1", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def find_media_dir() -> Path | None:
    """Locate Anki's collection.media directory from apy info output."""
    try:
        result = subprocess.run(
            ["apy", "info"], capture_output=True, text=True, check=False
        )
        # apy wraps long paths across multiple lines — join the full output
        # and extract with a regex that spans newlines.
        text = result.stdout
        m = re.search(r"Collection path:\s*(.+?\.anki2)", text, re.DOTALL)
        if m:
            collection_path = re.sub(r"\s+", " ", m.group(1)).strip()
            media_dir = Path(collection_path).parent / "collection.media"
            if media_dir.is_dir():
                return media_dir
    except Exception:
        pass
    return None


def copy_images(note: str, media_dir: Path, images_dir: Path) -> str:
    """Copy referenced images from Anki's media dir into images_dir and replace
    <img src="filename"> tags with relative markdown image references."""
    images_dir.mkdir(parents=True, exist_ok=True)

    def _replace(match: re.Match) -> str:
        src = match.group(1)
        img_path = media_dir / src
        if not img_path.exists():
            return match.group(0)
        dest = images_dir / src
        if not dest.exists():
            shutil.copy2(img_path, dest)
        return f"![image](images/{src})"

    return re.sub(r'<img\s+src="([^"]+)"[^>]*>', _replace, note)


def sanitize_name(value: str) -> str:
    value = re.sub(r"[^\w\s\-]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./anki-export"

    if not query:
        usage()
        return 1

    os.makedirs(output_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix="anki-export-", suffix=".md")
    os.close(fd)

    try:
        # Match shell script behavior: capture stdout+stderr into temp file.
        with open(tmp_path, "w", encoding="utf-8") as tmpfile:
            subprocess.run(
                ["apy", "list-notes", "-v", query],
                stdout=tmpfile,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
            )

        if os.path.getsize(tmp_path) == 0:
            print(f"No notes found for query: {query}")
            return 1

        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()

        notes = re.split(r"(?=^# Note \(nid:)", content, flags=re.MULTILINE)
        notes = [n.strip() for n in notes if n.strip()]

        created: list[str] = []

        media_dir = find_media_dir()

        for note in notes:
            # Capture only the Back field content — stop at the next `## Field`
            # header so other fields (e.g. Image) are not fed to html_to_md.
            note = re.sub(
                r"(## Back\n)(.*?)(?=\n## |\Z)",
                lambda m: m.group(1) + html_to_md(m.group(2)),
                note,
                flags=re.DOTALL,
            )

            nid_match = re.search(r"^# Note \(nid:\s*([^)]+)\)", note, re.MULTILINE)
            if not nid_match:
                nid_match = re.search(r"^nid:\s*(\d+)", note, re.MULTILINE)
            nid = nid_match.group(1).strip() if nid_match else "no-nid"
            safe_nid = sanitize_name(nid) or "no-nid"

            deck_match = re.search(r"^deck:\s*(.+)$", note, re.MULTILINE)
            deck = deck_match.group(1).strip() if deck_match else "Default"
            safe_deck = sanitize_name(deck) or "Default"
            deck_dir = os.path.join(output_dir, safe_deck)
            os.makedirs(deck_dir, exist_ok=True)

            # Copy referenced images into deck/images/ and replace src with
            # relative markdown paths (same model as Anki's collection.media).
            if media_dir:
                note = copy_images(note, media_dir, Path(deck_dir) / "images")

            front_match = re.search(r"## Front\n(.+?)(?=\n## |\Z)", note, re.DOTALL)
            front = front_match.group(1).strip() if front_match else "untitled"

            safe_front = sanitize_name(front)[:80] or "untitled"
            filename = f"{safe_nid}_{safe_front}"
            filepath = os.path.join(deck_dir, f"{filename}.md")

            if os.path.exists(filepath):
                filepath = os.path.join(deck_dir, f"{filename}_{len(created)}.md")

            with open(filepath, "w", encoding="utf-8") as out:
                out.write(note + "\n")

            created.append(os.path.join(deck, os.path.basename(filepath)))

        print(f"Exported {len(created)} notes to: {output_dir}")
        for name in created:
            print(f"  {name}")

        return 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    raise SystemExit(main())
