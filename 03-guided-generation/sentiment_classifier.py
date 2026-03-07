"""
03 — Sentiment Classifier
Constrain model output to exact labels with confidence scores.
Demonstrates: @generable, anyOf constraint, range constraint.

This is where Apple FM really shines — structured classification
with guaranteed output shape, running entirely on-device for free.
"""

import asyncio

import apple_fm_sdk as fm


# Define the output schema — the model MUST produce this exact structure
@fm.generable("Sentiment analysis result")
class SentimentResult:
    label: str = fm.guide(anyOf=["positive", "negative", "neutral"])
    confidence: float = fm.guide(range=(0.0, 1.0))


REVIEWS = [
    "This product is amazing! Best purchase I've made all year.",
    "Terrible quality. Broke after two days. Want my money back.",
    "It's okay. Does what it says, nothing special.",
    "Absolutely love it, exceeded all expectations!",
    "Shipping was slow but the product itself is fine.",
    "Complete waste of money. Do not buy.",
]


async def main():
    model = fm.SystemLanguageModel(
        use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING,
    )
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    print(f"{'Review':<60} {'Label':<10} {'Confidence'}")
    print("-" * 85)

    for review in REVIEWS:
        # Create a fresh session per review to avoid context window buildup
        session = fm.LanguageModelSession(
            instructions="You are a sentiment classifier. Analyze the sentiment of the given text.",
            model=model,
        )

        try:
            result = await session.respond(review, generating=SentimentResult)

            # Access typed fields directly — it's a dataclass, not JSON to parse
            label = result.label
            confidence = result.confidence

            truncated = review[:57] + "..." if len(review) > 60 else review
            print(f"{truncated:<60} {label:<10} {confidence:.2f}")
        except fm.ExceededContextWindowSizeError:
            print(f"{'(context exceeded)':<60} {'—':<10} —")
        except fm.GenerationError as e:
            print(f"{'(error: ' + type(e).__name__ + ')':<60} {'—':<10} —")


if __name__ == "__main__":
    asyncio.run(main())
