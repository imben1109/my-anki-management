#!/bin/bash

# Script to update Anki notes using apy CLI
# Usage: ./update-anki-notes.sh <mode> <argument>
# Modes:
#   file <markdown_file>  - Update notes from markdown file
#   edit <query>          - Interactively edit notes matching query

MODE=${1:-""}
ARGUMENT=${2:-""}

if [ -z "$MODE" ] || [ -z "$ARGUMENT" ]; then
  echo "Usage: $0 <mode> <argument>"
  echo ""
  echo "Modes:"
  echo "  file <markdown_file>  - Update notes from markdown file"
  echo "                          e.g., $0 file notes.md"
  echo "  edit <query>          - Interactively edit notes matching query"
  echo "                          e.g., $0 edit \"deck:English\""
  exit 1
fi

case "$MODE" in
  file)
    if [ ! -f "$ARGUMENT" ]; then
      echo "Error: File not found: $ARGUMENT"
      exit 1
    fi
    TMPFILE=$(mktemp /tmp/anki-update-XXXXXX.md)
    trap 'rm -f "$TMPFILE"' EXIT
    python3 - "$ARGUMENT" "$TMPFILE" <<'PYEOF'
import re
import sys

source_path = sys.argv[1]
target_path = sys.argv[2]

with open(source_path, encoding="utf-8") as source_file:
    content = source_file.read().strip()


def split_notes(text):
    if re.search(r'^# Note', text, flags=re.MULTILINE):
        return [part.strip() for part in re.split(r'(?=^# Note)', text, flags=re.MULTILINE) if part.strip()]
    return [text]


def capture_value(pattern, text):
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def capture_section(name, text):
    match = re.search(rf'^## {re.escape(name)}\n(.*?)(?=^## |\Z)', text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


normalized_notes = []
for index, note in enumerate(split_notes(content), start=1):
    nid = capture_value(r'^# Note \(nid: ([^)]+)\)', note) or capture_value(r'^nid:\s*(.+)$', note)
    cid = capture_value(r'^cid:\s*(.+)$', note)
    model = capture_value(r'^model:\s*(.+)$', note)
    model = re.sub(r'\s+\([0-9]+ cards\)$', '', model)
    tags = capture_value(r'^tags:\s*(.*)$', note)
    front = capture_section('Front', note)
    back = capture_section('Back', note)

    normalized = []
    if model:
        normalized.append(f'model: {model}')
    normalized.append(f'tags: {tags}')
    if nid:
        normalized.append(f'nid: {nid}')
    elif cid:
        normalized.append(f'cid: {cid}')
    normalized.append('')
    normalized.append(f'# Note {index}')
    normalized.append('## Front')
    normalized.append(front)
    normalized.append('')
    normalized.append('## Back')
    normalized.append(back)
    normalized_notes.append('\n'.join(normalized).strip())

with open(target_path, 'w', encoding='utf-8') as target_file:
    target_file.write('\n\n'.join(normalized_notes) + '\n')
PYEOF
    apy update-from-file "$TMPFILE"
    ;;
  edit)
    apy edit "$ARGUMENT"
    ;;
  *)
    echo "Error: Unknown mode '$MODE'"
    echo "Valid modes: file, edit"
    exit 1
    ;;
esac
