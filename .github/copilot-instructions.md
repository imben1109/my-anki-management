# Copilot Instructions for my-anki-management

This file provides guidance for Copilot when working in this repository.

## Project Overview

An Anki note management tool with a Flet-based web UI. Uses `apy` CLI to interact with Anki's database.

- **Export**: Convert Anki notes to individual markdown files (one per note)
- **Update**: Push changes from markdown files back to Anki
- **Preview**: Built-in markdown preview with image support
- **Copilot Panel**: Chat with GitHub Copilot CLI from within the app

## Key Tools

### apy CLI

`apy` is the bridge to Anki. Key commands:

```sh
apy info                          # Collection info + path
apy list-notes -v "deck:English"  # List notes with full content
apy list-decks                    # List all decks
```

The collection path from `apy info` reveals where `collection.media/` lives (images).

### Flet Web App

The UI runs as a Flet web app on port 8550:

```sh
python3 src/web.py
```

Entry points:
- `src/web.py` — Launcher, sets view to `WEB_BROWSER`
- `src/ui/app.py` — Main app class, builds layout
- `src/ui/decks.py` — `_DecksMixin` with export/update/preview logic
- `src/ui/copilot.py` — Copilot chat panel
- `src/ui/image_gen.py` — AI image generation panel
- `src/api/export.py` — Export script (also usable standalone)
- `src/api/update.py` — Update script (also usable standalone)

### Export Script (standalone)

```sh
python3 src/api/export.py 'deck:"English"' anki-export
```

Output structure:
```
anki-export/
└── English/
    ├── images/                          # Copied from Anki's collection.media/
    │   └── paste-bfff9159....jpg
    ├── 1771152458558_curate.md          # Uses ![image](images/filename.jpg)
    └── ...
```

### Image Handling

Anki stores images as loose files in `collection.media/` and references them as `<img src="filename.jpg">` in note data.

The export pipeline:
1. Parse `apy info` to find `collection.media/` path (handles multi-line wrapping)
2. Copy referenced images to `deck/images/` relative to exported .md files
3. Replace `<img src="filename">` with `![image](images/filename)` in markdown

Images are stored alongside the markdown files — the same model Anki uses. No base64 embedding. The markdown files reference images via relative paths and display correctly in any local markdown viewer.

### Available Skills

- `anki-decks` — List Anki decks via `apy list-decks`
- `anki-list` — List Anki notes via `apy list-notes -v`
- `anki-export` — Export notes to markdown files
- `anki-update` — Update notes from markdown files

## Automated UI Testing with playwright-cli

When `playwright-cli` is installed, use it to verify UI changes end-to-end before reporting completion.

### Setup

```sh
npm install -g @playwright/cli
```

### Workflow

1. **Start the app**: `python3 src/web.py` (background, port 8550)
2. **Open in playwright**: `playwright-cli open http://localhost:8550`
3. **Enable accessibility**: Flet renders on a Flutter canvas — click "Enable accessibility" to convert to DOM elements. Use `playwright-cli eval "document.querySelector('[aria-label=\"Enable accessibility\"]').click()"` if the button is out of viewport.
4. **Interact** using `playwright-cli snapshot`, `click`, `fill`, `eval`, etc.
5. **Screenshot** with `playwright-cli screenshot` for visual verification
6. **Close** with `playwright-cli close` when done

### Common Patterns

```sh
# Get current page state
playwright-cli snapshot

# Fill a text field and trigger search
playwright-cli fill <ref> "search text"

# Click a button by ref
playwright-cli click <ref>

# Execute JavaScript (e.g., for elements outside viewport)
playwright-cli eval "document.querySelector('[aria-label=\"...\"]').click()"

# Take a screenshot
playwright-cli screenshot

# Resize viewport
playwright-cli resize 1280 900
```

### Important Notes

- Flet 0.28.2 renders on a Flutter canvas — the "Enable accessibility" button is required for DOM-based interaction
- Elements may be outside the viewport — use `resize` or `eval` for JS clicks
- The app uses `page.open(dialog)` / `page.close(dialog)` for non-blocking dialogs (not `page.dialog`)
- Exported files go to `anki-export/` by default (gitignored)

## Commit Convention

Include `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` in commit messages.
