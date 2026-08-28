---
name: anki-list
description: List Anki notes matching a search query using the apy CLI.
---

# Anki List Notes Skill

## When to Use
/list-anki-notes or "list Anki notes" or "show notes in deck".

## Workflow
1. Find the deck name (use anki-decks skill if unsure).
2. Run `./list-anki-notes.sh "<query>"` to list matching notes.
3. Optionally pass a line limit as the second argument.

## Script Usage
```bash
./list-anki-notes.sh "<query>" [line_limit]
```

### Examples
```bash
# List all notes in a deck
./list-anki-notes.sh 'deck:English'

# List notes with a line limit
./list-anki-notes.sh 'deck:English' 40

# List notes by tag
./list-anki-notes.sh 'tag:marked'

# List new notes only
./list-anki-notes.sh 'deck:English is:new'
```

## Notes
- Returns all matching notes by default.
- Pass a line limit as the second argument to cap output length.
- Requires `apy` to be available on PATH.
