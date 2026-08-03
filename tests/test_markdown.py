"""Unit tests for src/api/markdown.py — note parsing, prompts, content rebuild."""

from __future__ import annotations

import pytest

from src.api.markdown import (
    extract_section,
    parse_note_sections,
    extract_image_ref,
    build_description_prompt,
    rebuild_note_content,
)


# ---------------------------------------------------------------------------
# extract_section
# ---------------------------------------------------------------------------
class TestExtractSection:
    def test_extract_front(self):
        text = "## Front\nhello world\n\n## Back\ngoodbye"
        assert extract_section("Front", text) == "hello world"

    def test_extract_back(self):
        text = "## Front\nhello\n\n## Back\ngoodbye"
        assert extract_section("Back", text) == "goodbye"

    def test_extract_image(self):
        text = "## Front\nhello\n\n## Back\nbye\n\n## Image\n![img](images/x.png)"
        assert extract_section("Image", text) == "![img](images/x.png)"

    def test_extract_missing_section(self):
        text = "## Front\nhello"
        assert extract_section("Back", text) == ""

    def test_extract_empty_section(self):
        text = "## Front\nhello\n\n## Back\n\n## Image"
        assert extract_section("Back", text) == ""

    def test_extract_with_markdown_tag(self):
        text = "## Front (markdown)\nhello\n\n## Back\nbye"
        assert extract_section("Front", text) == "hello"

    def test_extract_multiline(self):
        text = "## Front\nline 1\nline 2\nline 3\n\n## Back\nbye"
        assert extract_section("Front", text) == "line 1\nline 2\nline 3"


# ---------------------------------------------------------------------------
# parse_note_sections
# ---------------------------------------------------------------------------
class TestParseNoteSections:
    SAMPLE = (
        "# My Card\n"
        "model: Basic\n"
        "deck: English\n"
        "tags: vocab\n"
        "nid: 12345\n"
        "\n"
        "## Front\n"
        "apple\n"
        "\n"
        "## Back\n"
        "A round fruit\n"
        "\n"
        "## Image\n"
        "![image](images/apple.png)\n"
    )

    def test_title(self):
        result = parse_note_sections(self.SAMPLE)
        assert result["title"] == "My Card"

    def test_meta_lines(self):
        result = parse_note_sections(self.SAMPLE)
        assert "model: Basic" in result["meta_lines"]
        assert "deck: English" in result["meta_lines"]
        assert "tags: vocab" in result["meta_lines"]
        assert "nid: 12345" in result["meta_lines"]

    def test_front(self):
        result = parse_note_sections(self.SAMPLE)
        assert result["front"] == "apple"

    def test_back(self):
        result = parse_note_sections(self.SAMPLE)
        assert result["back"] == "A round fruit"

    def test_image(self):
        result = parse_note_sections(self.SAMPLE)
        assert result["image"] == "![image](images/apple.png)"

    def test_no_image_section(self):
        text = "# Card\n\n## Front\nhello\n\n## Back\nbye\n"
        result = parse_note_sections(text)
        assert result["image"] == ""

    def test_empty_note(self):
        result = parse_note_sections("")
        assert result["title"] == ""
        assert result["front"] == ""
        assert result["back"] == ""
        assert result["image"] == ""

    def test_title_only(self):
        result = parse_note_sections("# Just a title")
        assert result["title"] == "Just a title"
        assert result["front"] == ""


# ---------------------------------------------------------------------------
# extract_image_ref
# ---------------------------------------------------------------------------
class TestExtractImageRef:
    def test_extract_ref(self):
        assert extract_image_ref("![image](images/cat.png)") == "images/cat.png"

    def test_no_image(self):
        assert extract_image_ref("") == ""

    def test_non_image_text(self):
        assert extract_image_ref("Some random text") == ""

    def test_nested_path(self):
        assert extract_image_ref("![img](images/sub/folder/pic.jpg)") == "images/sub/folder/pic.jpg"


# ---------------------------------------------------------------------------
# build_description_prompt
# ---------------------------------------------------------------------------
class TestBuildDescriptionPrompt:
    def test_contains_vocab(self):
        result = build_description_prompt("apple")
        assert "Vocabulary: apple" in result
        assert "comprehensible input" in result
        assert "80 words" in result

    def test_empty_vocab(self):
        result = build_description_prompt("")
        assert "Vocabulary: " in result
        # Should still produce a valid prompt
        assert len(result) > 50

    def test_special_chars(self):
        result = build_description_prompt("café & croissant")
        assert "café & croissant" in result


# ---------------------------------------------------------------------------
# rebuild_note_content
# ---------------------------------------------------------------------------
class TestRebuildNoteContent:
    ORIGINAL = (
        "# My Card\n"
        "model: Basic\n"
        "nid: 12345\n"
        "\n"
        "## Front\n"
        "old front\n"
        "\n"
        "## Back\n"
        "old back\n"
        "\n"
        "## Image\n"
        "![image](images/old.png)\n"
    )

    def test_rebuild_with_image(self):
        result = rebuild_note_content(
            self.ORIGINAL,
            front="new front",
            back="new back",
            image="![image](images/new.png)",
        )
        assert "## Front\nnew front" in result
        assert "## Back\nnew back" in result
        assert "![image](images/new.png)" in result
        # Header preserved
        assert "# My Card" in result
        assert "model: Basic" in result

    def test_rebuild_without_image(self):
        result = rebuild_note_content(
            self.ORIGINAL,
            front="new front",
            back="new back",
            image="",
        )
        assert "## Front\nnew front" in result
        assert "## Back\nnew back" in result
        assert "## Image" in result
        # No dangling image reference
        assert "images/old.png" not in result

    def test_missing_front_header_raises(self):
        with pytest.raises(ValueError, match="Cannot find ## Front"):
            rebuild_note_content(
                "# No sections here\n",
                front="f", back="b", image="",
            )

    def test_preserves_original_header_exactly(self):
        """The header (everything before ## Front) stays unchanged."""
        result = rebuild_note_content(
            self.ORIGINAL,
            front="f", back="b", image="",
        )
        header = result[: result.find("\n## Front")]
        assert "# My Card" in header
        assert "model: Basic" in header
