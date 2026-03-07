"""
03 — Email Parser
Parse emails into structured fields using enum constraints.
Demonstrates: anyOf constraints, combining multiple constraint types.

Note: Apple FM's regex support is limited to simple patterns.
Complex patterns like email validation will raise UnsupportedGuideError.
For emails, use a plain string field and validate in your own code.
"""

import asyncio

import apple_fm_sdk as fm


@fm.generable("Parsed email metadata")
class ParsedEmail:
    sender_name: str = fm.guide("Full name of the sender")
    sender_email: str = fm.guide("Email address of the sender")
    priority: str = fm.guide(anyOf=["low", "medium", "high", "urgent"])
    category: str = fm.guide(anyOf=["meeting", "action_item", "fyi", "question", "social"])
    action_required: str = fm.guide(anyOf=["yes", "no"])
    summary: str = fm.guide("One-sentence summary of the email content")


SAMPLE_EMAILS = [
    """
    From: Sarah Chen <sarah.chen@acme.com>
    Subject: URGENT: Production database migration tonight

    Team, we need all hands on deck. The production DB migration is scheduled
    for tonight at 11 PM EST. Please confirm your availability ASAP.
    Each team lead needs to be on the bridge call. No exceptions.
    """,
    """
    From: Mike Johnson <mike.j@company.org>
    Subject: Friday lunch plans?

    Hey! A bunch of us are going to that new Thai place on Friday.
    Want to join? No pressure either way, just thought I'd ask.
    Let me know by Thursday if you're in!
    """,
    """
    From: Jenkins CI <noreply@jenkins.internal.io>
    Subject: Build #4521 passed

    Build #4521 for main branch completed successfully.
    All 342 tests passed. Coverage: 94.2%.
    No action required.
    """,
]


async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    for i, email in enumerate(SAMPLE_EMAILS, 1):
        # Create a fresh session per email to avoid context window buildup
        session = fm.LanguageModelSession(
            instructions=(
                "You are an email classifier. Extract metadata from emails. "
                "Determine priority based on urgency cues and action requirements."
            ),
            model=model,
        )

        try:
            result = await session.respond(
                f"Parse this email:\n{email}",
                generating=ParsedEmail,
            )

            print(f"=== Email {i} ===")
            print(f"From:     {result.sender_name}")
            print(f"Email:    {result.sender_email}")
            print(f"Priority: {result.priority}")
            print(f"Category: {result.category}")
            print(f"Action:   {result.action_required}")
            print(f"Summary:  {result.summary}")
            print()
        except fm.ExceededContextWindowSizeError:
            print(f"=== Email {i} === [context window exceeded]")
        except fm.GenerationError as e:
            print(f"=== Email {i} === [error: {type(e).__name__}]")


if __name__ == "__main__":
    asyncio.run(main())
