"""
01 — Error Handling & Recovery Guide
Demonstrates: All error types, availability checks, recovery strategies.

Apple FM SDK can raise several error types:
- GenerationError subclasses (GuardrailViolation, UnsupportedLanguage, etc.)
- Python validation errors (ValueError, TypeError)
- SystemLanguageModelUnavailableReason codes

This example shows how to handle each properly.
"""

import asyncio
import sys

import apple_fm_sdk as fm


async def example_1_availability_check():
    """Example 1: Always check availability before using the model."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Availability Check")
    print("=" * 70)

    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()

    print(f"Model available: {is_available}")

    if not is_available:
        print(f"Reason: {reason}")

        # Handle each unavailability reason
        if reason == fm.SystemLanguageModelUnavailableReason.APPLE_INTELLIGENCE_NOT_ENABLED:
            print("→ Action: Enable Apple Intelligence in System Settings > Intelligence")
            return False

        elif reason == fm.SystemLanguageModelUnavailableReason.DEVICE_NOT_ELIGIBLE:
            print("→ Action: This device doesn't support Apple Intelligence")
            print("  Required: Apple Silicon Mac, iPhone 15 Pro+, iPad with M1+")
            return False

        elif reason == fm.SystemLanguageModelUnavailableReason.MODEL_NOT_READY:
            print("→ Action: Model is downloading/preparing")
            print("  You can wait for it to be ready, or check again later")
            return False

        else:
            print(f"→ Action: Unknown reason ({reason})")
            return False

    print("✓ Model is available and ready to use")
    return True


async def example_2_guardrail_violation():
    """Example 2: Handling guardrail violations (unsafe content)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Guardrail Violation Handling")
    print("=" * 70)

    model = fm.SystemLanguageModel()
    is_available, _ = model.is_available()

    if not is_available:
        print("Model not available, skipping example")
        return

    session = fm.LanguageModelSession(model=model)

    # Try prompts that might trigger guardrails
    test_prompts = [
        ("Safe prompt", "What is Python?"),
        ("Potentially unsafe", "Write instructions for harmful activity"),
        (
            "Sensitive but educational",
            "Explain how to identify scam attempts targeting elderly people",
        ),
    ]

    for name, prompt in test_prompts:
        print(f"\nTesting: {name}")
        print(f"Prompt: '{prompt[:50]}...'")

        try:
            response = await session.respond(prompt)
            print(f"✓ Response: {response[:60]}...")

        except fm.GuardrailViolationError as e:
            print(f"✗ GuardrailViolationError")
            print(f"  The content violates safety guidelines")
            print(f"  → Action: Rephrase with safer language")
            print(f"  → Alternative: Use PERMISSIVE_CONTENT_TRANSFORMATIONS guardrail")

        except fm.RefusalError as e:
            print(f"✗ RefusalError")
            print(f"  Model refused to generate this content")
            print(f"  Explanation: {e}")
            print(f"  → Action: Ask something else or rephrase")

        except fm.ExceededContextWindowSizeError:
            print(f"✗ ExceededContextWindowSizeError")
            print(f"  → Action: Start a new session")

        except fm.GenerationError as e:
            print(f"✗ GenerationError: {type(e).__name__}")
            print(f"  → Action: Investigate and retry")


