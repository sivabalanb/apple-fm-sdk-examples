# 🍎 Apple Foundation Models SDK — Python Examples

A comprehensive collection of **22 runnable Python examples** for Apple's on-device Foundation Models framework, introduced in macOS 26 (Tahoe). Every example runs entirely on-device — no cloud APIs, no API keys, no data leaving your Mac.

The examples progress from basics to production patterns: plain-text generation, streaming with latency profiling, structured output via `@generable` schemas, multi-tool agentic workflows with persistent state, batch evaluation with accuracy scoring, head-to-head comparisons against Claude, and real-world utilities like commit message generation and document classification.

## 🔒 Why On-Device?

| | Apple FM (on-device) | Cloud LLMs |
|---|---|---|
| **Privacy** | Nothing leaves your Mac | Data sent to external servers |
| **Cost** | Free, unlimited | Per-token billing |
| **Latency** | No network round-trip | Network-dependent |
| **Offline** | Works without internet | Requires connectivity |
| **Classification** | Excellent for tagging & extraction | Excellent |
| **Reasoning** | Basic | Advanced |

> **Mental model:** Apple FM is like SQLite — local, free, great for structured tasks.
> Cloud LLMs are like Postgres — powerful, for heavy reasoning.

## 📋 Requirements

- **macOS 26.0+** (Tahoe)
- **Apple Silicon** Mac with Apple Intelligence enabled
- **Python 3.10+**

> **Note:** These examples use a version of `apple-fm-sdk` that does not require Xcode. The library is imported locally via `pip install` — no Xcode installation or Swift toolchain needed.

## 🚀 Quick Start

```bash
git clone https://github.com/sivabalanb/apple-fm-sdk-examples.git
cd apple-fm-sdk-examples

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run your first example
python3 01-basics/hello_world.py
```

For comparison examples (folder `06-comparisons/`), you also need:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## 🛡️ Standalone Demo: PII Guardian

**[`pii_guardian.py`](PII_GUARDIAN_README.md)** — A production-ready local PII scanner and redactor. Scan files for SSNs, credit cards, API keys, and passwords with zero external dependencies. Features file scanning, directory recursion, JSON reports, redaction with safe placeholders (`[SSN_1]`, `[EMAIL_2]`), and a git pre-commit hook mode to block commits containing PII.

```bash
python pii_guardian.py scan document.txt              # Scan a file
python pii_guardian.py scan ./data/ --recursive      # Scan a directory
python pii_guardian.py scan data.txt --redact        # Create redacted copy
python pii_guardian.py --install-hook                # Install git hook
```

**[Full documentation →](PII_GUARDIAN_README.md)**

---

## 📂 What's Inside

### 01 — Basics

| Script | What It Covers |
|--------|----------------|
| `hello_world.py` | Model initialization, availability check, first `session.respond()` call |
| `availability_check.py` | Querying availability across model configurations (`CONTENT_TAGGING`, `PERMISSIVE_CONTENT_TRANSFORMATIONS`) |
| `multi_turn.py` | Multi-turn conversations with `instructions=`, session memory, context window overflow recovery |
| `content_tagging_showcase.py` | Full tagging pipeline — classifying 5 articles by category, sentiment, and keywords using `@generable` schemas |
| `error_handling_guide.py` | All 7 error types: `GuardrailViolationError`, `ExceededContextWindowSizeError`, `RefusalError`, `RateLimitedError`, and more |

### 02 — Streaming

| Script | What It Covers |
|--------|----------------|
| `stream_response.py` | Real-time `session.stream_response()` with `async for`, multi-turn streaming |
| `instrumentation_and_profiling.py` | Custom `PerformanceProfiler`: measures total latency, time-to-first-token (TTFT), and throughput across 10 requests |

### 03 — Guided Generation (Structured Output)

All scripts use `@fm.generable` to produce typed Python dataclass output — no JSON parsing needed.

| Script | Schema & Constraints |
|--------|----------------------|
| `sentiment_classifier.py` | `SentimentResult` — `anyOf` enum constraint for labels, `range` constraint for confidence scores |
| `email_parser.py` | `ParsedEmail` — 6 fields including priority, category, action required; notes that regex is not supported |
| `receipt_extractor.py` | **Nested schemas** — `LineItem` objects inside a `Receipt`; post-generation validation of subtotals |
| `rating_predictor.py` | `RatingPrediction` — both `float` and `int` range constraints on scores |

### 04 — Tool Calling (Agentic Workflows)

Tools subclass `FoundationModels.Tool` with typed `@generable` argument schemas. The model decides which tool to invoke at each turn.

| Script | Tools | Key Pattern |
|--------|-------|-------------|
| `calculator_tool.py` | `CalculatorTool` | Single tool with context window recovery |
| `file_search_tool.py` | `FileSearchTool`, `FileReaderTool` | Multi-tool sessions — model picks the right tool per query |
| `multi_tool_agent.py` | `DateTimeTool`, `UnitConverterTool`, `TextAnalyzerTool` | Three tools, autonomous selection |
| `stateful_agent.py` | `TaskManagerTool`, `ContextTool` | **Stateful memory** — Python objects survive session resets |
| `code_review_agent.py` | `SnippetStorageTool`, `ReviewFeedbackTool` | Domain-specific memory for storing code snippets and accumulating review feedback |

