"""
01 — Hello World
The simplest possible Apple FM generation.
Demonstrates: model init, availability check, single prompt.
"""

import asyncio

import apple_fm_sdk as fm


async def main():
    # Initialize the on-device model
    model = fm.SystemLanguageModel()

    # Always check availability first — the model requires specific
    # hardware (Apple Silicon) and macOS 26+
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        print("Ensure you're on macOS 26+ with Apple Intelligence enabled.")
        return

    # Create a session (manages conversation context)
    session = fm.LanguageModelSession(model=model)

    # Generate a response — this runs entirely on your device
    try:
        response = await session.respond("What is Python in one sentence?")
        print("Prompt:   What is Python in one sentence?")
        print(f"Response: {response}")
    except fm.ExceededContextWindowSizeError:
        print("Error: Prompt exceeds context window")
    except fm.GenerationError as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
