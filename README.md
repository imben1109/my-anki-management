# My Anki Management

This project contains small helper scripts for managing Anki data with the `apy` command-line tool.

It is also structured as a GitHub Copilot skill repository, so the scripts can be invoked through GitHub Copilot in VS Code in addition to being run directly from the shell.

The repository currently supports three tasks:

1. List available Anki decks.
2. Export Anki notes to individual markdown files.
3. Update Anki note fields from a markdown file or interactively.

## What Is `apy`

`apy` is a CLI for working with an Anki collection from the terminal. It can read your Anki database, list notes and cards, inspect models, and perform other collection management tasks.

This project uses `apy` instead of talking to Anki directly.

## Prerequisites

Before using this project, make sure the following are available:

1. Anki is installed on your machine.
2. You have an existing Anki profile and collection.
3. `apy` is installed and available on your `PATH`.
4. `apy` is configured to point at your Anki data directory.
5. A POSIX shell such as `sh` or `bash` is available.
6. GitHub Copilot in VS Code, if you want to use the scripts through Copilot skills instead of running them manually.

## GitHub Copilot Integration

This repository includes GitHub Copilot skill definitions under `.github/skills`.

That means you can:

1. Run the shell scripts directly yourself.
2. Use GitHub Copilot in VS Code to trigger the deck, export, and update workflows.

The current Copilot skill folders are:

1. `.github/skills/anki-decks`
2. `.github/skills/anki-export`
3. `.github/skills/anki-update`

## Anki Collection Location

`apy` needs access to the Anki base directory.

Point it to the root directory that contains your Anki profiles and collection data.

## Configure `apy`

`apy` can be configured in one of these ways:

1. Set `APY_BASE` to your Anki base directory.
2. Set `ANKI_BASE` to your Anki base directory.
3. Create `~/.config/apy/apy.json` and store the base path there.

Example:

```json
{
  "base_path": "<path-to-anki-base-directory>"
}
```

You can verify that `apy` is working with:

```sh
apy -h
apy info
```

If `apy info` succeeds, the tool can see your Anki collection.

## Install `apy`

If `apy` is not installed yet, install it with your preferred Python package workflow.

Common options are:

```sh
pip install apy
```

or:

```sh
pipx install apy
```

After installation, confirm it is available:

```sh
apy -V
```

## Project Structure

```text
.github/skills/anki-decks/
.github/skills/anki-export/
.github/skills/anki-update/
```

Main scripts:

1. `.github/skills/anki-decks/list-anki-decks.sh`
2. `.github/skills/anki-export/export-anki-notes.sh`
3. `.github/skills/anki-update/update-anki-notes.sh`

## Usage

List decks:

```sh
cd .github/skills/anki-decks
sh list-anki-decks.sh
```

Export all notes in the `English` deck to markdown files:

```sh
cd .github/skills/anki-export
sh export-anki-notes.sh "deck:English" ./english-notes
```

Export notes matching any Anki query:

```sh
sh export-anki-notes.sh 'tag:leech' ./leeches
sh export-anki-notes.sh 'deck:English is:new' ./new-english
```

Update notes from a markdown file:

```sh
cd .github/skills/anki-update
sh update-anki-notes.sh file path/to/notes.md
```

Interactively edit notes matching a query:

```sh
sh update-anki-notes.sh edit "deck:English"
```

## Notes

1. The deck listing script extracts deck names from `apy info`.
2. The export script uses `apy list-notes -v` and saves each note as a separate `.md` file named after its Front field.
3. HTML tags in Back fields (`<ul>`, `<li>`, `<br>`, etc.) are converted to markdown during export.
4. The update script supports two modes: `file` (apply edits from a markdown file) and `edit` (open notes in your default editor).

## Troubleshooting

If `apy` is not found:

```sh
command -v apy
```

If the scripts cannot find your collection, check:

1. Your Anki profile exists.
2. `APY_BASE` or `ANKI_BASE` is set correctly, or `~/.config/apy/apy.json` is configured.
3. `apy info` runs successfully.

If the export script prints "No notes found", verify your query returns results with `apy list-notes -v "<query>"`.

If the update script fails, make sure the markdown file contains valid note headers in the format `# Note (nid: <id>)`.