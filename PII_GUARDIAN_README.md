# PII Guardian

A local PII scanner and redactor. Scans files or directories for personally identifiable information — SSNs, credit cards, emails, phone numbers, API keys, and passwords — using regex patterns. All processing runs on-device with zero external dependencies beyond the Python standard library.

## Quick Start

```bash
# Scan a file
python pii_guardian.py scan document.txt

# Pipe from stdin
echo "SSN: 123-45-6789, email: john@example.com" | python pii_guardian.py scan -
```

## Commands

| Command | Description |
|---------|-------------|
| `scan <file>` | Scan a single file for PII |
| `scan <dir> --recursive` | Recursively scan a directory |
| `scan <file> --redact` | Write a redacted copy with placeholders |
| `scan <file> --output report.json` | Export findings to JSON |
| `scan <file> --hook` | Structured findings + masked prompt to stderr (for hooks) |
| `scan -` | Read from stdin |
| `pre-commit` | Scan git staged files (for hook use) |
| `--install-hook` | Install as a git pre-commit hook |

## What It Detects

| PII Type | Severity | Example |
|----------|----------|---------|
| SSN | Critical | `123-45-6789` |
| Credit card | Critical | `4111 1111 1111 1111` |
| API key / secret | Critical | `api_key = "abc123..."` |
| Password | Critical | `password = "hunter2"` |
| Email | Medium | `john@example.com` |
| Phone | Medium | `555-867-5309` |

## Redaction

Pass `--redact` to produce a `.redacted` copy of the file with PII replaced by numbered type-safe placeholders:

**Before:**
```
Dear Sarah, SSN: 123-45-6789, email: sarah@acme.com, call 555-867-5309
```

**After (`document.txt.redacted`):**
```
Dear Sarah, SSN: [SSN_1], email: [EMAIL_1], call [PHONE_1]
```

Multiple occurrences of the same type are numbered sequentially: `[EMAIL_1]`, `[EMAIL_2]`, etc.

## Pre-commit Hook

### Option 1 — Auto install

```bash
python pii_guardian.py --install-hook
```

This writes `.git/hooks/pre-commit` and makes it executable. Any subsequent `git commit` will scan staged files first and block the commit if PII is found:

```
PII Guardian — Pre-commit Hook
Scanning 2 staged file(s)...

⚠️  config.yaml: 1 PII findings

============================================================
COMMIT BLOCKED: PII detected in staged files
============================================================

🔴 [API_KEY] Line 4
   Value  : api_key = "sk-abc123xyz..."
   Context: database:   api_key = "sk-abc123xyz..."

Action: Remove PII before committing, or use --no-verify to override.
```

### Option 2 — Manual install

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python "$(git rev-parse --show-toplevel)/pii_guardian.py" pre-commit
exit $?
EOF
chmod +x .git/hooks/pre-commit
```

### Bypass the hook

If you intentionally need to commit sensitive data (e.g., test fixtures with fake PII):

```bash
git commit --no-verify
```

### Uninstall

```bash
rm .git/hooks/pre-commit
```

## JSON Report Format

```bash
python pii_guardian.py scan ./data/ --recursive --output report.json
```

```json
{
  "scan_results": [
    {
      "file": "data/config.yaml",
      "risk_level": "critical",
      "contains_pii": true,
      "findings_count": 2,
      "findings": [
        {
          "type": "api_key",
          "value": "api_key = \"sk-abc123...\"",
          "severity": "critical",
          "context": "  database:\n    api_key = \"sk-abc123...\"",
          "line": 4,
          "file": "data/config.yaml"
        }
      ]
    }
  ],
  "summary": {
    "total_files": 3,
    "files_with_pii": 1,
    "total_findings": 2
  }
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No PII found — clean |
| `1` | PII detected |

Exit codes make the tool composable with CI pipelines and shell scripts:

```bash
python pii_guardian.py scan ./src/ --recursive || echo "PII found — review before deploying"
```

## Apple FM Integration

PII Guardian uses a **hybrid approach**: fast regex pre-filter + Apple FM for contextual detection.

### Regex-Only Mode (Default)

```bash
python pii_guardian.py scan document.txt
```

Fast, works everywhere. Catches: SSNs, credit cards, emails, phone numbers, API keys, passwords.

### Apple FM Mode (On-Device Model)

```bash
python pii_guardian.py scan document.txt --fm
```

Enables Apple FM scanning for **contextual PII** that regex can't catch:
- Person names
- Physical addresses
- Medical information (diagnoses, medications)
- Salary / compensation details
- Employee IDs with context
- Job titles with sensitive context

**Note:** Requires macOS 26+ with Apple Intelligence. Falls back gracefully to regex-only if FM is unavailable.

### Performance

| Mode | Speed | Coverage |
|------|-------|----------|
| Regex only | <50ms | 70% of PII (patterns) |
| Regex + FM | ~500ms | 95%+ (patterns + context) |

Use `--fm` for maximum security when scanning sensitive documents. Use regex-only for quick checks in CI/pre-commit.

## Claude Code Integration

PII Guardian is integrated into Claude Code as a privacy hook — every prompt you type is scanned locally before reaching Claude's API.

If PII is detected, the prompt is blocked with structured output showing each finding and a masked version you can resubmit:

```
🚨 PII DETECTED — 2 finding(s) (risk: CRITICAL)
  🔴 [SSN]                 "SSN: 123-45-6789"
  🟡 [EMAIL]               "john@example.com"

✂ Masked version (copy & resubmit):
────────────────────────────────────────
My name is John. SSN: [SSN_1], email: [EMAIL_1]
────────────────────────────────────────
Remove PII or resubmit the masked version above.
```

This ensures you never accidentally send PII to Claude's cloud API.

## Testing

Run these commands from the repo root to verify everything works:

```bash
# 1. Regex-only scan — SSN detected by pattern matching
python pii_guardian.py scan 07-real-world/privacy_doc_classifier.py

# 2. Regex + Apple FM scan — detects both patterns AND contextual PII (names, salary)
python pii_guardian.py scan 07-real-world/privacy_doc_classifier.py --fm

# 3. Pipe text with PII via stdin
echo "Call John at 555-123-4567, SSN 123-45-6789, email john@test.com" | python pii_guardian.py scan -

# 4. Test redaction — should produce .redacted file with [SSN_1], [EMAIL_1] placeholders
echo "Dear Sarah, SSN: 123-45-6789, email: sarah@acme.com" > /tmp/test_pii.txt
python pii_guardian.py scan /tmp/test_pii.txt --redact
cat /tmp/test_pii.txt.redacted

# 5. Test JSON export
python pii_guardian.py scan 07-real-world/privacy_doc_classifier.py --output /tmp/report.json
cat /tmp/report.json

# 6. Scan a clean file — should exit 0
python pii_guardian.py scan README.md

# 7. Test Claude Code hook — should block prompt with PII
echo '{"prompt":"My SSN is 123-45-6789"}' | bash pii_hook.sh
echo "Exit code: $?"  # Should be 2 (blocked)

# 8. Test hook with clean prompt — should allow
echo '{"prompt":"Hello world"}' | bash pii_hook.sh
echo "Exit code: $?"  # Should be 0 (allowed)
```

## File Types Scanned

When scanning a directory, only text-like files are scanned:

`.txt` `.py` `.json` `.csv` `.md` `.log` `.cfg` `.ini` `.yaml` `.yml` `.toml` `.xml` `.html` `.env` `.conf` `.properties` `.sql`
