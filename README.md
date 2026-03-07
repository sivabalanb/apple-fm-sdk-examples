# apple-fm-sdk-examples

Hands-on examples for Apple's on-device Foundation Models SDK for Python — structured generation, tool calling, content tagging, error handling, and head-to-head comparisons with Claude. Everything runs on-device, no API keys needed.

## Requirements

- macOS 26.0+ (Tahoe)
- Python 3.10+
- Apple Silicon Mac with Apple Intelligence enabled

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# For comparison examples only
export ANTHROPIC_API_KEY="your-key-here"
```

## Examples

| # | Folder | What You'll Learn |
|---|--------|-------------------|
| 01 | `01-basics/` | Model init, availability, multi-turn, content tagging, error handling |
| 02 | `02-streaming/` | Real-time streaming, latency profiling, throughput |
| 03 | `03-guided-generation/` | Structured output with `@generable`, constraints |
| 04 | `04-tool-calling/` | Function calling, stateful agents, multi-turn workflows |
| 05 | `05-batch-evaluation/` | Batch testing, accuracy scoring, transcript analysis |
| 06 | `06-comparisons/` | Apple FM vs Claude — side-by-side |
| 07 | `07-real-world/` | Commit suggester, doc classifier, bulk tagger |

## Key Patterns

### Content Tagging
```python
model = fm.SystemLanguageModel(use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING)

@fm.generable("Article metadata")
class ArticleMetadata:
    category: str = fm.guide(anyOf=["technology", "business", "health"])
    sentiment: str = fm.guide(anyOf=["positive", "neutral", "negative"])

result = await session.respond(article, generating=ArticleMetadata)
print(result.category, result.sentiment)
```

### Error Handling
```python
try:
    result = await session.respond(prompt, generating=Schema)
except fm.ExceededContextWindowSizeError:
    session = fm.LanguageModelSession(model=model)  # Fresh session
    result = await session.respond(prompt, generating=Schema)
except fm.GuardrailViolationError:
    print("Content violates guidelines")
except fm.GenerationError as e:
    print(f"Error: {type(e).__name__}")
```

### Stateful Tool Calling
```python
memory = TaskMemory()
session = fm.LanguageModelSession(
    tools=[TaskManagerTool(memory)],
    model=model,
)
# Memory persists across session resets
```

## Mental Model

> Apple FM is like SQLite — local, free, great for classification.
> Claude is like Postgres — powerful, for heavy lifting.

| | Apple FM | Claude |
|---|---|---|
| Privacy | On-device | Cloud |
| Cost | Free | Per-token |
| Classification | Excellent | Excellent |
| Reasoning | Basic | Excellent |
| Offline | Yes | No |

## Running Examples

```bash
python3 01-basics/hello_world.py
python3 01-basics/content_tagging_showcase.py
python3 02-streaming/instrumentation_and_profiling.py
python3 04-tool-calling/stateful_agent.py
python3 06-comparisons/compare_classification.py  # needs ANTHROPIC_API_KEY
```

## Tests

```bash
python3 -m pytest tests/ -v
```

## Documentation

| Guide | Coverage |
|-------|----------|
| `docs/CONTENT_TAGGING_GUIDE.md` | CONTENT_TAGGING mode, use cases, best practices |
| `docs/ERROR_HANDLING_REFERENCE.md` | All 10 error types + recovery strategies |
| `docs/INSTRUMENTATION_AND_TOOLS_GUIDE.md` | Latency profiling + Tool architecture |
| `docs/STATEFUL_PATTERNS.md` | Multi-turn workflows with tool state |
