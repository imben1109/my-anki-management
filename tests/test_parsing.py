"""Unit tests for src/api/parsing.py — deck listing and query building."""

from __future__ import annotations

import pytest

from src.api.parsing import parse_decks, deck_query


# ---------------------------------------------------------------------------
# parse_decks
# ---------------------------------------------------------------------------
class TestParseDecks:
    APY_INFO = (
        "Collection path: /Users/ben/Library/.../collection.anki2\n"
        "Decks:\n"
        "  - English\n"
        "  - Math\n"
        "  - History\n"
        "Model: Basic\n"
        "Notes: 100\n"
    )

    def test_parses_all_decks(self):
        decks = parse_decks(self.APY_INFO)
        assert decks == ["English", "Math", "History"]

    def test_empty_output(self):
        assert parse_decks("") == []

    def test_no_decks_section(self):
        text = "Collection path: /foo\nModel: Basic\n"
        assert parse_decks(text) == []

    def test_decks_but_no_model_header(self):
        """Should stop at end of string if no Model header found."""
        text = "Decks:\n  - Only\n"
        assert parse_decks(text) == ["Only"]

    def test_deck_with_spaces(self):
        text = "Decks:\n  - My Special Deck\nModel: Basic\n"
        assert parse_decks(text) == ["My Special Deck"]

    def test_deck_with_hyphen(self):
        text = "Decks:\n  - English-Vocab\n"
        assert parse_decks(text) == ["English-Vocab"]


# ---------------------------------------------------------------------------
# deck_query
# ---------------------------------------------------------------------------
class TestDeckQuery:
    def test_simple_deck(self):
        assert deck_query("English") == 'deck:"English"'

    def test_deck_with_spaces(self):
        assert deck_query("My Deck") == 'deck:"My Deck"'

    def test_deck_with_quotes(self):
        result = deck_query('deck "name"')
        assert result == 'deck:"deck \\"name\\""'

    def test_empty_deck(self):
        assert deck_query("") == 'deck:""'
