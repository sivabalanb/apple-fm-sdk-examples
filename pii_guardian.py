"""
PII Guardian — Local PII scanner and redactor using Apple FM SDK.

Scans files or directories for personally identifiable information (PII)
using a hybrid approach: fast regex pre-filter + Apple FM on-device model
for contextual detection (names, addresses, medical info, salary data).
All processing runs locally — no data sent to cloud services.

Usage:
  python pii_guardian.py scan document.txt
  python pii_guardian.py scan document.txt --fm        # Enable Apple FM scanning
  python pii_guardian.py scan ./data/ --recursive
  python pii_guardian.py scan document.txt --redact
  python pii_guardian.py scan ./data/ --output report.json
  python pii_guardian.py pre-commit
  python pii_guardian.py --install-hook
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Apple FM SDK — optional, graceful degradation if unavailable
# ---------------------------------------------------------------------------

try:
    import apple_fm_sdk as fm
    FM_AVAILABLE = True
except ImportError:
    FM_AVAILABLE = False

# ---------------------------------------------------------------------------
# PII Types and Severity
# ---------------------------------------------------------------------------

PII_TYPES = [
    "ssn",
    "credit_card",
    "email",
    "phone",
    "name",
    "address",
    "date_of_birth",
    "account_number",
    "api_key",
    "password",
    "medical_info",
    "financial_info",
    "employee_id",
    "other",
]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

# Regex patterns for PII detection
REGEX_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "api_key": r"(?:api[_-]?key|secret[_-]?key|access[_-]?token)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_-]{20,}",
    "password": r"(?:password|passwd)['\"]?\s*[:=]\s*['\"]?[^\s\"']{8,}",
}

# Apple FM schema for PII detection (optional, if FM is available)
if FM_AVAILABLE:
    @fm.generable("Detect PII in text")
    class PIIScanSchema:
        contains_pii: bool = fm.guide(description="True if any PII is detected")
        findings: str = fm.guide(
            description=(
                "Comma-separated list of detected PII in format 'type:value:severity'. "
                "Example: 'name:John Smith:high,salary:$150000:high'. "
                "Empty if no PII found."
            )
        )
        risk_level: str = fm.guide(
            description="Overall risk level of this text",
            anyOf=SEVERITY_LEVELS
        )

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PIIFinding:
    """A single PII finding."""

    pii_type: str
    value: str
    severity: str
    context: str
    line_number: int
    source_file: str

    def to_dict(self) -> dict:
        return {
            "type": self.pii_type,
            "value": self.value,
            "severity": self.severity,
            "context": self.context,
            "line": self.line_number,
            "file": self.source_file,
        }


@dataclass
class ScanResult:
    """Aggregated scan results for a file."""

    file_path: str
    contains_pii: bool
    findings: list[PIIFinding]
    risk_level: str
    scanned_chars: int


# ---------------------------------------------------------------------------
# Regex-based PII detection
# ---------------------------------------------------------------------------


def _severity_for_type(pii_type: str) -> str:
    """Map PII type to default severity level."""
    severity_map = {
        "ssn": "critical",
        "credit_card": "critical",
        "api_key": "critical",
        "password": "critical",
        "email": "medium",
        "phone": "medium",
        "name": "low",
        "address": "medium",
        "date_of_birth": "high",
        "account_number": "high",
        "medical_info": "critical",
        "financial_info": "high",
        "employee_id": "high",
        "other": "medium",
    }
    return severity_map.get(pii_type, "medium")


def regex_scan(text: str, source_file: str) -> list[PIIFinding]:
    """Scan text for PII using regex patterns."""
    findings = []

    for pii_type, pattern in REGEX_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(0)
            start_pos = match.start()

            # Find line number
            line_num = text[:start_pos].count("\n") + 1

            # Extract context (surrounding text)
            context_start = max(0, start_pos - 30)
            context_end = min(len(text), start_pos + len(value) + 30)
            context = text[context_start:context_end].replace("\n", " ")

            # Assign severity based on type
            severity = _severity_for_type(pii_type)

            findings.append(
                PIIFinding(
                    pii_type=pii_type,
                    value=value,
                    severity=severity,
                    context=context,
                    line_number=line_num,
                    source_file=source_file,
                )
            )

    return findings


async def fm_scan_file(text: str, source_file: str, chunk_size: int = 500) -> list[PIIFinding]:
    """
    Scan text for PII using Apple FM with batching.
    One session per file, chunks scanned sequentially.
    Session is refreshed every 5 chunks to avoid context window overflow.
    """
    if not FM_AVAILABLE:
        return []

    findings = []
    try:
        model = fm.SystemLanguageModel()
        is_available, _ = model.is_available()
        if not is_available:
            return []

        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        session = None
        chunks_since_refresh = 0

        for chunk_idx, chunk in enumerate(chunks):
            start_line = text[: sum(len(chunks[j]) for j in range(chunk_idx))].count("\n") + 1

            # Refresh session every 5 chunks to clear context window
            if chunks_since_refresh >= 5 or session is None:
                session = fm.LanguageModelSession(
                    instructions=(
                        "You are a privacy and PII detection specialist. Scan text for personally "
                        "identifiable information: names, addresses, medical info, financial data, "
                        "salary/compensation, employee details, and other sensitive personal data. "
                        "Be thorough and conservative. Format findings as type:value:severity."
                    ),
                    model=model,
                )
                chunks_since_refresh = 0

            prompt = (
                "Scan this text for PII and report findings:\n\n"
                f"{chunk}\n\n"
                "Format: type:value:severity (e.g., name:John Smith:high,salary:$150000:high)"
            )

            try:
                result = await session.respond(prompt, generating=PIIScanSchema)

                if result.contains_pii and result.findings.strip():
                    for finding_str in result.findings.split(","):
                        finding_str = finding_str.strip()
                        if not finding_str or ":" not in finding_str:
                            continue

                        parts = finding_str.split(":")
                        if len(parts) >= 3:
                            pii_type = parts[0].strip().lower()
                            value = ":".join(parts[1:-1]).strip()
                            severity = parts[-1].strip().lower()

                            if severity not in SEVERITY_LEVELS:
                                severity = "medium"

                            findings.append(
                                PIIFinding(
                                    pii_type=pii_type,
                                    value=value,
                                    severity=severity,
                                    context=value[:100],
                                    line_number=start_line,
                                    source_file=source_file,
                                )
                            )

                chunks_since_refresh += 1

            except fm.ExceededContextWindowSizeError:
                # Skip this chunk and refresh session
                chunks_since_refresh = 5

    except Exception as e:
        print(f"  [WARNING] FM scan error: {type(e).__name__}", file=sys.stderr)

    return findings


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------


def scan_file(file_path: Path, use_fm: bool = False) -> ScanResult:
    """Scan a single file for PII using regex and optionally Apple FM."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ScanResult(
            file_path=str(file_path),
            contains_pii=False,
            findings=[],
            risk_level="unknown",
            scanned_chars=0,
        )

    # Step 1: Fast regex pre-filter
    findings = regex_scan(text, str(file_path))

    # Step 2: FM scanning (optional, batched) — one session per file, chunks to avoid context window
    # Only use FM on longer text (>200 chars) to avoid hallucination on short prompts
    if use_fm and FM_AVAILABLE and len(text) > 200:
        fm_findings = asyncio.run(fm_scan_file(text, str(file_path)))
        findings.extend(fm_findings)

    # Step 3: Deduplicate findings based on type+value
    seen = set()
    unique = []
    for f in findings:
        key = (f.pii_type, f.value)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    findings = unique

    # Determine overall risk
    if not findings:
        risk_level = "clear"
    else:
        risk_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_risk = max(risk_scores.get(f.severity, 0) for f in findings)
        risk_level = {4: "critical", 3: "high", 2: "medium", 1: "low"}.get(
            max_risk, "unknown"
        )

    return ScanResult(
        file_path=str(file_path),
        contains_pii=len(findings) > 0,
        findings=findings,
        risk_level=risk_level,
        scanned_chars=len(text),
    )


