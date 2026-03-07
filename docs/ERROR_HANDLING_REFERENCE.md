# Error Handling Reference

Complete reference for all Apple FM SDK error types, when they occur, and how to handle them.

## Quick Reference

| Error | Status | When | Action |
|-------|--------|------|--------|
| `ExceededContextWindowSizeError` | 1 | Prompt + history too long | New session, chunk input |
| `AssetsUnavailableError` | 2 | Model resources missing | Retry, check storage |
| `GuardrailViolationError` | 3 | Unsafe content | Rephrase, use permissive guardrail |
| `UnsupportedGuideError` | 4 | Invalid schema constraint | Fix `@generable` definition |
| `UnsupportedLanguageOrLocaleError` | 5 | Unsupported language | Translate to English |
| `DecodingFailureError` | 6 | Output doesn't match schema | Simplify schema |
| `RateLimitedError` | 7 | Too many requests | Backoff and retry |
| `ConcurrentRequestsError` | 8 | System concurrency limit | Reduce simultaneous requests |
| `RefusalError` | 9 | Model refused generation | Try different approach |
| `InvalidGenerationSchemaError` | 10 | Malformed schema | Validate schema structure |

## Availability Checking

Always check before using the model:

```python
model = fm.SystemLanguageModel()
is_available, reason = model.is_available()

if not is_available:
    if reason == fm.SystemLanguageModelUnavailableReason.APPLE_INTELLIGENCE_NOT_ENABLED:
        print("Enable Apple Intelligence in System Settings")
    elif reason == fm.SystemLanguageModelUnavailableReason.DEVICE_NOT_ELIGIBLE:
        print("Need Apple Silicon Mac / iPhone 15 Pro+ / iPad M1+")
    elif reason == fm.SystemLanguageModelUnavailableReason.MODEL_NOT_READY:
        print("Model is downloading, wait and retry")
    elif reason == fm.SystemLanguageModelUnavailableReason.UNKNOWN:
        print("Unknown issue, investigate")
    return
```

## Error Details

### `ExceededContextWindowSizeError` (Status 1)

Occurs when the combined prompt + session history exceeds the model's context limit.

```python
try:
    response = await session.respond(very_long_text)
except fm.ExceededContextWindowSizeError:
    # Start a fresh session — application-level state is preserved
    session = fm.LanguageModelSession(model=model)
    response = await session.respond(very_long_text)
```

**Prevention:** Use a fresh session per item in batch loops. Keep prompts concise.

---

### `GuardrailViolationError` (Status 3)

Content violates safety guidelines.

```python
try:
    response = await session.respond(prompt)
except fm.GuardrailViolationError:
    # Option 1: Rephrase
    # Option 2: Use permissive guardrails for content transformation
    model = fm.SystemLanguageModel(
        guardrails=fm.SystemLanguageModelGuardrails.PERMISSIVE_CONTENT_TRANSFORMATIONS
    )
    # Option 3: Skip and log
    return None
```

---

### `UnsupportedLanguageOrLocaleError` (Status 5)

Input is in a language the model doesn't support. Apple FM supports English and limited Western European languages.

```python
try:
    response = await session.respond(non_english_text)
except fm.UnsupportedLanguageOrLocaleError:
    # Translate to English first, or route to Claude
    translated = translate_to_english(non_english_text)
    response = await session.respond(translated)
```

---

### `RefusalError` (Status 9)

Model refuses to generate (different from guardrail violation).

```python
try:
    response = await session.respond(prompt)
except fm.RefusalError as e:
    print(f"Model refused: {e}")
    # Try rephrasing or a different approach
```

---

### `UnsupportedGuideError` (Status 4)

Schema constraint not supported. Common causes: complex regex patterns, `range` on string fields.

```python
# Bad — complex regex unsupported
email: str = fm.guide(regex=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Good — use description instead
email: str = fm.guide("Email address")
```

---

### `RateLimitedError` (Status 7)

System throttling. Use exponential backoff:

```python
async def respond_with_retry(session, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await session.respond(prompt)
        except fm.RateLimitedError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
```

---

### `ConcurrentRequestsError` (Status 8)

Too many simultaneous requests. Run requests sequentially:

```python
# Good — sequential
for prompt in prompts:
    response = await session.respond(prompt)

# Risky — may hit concurrency limit
responses = await asyncio.gather(*[session.respond(p) for p in prompts])
```

---

## Comprehensive Pattern

```python
async def safe_generate(session, prompt, schema=None, model=None):
    try:
        if schema:
            return await session.respond(prompt, generating=schema)
        return await session.respond(prompt)

    except fm.ExceededContextWindowSizeError:
        # Recoverable — recreate session
        if model:
            session = fm.LanguageModelSession(model=model)
            return await session.respond(prompt, **({"generating": schema} if schema else {}))
        return None

    except fm.GuardrailViolationError:
        return None  # Content blocked

    except fm.UnsupportedLanguageOrLocaleError:
        raise  # Caller should translate first

    except fm.RateLimitedError:
        await asyncio.sleep(5)
        return await safe_generate(session, prompt, schema, model)

    except fm.GenerationError as e:
        print(f"Generation error: {type(e).__name__}: {e}")
        raise
```

---

## Error Handling Checklist

- [ ] Check `model.is_available()` before use
- [ ] Wrap `respond()` calls in try-except
- [ ] Handle `ExceededContextWindowSizeError` with fresh session
- [ ] Handle `GuardrailViolationError` gracefully (return None or rephrase)
- [ ] Handle `UnsupportedLanguageOrLocaleError` with translation
- [ ] Implement backoff for `RateLimitedError`
- [ ] Log errors for monitoring
- [ ] Test error paths

## See Also

- `01-basics/error_handling_guide.py` — Working examples for all error types
- `01-basics/content_tagging_showcase.py` — Error handling in batch context
- `docs/CONTENT_TAGGING_GUIDE.md` — Content tagging specific errors