### 05 — Batch Evaluation

| Script | What It Covers |
|--------|----------------|
| `evaluate_classifier.py` | Batch accuracy testing on 15 labeled support tickets — measures overall accuracy and per-category breakdown; exports JSON results |
| `transcript_analysis.py` | Pure-Python analysis of customer service transcripts — turn counts, response lengths, quality metrics |

Pre-computed results in `classification_results.json` show **73.3% accuracy** (11/15) in ~6.7 seconds.

### 06 — Apple FM vs Claude Comparisons

Side-by-side evaluation against `claude-sonnet-4-6` using `anthropic` SDK. Requires `ANTHROPIC_API_KEY`.

| Script | Task | What It Measures |
|--------|------|------------------|
| `compare_classification.py` | Sentiment analysis on 5 texts | Label agreement rate, timing |
| `compare_extraction.py` | Contact extraction from messy text | Per-field match analysis |
| `compare_reasoning.py` | Math, code gen, unit economics, logic puzzle | Response quality, length, timing |

### 07 — Real-World Utilities

| Script | What It Does |
|--------|-------------|
| `local_commit_suggester.py` | Reads `git diff --cached`, generates conventional commit messages on-device |
| `privacy_doc_classifier.py` | Classifies documents by type, sensitivity, and PII presence — fully private |
| `bulk_tagger.py` | Tags 15 items across 4 dimensions with progress bar and CSV export; prints cost comparison ($0 vs cloud pricing) |

*Note: `pii_guardian.py` has been promoted to a standalone demo at the repo root — [see PII Guardian docs](PII_GUARDIAN_README.md).*

## 🧩 Key API Patterns

### Structured Output with `@generable`
```python
import apple_fm_sdk as fm

model = fm.SystemLanguageModel(use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING)

@fm.generable("Article metadata")
class ArticleMetadata:
    category: str = fm.guide(anyOf=["technology", "business", "health"])
    sentiment: str = fm.guide(anyOf=["positive", "neutral", "negative"])

session = fm.LanguageModelSession(model=model)
result = await session.respond(article_text, generating=ArticleMetadata)
print(result.category, result.sentiment)
```

### Stateful Tool Calling
```python
import FoundationModels

class TaskMemory:
    """Python object that survives session resets."""
    def __init__(self):
        self.tasks = {}

memory = TaskMemory()
session = fm.LanguageModelSession(
    tools=[TaskManagerTool(memory), ContextTool(memory)],
    model=model,
)
# When context window overflows, recreate the session
# but pass the SAME memory object — state is preserved
```

### Error Recovery
```python
try:
    result = await session.respond(prompt, generating=Schema)
except fm.ExceededContextWindowSizeError:
    session = fm.LanguageModelSession(model=model)  # Fresh session
    result = await session.respond(prompt, generating=Schema)
except fm.GuardrailViolationError:
    print("Content violates safety guidelines")
except fm.GenerationError as e:
    print(f"Generation failed: {type(e).__name__}")
```

## 🗂️ Project Structure

```
apple-fm-sdk-examples/
├── pii_guardian.py              # Standalone demo — local PII scanner & redactor
├── PII_GUARDIAN_README.md       # PII Guardian documentation
├── 01-basics/                   # 5 scripts — init, availability, multi-turn, tagging, errors
├── 02-streaming/                # 2 scripts — streaming, latency profiling
├── 03-guided-generation/        # 4 scripts — structured output with constraints
├── 04-tool-calling/             # 5 scripts — tools, multi-tool agents, stateful memory
├── 05-batch-evaluation/         # 2 scripts — accuracy testing, transcript analysis
├── 06-comparisons/              # 3 scripts — Apple FM vs Claude benchmarks
├── 07-real-world/               # 3 scripts — commit suggester, doc classifier, bulk tagger
├── docs/                        # 4 in-depth guides
├── tests/                       # Structural + module-loadability tests (no device required)
├── utils/                       # Claude client wrapper, timing helpers
└── requirements.txt
```

## 📖 Documentation

| Guide | What It Covers |
|-------|----------------|
| [Content Tagging Guide](docs/CONTENT_TAGGING_GUIDE.md) | `CONTENT_TAGGING` mode vs general mode, use cases, best practices |
| [Error Handling Reference](docs/ERROR_HANDLING_REFERENCE.md) | All 10 error types with recovery strategies and code samples |
| [Instrumentation & Tools Guide](docs/INSTRUMENTATION_AND_TOOLS_GUIDE.md) | Latency profiling patterns, tool architecture, lifecycle diagrams |
| [Stateful Patterns](docs/STATEFUL_PATTERNS.md) | Application state across session resets, design patterns, pitfalls |

## 🧪 Tests

Tests validate file structure and module loadability — they run on any machine without Apple Intelligence hardware.

```bash
python3 -m pytest tests/ -v
```

## 📄 License

MIT
