"""
Bulk content tagger using Apple FM SDK.

Tags 15 content items across multiple dimensions (topic, tone, audience,
length category). Uses CONTENT_TAGGING mode. Shows a progress bar, exports
results to CSV, and provides a cost comparison note vs cloud API equivalents.
"""

import csv
import time
from pathlib import Path

import FoundationModels

# ---------------------------------------------------------------------------
# Content items to tag
# ---------------------------------------------------------------------------

CONTENT_ITEMS = [
    {
        "id": "c001",
        "title": "Getting Started with Swift Concurrency",
        "excerpt": (
            "Swift's async/await syntax transforms how we write asynchronous code. "
            "In this tutorial we'll build a simple weather app that fetches data "
            "concurrently using TaskGroup, with error handling at every step."
        ),
    },
    {
        "id": "c002",
        "title": "The Hidden Costs of Technical Debt",
        "excerpt": (
            "Every shortcut you take today compounds interest tomorrow. This post "
            "examines three real codebases where accumulated technical debt caused "
            "six-figure engineering costs and how to break the cycle."
        ),
    },
    {
        "id": "c003",
        "title": "10 Must-Try Pasta Recipes for Weeknight Dinners",
        "excerpt": (
            "Tired of the same old spaghetti bolognese? These crowd-pleasing pasta "
            "dishes come together in under 30 minutes with pantry staples you "
            "already have. Your family will beg for seconds!"
        ),
    },
    {
        "id": "c004",
        "title": "Understanding Transformer Architecture",
        "excerpt": (
            "The attention mechanism is the cornerstone of modern language models. "
            "We derive the scaled dot-product attention formula from first principles, "
            "then implement a minimal transformer in PyTorch with annotated code."
        ),
    },
    {
        "id": "c005",
        "title": "My Year of Cold Showers: What I Learned",
        "excerpt": (
            "I challenged myself to take cold showers every morning for 365 days. "
            "Here's what actually happened to my energy levels, mood, and willpower — "
            "including the weeks when I wanted to quit."
        ),
    },
    {
        "id": "c006",
        "title": "VC Funding Is Down 40% — What Founders Should Do Now",
        "excerpt": (
            "The funding environment has fundamentally shifted. Q1 deal counts hit a "
            "five-year low and valuations compressed across all stages. We spoke with "
            "12 founders who closed rounds in 2024 to learn what actually works."
        ),
    },
    {
        "id": "c007",
        "title": "SQL Window Functions Explained with Real Examples",
        "excerpt": (
            "Window functions are one of SQL's most powerful and underused features. "
            "We walk through ROW_NUMBER, RANK, LEAD, LAG, and running totals with "
            "concrete datasets you can run against your own Postgres instance."
        ),
    },
    {
        "id": "c008",
        "title": "Why Your Morning Routine Is Killing Your Productivity",
        "excerpt": (
            "Stop optimizing your morning and start protecting your deep work hours. "
            "Science shows that most productivity rituals are procrastination in disguise. "
            "Here's a contrarian take backed by cognitive research."
        ),
    },
    {
        "id": "c009",
        "title": "A Beginner's Guide to Home Composting",
        "excerpt": (
            "Composting turns kitchen scraps into rich garden soil and it's easier "
            "than you think. This step-by-step guide covers bins, layering, moisture "
            "balance, and how to troubleshoot a smelly pile."
        ),
    },
    {
        "id": "c010",
        "title": "Zero-Knowledge Proofs: A Technical Deep Dive",
        "excerpt": (
            "ZK-SNARKs enable one party to prove knowledge of information without "
            "revealing it. We explore the mathematics behind Groth16 and PLONK, "
            "survey production use cases in blockchain, and benchmark proof generation."
        ),
    },
    {
        "id": "c011",
        "title": "How to Negotiate Your Salary (And Win)",
        "excerpt": (
            "Most people leave money on the table because they're afraid to negotiate. "
            "Former recruiter shares the exact scripts and strategies used by candidates "
            "who successfully negotiated 15–30% above initial offers."
        ),
    },
    {
        "id": "c012",
        "title": "Building a Sourdough Starter from Scratch",
        "excerpt": (
            "Day 1 through Day 14: a photo-documented journey of creating a healthy "
            "sourdough starter using only flour and water. Includes troubleshooting "
            "for common failures like hooch, mold, and sluggish fermentation."
        ),
    },
    {
        "id": "c013",
        "title": "GraphQL vs REST: Choosing the Right API for Your Team",
        "excerpt": (
            "Both REST and GraphQL have clear strengths and sharp edges. We compare "
            "them across caching, type safety, developer experience, and operational "
            "complexity using case studies from companies that switched in both directions."
        ),
    },
    {
        "id": "c014",
        "title": "The Climate Case for Nuclear Energy",
        "excerpt": (
            "Intermittency, grid storage costs, and land use make 100% renewables "
            "difficult to achieve at scale. A rigorous examination of whether modern "
            "nuclear reactors belong in a serious decarbonization roadmap."
        ),
    },
    {
        "id": "c015",
        "title": "Docker Compose Secrets Every Developer Should Know",
        "excerpt": (
            "Beyond docker-compose up: practical tips for multi-stage builds, "
            "health checks, named volumes, network isolation, and using .env files "
            "safely in local development and CI pipelines."
        ),
    },
]

# ---------------------------------------------------------------------------
# Tag schema
# ---------------------------------------------------------------------------

PRIMARY_TOPICS = [
    "software_development",
    "data_science_ml",
    "food_cooking",
    "personal_development",
    "business_finance",
    "science_technology",
    "lifestyle_wellness",
    "other",
]

TONES = ["educational", "inspirational", "analytical", "conversational", "controversial"]

