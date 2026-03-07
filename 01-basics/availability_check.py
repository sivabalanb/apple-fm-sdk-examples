"""
01 — Availability Check
Shows how to properly check model availability and inspect configuration.
Demonstrates: is_available(), use cases, guardrail settings.
"""

import asyncio

import apple_fm_sdk as fm


async def main():
    # Default model — general-purpose use case
    default_model = fm.SystemLanguageModel()
    avail, reason = default_model.is_available()
    print(f"Default model available: {avail}")
    if not avail:
        print(f"  Reason: {reason}")

    # Model configured for content tagging — a specific use case that
    # may have different guardrail behavior
    tagging_model = fm.SystemLanguageModel(
        use_case=fm.SystemLanguageModelUseCase.CONTENT_TAGGING,
    )
    avail, reason = tagging_model.is_available()
    print(f"Tagging model available: {avail}")

    # Model with permissive guardrails — useful when you're transforming
    # content (e.g., summarizing user text) rather than generating new content
    permissive_model = fm.SystemLanguageModel(
        guardrails=fm.SystemLanguageModelGuardrails.PERMISSIVE_CONTENT_TRANSFORMATIONS,
    )
    avail, reason = permissive_model.is_available()
    print(f"Permissive model available: {avail}")

    print("\n--- Use Cases ---")
    print("GENERAL:         Default, broad tasks")
    print("CONTENT_TAGGING: Optimized for classification/labeling")

    print("\n--- Guardrails ---")
    print("DEFAULT:                          Standard safety filters")
    print("PERMISSIVE_CONTENT_TRANSFORMATIONS: Looser filters for content transformation")


if __name__ == "__main__":
    asyncio.run(main())
