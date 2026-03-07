# Content Tagging Guide

A comprehensive reference for using `SystemLanguageModelUseCase.CONTENT_TAGGING` with the Apple FM SDK.

---

## What Is Content Tagging?

Content tagging is a broad category of NLP tasks where the model's job is to *label*, *classify*, or *extract metadata* from existing text rather than generate new text from scratch. Examples include:

- Classifying a support ticket as `bug_report`, `feature_request`, or `question`
- Labeling an article with a topic category and sentiment
- Extracting structured fields (sender, priority, action required) from an email
- Assigning moderation ratings to user-generated content
- Tagging products with attributes from their descriptions

Apple FM SDK exposes a dedicated `CONTENT_TAGGING` use case that signals to the underlying on-device model that your workload is classification-oriented, potentially enabling optimizations for that pattern.

---

## CONTENT_TAGGING vs. GENERAL: Comparison Table

| Dimension | `CONTENT_TAGGING` | `GENERAL` |
|-----------|-------------------|-----------|
| **Primary purpose** | Label, classify, extract metadata | Open-ended generation, reasoning, Q&A |
| **Output style** | Structured, constrained | Freeform prose or structured |
| **Guardrail behavior** | May differ; verify with `is_available()` | Standard defaults |
| **Ideal with `@generable`** | Yes — designed for this pattern | Yes, but less optimized |
| **Batch processing** | Excellent fit | Possible but less efficient |
| **Context window usage** | Lower (short prompts + structured output) | Potentially higher |
| **Cost** | Free, fully on-device | Free, fully on-device |
| **Example use case** | Tag 10,000 articles by category | Write a blog post or explain a concept |

---

## When to Use CONTENT_TAGGING

Use `CONTENT_TAGGING` when:

1. Your prompt is primarily a piece of input text (email, article, ticket) that needs labeling.
2. The model's output is a small, well-defined set of fields rather than flowing prose.
3. You are using `@generable` with `anyOf` or `range` constraints to guarantee output shape.
4. You are batch-processing many items in a pipeline.
5. The input content originates from users (documents, messages, posts) rather than being AI-generated.

Use `GENERAL` when:

1. You need multi-step reasoning or chain-of-thought responses.
2. The task is open-ended writing, summarization, or tutoring.
3. Your output schema is complex and deeply nested.
4. You need longer, narrative-style responses.

---

## Article Tagging — Example Code

```python
import asyncio
import apple_fm_sdk as fm


@fm.generable("Article metadata")
class ArticleMetadata:
    title: str = fm.guide("Article title, extracted from the text")
    category: str = fm.guide(
        anyOf=[
            "technology", "business", "health",
            "science", "politics", "sports",
            "entertainment", "education",
        ]
    )
    sentiment: str = fm.guide(anyOf=["positive", "neutral", "negative"])
    keywords: str = fm.guide("3-5 key topics, comma-separated")


async def tag_article(text: str) -> ArticleMetadata | None:
    model = fm.SystemLanguageModel(
        use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING,
    )
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model unavailable: {reason}")
        return None

    session = fm.LanguageModelSession(
        instructions=(
            "You are a content classifier. "
            "Extract title, category, sentiment, and keywords from articles. "
            "Be accurate and consistent."
        ),
        model=model,
    )

    try:
        return await session.respond(
            f"Tag this article:\n{text}",
            generating=ArticleMetadata,
        )
    except fm.GuardrailViolationError:
        print("Content violates safety guidelines")
        return None
    except fm.ExceededContextWindowSizeError:
        print("Article too long for context window — chunk it")
        return None
    except fm.GenerationError as e:
        print(f"Generation failed: {type(e).__name__}: {e}")
        return None


async def main():
    article = """
    Apple Announces Revolutionary M5 Chip

    Cupertino — Apple unveiled its latest M5 processor today, featuring a 40%
    performance boost and 25% improved battery efficiency. The new chip supports
    advanced machine learning operations and is set to power next-generation
    MacBooks and iPads. Industry analysts praise the innovation.
    """
    result = await tag_article(article)
    if result:
        print(f"Category:  {result.category}")
        print(f"Sentiment: {result.sentiment}")
        print(f"Keywords:  {result.keywords}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Real-World Use Cases

### 1. Email Triage

Tag incoming emails with priority and action-required flags to route them automatically.

```python
@fm.generable("Email triage result")
class EmailTag:
    priority: str = fm.guide(anyOf=["low", "medium", "high", "urgent"])
    category: str = fm.guide(anyOf=["meeting", "action_item", "fyi", "question", "social"])
    action_required: str = fm.guide(anyOf=["yes", "no"])
    summary: str = fm.guide("One-sentence summary of the email")
```

**When it shines:** Inbox zero automation, routing support tickets to the right team, filtering notification noise.

### 2. Product Attribute Extraction

Extract structured attributes from unstructured product descriptions for catalog enrichment.

```python
@fm.generable("Product attributes")
class ProductTag:
    product_type: str = fm.guide(anyOf=["laptop", "phone", "tablet", "accessory", "other"])
    brand: str = fm.guide("Brand name if mentioned, else 'unknown'")
    price_range: str = fm.guide(anyOf=["budget", "mid-range", "premium", "ultra-premium"])
    condition: str = fm.guide(anyOf=["new", "refurbished", "used"])
