"""Markdown note parsing and manipulation for Anki notes.

Pure backend logic — no Flet imports. Used by both CLI tools (export.py, update.py)
and the UI layer.
"""

from __future__ import annotations

import re
from pathlib import Path


def extract_section(name: str, text: str) -> str:
    """Extract the content of a ## section from markdown text."""
    pattern = rf"^## {re.escape(name)}(?:\s+\(markdown\))?\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_note_sections(text: str) -> dict:
    """Parse a markdown note into its structural components.

    Returns a dict with keys: title, meta_lines, front, back, image.
    title is the text after the "# " heading. meta_lines are the metadata
    lines between the title and the first ## section.
    """
    title_match = re.match(r"^# (.+)", text)
    title = title_match.group(1) if title_match else ""

    meta_lines: list[str] = []
    front_content = ""
    back_content = ""
    image_content = ""

    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    for i, section in enumerate(sections):
        section_stripped = section.strip()
        if section_stripped.startswith("Front"):
            front_content = section_stripped[len("Front"):].strip()
        elif section_stripped.startswith("Back"):
            back_content = section_stripped[len("Back"):].strip()
        elif section_stripped.startswith("Image"):
            image_content = section_stripped[len("Image"):].strip()
        elif i == 0:
            # Header block: skip the # title line, collect metadata
            lines = section.splitlines()
            for line in lines[1:]:
                line = line.strip()
                if line and not line.startswith("##"):
                    meta_lines.append(line)

    return {
        "title": title,
        "meta_lines": meta_lines,
        "front": front_content,
        "back": back_content,
        "image": image_content,
    }


def extract_image_ref(image_content: str) -> str:
    """Extract the image path from a markdown image reference.

    Returns the path like 'images/foo.png' or empty string.
    """
    match = re.search(r"!\[.*?\]\((images/[^)]+)\)", image_content)
    return match.group(1) if match else ""


def build_description_prompt(vocab_front: str) -> str:
    """Build the AI prompt for generating a vivid image description from vocabulary."""
    return (
        "You are a language learning assistant using the comprehensible input method. "
        "Given a vocabulary word or phrase, create a single-sentence, vivid image description "
        "that clearly illustrates its meaning in a natural scene. "
        "Focus on the core meaning — avoid abstract metaphors. "
        "Keep it under 80 words. Do NOT include any explanation, just the description.\n\n"
        f"Vocabulary: {vocab_front}"
    )


def rebuild_note_content(original_md: str, front: str, back: str, image: str) -> str:
    """Reconstruct markdown from original header + edited fields.

    Preserves the original header (everything before ## Front) and replaces
    the Front, Back, and Image sections with the edited content.
    """
    header_end = original_md.find("\n## Front")
    if header_end == -1:
        raise ValueError("Cannot find ## Front section in file.")
    header = original_md[:header_end]

    parts = [header, "\n## Front\n", front, "\n\n## Back\n", back, "\n"]
    if image:
        parts.extend(["## Image\n", image, "\n"])
    else:
        parts.append("## Image\n")
    return "".join(parts)


def save_image_and_update_note(
    path: Path,
    image_data: bytes,
    front_text: str,
) -> tuple[str, str]:
    """Save image bytes to images/ folder and update the note's ## Image section.

    Args:
        path: Path to the .md note file.
        image_data: Raw image bytes.
        front_text: The Front field content (used to generate filename).

    Returns:
        Tuple of (image_filename, new_markdown_content).
    """
    # Sanitize front text for filename
    safe_name = re.sub(r"[^\w\-]", "_", front_text)[:40] if front_text else "image"
    image_filename = f"gen-{safe_name}.png"

    # Ensure images/ directory
    images_dir = path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Write image
    image_path = images_dir / image_filename
    image_path.write_bytes(image_data)

    # Read current content
    content = path.read_text(encoding="utf-8")

    # Remove existing ## Image section, then append new one
    content = re.sub(r"\n*## Image\n.*?(?=\n#|\Z)", "", content, flags=re.DOTALL)
    md_ref = f"![image](images/{image_filename})"
    content = content.rstrip() + f"\n\n## Image\n{md_ref}\n"

    # Write back
    path.write_text(content, encoding="utf-8")

    return image_filename, content
