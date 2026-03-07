"""
Contact info extraction comparison: Apple FM SDK vs Claude API.

Processes 3 messy real-world text samples. Apple FM uses a @generable
ContactInfo struct. Claude uses a JSON schema passed via ask_claude_json.
Results are displayed side-by-side with field-level agreement analysis.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import FoundationModels
from utils.claude_client import ask_claude_json
from utils.helpers import print_comparison, timer, truncate

# ---------------------------------------------------------------------------
# Test data — messy real-world contact snippets
# ---------------------------------------------------------------------------

MESSY_TEXTS = [
    (
        "Hey! Reach out to Jennifer Martinez — she's our new Partnership Lead. "
        "Best at jen.martinez@acmecorp.io or just ping her on Slack. "
        "Her direct line is +1 (415) 555-0192 if it's urgent. ACME Corp, SF office."
    ),
    (
        "From: dr_alex_chen@globalhealth.org\n"
        "Sent: Tuesday\n"
        "Dr. Alexander Chen, MD — Senior Researcher, Global Health Initiative\n"
        "Mobile: 001-212-555-8847  |  Office ext. 3302\n"
        "Please cc billing@globalhealth.org on any invoice."
    ),
    (
        "Spoke with a rep named Sam (wouldn't give last name). "
        "Company is TechStart Ltd. He said to email sales@techstart.co "
        "or call their main line 800-555-0011. No direct number given. "
        "He's apparently a 'Solutions Consultant' whatever that means."
    ),
]

# ---------------------------------------------------------------------------
# Apple FM SDK
# ---------------------------------------------------------------------------


@FoundationModels.generable
class ContactInfo:
    """Extracted contact information from unstructured text."""

    full_name: str = FoundationModels.GenerationSchema(
        description="Full name of the contact person, or empty string if not found",
    )
    email: str = FoundationModels.GenerationSchema(
        description="Primary email address, or empty string if not found",
    )
    phone: str = FoundationModels.GenerationSchema(
        description="Phone number in a normalized format, or empty string if not found",
    )
    company: str = FoundationModels.GenerationSchema(
        description="Company or organization name, or empty string if not found",
    )
    role: str = FoundationModels.GenerationSchema(
        description="Job title or role, or empty string if not found",
    )


def extract_apple_fm(text: str) -> dict | None:
    """Extract contact info using Apple FM SDK with a fresh session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a contact information extractor. Given unstructured text, "
            "extract the primary contact's full name, email, phone number, company, "
            "and job role. Use empty strings for fields not present in the text."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )
    try:
        result = session.respond(
            f"Extract contact information from this text:\n\n{text}",
            generating=ContactInfo,
        )
        return {
            "full_name": result.full_name,
            "email": result.email,
            "phone": result.phone,
            "company": result.company,
            "role": result.role,
        }
    except FoundationModels.ExceededContextWindowSizeError:
        print("    [Apple FM] Context window exceeded — skipping this text.")
        return None


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

CLAUDE_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string", "description": "Full name of the contact"},
        "email": {"type": "string", "description": "Primary email address"},
        "phone": {"type": "string", "description": "Phone number, normalized"},
        "company": {"type": "string", "description": "Company or organization name"},
        "role": {"type": "string", "description": "Job title or role"},
    },
    "required": ["full_name", "email", "phone", "company", "role"],
}

CLAUDE_PROMPT_TEMPLATE = (
    "Extract the primary contact's information from the text below. "
    "Return a JSON object matching the schema. Use empty strings for missing fields.\n\n"
    "Text:\n{text}\n\n"
    "JSON schema:\n{schema}"
)


def extract_claude(text: str) -> dict | None:
    """Extract contact info using Claude API."""
    prompt = CLAUDE_PROMPT_TEMPLATE.format(
        text=text,
        schema=json.dumps(CLAUDE_SCHEMA, indent=2),
    )
    return ask_claude_json(prompt)


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

CONTACT_FIELDS = ["full_name", "email", "phone", "company", "role"]


def field_agreement(apple: dict, claude: dict) -> dict[str, bool]:
    """Return per-field agreement between two extraction results."""
    return {
        field: (
            apple.get(field, "").strip().lower() == claude.get(field, "").strip().lower()
        )
        for field in CONTACT_FIELDS
    }


def print_extraction_comparison(
    text: str,
    apple: dict | None,
    claude: dict | None,
    index: int,
) -> None:
    """Print a detailed side-by-side comparison for one extraction."""
    print(f"--- Sample {index} ---")
    print(f"Text: {truncate(text, 80)}")
    print()

    col_w = 30
    print(f"{'Field':<15} {'Apple FM':<{col_w}} {'Claude':<{col_w}} {'Match'}")
    print("-" * (15 + col_w * 2 + 8))

    agree_count = 0
    for field in CONTACT_FIELDS:
        a_val = apple.get(field, "N/A") if apple else "ERROR"
        c_val = claude.get(field, "N/A") if claude else "ERROR"

        if apple and claude:
            match = a_val.strip().lower() == c_val.strip().lower()
            match_str = "YES" if match else "NO "
            if match:
                agree_count += 1
        else:
            match_str = "N/A"

        print(
            f"{field:<15} {truncate(a_val, col_w - 1):<{col_w}} "
            f"{truncate(c_val, col_w - 1):<{col_w}} {match_str}"
        )

    if apple and claude:
        pct = agree_count / len(CONTACT_FIELDS) * 100
        print(f"\nField agreement: {agree_count}/{len(CONTACT_FIELDS)} ({pct:.0f}%)")
    print()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_comparison() -> None:
    print("=" * 70)
    print("Contact Info Extraction Comparison: Apple FM SDK vs Claude API")
    print("=" * 70)
    print(f"Text samples : {len(MESSY_TEXTS)}")
    print(f"Fields       : {', '.join(CONTACT_FIELDS)}")
    print()

    total_fields = 0
    total_agreed = 0
    apple_times = []
    claude_times = []

    for i, text in enumerate(MESSY_TEXTS, 1):
        with timer() as t:
            apple = extract_apple_fm(text)
        apple_times.append(t.elapsed)

        with timer() as t:
            claude = extract_claude(text)
        claude_times.append(t.elapsed)

        print_extraction_comparison(text, apple, claude, i)

        if apple and claude:
            agreement = field_agreement(apple, claude)
            total_fields += len(CONTACT_FIELDS)
            total_agreed += sum(agreement.values())

    print("=" * 70)
    print("Overall Summary")
    print("=" * 70)
    overall_pct = (total_agreed / total_fields * 100) if total_fields > 0 else 0.0
    print(f"Total field comparisons : {total_fields}")
    print(f"Fields agreed           : {total_agreed} ({overall_pct:.0f}%)")
    print()

    avg_apple = sum(apple_times) / len(apple_times) if apple_times else 0
    avg_claude = sum(claude_times) / len(claude_times) if claude_times else 0
    print(f"Avg Apple FM time : {avg_apple:.3f}s")
    print(f"Avg Claude time   : {avg_claude:.3f}s")


if __name__ == "__main__":
    run_comparison()
