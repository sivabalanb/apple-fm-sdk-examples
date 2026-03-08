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
if python3 "$REPO_ROOT/pii_guardian.py" scan "$TEMP_FILE" --fm > /dev/null; then
    # Exit 0 means no PII found — allow the prompt
    exit 0
else
    # Exit code 1 from pii_guardian means PII detected — block the prompt
    echo "🚨 PII DETECTED — Prompt contains sensitive data (SSN, credit card, email, phone, API key)" >&2
    echo "   Privacy check blocked this prompt to protect your data." >&2
    echo "   Please remove sensitive information before submitting." >&2
    exit 2
fi
