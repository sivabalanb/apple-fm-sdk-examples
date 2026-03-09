#!/bin/bash
# PII Guardian — Claude Code Hook
# Blocks prompts containing PII before they reach Claude's API
# Reads UserPromptSubmit hook event JSON from stdin, extracts prompt, scans with pii_guardian.py

set -uo pipefail

# Extract the prompt from the JSON hook event
PROMPT=$(cat | jq -r '.prompt // ""')

# If prompt is empty, allow it
if [ -z "$PROMPT" ]; then
    exit 0
fi

# Write prompt to a temp file
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

echo "$PROMPT" > "$TEMP_FILE"

# Get the repo root (where pii_guardian.py lives) from the script's own location
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Scan with pii_guardian.py using Apple FM for contextual detection (batched/chunked to avoid context overflow)
# --hook outputs structured findings + masked prompt to stderr
if python3 "$REPO_ROOT/pii_guardian.py" scan "$TEMP_FILE" --fm --hook; then
    exit 0
else
    exit 2
fi
