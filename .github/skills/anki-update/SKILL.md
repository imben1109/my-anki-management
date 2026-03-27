---
name: anki-update
description: Update Front and Back fields in existing Anki notes via query or markdown file.
---

# Anki Apy Update Notes Skill

## When to Use
/update-anki-notes or "update Anki note fields" or "modify Anki cards".

## Workflow
1. Update notes from markdown file: `./update-anki-notes.sh file <markdown_file>`
2. Interactively edit notes matching a query: `./update-anki-notes.sh edit <query>`
3. Example: `./update-anki-notes.sh edit "deck:English"`

## Script Usage

### Update from Markdown File
```bash
./update-anki-notes.sh file path/to/notes.md
```

Markdown file format:
```
# Note (nid: <note_id>)

model: Basic
tags: 

## Front
Updated front content

## Back
Updated back content
```

### Edit Notes Interactively
```bash
./update-anki-notes.sh edit "deck:English"
```

Opens your default editor to modify notes matching the query.
