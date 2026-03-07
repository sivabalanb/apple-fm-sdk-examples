"""
02 — Streaming Responses
Receive model output token-by-token as it's generated.
Demonstrates: stream_response(), real-time display, follow-up streaming.
"""

import asyncio

import apple_fm_sdk as fm


async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    session = fm.LanguageModelSession(
        instructions="You are a helpful assistant.",
        model=model,
    )

    # --- Basic streaming ---
    print("=== Streaming: Explain what an API is ===\n")
    try:
        async for chunk in session.stream_response("Explain what an API is in simple terms."):
            print(chunk, end="", flush=True)
        print("\n")
    except fm.ExceededContextWindowSizeError:
        print("\n[Context window exceeded]\n")

    # --- Streaming with follow-up (context preserved) ---
    print("=== Streaming follow-up: Give an example ===\n")
    try:
        async for chunk in session.stream_response("Give me a real-world analogy for that."):
            print(chunk, end="", flush=True)
        print("\n")
    except fm.ExceededContextWindowSizeError:
        print("\n[Context window exceeded — starting fresh session]\n")
        session = fm.LanguageModelSession(
            instructions="You are a helpful assistant.",
            model=model,
        )
        async for chunk in session.stream_response("Give me a real-world analogy for an API."):
            print(chunk, end="", flush=True)
        print("\n")

    # --- Practical use: progress indicator ---
    print("=== With a progress indicator ===\n")
    char_count = 0
    try:
        async for chunk in session.stream_response("List 3 popular Python libraries."):
            print(chunk, end="", flush=True)
            char_count += len(chunk)
        print(f"\n\n[Total characters received: {char_count}]")
    except fm.ExceededContextWindowSizeError:
        print("\n[Context window exceeded]")
    except fm.GenerationError as e:
        print(f"\n[Error: {type(e).__name__}]")


if __name__ == "__main__":
    asyncio.run(main())
