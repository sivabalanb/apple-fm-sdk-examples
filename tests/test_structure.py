"""
Structural validation tests — verify every example file exists and
contains the expected identifiers, imports, and patterns.

These tests do NOT run the model; they just parse file contents.
"""

from pathlib import Path

REPO = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# 01 — Basics
# ---------------------------------------------------------------------------

class TestBasicsExamples:
    """Verify 01-basics/ example files exist and have the expected content."""

    def test_hello_world(self):
        path = REPO / "01-basics" / "hello_world.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "apple_fm_sdk" in text or "import fm" in text or "import apple_fm_sdk" in text
        assert "SystemLanguageModel" in text
        assert "LanguageModelSession" in text
        assert "is_available" in text
        assert "respond" in text
        assert "ExceededContextWindowSizeError" in text

    def test_availability_check(self):
        path = REPO / "01-basics" / "availability_check.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "SystemLanguageModel" in text
        assert "is_available" in text
        assert "CONTENT_TAGGING" in text
        assert "SystemLanguageModelUseCase" in text
        assert "PERMISSIVE_CONTENT_TRANSFORMATIONS" in text

    def test_multi_turn(self):
        path = REPO / "01-basics" / "multi_turn.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "SystemLanguageModel" in text
        assert "LanguageModelSession" in text
        assert "instructions" in text
        assert "ExceededContextWindowSizeError" in text
        assert "is_responding" in text

    def test_content_tagging_showcase(self):
        path = REPO / "01-basics" / "content_tagging_showcase.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "CONTENT_TAGGING" in text
        assert "generable" in text
        assert "ArticleMetadata" in text
        assert "GuardrailViolationError" in text
        assert "UnsupportedLanguageOrLocaleError" in text
        assert "ExceededContextWindowSizeError" in text
        assert "SystemLanguageModelUnavailableReason" in text

    def test_error_handling_guide(self):
        path = REPO / "01-basics" / "error_handling_guide.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "GuardrailViolationError" in text
        assert "UnsupportedLanguageOrLocaleError" in text
        assert "ExceededContextWindowSizeError" in text
        assert "RefusalError" in text
        assert "RateLimitedError" in text
        assert "UnsupportedGuideError" in text
        assert "ConcurrentRequestsError" in text
        assert "APPLE_INTELLIGENCE_NOT_ENABLED" in text
        assert "DEVICE_NOT_ELIGIBLE" in text
        assert "MODEL_NOT_READY" in text


# ---------------------------------------------------------------------------
# 02 — Streaming
# ---------------------------------------------------------------------------

class TestStreamingExamples:
    """Verify 02-streaming/ example files exist and have the expected content."""

    def test_stream_response(self):
        path = REPO / "02-streaming" / "stream_response.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "stream_response" in text
        assert "SystemLanguageModel" in text
        assert "LanguageModelSession" in text
        assert "async for" in text
        assert "ExceededContextWindowSizeError" in text
        assert "flush=True" in text

    def test_instrumentation_and_profiling(self):
        path = REPO / "02-streaming" / "instrumentation_and_profiling.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "PerformanceProfiler" in text
        assert "LatencyMetrics" in text
        assert "time.perf_counter" in text
        assert "measure_latency" in text
        assert "measure_streaming_latency" in text
        assert "first_token_time" in text
        assert "tokens_per_second" in text


# ---------------------------------------------------------------------------
# 03 — Guided Generation
# ---------------------------------------------------------------------------

class TestGuidedGenerationExamples:
    """Verify 03-guided-generation/ example files exist and have the expected content."""

    def test_sentiment_classifier(self):
        path = REPO / "03-guided-generation" / "sentiment_classifier.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "generable" in text
        assert "SentimentResult" in text
        assert "anyOf" in text
        assert "positive" in text
        assert "negative" in text
        assert "neutral" in text
        assert "confidence" in text
        assert "CONTENT_TAGGING" in text

    def test_receipt_extractor(self):
        path = REPO / "03-guided-generation" / "receipt_extractor.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "generable" in text
        assert "Receipt" in text
        assert "LineItem" in text
        assert "list[LineItem]" in text
        assert "payment_method" in text
        assert "HARBOR LANE CAFE" in text or "store_name" in text
        assert "OCR" in text or "Vision" in text

    def test_rating_predictor(self):
        path = REPO / "03-guided-generation" / "rating_predictor.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "generable" in text
        assert "RatingPrediction" in text
        assert "overall_score" in text
        assert "quality_score" in text
        assert "would_recommend" in text
        assert "range" in text

    def test_email_parser(self):
        path = REPO / "03-guided-generation" / "email_parser.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "generable" in text
        assert "ParsedEmail" in text
        assert "priority" in text
        assert "category" in text
        assert "action_required" in text
        assert "anyOf" in text
        assert "UnsupportedGuideError" in text or "regex" in text.lower()


# ---------------------------------------------------------------------------
# 04 — Tool Calling
# ---------------------------------------------------------------------------

