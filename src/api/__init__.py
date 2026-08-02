"""API layer — pure business logic (no Flet/ui imports).

Modules:
- agent.py    — LLM provider setup, agent building, async execution
- batch.py    — batch image generation orchestrator
- export.py   — export Anki notes to markdown files via apy
- image_gen.py — Pollinations.ai & OpenRouter image generation
- markdown.py — markdown note parsing, manipulation, prompt building
- parsing.py  — text parsing utilities (deck listing, query building)
- update.py   — create/update Anki notes from markdown files via apy
"""