SCAN_EXTENSIONS = {
    ".txt", ".py", ".json", ".csv", ".md", ".log", ".cfg", ".ini", ".yaml",
    ".yml", ".toml", ".xml", ".html", ".env", ".conf", ".properties", ".sql",
}


def scan_directory(
    dir_path: Path, recursive: bool = True, use_fm: bool = False
) -> list[ScanResult]:
    """Scan all text-like files in a directory."""
    results = []
    pattern = "**/*" if recursive else "*"

    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in SCAN_EXTENSIONS:
            result = scan_file(file_path, use_fm=use_fm)
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def redact_text(text: str, findings: list[PIIFinding]) -> str:
    """Redact PII in text by replacing with type-safe placeholders."""
    # Build (start, end, pii_type) spans for each finding
    spans = []
    for finding in findings:
        idx = text.find(finding.value)
        if idx != -1:
            spans.append((idx, idx + len(finding.value), finding.pii_type))

    if not spans:
        return text

    # Sort by position, deduplicate overlapping spans (keep earliest)
    spans.sort()
    merged = [spans[0]]
    for start, end, pii_type in spans[1:]:
        if start >= merged[-1][1]:
            merged.append((start, end, pii_type))

    # Build result in one pass (reverse order to preserve offsets)
    type_counters = {}
    # Assign counter numbers in forward order for readability
    for _, _, pii_type in merged:
        type_counters.setdefault(pii_type, 0)
        type_counters[pii_type] += 1

    # Reset and apply in reverse
    type_idx = {}
    for _, _, pii_type in merged:
        type_idx.setdefault(pii_type, 0)

    redacted = text
    for start, end, pii_type in reversed(merged):
        type_idx[pii_type] += 1
        # Number from end so reversed iteration gives sequential 1, 2, 3
        counter = type_counters[pii_type] - type_idx[pii_type] + 1
        placeholder = f"[{pii_type.upper()}_{counter}]"
        redacted = redacted[:start] + placeholder + redacted[end:]

    return redacted


