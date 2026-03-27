---
name: anki-export
description: Export Anki notes to individual markdown files, one file per note, named after the Front field. HTML in Back fields is converted to markdown.
---

# Anki Export Notes Skill

## When to Use
/export-anki-notes or "export Anki cards to markdown" or "save Anki notes as files".

## Workflow
1. Find the deck name (use anki-decks skill if unsure).
2. Create the output directory.
3. Run `./export-anki-notes.sh "<query>" <output_dir>`.
4. Each note becomes a separate `.md` file named after its Front field.

## Script Usage
```bash
./export-anki-notes.sh "<query>" [output_dir]
```

### Examples
```bash
# Export a specific deck
./export-anki-notes.sh 'deck:"My Deck"' ./my-deck

# Export notes with a tag
./export-anki-notes.sh 'tag:leech' ./leeches

# Export to default folder (./anki-export)
./export-anki-notes.sh 'deck:"English"'
```

## Output Format
Each note is saved as `<Front field>.md` with this structure:

```markdown
# Note (nid: 1234567890)

model: Basic (1 cards)
tags: 
created: 2026-02-21 22:42
modified: 2026-02-26 09:11
deck: My Deck

## Front
Note title / question

## Back
Answer content (HTML converted to markdown lists)
```

## Notes
- Duplicate front fields are disambiguated using the note ID suffix.
- HTML tags (`<ul>`, `<li>`, `<br>`, etc.) are converted to markdown.
- Requires `apy` and `python3` to be available on PATH.
