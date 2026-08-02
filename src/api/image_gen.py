"""Image Generation API — Pollinations.ai and OpenRouter backends.

All functions return raw image bytes — callers handle display, caching, etc.
"""

from __future__ import annotations

import base64
import urllib.parse

import requests

# Providers
PROVIDER_POLLINATIONS = "pollinations"
PROVIDER_OPENROUTER = "openrouter"

# Available OpenRouter image models with metadata
OPENROUTER_IMAGE_MODELS = [
    {"id": "black-forest-labs/flux.2-flex", "supports_dimensions": True},
    {"id": "black-forest-labs/flux.2-pro", "supports_dimensions": True},
    {"id": "black-forest-labs/flux.2-klein-4b", "supports_dimensions": True},
    {"id": "bytedance-seed/seedream-4.5", "supports_dimensions": False},
    {"id": "openai/gpt-image-2", "supports_dimensions": False},
]

# Preset dimension options (width × height, must be multiples of 16)
# Only used for models with supports_dimensions=True
IMAGE_DIMENSIONS = {
    "Small (512×384)":   (512, 384),
    "Medium (768×576)":  (768, 576),
    "Large (1024×768)":  (1024, 768),
    "HD (1360×768)":     (1360, 768),
    "FHD (1920×1088)":   (1920, 1088),
}


def generate_pollinations(
    prompt: str,
    width: int = 768,
    height: int = 576,
    timeout: int = 120,
) -> bytes:
    """Generate an image via Pollinations.ai (free, no API key required).

    Returns raw image bytes.
    """
    encoded = urllib.parse.quote(prompt, safe="")
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&nologo=true"
    )
    r = requests.get(image_url, timeout=timeout)
    r.raise_for_status()
    if len(r.content) <= 100:
        raise ValueError(f"Pollinations returned tiny response ({len(r.content)} bytes)")
    return r.content


def _build_or_payload(
    prompt: str,
    model: str,
    width: int | None,
    height: int | None,
) -> dict:
    """Build OpenRouter image gen payload, omitting dimensions if None."""
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "response_format": "b64_json",
    }
    if width is not None and height is not None:
        payload["width"] = width
        payload["height"] = height
    return payload


def generate_openrouter(
    prompt: str,
    api_key: str,
    model: str = "bytedance-seed/seedream-4.5",
    width: int | None = None,
    height: int | None = None,
    timeout: int = 180,
) -> bytes:
    """Generate an image via OpenRouter. Returns raw image bytes.

    Requires a valid OpenRouter API key (starts with sk-or-v1-...).
    width/height must be multiples of 16 if provided. If None, the model uses defaults.
    """
    if not api_key:
        raise ValueError("OpenRouter API key is required")

    r = requests.post(
        "https://openrouter.ai/api/v1/images",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=_build_or_payload(prompt, model, width, height),
        timeout=timeout,
    )
    r.raise_for_status()

    data = r.json()
    img_data = data.get("data", [])

    if isinstance(img_data, list) and len(img_data) > 0:
        img_b64 = img_data[0].get("b64_json", "")
    elif isinstance(img_data, str):
        img_b64 = img_data
    else:
        raise ValueError(f"No image in response: {data.get('error', data)}")

    if not img_b64:
        raise ValueError("Empty b64_json in response")

    return base64.b64decode(img_b64)
