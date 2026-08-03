"""Unit tests for src/api/batch.py — batch image generation orchestration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.api.batch import filter_cards_to_process


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_note(dir_path: Path, name: str, front: str, image: str = "") -> Path:
    """Create a temporary .md note file for testing."""
    path = dir_path / f"{name}.md"
    parts = [f"# {name}", "", "## Front", front, "", "## Back", "back content"]
    if image:
        parts.extend(["", "## Image", image])
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# filter_cards_to_process
# ---------------------------------------------------------------------------
class TestFilterCardsToProcess:
    def test_missing_mode_skips_cards_with_images(self, tmp_path):
        _make_note(tmp_path, "card1", "apple", "![image](images/apple.png)")
        _make_note(tmp_path, "card2", "banana")  # no image
        _make_note(tmp_path, "card3", "cherry", "![image](images/cherry.png)")

        files = sorted(tmp_path.glob("*.md"))
        result = filter_cards_to_process(files, regenerate_all=False)

        assert len(result) == 1
        assert result[0].name == "card2.md"

    def test_regenerate_all_includes_all_with_front(self, tmp_path):
        _make_note(tmp_path, "card1", "apple", "![image](images/apple.png)")
        _make_note(tmp_path, "card2", "banana")
        _make_note(tmp_path, "card3", "cherry", "![image](images/cherry.png)")

        files = sorted(tmp_path.glob("*.md"))
        result = filter_cards_to_process(files, regenerate_all=True)

        assert len(result) == 3

    def test_empty_files(self):
        assert filter_cards_to_process([], regenerate_all=False) == []

    def test_files_with_no_front(self, tmp_path):
        path = tmp_path / "nofront.md"
        path.write_text("# No front\n\n## Back\nsome content\n", encoding="utf-8")
        result = filter_cards_to_process([path], regenerate_all=True)
        assert len(result) == 0

    def test_unreadable_file_skipped(self, tmp_path):
        _make_note(tmp_path, "good", "test front")
        bad = tmp_path / "bad.md"
        bad.write_text("garbage", encoding="utf-8")
        bad.chmod(0o000)  # remove all permissions
        try:
            result = filter_cards_to_process(sorted(tmp_path.glob("*.md")), regenerate_all=True)
            assert len(result) == 1
            assert result[0].name == "good.md"
        finally:
            bad.chmod(0o644)  # restore so cleanup works

    def test_nonexistent_file_skipped(self, tmp_path):
        _make_note(tmp_path, "good", "test")
        ghost = tmp_path / "ghost.md"
        result = filter_cards_to_process([tmp_path / "good.md", ghost], regenerate_all=True)
        assert len(result) == 1

    def test_all_have_images_missing_mode(self, tmp_path):
        _make_note(tmp_path, "card1", "a", "![img](x.png)")
        _make_note(tmp_path, "card2", "b", "![img](y.png)")
        files = sorted(tmp_path.glob("*.md"))
        result = filter_cards_to_process(files, regenerate_all=False)
        assert len(result) == 0
