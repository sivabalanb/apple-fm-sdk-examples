"""
Analyze a sample customer service transcript using Apple FM SDK.

Creates a representative Swift app support transcript (7 conversation entries),
then analyzes it for turn counts, response lengths, and quality signals such as
acknowledgment phrases and whether responses include next steps.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Sample transcript data
# ---------------------------------------------------------------------------

SAMPLE_TRANSCRIPT = [
    {
        "turn": 1,
        "role": "user",
        "text": (
            "Hi, I downloaded your Swift app yesterday and I'm having trouble "
            "getting it to compile. I keep seeing 'No such module FoundationModels' "
            "even though I followed the setup guide exactly."
        ),
    },
    {
        "turn": 2,
        "role": "assistant",
        "text": (
            "Thanks for reaching out! I understand how frustrating a missing module "
            "error can be, especially right after setup. Let me help you resolve this. "
            "First, could you confirm which version of Xcode you're using? The "
            "FoundationModels framework requires Xcode 16.4 or later."
        ),
    },
    {
        "turn": 3,
        "role": "user",
        "text": "I'm on Xcode 16.2. Could that be the issue?",
    },
    {
        "turn": 4,
        "role": "assistant",
        "text": (
            "Yes, that's exactly the issue! Xcode 16.2 does not bundle the "
            "FoundationModels framework. You'll need to upgrade to Xcode 16.4 or later. "
            "Here are your next steps: (1) Download Xcode 16.4+ from the Mac App Store "
            "or developer.apple.com, (2) Open your project in the new Xcode, "
            "(3) Clean the build folder (Shift+Cmd+K), then build again. "
            "This should resolve the module error entirely."
        ),
    },
    {
        "turn": 5,
        "role": "user",
        "text": (
            "That fixed the module error, thank you! Now I'm hitting a different "
            "problem — my LanguageModelSession is returning empty responses when I "
            "use CONTENT_TAGGING mode. Plain respond() works fine."
        ),
    },
    {
        "turn": 6,
        "role": "assistant",
        "text": (
            "Great that the first issue is resolved! Empty responses in CONTENT_TAGGING "
            "mode usually mean one of two things: (1) Your @generable struct is missing "
            "required GenerationSchema annotations on its properties, or (2) the model "
            "cannot fit a valid structured response within the context window. "
            "Please double-check that every property in your @generable class has a "
            "GenerationSchema descriptor with a clear description field. If the problem "
            "persists after that, try shortening your prompt or splitting the input into "
            "smaller chunks and let me know what you find."
        ),
    },
    {
        "turn": 7,
        "role": "user",
        "text": (
            "Adding the descriptions to GenerationSchema fixed it! Works perfectly now. "
            "Really appreciate the help — your documentation should probably mention "
            "this requirement more prominently."
        ),
    },
]

# ---------------------------------------------------------------------------
# Analysis dataclass
# ---------------------------------------------------------------------------


@dataclass
class TranscriptAnalysis:
    """Structured analysis results for a conversation transcript."""

    total_turns: int = 0
    user_turns: int = 0
    assistant_turns: int = 0
    avg_user_length: float = 0.0
    avg_assistant_length: float = 0.0
    longest_assistant_turn: int = 0
    shortest_assistant_turn: int = 0
    acknowledgment_rate: float = 0.0
    next_steps_rate: float = 0.0
    issues_raised: list[str] = field(default_factory=list)
    issues_resolved: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Acknowledgment and next-step signals
# ---------------------------------------------------------------------------

ACKNOWLEDGMENT_PHRASES = [
    "i understand",
    "thanks for",
    "thank you",
    "great that",
    "i see",
    "got it",
    "absolutely",
    "of course",
    "i appreciate",
    "understood",
]

NEXT_STEP_PHRASES = [
    "next step",
    "here are",
    "please",
    "could you",
    "try ",
    "let me know",
    "you'll need",
    "you should",
    "make sure",
    "double-check",
]


def has_signal(text: str, phrases: list[str]) -> bool:
    """Return True if the lowercased text contains any of the signal phrases."""
    lower = text.lower()
    return any(phrase in lower for phrase in phrases)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def analyze_transcript(transcript: list[dict]) -> TranscriptAnalysis:
    """Analyze a conversation transcript and return structured results."""
    analysis = TranscriptAnalysis()

    user_texts = [t["text"] for t in transcript if t["role"] == "user"]
    assistant_texts = [t["text"] for t in transcript if t["role"] == "assistant"]

    analysis.total_turns = len(transcript)
    analysis.user_turns = len(user_texts)
    analysis.assistant_turns = len(assistant_texts)

    # Length stats
    user_lengths = [len(t.split()) for t in user_texts]
    assistant_lengths = [len(t.split()) for t in assistant_texts]

    analysis.avg_user_length = (
        sum(user_lengths) / len(user_lengths) if user_lengths else 0.0
    )
    analysis.avg_assistant_length = (
        sum(assistant_lengths) / len(assistant_lengths) if assistant_lengths else 0.0
    )
    analysis.longest_assistant_turn = max(assistant_lengths) if assistant_lengths else 0
    analysis.shortest_assistant_turn = min(assistant_lengths) if assistant_lengths else 0

    # Quality signals
    ack_count = sum(1 for t in assistant_texts if has_signal(t, ACKNOWLEDGMENT_PHRASES))
    next_count = sum(1 for t in assistant_texts if has_signal(t, NEXT_STEP_PHRASES))

    analysis.acknowledgment_rate = (
        ack_count / len(assistant_texts) if assistant_texts else 0.0
    )
    analysis.next_steps_rate = (
        next_count / len(assistant_texts) if assistant_texts else 0.0
    )

    # Issue tracking (heuristic: user turns that contain problem keywords)
    problem_keywords = ["error", "trouble", "issue", "problem", "hitting", "failing"]
    for t in user_texts:
        if has_signal(t["text"] if isinstance(t, dict) else t, problem_keywords):
            analysis.issues_raised.append(
                (t[:60] + "...") if len(t) > 60 else t
            )

    # Resolved: final user turn expresses success
    final_user = user_texts[-1] if user_texts else ""
    success_keywords = ["fixed", "works", "resolved", "perfect", "thank"]
    if has_signal(final_user, success_keywords):
        analysis.issues_resolved = analysis.issues_raised[:]

    # Quality flags
    if analysis.acknowledgment_rate < 0.5:
        analysis.quality_flags.append("LOW_ACKNOWLEDGMENT_RATE")
    if analysis.next_steps_rate < 0.5:
        analysis.quality_flags.append("LOW_NEXT_STEPS_RATE")
    if analysis.avg_assistant_length > 150:
        analysis.quality_flags.append("VERBOSE_RESPONSES")
    if analysis.avg_assistant_length < 20:
        analysis.quality_flags.append("TERSE_RESPONSES")
    if not analysis.quality_flags:
        analysis.quality_flags.append("NO_ISSUES_DETECTED")

    return analysis


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def print_transcript(transcript: list[dict]) -> None:
    """Print the transcript in a readable format."""
    print("=" * 60)
    print("Sample Customer Service Transcript")
    print("=" * 60)
    for entry in transcript:
        role_label = "USER      " if entry["role"] == "user" else "ASSISTANT "
        words = entry["text"].split()
        # Wrap at ~72 chars
        lines = []
        current = []
        for word in words:
            current.append(word)
            if len(" ".join(current)) > 68:
                lines.append(" ".join(current[:-1]))
                current = [word]
        if current:
            lines.append(" ".join(current))
        prefix = f"[Turn {entry['turn']}] {role_label}: "
        indent = " " * len(prefix)
        print(f"{prefix}{lines[0]}")
        for line in lines[1:]:
            print(f"{indent}{line}")
    print()


def print_analysis(analysis: TranscriptAnalysis) -> None:
    """Print the analysis results."""
    print("=" * 60)
    print("Transcript Analysis Results")
    print("=" * 60)

    print(f"Total turns          : {analysis.total_turns}")
    print(f"  User turns         : {analysis.user_turns}")
    print(f"  Assistant turns    : {analysis.assistant_turns}")
    print()

    print("Response Length Statistics (words):")
    print(f"  Avg user length    : {analysis.avg_user_length:.1f}")
    print(f"  Avg assistant len  : {analysis.avg_assistant_length:.1f}")
    print(f"  Longest assistant  : {analysis.longest_assistant_turn}")
    print(f"  Shortest assistant : {analysis.shortest_assistant_turn}")
    print()

    print("Quality Checks:")
    print(f"  Acknowledgment rate : {analysis.acknowledgment_rate:.0%}")
    print(f"  Next-steps rate     : {analysis.next_steps_rate:.0%}")
    print()

    print(f"Issues raised    : {len(analysis.issues_raised)}")
    for issue in analysis.issues_raised:
        print(f"  - {issue}")

    print(f"Issues resolved  : {len(analysis.issues_resolved)}")
    for issue in analysis.issues_resolved:
        print(f"  - {issue}")

    print()
    print("Quality Flags:")
    for flag in analysis.quality_flags:
        print(f"  [{flag}]")

    overall = "PASS" if "NO_ISSUES_DETECTED" in analysis.quality_flags else "REVIEW"
    print()
    print(f"Overall assessment: {overall}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print_transcript(SAMPLE_TRANSCRIPT)
    analysis = analyze_transcript(SAMPLE_TRANSCRIPT)
    print_analysis(analysis)


if __name__ == "__main__":
    main()