async def example_3_unsupported_language():
    """Example 3: Handling unsupported languages."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Unsupported Language Handling")
    print("=" * 70)

    model = fm.SystemLanguageModel()
    is_available, _ = model.is_available()

    if not is_available:
        print("Model not available, skipping example")
        return

    session = fm.LanguageModelSession(model=model)

    # Test different languages
    test_languages = [
        ("English", "What is machine learning?"),
        ("French", "Qu'est-ce que l'apprentissage automatique?"),
        ("Spanish", "¿Qué es el aprendizaje automático?"),
        ("Chinese", "什么是机器学习?"),
        ("Arabic", "ما هو التعلم الآلي؟"),
    ]

    for lang, prompt in test_languages:
        print(f"\nTesting {lang}: '{prompt[:40]}...'")

        try:
            response = await session.respond(prompt)
            print(f"✓ Supported. Response: {response[:50]}...")

        except fm.UnsupportedLanguageOrLocaleError as e:
            print(f"✗ UnsupportedLanguageOrLocaleError")
            print(f"  This language is not supported by the on-device model")
            print(f"  → Action: Translate to English first, or use Claude")

        except fm.ExceededContextWindowSizeError:
            print(f"✗ Context window exceeded — starting fresh session")
            session = fm.LanguageModelSession(model=model)

        except fm.GenerationError as e:
            print(f"✗ {type(e).__name__}")


async def example_4_context_window():
    """Example 4: Handling context window exceeded."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Context Window Limit Handling")
    print("=" * 70)

    model = fm.SystemLanguageModel()
    is_available, _ = model.is_available()

    if not is_available:
        print("Model not available, skipping example")
        return

    session = fm.LanguageModelSession(model=model)

    # Small conversation that's fine
    print("Small conversation (should work):")
    try:
        r1 = await session.respond("Hello, how are you?")
        print(f"✓ Turn 1: OK")

        r2 = await session.respond("What's 2+2?")
        print(f"✓ Turn 2: OK")

    except fm.ExceededContextWindowSizeError as e:
        print(f"✗ ExceededContextWindowSizeError")
        print(f"  Combined conversation history exceeds model's context limit")
        print(f"  → Action: Start a new session or summarize prior context")

    # Try an extremely long prompt (likely to fail)
    print("\nExtremely long prompt (might exceed limit):")
    long_text = "x " * 50000  # Very long text
    try:
        response = await session.respond(
            f"Summarize this: {long_text}"
        )
        print(f"✓ Long text accepted")

    except fm.ExceededContextWindowSizeError as e:
        print(f"✗ ExceededContextWindowSizeError")
        print(f"  Text is too long for the context window")
        print(f"  → Action: Break into chunks or summarize before sending")

    except fm.GenerationError as e:
        print(f"✗ {type(e).__name__}")


async def example_5_unsupported_schema():
    """Example 5: Handling unsupported schema constraints."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Unsupported Schema Constraint Handling")
    print("=" * 70)

    model = fm.SystemLanguageModel()
    is_available, _ = model.is_available()

    if not is_available:
        print("Model not available, skipping example")
        return

    # Try valid schema
    @fm.generable("Valid result")
    class ValidResult:
        label: str = fm.guide(anyOf=["A", "B", "C"])

    session = fm.LanguageModelSession(model=model)

    print("Testing valid schema (anyOf constraint):")
    try:
        result = await session.respond(
            "Pick A, B, or C",
            generating=ValidResult,
        )
        print(f"✓ Schema accepted: {result.label}")

    except fm.UnsupportedGuideError as e:
        print(f"✗ UnsupportedGuideError: Schema not supported")

    except fm.GenerationError as e:
        print(f"✗ {type(e).__name__}")

    # Invalid schema would be caught by Python first, not at runtime
    print("\nTesting invalid constraint (Python-side):")
    try:
        # This raises ValueError in Python, before hitting the C layer
        bad_guide = fm.guide(anyOf=["A", 1, 2])  # Mix strings and ints
        print("✗ Should have raised ValueError")

    except ValueError as e:
        print(f"✓ Python caught it early: ValueError")
        print(f"  anyOf must be a list of strings")
        print(f"  → Action: Fix the schema definition")


async def example_6_rate_limiting():
    """Example 6: Handling rate limiting."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Rate Limiting & Concurrent Requests")
    print("=" * 70)

    print("""
Rate limiting and concurrent request errors are system-level:

- RateLimitedError (status 7): Request throttled by system
  → Action: Wait before retrying

- ConcurrentRequestsError (status 8): Too many simultaneous requests
  → Action: Reduce concurrent requests

On-device model constraint:
  • Single-threaded at hardware level
  • One request at a time
  • Plan accordingly for batch operations
    """)

    model = fm.SystemLanguageModel()
    is_available, _ = model.is_available()

    if not is_available:
        return

    session = fm.LanguageModelSession(model=model)

    print("Testing sequential requests (should work):")
    try:
        for i in range(3):
            response = await session.respond(f"Question {i+1}: What is AI?")
            print(f"  ✓ Request {i+1} succeeded")

    except fm.RateLimitedError:
        print(f"  ✗ RateLimitedError: Too many requests")
        print(f"  → Action: Add delay between requests")

    except fm.ConcurrentRequestsError:
        print(f"  ✗ ConcurrentRequestsError: System limit reached")
        print(f"  → Action: Reduce concurrent requests")

    except fm.ExceededContextWindowSizeError:
        print(f"  ✗ Context window exceeded after multiple turns")