def redact_file(file_path: Path, findings: list[PIIFinding]) -> Path:
    """Create a redacted version of the file."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    redacted_text = redact_text(text, findings)

    redacted_path = file_path.with_suffix(file_path.suffix + ".redacted")
    redacted_path.write_text(redacted_text, encoding="utf-8")

    return redacted_path


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_summary(results: list[ScanResult]) -> None:
    """Print a summary table of scan results."""
    print("=" * 80)
    print("PII Guardian — Scan Results")
    print("=" * 80)
    print(f"{'File':<40} {'Risk':<12} {'Findings':<10}")
    print("-" * 80)

    total_pii = 0
    for result in results:
        finding_count = len(result.findings)
        total_pii += finding_count

        risk_display = result.risk_level.upper() if result.risk_level != "clear" else "CLEAR"
        print(
            f"{Path(result.file_path).name:<40} {risk_display:<12} {finding_count:<10}"
        )

    print("-" * 80)
    print(f"Total files scanned: {len(results)}")
    print(f"Total PII findings : {total_pii}")
    print()


def print_detailed_findings(results: list[ScanResult]) -> None:
    """Print detailed findings for each result."""
    for result in results:
        if not result.findings:
            continue

        print(f"\n[{result.file_path}]")
        print(f"Risk Level: {result.risk_level.upper()}")
        print(f"Findings: {len(result.findings)}")
        print("-" * 60)

        for finding in result.findings:
            severity_marker = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🔵",
            }.get(finding.severity, "⚪")

            print(f"{severity_marker} [{finding.pii_type.upper()}] Line {finding.line_number}")
            print(f"   Value  : {finding.value[:60]}")
            print(f"   Context: {finding.context[:70]}")
            print()


def export_json(results: list[ScanResult], output_path: Path) -> None:
    """Export results to JSON."""
    data = {
        "scan_results": [
            {
                "file": r.file_path,
                "risk_level": r.risk_level,
                "contains_pii": r.contains_pii,
                "findings_count": len(r.findings),
                "findings": [f.to_dict() for f in r.findings],
            }
            for r in results
        ],
        "summary": {
            "total_files": len(results),
            "files_with_pii": sum(1 for r in results if r.contains_pii),
            "total_findings": sum(len(r.findings) for r in results),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Pre-commit hook
# ---------------------------------------------------------------------------


def get_staged_files() -> list[Path]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [Path(f) for f in result.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def pre_commit_scan() -> int:
    """Scan staged files for PII. Return 0 if clean, 1 if PII found."""
    staged_files = get_staged_files()

    if not staged_files:
        print("PII Guardian — Pre-commit Hook")
        print("No staged files found. Nothing to scan.")
        return 0

    print("PII Guardian — Pre-commit Hook")
    print(f"Scanning {len(staged_files)} staged file(s)...")
    print()

    results = []
    for file_path in staged_files:
        if file_path.exists() and file_path.is_file():
            result = scan_file(file_path)
            if result.contains_pii:
                results.append(result)
                print(f"⚠️  {file_path.name}: {len(result.findings)} PII findings")

    if results:
        print()
        print("=" * 60)
        print("COMMIT BLOCKED: PII detected in staged files")
        print("=" * 60)
        print()
        print_detailed_findings(results)
        print()
        print("Action: Remove PII before committing, or use --no-verify to override.")
        return 1

    print("✓ No PII detected in staged files")
    return 0


def install_hook() -> None:
    """Install the pre-commit hook."""
    hook_dir = Path(".git/hooks")
    if not hook_dir.exists():
        print("[ERROR] Not in a git repository (.git/hooks not found)")
        return

    hook_path = hook_dir / "pre-commit"
    script_path = Path(__file__).resolve()

    hook_content = f"""#!/bin/bash
