"""
01 — Multi-Turn Conversations
Sessions automatically maintain context across exchanges.
Demonstrates: session memory, follow-up questions, instructions.
"""

import asyncio

import apple_fm_sdk as fm


async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    # System instructions shape the model's behavior for the entire session
    session = fm.LanguageModelSession(
        instructions="You are a concise Python tutor. Keep answers under 3 sentences.",
        model=model,
    )

    # Multi-turn conversation — each turn builds on prior context.
    # The on-device model has a limited context window, so we handle
    # ExceededContextWindowSizeError by creating a fresh session if needed.
    turns = [
        ("Turn 1", "What is a list comprehension?"),
        ("Turn 2", "Give me an example of one."),
        ("Turn 3", "How is that different from a generator expression?"),
    ]

    for label, question in turns:
        print(f"--- {label} ---")
        print(f"Q: {question}")
        try:
            response = await session.respond(question)
            print(f"A: {response}\n")
        except fm.ExceededContextWindowSizeError:
            print("[Context window exceeded — starting fresh session]")
            session = fm.LanguageModelSession(
                instructions="You are a concise Python tutor. Keep answers under 3 sentences.",
                model=model,
            )
            response = await session.respond(question)
            print(f"A: {response}\n")
        except fm.GenerationError as e:
            print(f"Error: {type(e).__name__}: {e}\n")

    # Check if the session is still processing
    print(f"Session still responding: {session.is_responding}")


if __name__ == "__main__":
    asyncio.run(main())
