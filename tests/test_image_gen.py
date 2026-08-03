"""Unit tests for src/api/image_gen.py — image generation API."""

from __future__ import annotations

import pytest

from src.api.image_gen import (
    PROVIDER_POLLINATIONS,
    PROVIDER_OPENROUTER,
    OPENROUTER_IMAGE_MODELS,
    IMAGE_DIMENSIONS,
    _build_or_payload,
    model_supports_dimensions,
)


# ---------------------------------------------------------------------------
# _build_or_payload
# ---------------------------------------------------------------------------
class TestBuildOrPayload:
    def test_with_dimensions(self):
        payload = _build_or_payload(
            "a cat", model="flux", width=768, height=576,
        )
        assert payload["model"] == "flux"
        assert payload["prompt"] == "a cat"
        assert payload["response_format"] == "b64_json"
        assert payload["width"] == 768
        assert payload["height"] == 576

    def test_without_dimensions(self):
        payload = _build_or_payload(
            "a dog", model="seedream", width=None, height=None,
        )
        assert "width" not in payload
        assert "height" not in payload


# ---------------------------------------------------------------------------
# model_supports_dimensions
# ---------------------------------------------------------------------------
class TestModelSupportsDimensions:
    def test_pollinations_always_supports(self):
        assert model_supports_dimensions(PROVIDER_POLLINATIONS, "") is True

    def test_flux_models_support(self):
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "black-forest-labs/flux.2-flex") is True
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "black-forest-labs/flux.2-pro") is True
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "black-forest-labs/flux.2-klein-4b") is True

    def test_seedream_does_not_support(self):
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "bytedance-seed/seedream-4.5") is False

    def test_gpt_image_does_not_support(self):
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "openai/gpt-image-2") is False

    def test_unknown_model_defaults_false(self):
        assert model_supports_dimensions(PROVIDER_OPENROUTER, "unknown/model") is False


# ---------------------------------------------------------------------------
# IMAGE_DIMENSIONS structure
# ---------------------------------------------------------------------------
class TestImageDimensions:
    def test_all_dimensions_are_tuples(self):
        for key, value in IMAGE_DIMENSIONS.items():
            assert isinstance(value, tuple), f"{key} should be a tuple"
            assert len(value) == 2, f"{key} should have width and height"
            assert isinstance(value[0], int)
            assert isinstance(value[1], int)

    def test_dimensions_multiples_of_16(self):
        """Flux requires multiples of 16."""
        for key, (w, h) in IMAGE_DIMENSIONS.items():
            assert w % 16 == 0, f"{key} width {w} not multiple of 16"
            assert h % 16 == 0, f"{key} height {h} not multiple of 16"


# ---------------------------------------------------------------------------
# OPENROUTER_IMAGE_MODELS structure
# ---------------------------------------------------------------------------
class TestOpenRouterModels:
    def test_all_models_have_id_and_flag(self):
        for model in OPENROUTER_IMAGE_MODELS:
            assert "id" in model
            assert "supports_dimensions" in model
            assert isinstance(model["supports_dimensions"], bool)

    def test_model_ids_are_unique(self):
        ids = [m["id"] for m in OPENROUTER_IMAGE_MODELS]
        assert len(ids) == len(set(ids))
