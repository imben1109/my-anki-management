#!/bin/bash

# Script to list Anki notes using apy CLI
# Usage: ./list-anki-notes.sh <query> [line_limit]
# Example: ./list-anki-notes.sh 'deck:English'
# Example: ./list-anki-notes.sh 'deck:English' 40

QUERY=${1:-""}
LINE_LIMIT=${2:-""}

if [ -z "$QUERY" ]; then
  echo "Usage: $0 <query> [line_limit]"
  echo ""
  echo "Examples:"
  echo "  $0 'deck:English'"
  echo "  $0 'deck:English' 40"
  echo "  $0 'tag:marked'"
  exit 1
fi

if [ -n "$LINE_LIMIT" ]; then
  apy list-notes -v "$QUERY" | head -n "$LINE_LIMIT"
else
  apy list-notes -v "$QUERY"
fi