class TestToolCallingExamples:
    """Verify 04-tool-calling/ example files exist and have the expected content."""

    def test_calculator_tool(self):
        path = REPO / "04-tool-calling" / "calculator_tool.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "CalculatorTool" in text
        assert "fm.Tool" in text or "FoundationModels.Tool" in text
        assert "arguments_schema" in text
        assert "async def call" in text
        assert "ExceededContextWindowSizeError" in text
        assert "create_session" in text

    def test_file_search_tool(self):
        path = REPO / "04-tool-calling" / "file_search_tool.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "FileSearchTool" in text
        assert "FileReaderTool" in text
        assert "fm.Tool" in text or "FoundationModels.Tool" in text
        assert "arguments_schema" in text
        assert "pathlib" in text
        assert "glob" in text
        assert "ExceededContextWindowSizeError" in text

    def test_multi_tool_agent(self):
        path = REPO / "04-tool-calling" / "multi_tool_agent.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "DateTimeTool" in text
        assert "UnitConverterTool" in text
        assert "TextAnalyzerTool" in text
        assert "create_session" in text
        assert "ExceededContextWindowSizeError" in text
        assert "tools=" in text

    def test_stateful_agent(self):
        path = REPO / "04-tool-calling" / "stateful_agent.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "session" in text.lower()
        assert "stateful" in text.lower() or "state" in text.lower()

    def test_code_review_agent(self):
        path = REPO / "04-tool-calling" / "code_review_agent.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "code" in text.lower()
        assert "review" in text.lower()


# ---------------------------------------------------------------------------
# 05 — Batch Evaluation
# ---------------------------------------------------------------------------

class TestBatchEvaluation:
    """Verify 05-batch-evaluation/ example files exist and have the expected content."""

    def test_evaluate_classifier(self):
        path = REPO / "05-batch-evaluation" / "evaluate_classifier.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "TicketCategory" in text
        assert "bug_report" in text
        assert "feature_request" in text
        assert "CONTENT_TAGGING" in text
        assert "accuracy" in text.lower()
        assert "json" in text.lower()
        assert "ExceededContextWindowSizeError" in text

    def test_transcript_analysis(self):
        path = REPO / "05-batch-evaluation" / "transcript_analysis.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "TranscriptAnalysis" in text
        assert "analyze_transcript" in text
        assert "acknowledgment_rate" in text
        assert "next_steps_rate" in text
        assert "SAMPLE_TRANSCRIPT" in text
        assert "quality_flags" in text


# ---------------------------------------------------------------------------
# 06 — Comparisons
# ---------------------------------------------------------------------------

class TestComparisonExamples:
    """Verify 06-comparisons/ example files exist and have the expected content."""

    def test_compare_classification(self):
        path = REPO / "06-comparisons" / "compare_classification.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "apple" in text.lower() or "fm" in text.lower()
        assert "claude" in text.lower() or "anthropic" in text.lower()
        assert "classif" in text.lower()

    def test_compare_extraction(self):
        path = REPO / "06-comparisons" / "compare_extraction.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "extract" in text.lower()
        assert "apple" in text.lower() or "fm" in text.lower()

    def test_compare_reasoning(self):
        path = REPO / "06-comparisons" / "compare_reasoning.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "reason" in text.lower()
        assert "apple" in text.lower() or "fm" in text.lower()


# ---------------------------------------------------------------------------
# 07 — Real World
# ---------------------------------------------------------------------------

class TestRealWorldExamples:
    """Verify 07-real-world/ example files exist and have the expected content."""

    def test_commit_suggester(self):
        path = REPO / "07-real-world" / "local_commit_suggester.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "commit" in text.lower()
        assert "git" in text.lower() or "diff" in text.lower()

    def test_privacy_classifier(self):
        path = REPO / "07-real-world" / "privacy_doc_classifier.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "privacy" in text.lower()
        assert "classif" in text.lower()

    def test_bulk_tagger(self):
        path = REPO / "07-real-world" / "bulk_tagger.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "tag" in text.lower()
        assert "bulk" in text.lower() or "batch" in text.lower()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

class TestUtilities:
    """Verify utils/ helper files exist and have the expected content."""

    def test_claude_client(self):
        path = REPO / "utils" / "claude_client.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "claude" in text.lower() or "anthropic" in text.lower()

    def test_helpers(self):
        path = REPO / "utils" / "helpers.py"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert len(text.strip()) > 0, "helpers.py is empty"


# ---------------------------------------------------------------------------
# Meta files
# ---------------------------------------------------------------------------

class TestMetaFiles:
    """Verify top-level meta files exist and have the expected content."""

    def test_readme(self):
        path = REPO / "README.md"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert len(text.strip()) > 0, "README.md is empty"

    def test_requirements(self):
        path = REPO / "requirements.txt"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert "apple-fm-sdk" in text
        assert "pytest" in text

    def test_gitignore(self):
        path = REPO / ".gitignore"
        assert path.exists(), f"Missing: {path}"
        text = path.read_text()
        assert ".venv" in text or "venv" in text
        assert "__pycache__" in text
        assert ".env" in text
