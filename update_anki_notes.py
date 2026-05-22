#!/usr/bin/env python3
"""Create or update Anki notes from markdown files using apy.

Usage:
  python3 update_anki_notes.py <path>

Examples:
  python3 update_anki_notes.py Equity/s/-_2.md
  python3 update_anki_notes.py Equity/s
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def capture_value(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def capture_section(name: str, text: str) -> str:
    pattern = rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def normalize_note_content(content: str) -> str:
    content = content.strip()

    nid = capture_value(r"^# Note \(nid: ([^)]+)\)", content) or capture_value(
        r"^nid:\s*(.+)$", content
    )
    model = capture_value(r"^model:\s*(.+)$", content)
    model = re.sub(r"\s+\([0-9]+ cards\)$", "", model)
    tags = capture_value(r"^tags:\s*(.*)$", content)
    front = capture_section("Front", content)
    back = capture_section("Back", content)

    normalized: list[str] = []
    if model:
        normalized.append(f"model: {model}")
    normalized.append(f"tags: {tags}")
    if nid:
        normalized.append(f"nid: {nid}")
    normalized.append("")
    normalized.append("# Note")
    normalized.append("## Front")
    normalized.append(front)
    normalized.append("")
    normalized.append("## Back")
    normalized.append(back)

    return "\n".join(normalized) + "\n"


def has_note_id(content: str) -> bool:
    return bool(
        capture_value(r"^# Note \(nid: ([^)]+)\)", content)
        or capture_value(r"^nid:\s*(.+)$", content)
        or capture_value(r"^cid:\s*(.+)$", content)
    )


def update_note_file(md_file: Path) -> tuple[bool, str]:
    with md_file.open("r", encoding="utf-8") as source_file:
        content = source_file.read()

    action = "UPDATE" if has_note_id(content) else "CREATE"

    normalized = normalize_note_content(content)

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(normalized)
        tmp_path = Path(tmp.name)

    try:
        result = subprocess.run(
            ["apy", "update-from-file", str(tmp_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return result.returncode == 0, action
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def collect_md_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".md":
        return [path]
    if path.is_dir():
        return sorted(p for p in path.glob("*.md") if p.is_file())
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update Anki notes from a markdown file or folder via apy."
    )
    parser.add_argument("path", help="Path to a .md file or directory containing .md files")
    args = parser.parse_args()

    target_path = Path(args.path)

    if not target_path.exists():
        print(f"Error: Path not found: {target_path}")
        return 1

    md_files = collect_md_files(target_path)
    if not md_files:
        print("No markdown files found to update")
        return 1

    print(f"Applying notes from: {target_path}")
    print("")

    success_count = 0
    for index, md_file in enumerate(md_files, start=1):
        ok, action = update_note_file(md_file)
        print(f"[{index}] {action}: {md_file.name} ... ", end="", flush=True)
        if ok:
            success_count += 1
            print("OK")
        else:
            print("FAIL")

    print("")
    print(f"Summary: {success_count}/{len(md_files)} files updated successfully")

    return 0 if success_count == len(md_files) else 1


if __name__ == "__main__":
    sys.exit(main())
