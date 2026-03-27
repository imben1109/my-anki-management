#!/bin/bash

# Script to export Anki notes to individual markdown files using apy CLI
# Usage: ./export-anki-notes.sh "<query>" [output_dir]
# Example: ./export-anki-notes.sh 'deck:"My Deck"' ./output

QUERY=${1:-""}
OUTPUT_DIR=${2:-"./anki-export"}

if [ -z "$QUERY" ]; then
  echo "Usage: $0 <query> [output_dir]"
  echo ""
  echo "Examples:"
  echo "  $0 'deck:\"My Deck\"'"
  echo "  $0 'deck:\"My Deck\"' ./my-notes"
  exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Export all matching notes to a temp file
TMPFILE=$(mktemp /tmp/anki-export-XXXXXX.md)
apy list-notes -v "$QUERY" > "$TMPFILE" 2>&1

if [ ! -s "$TMPFILE" ]; then
  echo "No notes found for query: $QUERY"
  rm -f "$TMPFILE"
  exit 1
fi

# Split into one file per note using Python
python3 - "$TMPFILE" "$OUTPUT_DIR" << 'PYEOF'
import re, os, sys

notes_file = sys.argv[1]
out_dir = sys.argv[2]

with open(notes_file) as f:
    content = f.read()

# Convert HTML lists to markdown
def html_to_md(text):
    text = re.sub(r'<ul>', '', text)
    text = re.sub(r'</ul>', '', text)
    text = re.sub(r'<ol>', '', text)
    text = re.sub(r'</ol>', '', text)
    text = re.sub(r'<li>(.*?)</li>', r'- \1', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)  # strip remaining tags
    return text.strip()

# Split on note headers
notes = re.split(r'(?=^# Note \(nid:)', content, flags=re.MULTILINE)
notes = [n.strip() for n in notes if n.strip()]

created = []
for note in notes:
    # Convert HTML in the Back field
    note = re.sub(
        r'(## Back\n)(.*?)(\Z|(?=^# Note))',
        lambda m: m.group(1) + html_to_md(m.group(2)) + ('\n' if m.group(3) else ''),
        note, flags=re.DOTALL | re.MULTILINE
    )
    # Extract front field for filename
    front_match = re.search(r'## Front\n(.+?)(?=\n## |\Z)', note, re.DOTALL)
    front = front_match.group(1).strip() if front_match else "untitled"
    # Sanitize filename
    filename = re.sub(r'[^\w\s\-]', '', front)
    filename = re.sub(r'\s+', ' ', filename).strip()[:80]
    filepath = os.path.join(out_dir, filename + ".md")
    # Handle duplicates
    if os.path.exists(filepath):
        nid_match = re.search(r'nid: (\d+)', note)
        nid = nid_match.group(1) if nid_match else str(len(created))
        filepath = os.path.join(out_dir, filename + f"_{nid}.md")
    with open(filepath, 'w') as f:
        f.write(note + "\n")
    created.append(os.path.basename(filepath))

print(f"Exported {len(created)} notes to: {out_dir}")
for name in created:
    print(f"  {name}")
PYEOF

rm -f "$TMPFILE"
