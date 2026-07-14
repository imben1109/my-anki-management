---
name: anki-list
description: Execute apy CLI via script to list Anki notes. Generates/runs shell commands, formats as tables.
---

# Anki Apy List Notes Skill

## When to Use
/list-anki-notes "deck:Japanese" or "show Anki cards tag:leech".

## Workflow
1. Use the skill entrypoint `./list-anki-notes.sh "[query]"`.
2. The script runs `apy list-notes -v` directly.
3. It accepts an optional second argument for line limit.
4. Pipe to awk/sed for table format.
5. Example: shell(./list-anki-notes.sh "deck:Japanese")

## Script Usage
./list-anki-notes.sh "query" | head -20