```

**When it shines:** E-commerce catalog management, price comparison engines, inventory systems.

### 3. Content Moderation

Classify user-generated content to flag policy violations before they reach production.

```python
@fm.generable("Moderation decision")
class ModerationTag:
    verdict: str = fm.guide(anyOf=["safe", "review", "remove"])
    reason: str = fm.guide("Brief reason for the decision")
    confidence: float = fm.guide(range=(0.0, 1.0))
```

**When it shines:** Community platforms, forums, review sites, social media filters.

### 4. Document Classification

Route documents to the right department or workflow by classifying them on receipt.

```python
@fm.generable("Document class")
class DocumentTag:
    doc_type: str = fm.guide(anyOf=["invoice", "contract", "policy", "report", "other"])
    department: str = fm.guide(anyOf=["legal", "finance", "hr", "engineering", "unknown"])
    urgency: str = fm.guide(anyOf=["routine", "priority", "critical"])
```

**When it shines:** Document management systems, accounts payable automation, legal review queues.

---

## Best Practices

### 1. Always Check Availability First

```python
model = fm.SystemLanguageModel(
    use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING
)
is_available, reason = model.is_available()
if not is_available:
    # Handle gracefully — don't proceed
    handle_unavailability(reason)
    return
```

### 2. Use a Fresh Session Per Item in Batch Jobs

Context window buildup across many items causes `ExceededContextWindowSizeError`. Create a new `LanguageModelSession` for each document in a batch:

```python
for item in items:
    session = fm.LanguageModelSession(instructions=INSTRUCTIONS, model=model)
    result = await session.respond(item["text"], generating=MySchema)
```

### 3. Keep Instructions Tight and Consistent

Verbose or ambiguous instructions confuse the classifier. State the task in one sentence, list the constraints, and repeat nothing.

```python
instructions = (
    "You are a support ticket classifier. "
    "Assign exactly one category: bug_report, feature_request, question, documentation, other. "
    "Be consistent across similar tickets."
)
```

### 4. Design Small, Focused Schemas

Each `@generable` class should represent one classification decision. Avoid schemas with more than 6–8 fields; split complex tasks into multiple passes.

### 5. Catch All Relevant Exceptions

```python
try:
    result = await session.respond(text, generating=MySchema)
except fm.GuardrailViolationError:
    ...  # Content blocked — skip or flag
except fm.UnsupportedLanguageOrLocaleError:
    ...  # Translate first
except fm.ExceededContextWindowSizeError:
    ...  # Chunk the input
except fm.UnsupportedGuideError:
    ...  # Fix the schema
except fm.GenerationError as e:
    ...  # Catch-all for other generation errors
```

### 6. Validate Output Downstream

The model will produce values within the `anyOf` or `range` you specified, but business logic validation (e.g., cross-field consistency, downstream referential integrity) belongs in your application code.

---

## Performance, Cost, and Scaling

| Concern | Notes |
|---------|-------|
| **Latency** | Typically 0.5–3s per item on Apple Silicon, depending on prompt length and output complexity |
| **Throughput** | Sequential only — on-device model is single-threaded at the hardware level |
| **Cost** | Zero — no API calls, no tokens billed |
| **Privacy** | Data never leaves the device |
| **Scale ceiling** | Constrained by device capability; for large-scale cloud jobs use Claude |
| **Cold start** | First call may be slower if the model is not yet warmed up |

**Tip:** For batch jobs of hundreds of items, measure latency with `time.perf_counter()` (see `02-streaming/instrumentation_and_profiling.py`) and set realistic throughput expectations before deploying.

---

## Error Handling Reference Table

| Error | When it occurs | Recommended action |
|-------|---------------|-------------------|
| `GuardrailViolationError` | Prompt or content violates safety policy | Rephrase prompt; use `PERMISSIVE_CONTENT_TRANSFORMATIONS` for transformation tasks |
| `UnsupportedLanguageOrLocaleError` | Input language not supported by on-device model | Translate to English first, or route to Claude |
| `ExceededContextWindowSizeError` | Combined prompt + history exceeds token limit | Create a new session; chunk long documents |
| `UnsupportedGuideError` | Schema constraint unsupported by the current model | Simplify the `@generable` schema; remove complex constraints |
| `RateLimitedError` | Request throttled at the system level | Wait before retrying; add backoff |
| `ConcurrentRequestsError` | Too many simultaneous requests | Run requests sequentially |
| `ValueError` (Python) | Invalid `anyOf` list (e.g., mixed types) | Fix the schema definition |

---

## Comparison with Cloud Classification Services

| Feature | Apple FM (CONTENT_TAGGING) | Cloud ML API |
|---------|---------------------------|--------------|
| **Cost** | Free | Per-request pricing |
| **Latency** | 0.5–3s, local | 100–500ms, network-dependent |
| **Privacy** | 100% on-device | Data sent to cloud |
| **Custom labels** | Yes, via `anyOf` | Varies by service |
| **Schema enforcement** | Strict via `@generable` | JSON parsing / prompt engineering |
| **Language support** | Limited (English + some) | Broad multilingual support |
| **Scalability** | Device-limited | Virtually unlimited |
| **Internet required** | No | Yes |

---

## Further Reading

- `01-basics/content_tagging_showcase.py` — Full working example tagging 5 articles
- `01-basics/availability_check.py` — Inspecting `CONTENT_TAGGING` model availability
- `03-guided-generation/sentiment_classifier.py` — Classification with `anyOf` and `range`
- `03-guided-generation/email_parser.py` — Multi-field extraction from emails
- `05-batch-evaluation/evaluate_classifier.py` — Accuracy evaluation across 15 test cases
- `docs/ERROR_HANDLING_REFERENCE.md` — Full error type reference
