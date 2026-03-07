"""
Privacy-first document classifier using Apple FM SDK.

Classifies 4 sample documents by type, sensitivity, PII presence, and
recommended action. Runs entirely on-device via Apple FM — no document
content is sent to external servers. Each document uses a fresh session.
"""

import FoundationModels

# ---------------------------------------------------------------------------
# Sample documents
# ---------------------------------------------------------------------------

DOCUMENTS = [
    {
        "id": "doc_001",
        "name": "Offer Letter — Sarah Kim",
        "content": (
            "Dear Sarah Kim,\n\n"
            "We are pleased to offer you the position of Senior Software Engineer "
            "at Acme Corp, effective March 15, 2025. Your annual base salary will be "
            "$165,000, with a signing bonus of $10,000. Your employee ID will be EMP-4821. "
            "Please review and sign this offer by March 10, 2025.\n\n"
            "Your Social Security Number on file: 123-45-6789.\n\n"
            "Human Resources\nAcme Corp"
        ),
    },
    {
        "id": "doc_002",
        "name": "Q3 Financial Report",
        "content": (
            "CONFIDENTIAL — INTERNAL USE ONLY\n\n"
            "Q3 2024 Financial Summary\n"
            "Total Revenue: $4.2M  |  EBITDA: $980K  |  Net Loss: ($120K)\n"
            "Cash on hand: $2.1M  |  Runway: 18 months\n\n"
            "Key highlights: SaaS MRR grew 12% QoQ. Enterprise segment churn "
            "increased to 4.2%, driven by two contract non-renewals in EMEA.\n\n"
            "Board discussion scheduled for October 14, 2024."
        ),
    },
    {
        "id": "doc_003",
        "name": "Medical Leave Request",
        "content": (
            "Employee: James Thornton  |  ID: EMP-2234  |  Dept: Engineering\n\n"
            "Request for Medical Leave of Absence\n\n"
            "I am requesting FMLA leave from April 1–30, 2025 for a scheduled "
            "surgical procedure and recovery. My physician, Dr. L. Patel, has "
            "confirmed that 30 days of recovery is medically necessary.\n\n"
            "Attached: Medical certification form (Form WH-380-E)\n"
            "Diagnosis code: M51.16 (intervertebral disc degeneration, lumbar)"
        ),
    },
    {
        "id": "doc_004",
        "name": "Team Lunch Invitation",
        "content": (
            "Hey everyone!\n\n"
            "We're celebrating the successful Q3 launch with a team lunch on Friday, "
            "October 18th at 12:30 PM. We'll be heading to Pizzeria Delfina on "
            "18th Street. The company is covering the tab.\n\n"
            "Please RSVP to this thread by Thursday so we can make a reservation. "
            "Let me know if you have any dietary restrictions.\n\n"
            "Looking forward to celebrating with you all!\n— Priya"
        ),
    },
]

# ---------------------------------------------------------------------------
# Classification schema
# ---------------------------------------------------------------------------

DOC_TYPES = [
    "employment_document",
    "financial_report",
    "medical_record",
    "internal_communication",
    "legal_document",
    "other",
]

SENSITIVITY_LEVELS = ["public", "internal", "confidential", "restricted", "highly_restricted"]

RECOMMENDED_ACTIONS = [
    "no_action_required",
    "store_with_standard_access_controls",
    "restrict_to_hr_only",
    "restrict_to_finance_only",
    "restrict_to_legal_and_executives",
    "encrypt_and_audit_access",
    "delete_after_retention_period",
]


@FoundationModels.generable
class DocClassification:
    """Classification result for a document."""

    doc_type: str = FoundationModels.GenerationSchema(
        description="Primary document type category",
        anyOf=DOC_TYPES,
    )
    sensitivity: str = FoundationModels.GenerationSchema(
        description="Sensitivity level of the document",
        anyOf=SENSITIVITY_LEVELS,
    )
    contains_pii: bool = FoundationModels.GenerationSchema(
        description="True if the document contains personally identifiable information",
    )
    summary: str = FoundationModels.GenerationSchema(
        description="One-sentence neutral summary of what the document contains",
    )
    recommended_action: str = FoundationModels.GenerationSchema(
        description="Recommended handling action for this document",
        anyOf=RECOMMENDED_ACTIONS,
    )


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_document(doc: dict) -> DocClassification | None:
    """Classify a single document using a fresh FM session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a privacy and document compliance classifier. "
            "Analyze documents to determine their type, sensitivity level, "
            "whether they contain PII, and what handling action is appropriate. "
            "Be conservative — when in doubt, classify as more sensitive rather than less."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )
    try:
        result = session.respond(
            f"Classify this document:\n\n{doc['content']}",
            generating=DocClassification,
        )
        return result
    except FoundationModels.ExceededContextWindowSizeError:
        print(f"  [SKIP] Context window exceeded for document: {doc['name']}")
        return None


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

SENSITIVITY_COLORS = {
    "public": "LOW",
    "internal": "LOW",
    "confidential": "MED",
    "restricted": "HIGH",
    "highly_restricted": "CRITICAL",
}


def print_classification(doc: dict, result: DocClassification | None) -> None:
    """Print a formatted classification result for one document."""
    print(f"  Document : {doc['name']}  [{doc['id']}]")
    if result is None:
        print("  Result   : SKIPPED (context window exceeded)")
        return

    risk_label = SENSITIVITY_COLORS.get(result.sensitivity, "?")
    print(f"  Type     : {result.doc_type}")
    print(f"  Sensitiv.: {result.sensitivity}  [{risk_label}]")
    print(f"  Has PII  : {'YES' if result.contains_pii else 'no'}")
    print(f"  Summary  : {result.summary}")
    print(f"  Action   : {result.recommended_action}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 65)
    print("Privacy-First Document Classifier (Apple FM SDK — on-device)")
    print("=" * 65)
    print("Note: All processing runs locally. No document content is sent")
    print("      to external APIs or cloud services.")
    print()

    results_summary = []

    for i, doc in enumerate(DOCUMENTS, 1):
        print(f"[{i}/{len(DOCUMENTS)}] Processing...")
        result = classify_document(doc)
        print_classification(doc, result)
        print()

        results_summary.append(
            {
                "id": doc["id"],
                "name": doc["name"],
                "classified": result is not None,
                "sensitivity": result.sensitivity if result else None,
                "contains_pii": result.contains_pii if result else None,
                "action": result.recommended_action if result else None,
            }
        )

    # Summary table
    print("=" * 65)
    print("Summary")
    print("=" * 65)
    print(f"{'Document':<35} {'Sensitivity':<18} {'PII':<5} {'Action'}")
    print("-" * 65)
    for r in results_summary:
        if r["classified"]:
            pii_str = "YES" if r["contains_pii"] else "no"
            print(
                f"{r['name']:<35} {r['sensitivity']:<18} {pii_str:<5} {r['action']}"
            )
        else:
            print(f"{r['name']:<35} SKIPPED")

    pii_count = sum(1 for r in results_summary if r.get("contains_pii"))
    high_sens = sum(
        1
        for r in results_summary
        if r.get("sensitivity") in ("restricted", "highly_restricted")
    )
    print()
    print(f"Documents with PII          : {pii_count}/{len(DOCUMENTS)}")
    print(f"High/critical sensitivity   : {high_sens}/{len(DOCUMENTS)}")


if __name__ == "__main__":
    main()
