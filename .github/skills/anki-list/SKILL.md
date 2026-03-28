---
name: anki-list
description: Execute apy CLI via script to list Anki notes matching a search query. Supports any valid Anki search syntax and an optional line limit.
---

# Anki Apy List Notes Skill

## When to Use
/list-anki-notes or "list Anki cards" or "show notes in deck".

## Workflow
1. Find the deck name (use anki-decks skill if unsure).
2. Run `./list-anki-notes.sh "<query>"`.
3. Optionally pass a line limit as the second argument.

## Script Usage
```bash
./list-anki-notes.sh "<query>" [line_limit]
```

### Examples
```bash
# List all notes in the English deck
./list-anki-notes.sh "deck:English"

# List up to 40 lines
./list-anki-notes.sh "deck:English" 40

# List notes with a specific tag
./list-anki-notes.sh "tag:marked"

# List new notes in a deck
./list-anki-notes.sh "deck:English is:new"
```

## Notes
- Uses `apy list-notes -v` to retrieve full note content.
- Returns all matching notes by default.
- Pass a second argument to limit the number of output lines.
