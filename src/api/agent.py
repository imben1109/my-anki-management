"""AI Agent API — provider creation, agent building, and execution."""

from __future__ import annotations

import os

import eval_type_backport  # noqa: F401 — needed for Python 3.9 compat

# Monkey-patch: openai-agents is incompatible with newer openai SDKs that
# require cache_write_tokens on InputTokensDetails. Provide a default.
from openai.types.responses.response_usage import InputTokensDetails as _ITD

_orig_init = _ITD.__init__


def _patched_init(self, **kwargs):
    kwargs.setdefault("cache_write_tokens", 0)
    _orig_init(self, **kwargs)


_ITD.__init__ = _patched_init

from agents import Agent, Runner, RunConfig
from agents.models.openai_provider import OpenAIProvider


def create_agent_provider(
    api_key: str = "",
    base_url: str = "",
) -> OpenAIProvider:
    """Create an OpenAIProvider configured via AI_CHAT_* env vars or explicit params.

    Normalizes the DeepSeek anthropic endpoint to the /v1 Chat Completions format.
    """
    api_key = api_key or os.environ.get("AI_CHAT_API_KEY", "")
    base_url = base_url or os.environ.get("AI_CHAT_BASE_URL", "")

    # Normalize: strip /anthropic suffix for OpenAI Chat Completions format
    if "/anthropic" in base_url:
        base_url = base_url.replace("/anthropic", "/v1")

    if not base_url:
        base_url = "https://api.deepseek.com/v1"
    elif "://" not in base_url:
        base_url = f"https://{base_url}"

    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        use_responses=False,  # Chat Completions API
    )


def build_agent(
    model: str | None = None,
    tools: list | None = None,
) -> Agent:
    """Build the Anki assistant agent with the given model and tools."""
    model = model or os.environ.get("AI_CHAT_MODEL", "deepseek-chat")
    tools = tools or []

    return Agent(
        name="Anki Assistant",
        instructions=(
            "You are a helpful Anki note management assistant. "
            "You can list decks, count notes, help with study plans, "
            "and answer questions about the user's Anki collection. "
            "Keep responses concise and actionable."
        ),
        model=model,
        tools=tools,
    )


async def run_agent(
    prompt: str,
    provider: OpenAIProvider,
    agent: Agent | None = None,
) -> str:
    """Run the agent asynchronously and return the final output."""
    if agent is None:
        agent = build_agent()

    if not provider._stored_api_key:
        return (
            "Error: No API key configured.\n\n"
            "Set the AI_CHAT_API_KEY environment variable:\n"
            "  export AI_CHAT_API_KEY=sk-your-key-here\n\n"
            "Then restart the app."
        )

    config = RunConfig(model_provider=provider, tracing_disabled=True)
    result = await Runner.run(agent, prompt, run_config=config)
    return result.final_output
