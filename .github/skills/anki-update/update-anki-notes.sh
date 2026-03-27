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
    apy update-from-file "$ARGUMENT"
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