# PII Guardian pre-commit hook
# Blocks commits if PII is detected in staged files

python "{script_path}" pre-commit
exit $?
"""

    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)

    print(f"✓ Pre-commit hook installed at {hook_path}")
    print(f"  Hook will run: python {script_path} pre-commit")
    print()
    print("To uninstall, remove .git/hooks/pre-commit")


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PII Guardian — Local PII scanner and redactor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python pii_guardian.py scan document.txt\n"
            "  python pii_guardian.py scan ./data/ --recursive\n"
            "  python pii_guardian.py scan document.txt --redact\n"
            "  python pii_guardian.py scan ./data/ --output report.json\n"
            "  python pii_guardian.py pre-commit\n"
            "  python pii_guardian.py --install-hook"
        ),
    )
    parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Install pre-commit hook to .git/hooks/pre-commit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan file or directory for PII")
    scan_parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="File or directory to scan (default: stdin)",
    )
    scan_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directories",
    )
    scan_parser.add_argument(
        "--fm",
        action="store_true",
        help="Enable Apple FM contextual scanning (detects names, addresses, medical info, salary)",
    )
    scan_parser.add_argument(
        "--redact",
        action="store_true",
        help="Generate redacted versions of files with PII",
    )
    scan_parser.add_argument(
        "--output",
        help="Export results to JSON file",
    )

    # Pre-commit command
    subparsers.add_parser(
        "pre-commit", help="Scan staged git files (for pre-commit hook)"
    )

    args = parser.parse_args()

    if args.install_hook:
        install_hook()
        return

    if args.command == "pre-commit":
        exit_code = pre_commit_scan()
        sys.exit(exit_code)

    if args.command == "scan":
        path_arg = args.path
        results = []

        # Handle stdin
        if path_arg == "-":
            text = sys.stdin.read()
            temp_file = Path("/tmp/pii_scan_stdin.txt")
            temp_file.write_text(text)
            try:
                result = scan_file(temp_file, use_fm=args.fm)
                results.append(result)
            finally:
                temp_file.unlink(missing_ok=True)
        else:
            path = Path(path_arg)
            if path.is_file():
                results.append(scan_file(path, use_fm=args.fm))
            elif path.is_dir():
                results.extend(scan_directory(path, recursive=args.recursive, use_fm=args.fm))
            else:
                print(f"[ERROR] Path not found: {path_arg}")
                sys.exit(1)

        # Display results
        print_summary(results)
        if any(r.contains_pii for r in results):
            print_detailed_findings(results)

        # Redact if requested
        if args.redact:
            for result in results:
                if result.findings:
                    redacted_path = redact_file(
                        Path(result.file_path), result.findings
                    )
                    print(f"Redacted: {redacted_path}")

        # Export to JSON if requested
        if args.output:
            output_path = Path(args.output)
            export_json(results, output_path)
            print(f"Exported: {output_path}")

        # Exit with code 1 if PII found (for scripting/CI)
        if any(r.contains_pii for r in results):
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
