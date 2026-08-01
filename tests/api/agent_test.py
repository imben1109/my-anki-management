#!/usr/bin/env python3
"""Standalone test: OpenAI Agents SDK + configurable provider.

Usage:
    export AI_CHAT_API_KEY=sk-your-key
    export AI_CHAT_MODEL=deepseek-v4-pro
    python3 src/api/agent_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from agents import Agent, Runner, RunConfig, function_tool
from agents.models.openai_provider import OpenAIProvider


# ---------------------------------------------------------------------------
# Example tools (replace with real apy CLI calls in production)
# ---------------------------------------------------------------------------
@function_tool
def list_decks() -> str:
    """List all Anki decks in the collection."""
    return "Decks: English (50 notes), Math (30 notes), History (42 notes)"


@function_tool
def get_note_count(deck_name: str) -> str:
    """Get the number of notes in a given deck."""
    counts = {"english": 50, "math": 30, "history": 42}
    return f"Deck '{deck_name}' has {counts.get(deck_name.lower(), '?')} notes."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    api_key = os.environ.get("AI_CHAT_API_KEY", "")
    base_url = os.environ.get("AI_CHAT_BASE_URL", "")
    model = os.environ.get("AI_CHAT_MODEL", "deepseek-chat")

    if not api_key:
        print("ERROR: Set AI_CHAT_API_KEY environment variable.")
        sys.exit(1)

    # Normalize: strip /anthropic suffix for OpenAI Chat Completions format
    if "/anthropic" in base_url:
        base_url = base_url.replace("/anthropic", "/v1")
    if not base_url:
        base_url = "https://api.deepseek.com/v1"

    provider = OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        use_responses=False,  # Chat Completions API
    )

    agent = Agent(
        name="Anki Assistant",
        instructions=(
            "You are a helpful Anki note management assistant. "
            "You can list decks and count notes. Keep responses concise."
        ),
        model=model,
        tools=[list_decks, get_note_count],
    )

    config = RunConfig(model_provider=provider, tracing_disabled=True)

    print("=" * 60)
    print(f"Agent: {agent.name}  |  Model: {model}  |  Base: {base_url}")
    print(f"Tools: {[t.name for t in agent.tools]}")
    print("=" * 60)

    # Test 1: Simple chat (no tool needed)
    print("\n--- Test 1: Simple chat ---")
    result = await Runner.run(agent, "Hello! What can you help with?", run_config=config)
    print(f"Output: {result.final_output}")

    # Test 2: Tool-using run
    print("\n--- Test 2: Tool-using run ---")
    result = await Runner.run(agent, "What decks do I have?", run_config=config)
    print(f"Output: {result.final_output}")

    # Test 3: Streaming
    print("\n--- Test 3: Streaming ---")
    stream = Runner.run_streamed(agent, "Count notes in the English deck.", run_config=config)
    async for event in stream.stream_events():
        if event.type == "run_item_stream_event":
            if event.item.type == "message_output_item":
                from agents.items import ItemHelpers
                print(ItemHelpers.text_message_output(event.item), end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
