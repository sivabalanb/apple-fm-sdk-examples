"""
Module-load tests for 03-guided-generation examples.

These tests verify that each module can be located and loaded by Python's
import machinery without executing the async main() function or requiring
the Apple FM SDK to be installed at runtime.
"""

import importlib.util
from pathlib import Path

GUIDED_GEN = Path(__file__).parent.parent / "03-guided-generation"


def _load_module(filename: str):
    """Load a module from a file path using importlib without executing it."""
    path = GUIDED_GEN / filename
    assert path.exists(), f"File not found: {path}"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None, f"Could not create spec for {path}"
    assert spec.loader is not None, f"Spec has no loader for {path}"
    module = importlib.util.module_from_spec(spec)
    return module, spec, path


def test_sentiment_classifier_module_loadable():
    """sentiment_classifier.py can be found and a module spec created for it."""
    module, spec, path = _load_module("sentiment_classifier.py")
    text = path.read_text()
    # Verify the module exposes expected top-level names via source inspection
    assert "SentimentResult" in text
    assert "REVIEWS" in text
    assert "async def main" in text


def test_rating_predictor_module_loadable():
    """rating_predictor.py can be found and a module spec created for it."""
    module, spec, path = _load_module("rating_predictor.py")
    text = path.read_text()
    assert "RatingPrediction" in text
    assert "overall_score" in text
    assert "would_recommend" in text
    assert "async def main" in text


def test_email_parser_module_loadable():
    """email_parser.py can be found and a module spec created for it."""
    module, spec, path = _load_module("email_parser.py")
    text = path.read_text()
    assert "ParsedEmail" in text
    assert "priority" in text
    assert "SAMPLE_EMAILS" in text
    assert "async def main" in text


def test_receipt_extractor_module_loadable():
    """receipt_extractor.py can be found and a module spec created for it."""
    module, spec, path = _load_module("receipt_extractor.py")
    text = path.read_text()
    assert "Receipt" in text
    assert "LineItem" in text
    assert "SAMPLE_RECEIPT" in text
    assert "async def main" in text


def test_compare_extraction_module_loadable():
    """06-comparisons/compare_extraction.py can be found and a module spec created."""
    compare_path = Path(__file__).parent.parent / "06-comparisons" / "compare_extraction.py"
    assert compare_path.exists(), f"File not found: {compare_path}"
    spec = importlib.util.spec_from_file_location("compare_extraction", compare_path)
    assert spec is not None, f"Could not create spec for {compare_path}"
    assert spec.loader is not None, f"Spec has no loader for {compare_path}"
    text = compare_path.read_text()
    assert "extract" in text.lower()
