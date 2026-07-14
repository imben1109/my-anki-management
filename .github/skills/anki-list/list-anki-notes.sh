#!/bin/bash

# Script to list Anki notes using apy CLI
# Usage: ./list-anki-notes.sh "<query>" [line_limit]

QUERY=${1:-""}
LINE_LIMIT=${2:-""}

if [ -z "$QUERY" ]; then
	echo "Usage: $0 <query> [line_limit]"
	echo ""
	echo "Examples:"
	echo "  $0 'deck:English'"
	echo "  $0 'deck:English' 40"
	exit 1
fi

if [ -n "$LINE_LIMIT" ]; then
	if ! [[ "$LINE_LIMIT" =~ ^[0-9]+$ ]]; then
		echo "Error: line_limit must be a positive integer"
		exit 1
	fi
	apy list-notes -v "$QUERY" | head -n "$LINE_LIMIT"
else
	apy list-notes -v "$QUERY"
fi
