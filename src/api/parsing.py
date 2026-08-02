"""Text parsing utilities for Anki management.

Pure backend logic — no Flet imports. Used by both CLI tools and the UI layer.
"""

from __future__ import annotations


def parse_decks(apy_info: str) -> list[str]:
    """Parse deck names from `apy info` output."""
    decks: list[str] = []
    in_decks = False
    for raw_line in apy_info.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("Decks:"):
            in_decks = True
            continue
        if in_decks and line.startswith("Model"):
            break
        if in_decks and line.startswith("  - "):
            decks.append(line.replace("  - ", "", 1).strip())
    return decks


def deck_query(deck_name: str) -> str:
    """Build an Anki query string for a deck name."""
    escaped = deck_name.replace('"', r"\"")
    return f'deck:"{escaped}"'
