"""
Batch accuracy evaluation for ticket classification using Apple FM SDK.

Tests 15 ticket samples across 5 categories: bug_report, feature_request,
question, documentation, other. Uses CONTENT_TAGGING mode with a fresh
session per test case and exports results to JSON.
"""

import json
import time
from pathlib import Path

import FoundationModels

TEST_CASES = [
    # bug_report
    {
        "text": "The app crashes whenever I try to upload a file larger than 10MB. Steps to reproduce: 1) Open upload dialog 2) Select file > 10MB 3) Click upload. Expected: file uploads. Actual: app crashes.",
        "expected": "bug_report",
    },
    {
        "text": "Login button is unresponsive on Safari 16.4. Works fine on Chrome. Console shows TypeError: Cannot read property 'token' of undefined.",
        "expected": "bug_report",
    },
    {
        "text": "Dark mode toggle saves preference but reverts to light mode after logout. Reproducible 100% of the time.",
        "expected": "bug_report",
    },
    # feature_request
    {
        "text": "It would be great if we could export reports to PDF format directly from the dashboard instead of having to copy data manually.",
        "expected": "feature_request",
    },
    {
        "text": "Please add support for two-factor authentication via SMS. Many of our enterprise clients require this for compliance.",
        "expected": "feature_request",
    },
    {
        "text": "Would love a bulk-edit feature for managing multiple records at once. Currently we have to update them one by one which is very time-consuming.",
        "expected": "feature_request",
    },
    # question
    {
        "text": "How do I reset my password if I no longer have access to my registered email address?",
        "expected": "question",
    },
    {
        "text": "What is the maximum number of team members I can add to a single workspace on the free plan?",
        "expected": "question",
    },
    {
        "text": "Is there a REST API available for integrating with our internal tools? Where can I find the documentation?",
        "expected": "question",
    },
    # documentation
    {
        "text": "The API reference page for /v2/users/list is missing the response schema. The example curl command is also outdated.",
        "expected": "documentation",
    },
    {
        "text": "The getting started guide doesn't mention that you need to set the STRIPE_KEY environment variable before running the setup script.",
        "expected": "documentation",
    },
    {
        "text": "Several screenshots in the onboarding tutorial show the old UI. They need to be updated to reflect the new dashboard redesign.",
        "expected": "documentation",
    },
    # other
    {
        "text": "Great product! We've been using it for 6 months and it has significantly improved our team's productivity.",
        "expected": "other",
    },
    {
        "text": "Is your company planning to expand to the European market? We have several clients in Germany interested in your service.",
        "expected": "other",
    },
    {
        "text": "Just wanted to say the support team was incredibly helpful resolving our issue last week. Kudos to Sarah!",
        "expected": "other",
    },
]

CATEGORIES = ["bug_report", "feature_request", "question", "documentation", "other"]


@FoundationModels.generable
class TicketCategory:
    """Classification result for a support ticket."""

    category: str = FoundationModels.GenerationSchema(
        description="The ticket category",
        anyOf=CATEGORIES,
    )
    confidence: float = FoundationModels.GenerationSchema(
        description="Confidence score between 0.0 and 1.0",
        range=(0.0, 1.0),
    )
    reasoning: str = FoundationModels.GenerationSchema(
        description="Brief explanation of why this category was chosen",
    )


def classify_ticket(text: str) -> TicketCategory | None:
    """Classify a single ticket using a fresh FM session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a support ticket classifier. Categorize tickets into exactly one of: "
            "bug_report, feature_request, question, documentation, other. "
            "Be precise and consistent in your classifications."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )
    try:
        result = session.respond(
            f"Classify this support ticket:\n\n{text}",
            generating=TicketCategory,
        )
        return result
    except FoundationModels.ExceededContextWindowSizeError:
        print(f"    [SKIP] Context window exceeded for ticket: {text[:60]}...")
        return None


def run_evaluation() -> dict:
    """Run batch evaluation across all test cases."""
    print("=" * 60)
    print("Ticket Classifier — Batch Accuracy Evaluation")
    print("=" * 60)
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Categories: {', '.join(CATEGORIES)}")
    print()

    results = []
    correct = 0
    skipped = 0
    start_time = time.perf_counter()

    for i, case in enumerate(TEST_CASES, 1):
        text = case["text"]
        expected = case["expected"]

        print(f"[{i:02d}/{len(TEST_CASES)}] Expected: {expected:<20}", end="", flush=True)

        prediction = classify_ticket(text)

        if prediction is None:
            skipped += 1
            print("SKIPPED")
            results.append(
                {
                    "index": i,
                    "text_preview": text[:80],
                    "expected": expected,
                    "predicted": None,
                    "correct": False,
                    "skipped": True,
                    "confidence": None,
                    "reasoning": None,
                }
            )
            continue

        predicted = prediction.category
        is_correct = predicted == expected
        if is_correct:
            correct += 1

        status = "PASS" if is_correct else f"FAIL (got {predicted})"
        print(f"Predicted: {predicted:<20} [{status}]  conf={prediction.confidence:.2f}")

        results.append(
            {
                "index": i,
                "text_preview": text[:80],
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "skipped": False,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
            }
        )

    elapsed = time.perf_counter() - start_time
    evaluated = len(TEST_CASES) - skipped
    accuracy = (correct / evaluated * 100) if evaluated > 0 else 0.0

    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Total test cases : {len(TEST_CASES)}")
    print(f"Evaluated        : {evaluated}")
    print(f"Skipped          : {skipped}")
    print(f"Correct          : {correct}")
    print(f"Accuracy         : {accuracy:.1f}%")
    print(f"Elapsed time     : {elapsed:.2f}s")

    # Per-category breakdown
    print()
    print("Per-category accuracy:")
    for cat in CATEGORIES:
        cat_cases = [r for r in results if r["expected"] == cat and not r["skipped"]]
        cat_correct = sum(1 for r in cat_cases if r["correct"])
        cat_total = len(cat_cases)
        cat_pct = (cat_correct / cat_total * 100) if cat_total > 0 else 0.0
        print(f"  {cat:<20} {cat_correct}/{cat_total}  ({cat_pct:.0f}%)")

    summary = {
        "model": "apple_fm_sdk",
        "mode": "CONTENT_TAGGING",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(TEST_CASES),
        "evaluated": evaluated,
        "skipped": skipped,
        "correct": correct,
        "accuracy_pct": round(accuracy, 2),
        "elapsed_seconds": round(elapsed, 2),
        "results": results,
    }

    output_path = Path(__file__).parent / "evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"Results exported to: {output_path}")

    return summary


if __name__ == "__main__":
    run_evaluation()
