---
name: anki-update
description: Update Anki notes one by one from a folder of markdown files.
---

# Anki Apy Update Notes Skill (One-by-One)

## When to Use
Update Anki notes individually from a folder. Perfect for syncing batch changes efficiently.

## Usage

```bash
./.github/skills/anki-update/update-anki-notes.sh <folder_path>
```

### Example
```bash
./.github/skills/anki-update/update-anki-notes.sh "notes/CFA Level 1 Derivatives"
```

### What It Does
- Scans the folder for all `.md` files
- Updates each note one by one in Anki
- Shows progress with a checkmark (✓) or X for each file
- Displays a summary count at the end

### Output
```
Updating notes from folder: notes/CFA Level 1 Derivatives

[1] Updating: Advantage of Derivative.md ... ✓
[2] Updating: Call Option.md ... ✓
[3] Updating: Derivative.md ... ✓
...
Summary: 29/29 files updated successfully
```

## Markdown File Format

Each `.md` file should have this structure:

```markdown
# Note (nid: <note_id>)

model: Basic (1 cards)
tags: 

## Front
Question or topic

## Back
Answer or definition
```

The script automatically extracts and normalizes these fields for Anki import.
