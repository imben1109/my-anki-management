"""Batch image generation orchestrator.

Pure backend orchestration — calls api functions, performs file I/O.
Takes callbacks for progress reporting and agent running so it has zero
Flet dependency.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from src.api.markdown import extract_section, build_description_prompt
from src.api.image_gen import generate_pollinations, generate_openrouter


def process_single_card(
    path: Path,
    provider: str,
    model: str,
    width: int | None,
    height: int | None,
    api_key: str,
    agent_runner: Callable[[str], str],
) -> tuple[bool, str]:
    """Process a single card: AI description → image gen → save to file.

    Args:
        path: Path to the .md note file.
        provider: Image provider ('pollinations' or 'openrouter').
        model: Model ID for OpenRouter (ignored for Pollinations).
        width/height: Image dimensions (None to use defaults).
        api_key: OpenRouter API key (for provider='openrouter').
        agent_runner: Async function that runs the AI agent and returns a string.

    Returns:
        Tuple of (success: bool, detail: str).
    """
    import asyncio

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, "Cannot read file"

    front = extract_section("Front", content)
    if not front:
        return False, "No Front field"

    # Step 1: AI description
    desc_prompt = build_description_prompt(front)
    try:
        description = asyncio.run(agent_runner(desc_prompt)).strip()
    except Exception as exc:
        return False, f"AI error: {exc}"

    # Step 2: Generate image
    try:
        if provider == "openrouter":
            img_bytes = generate_openrouter(
                description, api_key, model=model,
                width=width, height=height,
            )
        else:
            img_bytes = generate_pollinations(
                description,
                width=width if width else 768,
                height=height if height else 576,
            )
    except Exception as exc:
        return False, f"Image error: {exc}"

    # Step 3: Save image and update note
    images_dir = path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-]", "_", front)[:40]
    img_filename = f"batch-{safe_name}.png"
    img_path = images_dir / img_filename
    img_path.write_bytes(img_bytes)

    # Remove existing ## Image and append new
    content = re.sub(r"\n*## Image\n.*?(?=\n#|\Z)", "", content, flags=re.DOTALL)
    md_ref = f"![image](images/{img_filename})"
    content = content.rstrip() + f"\n\n## Image\n{md_ref}\n"
    path.write_text(content, encoding="utf-8")

    return True, "\u2713"


def sync_to_anki(output_dir: str, update_script: Path) -> tuple[bool, str]:
    """Run apy update-from-file for all notes in the output directory.

    Returns (success, message).
    """
    try:
        result = subprocess.run(
            [sys.executable, str(update_script), output_dir],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, "Synced to Anki"
        return False, f"Anki sync failed (exit {result.returncode})"
    except Exception as exc:
        return False, f"Anki sync error: {exc}"
