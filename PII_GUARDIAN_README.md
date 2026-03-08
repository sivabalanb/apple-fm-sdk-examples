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

## File Types Scanned

When scanning a directory, only text-like files are scanned:

`.txt` `.py` `.json` `.csv` `.md` `.log` `.cfg` `.ini` `.yaml` `.yml` `.toml` `.xml` `.html` `.env` `.conf` `.properties` `.sql`