async def example_7_comprehensive_error_handling():
    """Example 7: Complete error handling in production code."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Production Error Handling Pattern")
    print("=" * 70)

    # Check availability first
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()

    if not is_available:
        print(f"Model unavailable: {reason}")
        print("Cannot proceed")
        return

    session = fm.LanguageModelSession(
        instructions="You are helpful."
    )

    # Process with comprehensive error handling
    prompts = [
        "Simple question: What is Python?",
        "Coding task: Write a function",
        "Creative task: Write a poem",
    ]

    for prompt in prompts:
        print(f"\nProcessing: {prompt}")

        try:
            response = await session.respond(prompt)
            print(f"✓ Success: {response[:50]}...")

        # Specific error handling
        except fm.ExceededContextWindowSizeError:
            print(f"✗ Context too large — start new session")

        except fm.GuardrailViolationError:
            print(f"✗ Content violates guidelines — rephrase")

        except fm.UnsupportedLanguageOrLocaleError:
            print(f"✗ Language unsupported — translate first")

        except fm.UnsupportedGuideError:
            print(f"✗ Schema unsupported — change constraints")

        except fm.RefusalError as e:
            print(f"✗ Model refused: {e}")

        except fm.RateLimitedError:
            print(f"✗ Rate limited — backoff and retry")

        except fm.GenerationError as e:
            print(f"✗ Generation error: {type(e).__name__}")
            print(f"  Message: {e}")

        except Exception as e:
            print(f"✗ Unexpected error: {type(e).__name__}: {e}")

    print("\n✓ Comprehensive error handling complete")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  APPLE FM SDK — ERROR HANDLING GUIDE")
    print("  Complete reference for error types and recovery")
    print("=" * 70)

    # Run examples
    if not await example_1_availability_check():
        print("\n⚠️  Model not available. Other examples skipped.")
        return

    await example_2_guardrail_violation()
    await example_3_unsupported_language()
    await example_4_context_window()
    await example_5_unsupported_schema()
    await example_6_rate_limiting()
    await example_7_comprehensive_error_handling()

    # Summary
    print("\n" + "=" * 70)
    print("ERROR HANDLING SUMMARY")
    print("=" * 70)
    print("""
Always follow this pattern:

1. Check model.is_available() first
   → Handle: APPLE_INTELLIGENCE_NOT_ENABLED, DEVICE_NOT_ELIGIBLE, MODEL_NOT_READY

2. Wrap generation calls in try-except
   → ExceededContextWindowSizeError: Context too large
   → GuardrailViolationError: Unsafe content
   → UnsupportedLanguageOrLocaleError: Language not supported
   → UnsupportedGuideError: Invalid schema constraint
   → RefusalError: Model refused to generate
   → RateLimitedError: Too many requests
   → ConcurrentRequestsError: System limit exceeded

3. For schema errors, Python catches first
   → ValueError: Guide constraint validation failed
   → TypeError: Invalid field type

4. Implement retry logic for transient errors
   → RateLimitedError: Backoff and retry
   → ConcurrentRequestsError: Reduce concurrency

5. Log errors for debugging
   → Save error type, message, and context
   → Use for monitoring and analytics

See the Apple FM SDK docs for full error reference.
    """)


if __name__ == "__main__":
    asyncio.run(main())
