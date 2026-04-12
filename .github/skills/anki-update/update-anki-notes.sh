#!/bin/bash

# Script to update Anki notes using apy CLI one by one
# Usage: ./update-anki-notes.sh <folder>

FOLDER=${1:-""}

if [ -z "$FOLDER" ]; then
  echo "Usage: $0 <folder>"
  echo ""
  echo "Updates all markdown notes in a folder one by one"
  echo "Example: $0 notes/CFA\ Level\ 1\ Derivatives"
  exit 1
fi

if [ ! -d "$FOLDER" ]; then
  echo "Error: Directory not found: $FOLDER"
  exit 1
fi

echo "Updating notes from folder: $FOLDER"
echo ""

file_count=0
success_count=0

for file in "$FOLDER"/*.md; do
  if [ -f "$file" ]; then
    file_count=$((file_count + 1))
    filename=$(basename "$file")
    echo -n "[$file_count] Updating: $filename ... "
    
    # Process individual file
    TMPFILE=$(mktemp /tmp/anki-update-XXXXXX.md)
    trap 'rm -f "$TMPFILE"' EXIT
    
    python3 - "$file" "$TMPFILE" <<'PYEOF'
import re
import sys

source_path = sys.argv[1]
target_path = sys.argv[2]

with open(source_path, encoding="utf-8") as source_file:
    content = source_file.read().strip()

def capture_value(pattern, text):
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""

def capture_section(name, text):
    match = re.search(rf'^## {re.escape(name)}\n(.*?)(?=^## |\Z)', text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""

nid = capture_value(r'^# Note \(nid: ([^)]+)\)', content) or capture_value(r'^nid:\s*(.+)$', content)
model = capture_value(r'^model:\s*(.+)$', content)
model = re.sub(r'\s+\([0-9]+ cards\)$', '', model)
tags = capture_value(r'^tags:\s*(.*)$', content)
front = capture_section('Front', content)
back = capture_section('Back', content)

normalized = []
if model:
    normalized.append(f'model: {model}')
normalized.append(f'tags: {tags}')
if nid:
    normalized.append(f'nid: {nid}')
normalized.append('')
normalized.append('# Note')
normalized.append('## Front')
normalized.append(front)
normalized.append('')
normalized.append('## Back')
normalized.append(back)

with open(target_path, 'w', encoding='utf-8') as target_file:
    target_file.write('\n'.join(normalized) + '\n')
PYEOF

    if apy update-from-file "$TMPFILE" > /dev/null 2>&1; then
      success_count=$((success_count + 1))
      echo "✓"
    else
      echo "✗"
    fi
    rm -f "$TMPFILE"
  fi
done

echo ""
echo "Summary: $success_count/$file_count files updated successfully"

