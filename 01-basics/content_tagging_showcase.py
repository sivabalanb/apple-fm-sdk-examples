"""
01 — Content Tagging Use Case Showcase
Demonstrates: CONTENT_TAGGING use case, availability checks, practical workflow.

CONTENT_TAGGING is optimized for:
- Classifying, labeling, and categorizing content
- Extracting structured metadata from text
- Batch processing documents, articles, emails, etc.
- Tasks where the model primarily tags/categorizes rather than reasons

This example shows tagging at scale with proper error handling.
"""

import asyncio
from dataclasses import dataclass

import apple_fm_sdk as fm


@fm.generable("Article metadata")
class ArticleMetadata:
    title: str = fm.guide("Article title")
    category: str = fm.guide(
        anyOf=[
            "technology",
            "business",
            "health",
            "science",
            "politics",
            "sports",
            "entertainment",
            "education",
        ]
    )
    sentiment: str = fm.guide(anyOf=["positive", "neutral", "negative"])
    keywords: str = fm.guide("3-5 key topics, comma-separated")


# Sample articles for tagging
ARTICLES = [
    {
        "id": "article_001",
        "text": """
        Apple Announces Revolutionary M5 Chip

        Cupertino — Apple unveiled its latest M5 processor today, featuring a 40%
        performance boost and 25% improved battery efficiency. The new chip supports
        advanced machine learning operations and is set to power next-generation
        MacBooks and iPads. Industry analysts praise the innovation.
        """,
    },
    {
        "id": "article_002",
        "text": """
        Global Stock Markets Rally After Strong Tech Earnings

        Major stock indices climbed today following better-than-expected earnings
        reports from leading tech companies. The S&P 500 gained 2.3%, NASDAQ up 3.1%.
        Investors show renewed confidence in the sector despite earlier recession fears.
        """,
    },
    {
        "id": "article_003",
        "text": """
        New Study Links Mediterranean Diet to Longevity

        Researchers from a leading Mediterranean university found that people following
        a Mediterranean diet showed 30% lower mortality rates. The study tracked 10,000
        participants over 15 years, confirming earlier findings on the health benefits
        of olive oil, fish, and vegetables.
        """,
    },
    {
        "id": "article_004",
        "text": """
        Mars Rover Discovers Evidence of Ancient Water

        NASA's latest rover findings suggest Mars had substantial water billions of
        years ago. Geologists are excited about the implications for past microbial life.
        The discovery could reshape our understanding of the red planet's history.
        """,
    },
    {
        "id": "article_005",
        "text": """
        Election Results Show Record Voter Turnout

        Citizens voted at the highest rates in decades. The election saw record
        engagement, with new voters turning out in record numbers across all regions.
        Officials call it a victory for democracy.
        """,
    },
]


async def tag_article(session: fm.LanguageModelSession, article: dict) -> dict:
    """Tag a single article and return structured metadata."""
    try:
        result = await session.respond(
            f"""Tag this article with metadata.

Title and content:
{article['text']}

Provide accurate category, sentiment, and relevant keywords.""",
            generating=ArticleMetadata,
        )

        return {
            "id": article["id"],
            "success": True,
            "metadata": {
                "title": result.title,
                "category": result.category,
                "sentiment": result.sentiment,
                "keywords": result.keywords,
            },
        }
    except fm.GuardrailViolationError as e:
        return {
            "id": article["id"],
            "success": False,
            "error": "GuardrailViolationError",
            "message": "Content violates safety guidelines",
        }
    except fm.UnsupportedLanguageOrLocaleError as e:
        return {
            "id": article["id"],
            "success": False,
            "error": "UnsupportedLanguageOrLocaleError",
            "message": "Text language not supported by model",
        }
    except fm.ExceededContextWindowSizeError as e:
        return {
            "id": article["id"],
            "success": False,
            "error": "ExceededContextWindowSizeError",
            "message": "Article too long for context window",
        }
    except fm.UnsupportedGuideError as e:
        return {
            "id": article["id"],
            "success": False,
            "error": "UnsupportedGuideError",
            "message": "Schema constraint not supported",
        }
    except fm.GenerationError as e:
        return {
            "id": article["id"],
            "success": False,
            "error": type(e).__name__,
            "message": str(e),
        }


async def main():
    # Check model availability
    model = fm.SystemLanguageModel(
        use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING
    )

    is_available, reason = model.is_available()

    print("=" * 70)
    print("  CONTENT TAGGING SHOWCASE")
    print("  Optimized for classification & labeling tasks")
    print("=" * 70)

    print(f"\nModel Availability Check:")
    print(f"  Available: {is_available}")

    if not is_available:
        print(f"  Reason: {reason}")
        if reason == fm.SystemLanguageModelUnavailableReason.APPLE_INTELLIGENCE_NOT_ENABLED:
            print("  → Enable Apple Intelligence in System Settings")
        elif reason == fm.SystemLanguageModelUnavailableReason.DEVICE_NOT_ELIGIBLE:
            print("  → Your device doesn't support this model")
        elif reason == fm.SystemLanguageModelUnavailableReason.MODEL_NOT_READY:
            print("  → Model is downloading, please wait...")
        return

    # Create session optimized for tagging
    session = fm.LanguageModelSession(
        instructions=(
            "You are a content classifier. "
            "Analyze articles and extract: title, category, sentiment, and keywords. "
            "Be accurate and consistent in your categorization."
        ),
        model=model,
    )

    # Tag all articles
    print(f"\nTagging {len(ARTICLES)} articles...\n")

    results = []
    successful = 0
    failed = 0

    for article in ARTICLES:
        result = await tag_article(session, article)
        results.append(result)

        if result["success"]:
            successful += 1
            metadata = result["metadata"]
            print(f"✓ {result['id']}")
            print(f"  Category: {metadata['category']}")
            print(f"  Sentiment: {metadata['sentiment']}")
            print(f"  Keywords: {metadata['keywords']}")
        else:
            failed += 1
            print(f"✗ {result['id']}: {result['error']}")
            print(f"  {result['message']}")

    # Summary
    print(f"\n{'='*70}")
    print(f"Content Tagging Summary")
    print(f"{'='*70}")
    print(f"Total articles: {len(ARTICLES)}")
    print(f"Successfully tagged: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/len(ARTICLES)*100:.0f}%")

    # Category distribution
    if successful > 0:
        categories = {}
        sentiments = {}
        for result in results:
            if result["success"]:
                cat = result["metadata"]["category"]
                categories[cat] = categories.get(cat, 0) + 1

                sent = result["metadata"]["sentiment"]
                sentiments[sent] = sentiments.get(sent, 0) + 1

        print(f"\nCategory Distribution:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

        print(f"\nSentiment Distribution:")
        for sent, count in sorted(sentiments.items()):
            print(f"  {sent}: {count}")

    print(f"\n{'='*70}")
    print("Key Insights:")
    print("  • CONTENT_TAGGING is optimized for classification tasks")
    print("  • No internet required — runs entirely on-device")
    print("  • Always check model.is_available() before proceeding")
    print("  • Catch specific exceptions (GuardrailViolation, UnsupportedLanguage)")
    print("  • Can scale to thousands of items with no cost per token")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