TARGET_AUDIENCES = [
    "beginners",
    "intermediate_practitioners",
    "experts",
    "general_public",
    "business_professionals",
]

CONTENT_LENGTHS = ["short", "medium", "long", "deep_dive"]


@FoundationModels.generable
class ContentTags:
    """Multi-dimensional tags for a piece of content."""

    primary_topic: str = FoundationModels.GenerationSchema(
        description="Primary subject area of the content",
        anyOf=PRIMARY_TOPICS,
    )
    tone: str = FoundationModels.GenerationSchema(
        description="Predominant tone or style of the content",
        anyOf=TONES,
    )
    target_audience: str = FoundationModels.GenerationSchema(
        description="Primary intended audience",
        anyOf=TARGET_AUDIENCES,
    )
    content_length: str = FoundationModels.GenerationSchema(
        description="Inferred length category based on depth and complexity signals",
        anyOf=CONTENT_LENGTHS,
    )
    keywords: str = FoundationModels.GenerationSchema(
        description="Comma-separated list of 3-5 relevant keywords for search indexing",
    )


# ---------------------------------------------------------------------------
# Tagger
# ---------------------------------------------------------------------------


def tag_content(item: dict) -> ContentTags | None:
    """Tag a single content item using a fresh FM session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a content taxonomy system. Given a title and excerpt, "
            "assign precise tags for topic, tone, target audience, and length. "
            "Be consistent: similar content should receive the same tags."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )
    try:
        result = session.respond(
            f"Tag this content:\n\nTitle: {item['title']}\n\nExcerpt: {item['excerpt']}",
            generating=ContentTags,
        )
        return result
    except FoundationModels.ExceededContextWindowSizeError:
        print(f"  [SKIP] Context window exceeded for: {item['title'][:50]}")
        return None


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """Return a simple ASCII progress bar string."""
    filled = int(width * current / total) if total > 0 else 0
    bar = "#" * filled + "-" * (width - filled)
    pct = current / total * 100 if total > 0 else 0
    return f"[{bar}] {current}/{total} ({pct:.0f}%)"


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def export_csv(rows: list[dict], output_path: Path) -> None:
    """Write tagging results to a CSV file."""
    fieldnames = [
        "id",
        "title",
        "primary_topic",
        "tone",
        "target_audience",
        "content_length",
        "keywords",
        "skipped",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Cost comparison note
# ---------------------------------------------------------------------------


def print_cost_comparison(item_count: int, elapsed: float) -> None:
    """Print an illustrative cost comparison vs cloud API equivalents."""
    # Rough estimates: ~200 tokens per item, at common API pricing
    estimated_tokens = item_count * 200
    gpt4o_cost = estimated_tokens / 1_000_000 * 5.00  # $5/M input tokens (approx)
    claude_cost = estimated_tokens / 1_000_000 * 3.00  # $3/M input tokens (approx)

    print()
    print("Cost Comparison (illustrative estimates):")
    print(f"  Items processed       : {item_count}")
    print(f"  Est. tokens used      : ~{estimated_tokens:,}")
    print(f"  Apple FM SDK cost     : $0.00  (on-device, no API calls)")
    print(f"  GPT-4o equivalent     : ~${gpt4o_cost:.4f}")
    print(f"  Claude equivalent     : ~${claude_cost:.4f}")
    print(f"  Processing time       : {elapsed:.2f}s")
    print()
    print("Note: Apple FM runs entirely on-device — zero cloud costs and")
    print("      zero data egress. Ideal for bulk tagging at scale.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("Bulk Content Tagger (Apple FM SDK — CONTENT_TAGGING mode)")
    print("=" * 60)
    print(f"Items to tag: {len(CONTENT_ITEMS)}")
    print()

    rows = []
    tagged = 0
    skipped = 0
    start_time = time.perf_counter()

    for i, item in enumerate(CONTENT_ITEMS, 1):
        print(f"\r{progress_bar(i - 1, len(CONTENT_ITEMS))}  {item['title'][:30]:<30}", end="", flush=True)

        result = tag_content(item)

        if result is None:
            skipped += 1
            rows.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "primary_topic": "",
                    "tone": "",
                    "target_audience": "",
                    "content_length": "",
                    "keywords": "",
                    "skipped": True,
                }
            )
        else:
            tagged += 1
            rows.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "primary_topic": result.primary_topic,
                    "tone": result.tone,
                    "target_audience": result.target_audience,
                    "content_length": result.content_length,
                    "keywords": result.keywords,
                    "skipped": False,
                }
            )

    elapsed = time.perf_counter() - start_time
    print(f"\r{progress_bar(len(CONTENT_ITEMS), len(CONTENT_ITEMS))}")
    print()

    # Results table
    print("=" * 60)
    print("Tagging Results")
    print("=" * 60)
    print(f"{'ID':<6} {'Topic':<25} {'Tone':<16} {'Audience':<26} {'Length'}")
    print("-" * 90)
    for row in rows:
        if not row["skipped"]:
            print(
                f"{row['id']:<6} {row['primary_topic']:<25} "
                f"{row['tone']:<16} {row['target_audience']:<26} {row['content_length']}"
            )
        else:
            print(f"{row['id']:<6} SKIPPED")

    print()
    print(f"Tagged   : {tagged}/{len(CONTENT_ITEMS)}")
    print(f"Skipped  : {skipped}/{len(CONTENT_ITEMS)}")

    # CSV export
    output_path = Path(__file__).parent / "bulk_tags.csv"
    export_csv(rows, output_path)
    print(f"Exported : {output_path}")

    print_cost_comparison(tagged, elapsed)


if __name__ == "__main__":
    main()
