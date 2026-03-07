"""
03 — Rating Predictor
Predict a numeric rating from text with constrained ranges.
Demonstrates: range constraint on floats and ints, multiple fields.
"""

import asyncio

import apple_fm_sdk as fm


@fm.generable("Product rating prediction")
class RatingPrediction:
    overall_score: float = fm.guide(range=(1.0, 5.0))
    quality_score: int = fm.guide(range=(1, 10))
    would_recommend: str = fm.guide(anyOf=["yes", "no", "maybe"])
    summary: str = fm.guide("One-sentence summary of the review")


REVIEWS = [
    """Been using this mechanical keyboard for 3 months. The switches feel great,
    build quality is solid, and the RGB lighting is tasteful. Only downside is
    the software for customization is a bit clunky. Overall very happy.""",

    """This chair was a complete disappointment. The lumbar support broke within
    a week, the armrests wobble, and the cushion is rock hard. Save your money
    and buy literally anything else.""",

    """It's a monitor. It displays things. Colors are acceptable, refresh rate
    is what was advertised. Nothing blew me away but nothing was terrible either.
    Fine for the price point I guess.""",
]


async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    for i, review in enumerate(REVIEWS, 1):
        # Create a fresh session per review to avoid context window buildup
        session = fm.LanguageModelSession(
            instructions="You are a product review analyst. Predict ratings from review text.",
            model=model,
        )

        try:
            result = await session.respond(
                f"Analyze this review:\n{review}",
                generating=RatingPrediction,
            )

            print(f"=== Review {i} ===")
            print(f"Overall:   {result.overall_score:.1f} / 5.0")
            print(f"Quality:   {result.quality_score} / 10")
            print(f"Recommend: {result.would_recommend}")
            print(f"Summary:   {result.summary}")
            print()
        except fm.ExceededContextWindowSizeError:
            print(f"=== Review {i} === [context window exceeded]")
        except fm.GenerationError as e:
            print(f"=== Review {i} === [error: {type(e).__name__}]")


if __name__ == "__main__":
    asyncio.run(main())
