"""
Sentiment classification comparison: Apple FM SDK vs Claude API.

Runs 5 test texts through both models and reports per-text predictions,
agreement rate, and timing. Apple FM uses a @generable Sentiment class with
anyOf + range constraints. Claude uses ask_claude_json with a JSON schema.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import FoundationModels
from utils.claude_client import ask_claude_json
from utils.helpers import print_comparison, timer

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_TEXTS = [
    "This product completely exceeded my expectations. Absolutely love it!",
    "The shipping took three weeks and the item arrived damaged. Very disappointed.",
    "It's okay. Does what it says, nothing special.",
    "Worst customer service I have ever experienced. Never buying from here again.",
    "Pretty good value for the price, though the setup instructions could be clearer.",
]

SENTIMENTS = ["positive", "negative", "neutral", "mixed"]

# ---------------------------------------------------------------------------
# Apple FM SDK
# ---------------------------------------------------------------------------


@FoundationModels.generable
class Sentiment:
    """Sentiment classification for a text snippet."""

    label: str = FoundationModels.GenerationSchema(
        description="Sentiment label for the text",
        anyOf=SENTIMENTS,
    )
    score: float = FoundationModels.GenerationSchema(
        description="Sentiment intensity score between -1.0 (most negative) and 1.0 (most positive)",
        range=(-1.0, 1.0),
    )
    explanation: str = FoundationModels.GenerationSchema(
        description="One-sentence explanation of the sentiment classification",
    )


def classify_apple_fm(text: str) -> dict | None:
    """Classify sentiment using Apple FM SDK with a fresh session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a sentiment analysis system. Classify the sentiment of "
            "user-provided text as positive, negative, neutral, or mixed. "
            "Be precise and consistent."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )
    try:
        result = session.respond(
            f"Classify the sentiment of this text:\n\n{text}",
            generating=Sentiment,
        )
        return {
            "label": result.label,
            "score": result.score,
            "explanation": result.explanation,
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
        "label": {
            "type": "string",
            "enum": SENTIMENTS,
            "description": "Sentiment label",
        },
        "score": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Intensity score from -1.0 to 1.0",
        },
        "explanation": {
            "type": "string",
            "description": "One-sentence explanation",
        },
    },
    "required": ["label", "score", "explanation"],
}

CLAUDE_PROMPT_TEMPLATE = (
    "Classify the sentiment of the following text. "
    "Return JSON matching the schema provided.\n\n"
    "Text: {text}\n\n"
    "JSON schema:\n{schema}"
)


def classify_claude(text: str) -> dict | None:
    """Classify sentiment using Claude API."""
    import json

    prompt = CLAUDE_PROMPT_TEMPLATE.format(
        text=text,
        schema=json.dumps(CLAUDE_SCHEMA, indent=2),
    )
    return ask_claude_json(prompt)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_comparison() -> None:
    print("=" * 70)
    print("Sentiment Classification Comparison: Apple FM SDK vs Claude API")
    print("=" * 70)
    print(f"Test texts  : {len(TEST_TEXTS)}")
    print(f"Categories  : {', '.join(SENTIMENTS)}")
    print()

    apple_results = []
    claude_results = []
    apple_times = []
    claude_times = []
    agreements = 0
    compared = 0

    for i, text in enumerate(TEST_TEXTS, 1):
        print(f"[{i}/{len(TEST_TEXTS)}] {text[:65]}{'...' if len(text) > 65 else ''}")

        # Apple FM
        with timer() as t:
            apple = classify_apple_fm(text)
        apple_times.append(t.elapsed)
        apple_results.append(apple)

        # Claude
        with timer() as t:
            claude = classify_claude(text)
        claude_times.append(t.elapsed)
        claude_results.append(claude)

        # Display side-by-side
        apple_label = apple["label"] if apple else "ERROR"
        claude_label = claude["label"] if claude else "ERROR"

        print_comparison(
            label="Sentiment",
            apple_value=f"{apple_label} (score={apple['score']:.2f})" if apple else "ERROR",
            claude_value=f"{claude_label} (score={claude['score']:.2f})" if claude else "ERROR",
        )

        if apple and claude:
            agree = apple_label == claude_label
            compared += 1
            if agree:
                agreements += 1
            print(f"  Agreement: {'YES' if agree else 'NO'}")

        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Texts compared         : {compared} / {len(TEST_TEXTS)}")
    agreement_pct = (agreements / compared * 100) if compared > 0 else 0.0
    print(f"Agreement rate         : {agreements}/{compared} ({agreement_pct:.0f}%)")
    print()

    avg_apple = sum(apple_times) / len(apple_times) if apple_times else 0
    avg_claude = sum(claude_times) / len(claude_times) if claude_times else 0
    print(f"Avg Apple FM time      : {avg_apple:.3f}s")
    print(f"Avg Claude time        : {avg_claude:.3f}s")


if __name__ == "__main__":
    run_comparison()
