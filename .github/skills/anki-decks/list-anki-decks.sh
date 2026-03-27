#!/bin/bash

# Script to list Anki decks using apy CLI
# Usage: ./list-anki-decks.sh

# Extract the deck list from apy info output.
apy info | awk '
	/^Decks:/ { in_decks = 1; next }
	in_decks && /^Model[[:space:]]/ { exit }
	in_decks && /^  - / {
		sub(/^  - /, "")
		print
	}
'