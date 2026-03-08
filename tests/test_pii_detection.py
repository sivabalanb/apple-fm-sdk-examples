"""
PII Detection Benchmark — Regex vs Apple FM Classification.

Measures precision, recall, F1, and latency for two PII detection approaches:
1. Regex pattern matching (from pii_guardian.py)
2. Apple FM binary classification (simple yes/no schema)

The key insight: FM is a 3B classification model. Instead of asking it to
extract + rate PII (complex generation), we reframe detection as binary
classification — "does this text contain PII?" — which plays to its strength.

Usage:
  python tests/test_pii_detection.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add repo root so imports work when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from pii_guardian import REGEX_PATTERNS, regex_scan

# ---------------------------------------------------------------------------
# Apple FM SDK — optional
# ---------------------------------------------------------------------------

try:
    import apple_fm_sdk as fm

    FM_AVAILABLE = True
except ImportError:
    FM_AVAILABLE = False

# Define the simple classification schema (only if FM is available)
if FM_AVAILABLE:

    @fm.generable("Classify whether text contains sensitive personal or secret information")
    class PIIClassification:
        contains_pii: bool = fm.guide(
            description=(
                "True if the text contains any of: (1) personal data tied to "
                "a real or implied person such as a name, address, phone, "
                "email, SSN, date of birth, salary, or compensation, "
                "(2) protected health information like diagnoses, medications, "
                "or treatment details even without a patient name, "
                "(3) secrets such as passwords, API keys, access tokens, or "
                "credentials. False for generic statistics, code references, "
                "variable names, fictional examples, or documentation."
            ),
        )
        confidence: str = fm.guide(
            description="Confidence level",
            anyOf=["high", "medium", "low"],
        )
        pii_category: str = fm.guide(
            description="Primary category of sensitive data found, or 'none'",
            anyOf=[
                "ssn",
                "credit_card",
                "email",
                "phone",
                "name",
                "address",
                "medical",
                "financial",
                "dob",
                "employee_id",
                "api_key",
                "password",
                "none",
            ],
        )


# ---------------------------------------------------------------------------
# Test cases — ground truth
# ---------------------------------------------------------------------------

TEST_CASES = [
    # ---- True Positives: should detect PII ----
    {
        "id": 1,
        "text": "SSN: 123-45-6789",
        "has_pii": True,
        "pii_types": ["ssn"],
        "description": "SSN with dashes",
    },
    {
        "id": 2,
        "text": "Call me at 555-867-5309",
        "has_pii": True,
        "pii_types": ["phone"],
        "description": "Phone number",
    },
    {
        "id": 3,
        "text": "Email: sarah@acme.com",
        "has_pii": True,
        "pii_types": ["email"],
        "description": "Email address",
    },
    {
        "id": 4,
        "text": "CC: 4111 1111 1111 1111",
        "has_pii": True,
        "pii_types": ["credit_card"],
        "description": "Credit card number",
    },
    {
        "id": 5,
        "text": "api_key = sk_live_abc123xyz456def789",
        "has_pii": True,
        "pii_types": ["api_key"],
        "description": "API key in assignment",
    },
    {
        "id": 6,
        "text": "password = hunter2secret",
        "has_pii": True,
        "pii_types": ["password"],
        "description": "Password in assignment",
    },
    # ---- Contextual PII: regex should miss, FM should catch ----
    {
        "id": 7,
        "text": "My social is 123 45 6789",
        "has_pii": True,
        "pii_types": ["ssn"],
        "description": "SSN without dashes",
    },
    {
        "id": 8,
        "text": "John Smith's annual salary is $185,000",
        "has_pii": True,
        "pii_types": ["name", "financial"],
        "description": "Name + salary (natural)",
    },
    {
        "id": 9,
        "text": "Patient diagnosed with Type 2 diabetes",
        "has_pii": True,
        "pii_types": ["medical"],
        "description": "Medical diagnosis",
    },
    {
        "id": 10,
        "text": "Lives at 742 Evergreen Terrace, Springfield IL 62704",
        "has_pii": True,
        "pii_types": ["address"],
        "description": "Full street address",
    },
    {
        "id": 11,
        "text": "Employee ID: EMP-2024-5678, hired 03/15/1990",
        "has_pii": True,
        "pii_types": ["employee_id", "dob"],
        "description": "Employee ID + hire date",
    },
    {
        "id": 12,
        "text": "Dr. Williams prescribed metformin 500mg twice daily",
        "has_pii": True,
        "pii_types": ["medical", "name"],
        "description": "Medical prescription + doctor name",
    },
    {
        "id": 13,
        "text": "Sarah earned a $25,000 bonus this quarter",
        "has_pii": True,
        "pii_types": ["name", "financial"],
        "description": "Name + financial (bonus)",
    },
    {
        "id": 14,
        "text": "Send the package to Bob Miller, 456 Oak Ave, Denver CO 80201",
        "has_pii": True,
        "pii_types": ["name", "address"],
        "description": "Name + mailing address",
    },
    {
        "id": 15,
        "text": "My date of birth is March 15, 1990",
        "has_pii": True,
        "pii_types": ["dob"],
        "description": "Date of birth (natural lang)",
    },
    # ---- True Negatives: should NOT detect PII ----
    {
        "id": 16,
        "text": "The function returns 123-45-6789 as an error code",
        "has_pii": False,
        "pii_types": [],
        "description": "Error code looks like SSN",
    },
    {
        "id": 17,
        "text": "The price is $150,000 for the house",
        "has_pii": False,
        "pii_types": [],
        "description": "Dollar amount, no person",
    },
    {
        "id": 18,
        "text": "Call the support line at 1-800-555-0199",
        "has_pii": False,
        "pii_types": [],
        "description": "Toll-free number",
    },
    {
        "id": 19,
        "text": "See RFC 2822 for email format specifications",
        "has_pii": False,
        "pii_types": [],
        "description": "Mentions email, no actual email",
    },
    {
        "id": 20,
        "text": "The population of Springfield is 150,000",
        "has_pii": False,
        "pii_types": [],
        "description": "City name, not PII",
    },
    {
        "id": 21,
        "text": "Average salary in tech is $120,000 per year",
        "has_pii": False,
        "pii_types": [],
        "description": "Generic stat, not personal",
    },
    {
        "id": 22,
        "text": "The patient table has 50,000 rows",
        "has_pii": False,
        "pii_types": [],
        "description": "'patient' in database context",
    },
    {
        "id": 23,
        "text": "John is a common variable name in Java tutorials",
        "has_pii": False,
        "pii_types": [],
        "description": "Name but not a real person",
    },
    {
        "id": 24,
        "text": "Fix the bug in parse_address() function",
        "has_pii": False,
        "pii_types": [],
        "description": "'address' in code context",
    },
    {
        "id": 25,
        "text": "What is the best way to validate email input?",
        "has_pii": False,
        "pii_types": [],
        "description": "About email, no actual email",
    },
]


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------


def regex_detect(text: str) -> bool:
    """Run regex_scan and return True if any PII found."""
    findings = regex_scan(text, source_file="<benchmark>")
    return len(findings) > 0


FM_INSTRUCTIONS = (
    "You are a sensitive data classifier. Determine whether text contains "
    "personally identifiable information (PII) or secrets. "
    "PII includes: names tied to personal details, physical addresses, "
    "phone numbers, email addresses, SSNs, dates of birth, salary or "
    "compensation figures tied to a person, and employee identifiers. "
    "Protected health information counts as PII even without a patient "
    "name — diagnoses, medications, prescriptions, and treatment details. "
    "Secrets include: passwords, API keys, access tokens, and credentials. "
    "Do NOT flag: generic statistics, code variable names, documentation "
    "about PII concepts, fictional examples, toll-free or 1-800 numbers, "
    "or error codes that happen to look like sensitive patterns."
)


async def fm_classify(text: str, model) -> tuple[bool, str]:
    """
    Classify text using Apple FM binary classification.
    Creates a fresh session per call to avoid context bleed.
    Returns (contains_pii, category).
    """
    session = fm.LanguageModelSession(
        instructions=FM_INSTRUCTIONS,
        model=model,
    )
    try:
        result = await session.respond(
            f"Classify this text — does it contain PII or secrets?\n\n{text}",
            generating=PIIClassification,
        )
        return result.contains_pii, result.pii_category
    except fm.ExceededContextWindowSizeError:
        return False, "error"


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


async def run_benchmark() -> None:
    total_positives = sum(1 for tc in TEST_CASES if tc["has_pii"])
    total_negatives = sum(1 for tc in TEST_CASES if not tc["has_pii"])

    print("=" * 72)
    print("PII Detection Benchmark — Regex vs Apple FM")
    print("=" * 72)
    print(f"Test cases: {len(TEST_CASES)} ({total_positives} PII, "
          f"{total_negatives} clean)")
    print(f"FM available: {FM_AVAILABLE}")
    print()

    # Set up FM model
    fm_model = None
    if FM_AVAILABLE:
        try:
            fm_model = fm.SystemLanguageModel()
            is_available, _ = fm_model.is_available()
            if not is_available:
                print("[WARNING] FM model not available on this device")
                fm_model = None
        except Exception as e:
            print(f"[WARNING] FM init failed: {e}")

    # Column headers
    print(f"{'#':<4} {'Description':<32} {'Expected':<10} {'Regex':<10} ", end="")
    if fm_model:
        print(f"{'FM':<10} {'FM Cat':<12} {'FM ms':<8}", end="")
    print()
    print("-" * (72 if not fm_model else 96))

    # Metrics accumulators
    regex_tp = regex_fp = regex_tn = regex_fn = 0
    fm_tp = fm_fp = fm_tn = fm_fn = 0
    regex_times = []
    fm_times = []

    for tc in TEST_CASES:
        text = tc["text"]
        expected = tc["has_pii"]
        desc = tc["description"]

        # --- Regex ---
        t0 = time.perf_counter()
        regex_result = regex_detect(text)
        regex_ms = (time.perf_counter() - t0) * 1000
        regex_times.append(regex_ms)

        if expected and regex_result:
            regex_tp += 1
            regex_label = "\u2705 TP"
        elif expected and not regex_result:
            regex_fn += 1
            regex_label = "\u274c FN"
        elif not expected and not regex_result:
            regex_tn += 1
            regex_label = "\u2705 TN"
        else:
            regex_fp += 1
            regex_label = "\u274c FP"

        # --- FM ---
        fm_label = ""
        fm_cat = ""
        fm_ms_str = ""
        if fm_model:
            t0 = time.perf_counter()
            fm_result, fm_cat = await fm_classify(text, fm_model)
            fm_ms = (time.perf_counter() - t0) * 1000
            fm_times.append(fm_ms)

            if expected and fm_result:
                fm_tp += 1
                fm_label = "\u2705 TP"
            elif expected and not fm_result:
                fm_fn += 1
                fm_label = "\u274c FN"
            elif not expected and not fm_result:
                fm_tn += 1
                fm_label = "\u2705 TN"
            else:
                fm_fp += 1
                fm_label = "\u274c FP"

            fm_ms_str = f"{fm_ms:.0f}"

        # Print row
        expected_str = "PII" if expected else "CLEAN"
        print(f"{tc['id']:<4} {desc:<32} {expected_str:<10} {regex_label:<10} ", end="")
        if fm_model:
            print(f"{fm_label:<10} {fm_cat:<12} {fm_ms_str:<8}", end="")
        print()

    # --- Summary ---
    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)

    def calc_metrics(tp, fp, tn, fn):
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        return precision, recall, f1

    r_prec, r_rec, r_f1 = calc_metrics(regex_tp, regex_fp, regex_tn, regex_fn)

    header = f"{'Metric':<24} {'Regex':<20}"
    if fm_model:
        f_prec, f_rec, f_f1 = calc_metrics(fm_tp, fm_fp, fm_tn, fm_fn)
        header += f"{'Apple FM':<20}"
    print(header)
    print("-" * len(header))

    def row(label, regex_val, fm_val=None):
        line = f"{label:<24} {regex_val:<20}"
        if fm_model and fm_val is not None:
            line += f"{fm_val:<20}"
        print(line)

    row("Precision", f"{r_prec:.1%}",
        f"{f_prec:.1%}" if fm_model else None)
    row("Recall", f"{r_rec:.1%}",
        f"{f_rec:.1%}" if fm_model else None)
    row("F1 Score", f"{r_f1:.1%}",
        f"{f_f1:.1%}" if fm_model else None)

    avg_regex = sum(regex_times) / len(regex_times) if regex_times else 0
    row("Avg Latency", f"{avg_regex:.2f}ms",
        f"{sum(fm_times) / len(fm_times):.0f}ms" if fm_times else None)

    print()
    row("True Positives", f"{regex_tp}/{total_positives}",
        f"{fm_tp}/{total_positives}" if fm_model else None)
    row("False Negatives", f"{regex_fn}/{total_positives}",
        f"{fm_fn}/{total_positives}" if fm_model else None)
    row("True Negatives", f"{regex_tn}/{total_negatives}",
        f"{fm_tn}/{total_negatives}" if fm_model else None)
    row("False Positives", f"{regex_fp}/{total_negatives}",
        f"{fm_fp}/{total_negatives}" if fm_model else None)

    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
