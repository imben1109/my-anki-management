"""AI Agent chat — replaces Copilot CLI with OpenAI Agents SDK + DeepSeek."""

from __future__ import annotations

import asyncio
import os
import threading
import uuid

import flet as ft

import eval_type_backport  # noqa: F401 — needed for Python 3.9 compat

# Monkey-patch: openai-agents is incompatible with newer openai SDKs that
# require cache_write_tokens on InputTokensDetails. Provide a default.
from openai.types.responses.response_usage import InputTokensDetails as _ITD

_orig_init = _ITD.__init__
def _patched_init(self, **kwargs):
    kwargs.setdefault("cache_write_tokens", 0)
    _orig_init(self, **kwargs)
_ITD.__init__ = _patched_init

from agents import Agent, Runner, RunConfig, function_tool
from agents.models.openai_provider import OpenAIProvider


class _AgentChatMixin:
    """Mixin providing the AI agent chat dialog (OpenAI Agents SDK + DeepSeek)."""

    # ------------------------------------------------------------------
    # Agent setup (lazy — created once per session)
    # ------------------------------------------------------------------
    def _get_agent_provider(self) -> OpenAIProvider:
        """Return a cached OpenAIProvider configured via AI_CHAT_* env vars."""
        if not hasattr(self, "_agent_provider"):
            api_key = os.environ.get("AI_CHAT_API_KEY", "")
            base_url = os.environ.get("AI_CHAT_BASE_URL", "")

            # Normalize: strip /anthropic suffix for OpenAI Chat Completions format
            if "/anthropic" in base_url:
                base_url = base_url.replace("/anthropic", "/v1")

            if not base_url:
                base_url = "https://api.deepseek.com/v1"
            elif "://" not in base_url:
                base_url = f"https://{base_url}"

            self._agent_provider = OpenAIProvider(
                api_key=api_key,
                base_url=base_url,
                use_responses=False,  # Chat Completions API
            )
        return self._agent_provider

    def _build_agent(self) -> Agent:
        """Build the Anki assistant agent with tools."""
        model = os.environ.get("AI_CHAT_MODEL", "deepseek-chat")
        return Agent(
            name="Anki Assistant",
            instructions=(
                "You are a helpful Anki note management assistant. "
                "You can list decks, count notes, help with study plans, "
                "and answer questions about the user's Anki collection. "
                "Keep responses concise and actionable."
            ),
            model=model,
            tools=[],  # Add tools like list_decks, get_note_count, etc.
        )

    # ------------------------------------------------------------------
    # Dialog
    # ------------------------------------------------------------------
    def _open_agent_chat_dialog(self, _event: ft.ControlEvent | None = None) -> None:
        """Open the AI agent chat popup dialog."""
        dialog_prompt = ft.TextField(
            label="Ask AI Assistant",
            hint_text="e.g. list all decks, create a study plan...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            on_submit=lambda e: self._send_agent_message(
                dialog_prompt, dialog_output, dialog_status, dialog_ring
            ),
        )
        dialog_output = ft.Text(
            value="\n".join(self.copilot_log_lines),
            size=13,
            font_family="monospace",
            selectable=True,
        )
        dialog_output_container = ft.Container(
            content=ft.Column(
                controls=[dialog_output],
                scroll=ft.ScrollMode.AUTO,
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            padding=10,
            expand=True,
            height=300,
        )
        dialog_status = ft.Text("Ready.", color=ft.Colors.ON_SURFACE_VARIANT)
        dialog_ring = ft.ProgressRing(width=16, height=16, visible=False)

        def send_from_dialog(e: ft.ControlEvent) -> None:
            self._send_agent_message(dialog_prompt, dialog_output, dialog_status, dialog_ring)

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Text("AI Assistant", size=20, weight=ft.FontWeight.BOLD),
                    ft.TextButton(
                        "New conversation",
                        on_click=lambda e: self._reset_agent_chat(dialog_output, dialog_status),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=ft.Column(
                controls=[
                    dialog_prompt,
                    ft.Row(
                        controls=[
                            ft.FilledButton("Send", icon=ft.Icons.SEND, on_click=send_from_dialog),
                            ft.Row(controls=[dialog_ring, dialog_status], spacing=8),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    dialog_output_container,
                ],
                spacing=12,
                width=700,
                height=550,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
            on_dismiss=lambda e: self._on_agent_dialog_dismiss(dialog_output),
        )

        self._agent_dialog = dialog
        self.page.open(dialog)

    def _send_agent_message(
        self,
        prompt_field: ft.TextField,
        output_field: ft.Text,
        status_text: ft.Text,
        progress_ring: ft.ProgressRing,
    ) -> None:
        """Send a prompt to the AI agent via OpenAI Agents SDK."""
        prompt = prompt_field.value.strip()
        if not prompt:
            status_text.value = "Enter a prompt first."
            status_text.color = ft.Colors.RED_700
            self.page.update()
            return

        prompt_field.value = ""
        status_text.value = "Thinking..."
        status_text.color = ft.Colors.BLUE_700
        progress_ring.visible = True
        self.page.update()

        import asyncio as _asyncio

        def _run_and_update() -> None:
            output = ""
            try:
                output = _asyncio.run(self._run_agent(prompt))
            except Exception as exc:
                import traceback
                output = f"Error: {exc}\n{traceback.format_exc()}"

            self.copilot_log_lines.append(f"> {prompt}")
            self.copilot_log_lines.append(output)
            self.copilot_log_lines.append("")
            output_field.value = "\n".join(self.copilot_log_lines)
            status_text.value = "Done."
            status_text.color = ft.Colors.GREEN_700
            progress_ring.visible = False
            self.page.update()

        self.page.run_thread(_run_and_update)

    async def _run_agent(self, prompt: str) -> str:
        """Run the agent asynchronously and return the final output."""
        provider = self._get_agent_provider()

        if not provider._stored_api_key:
            return (
                "Error: No API key configured.\n\n"
                "Set the AI_CHAT_API_KEY environment variable:\n"
                "  export AI_CHAT_API_KEY=sk-your-key-here\n\n"
                "Then restart the app."
            )

        agent = self._build_agent()
        config = RunConfig(model_provider=provider, tracing_disabled=True)

        result = await Runner.run(agent, prompt, run_config=config)
        return result.final_output

    def _reset_agent_chat(
        self, output_field: ft.Text, status_text: ft.Text
    ) -> None:
        """Reset the conversation from the dialog."""
        self.copilot_session_id = str(uuid.uuid4())
        self.copilot_log_lines = ["Started a new AI assistant conversation.", ""]
        output_field.value = "\n".join(self.copilot_log_lines)
        status_text.value = "New conversation started."
        status_text.color = ft.Colors.GREEN_700
        self.page.update()

    def _on_agent_dialog_dismiss(self, output_field: ft.Text) -> None:
        """Sync dialog state back to main log field."""
        self._agent_dialog = None
        self.copilot_log_field.value = output_field.value

    # ------------------------------------------------------------------
    # Inline chat (preview workspace) — delegates to dialog approach
    # ------------------------------------------------------------------
    def reset_copilot_conversation(
        self, _event: ft.ControlEvent | None = None
    ) -> None:
        """Reset the conversation (inline panel)."""
        self.copilot_session_id = str(uuid.uuid4())
        self.copilot_prompt_field.value = ""
        self._append_copilot_log("Started a new AI assistant conversation.")
        self._set_copilot_status(
            "Started a new AI assistant conversation.", ft.Colors.GREEN_700
        )

    def ask_copilot(self, _event: ft.ControlEvent | None = None) -> None:
        """Send a prompt from the inline copilot panel."""
        prompt = self.copilot_prompt_field.value.strip()
        if not prompt:
            self._report_copilot_issue("Enter a prompt for the AI assistant first.")
            return

        self.copilot_prompt_field.value = ""
        self._set_copilot_status("Thinking...", ft.Colors.BLUE_700)
        self._set_copilot_busy(True)
        self.page.update()

        async def _run_and_update() -> None:
            output = ""
            try:
                output = await self._run_agent(prompt)
            except Exception as exc:
                import traceback
                output = f"Error: {exc}\n{traceback.format_exc()}"

            self._append_copilot_log(f"> {prompt}")
            self._append_copilot_log(output)
            self._append_copilot_log("")
            self._set_copilot_status("Done.", ft.Colors.GREEN_700)
            self._set_copilot_busy(False)
            self.page.update()

        self.page.run_task(_run_and_update)
