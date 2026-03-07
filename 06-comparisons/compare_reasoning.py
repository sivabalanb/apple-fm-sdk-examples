"""
Complex reasoning comparison: Apple FM SDK vs Claude API.

Tests 4 tasks that require multi-step reasoning: math word problem,
code generation, business analysis, and a logic puzzle. Demonstrates
where Claude's reasoning capabilities dominate over Apple FM's
on-device model for tasks requiring deep, structured thinking.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import FoundationModels
from utils.claude_client import ask_claude
from utils.helpers import print_comparison, timer, truncate

# ---------------------------------------------------------------------------
# Reasoning tasks
# ---------------------------------------------------------------------------

TASKS = [
    {
        "name": "Math Word Problem",
        "category": "math",
        "prompt": (
            "A train leaves Station A at 9:00 AM traveling at 80 mph toward Station B. "
            "Another train leaves Station B at 10:30 AM traveling at 60 mph toward Station A. "
            "The distance between the stations is 280 miles. "
            "At what time do the trains meet, and how far from Station A does the meeting occur? "
            "Show your full working."
        ),
    },
    {
        "name": "Code Generation",
        "category": "code",
        "prompt": (
            "Write a Python function `merge_sorted_lists(lists)` that merges an arbitrary "
            "number of sorted lists into a single sorted list in O(n log k) time, where n "
            "is the total number of elements and k is the number of lists. "
            "Include a brief explanation of the approach and a usage example."
        ),
    },
    {
        "name": "Business Analysis",
        "category": "analysis",
        "prompt": (
            "A SaaS startup has the following metrics: MRR=$42,000, monthly churn=3.5%, "
            "CAC=$1,200, average contract length=18 months, gross margin=72%. "
            "Calculate LTV, LTV:CAC ratio, and payback period. "
            "Then provide a concise assessment of unit economics health and the single "
            "most impactful lever to improve them."
        ),
    },
    {
        "name": "Logic Puzzle",
        "category": "logic",
        "prompt": (
            "Five colleagues — Alice, Bob, Carol, Dave, and Eve — each prefer a different "
            "programming language: Python, Go, Rust, TypeScript, and Swift. "
            "Clues: (1) Alice does not use a compiled language. "
            "(2) Bob's language compiles to native code and is not Go. "
            "(3) Carol and the TypeScript user sit next to each other. "
            "(4) Dave uses the language created by Mozilla. "
            "(5) Eve is not the Python user. "
            "Determine each person's preferred language with full reasoning."
        ),
    },
]

# ---------------------------------------------------------------------------
# Apple FM SDK — plain respond()
# ---------------------------------------------------------------------------


def reason_apple_fm(prompt: str) -> str:
    """Submit a reasoning task to Apple FM using a fresh session."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are a careful, step-by-step reasoner. Work through problems "
            "methodically, showing your reasoning before giving a final answer."
        ),
    )
    try:
        result = session.respond(prompt)
        return result
    except FoundationModels.ExceededContextWindowSizeError:
        return "[ERROR] Context window exceeded — try breaking the prompt into smaller parts."


# ---------------------------------------------------------------------------
# Claude API — plain ask_claude()
# ---------------------------------------------------------------------------


def reason_claude(prompt: str) -> str:
    """Submit a reasoning task to Claude API."""
    return ask_claude(
        prompt,
        system=(
            "You are a careful, step-by-step reasoner. Work through problems "
            "methodically, showing your reasoning before giving a final answer."
        ),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

PREVIEW_CHARS = 400


def run_comparison() -> None:
    print("=" * 70)
    print("Complex Reasoning Comparison: Apple FM SDK vs Claude API")
    print("=" * 70)
    print(f"Tasks: {len(TASKS)}")
    print("Note: Claude is expected to dominate on multi-step reasoning tasks.")
    print()

    apple_times = []
    claude_times = []

    for i, task in enumerate(TASKS, 1):
        name = task["name"]
        prompt = task["prompt"]

        print(f"[{i}/{len(TASKS)}] {name} ({task['category']})")
        print(f"Prompt: {truncate(prompt, 100)}")
        print()

        # Apple FM
        with timer() as t:
            apple_response = reason_apple_fm(prompt)
        apple_times.append(t.elapsed)

        # Claude
        with timer() as t:
            claude_response = reason_claude(prompt)
        claude_times.append(t.elapsed)

        print("Apple FM Response:")
        print(f"  {truncate(apple_response, PREVIEW_CHARS)}")
        print(f"  [Time: {t.elapsed:.2f}s  |  Words: {len(apple_response.split())}]")
        print()

        print("Claude Response:")
        print(f"  {truncate(claude_response, PREVIEW_CHARS)}")
        print(f"  [Time: {t.elapsed:.2f}s  |  Words: {len(claude_response.split())}]")
        print()

        print_comparison(
            label="Response length (words)",
            apple_value=str(len(apple_response.split())),
            claude_value=str(len(claude_response.split())),
        )
        print("-" * 70)
        print()

    print("=" * 70)
    print("Timing Summary")
    print("=" * 70)
    avg_apple = sum(apple_times) / len(apple_times) if apple_times else 0
    avg_claude = sum(claude_times) / len(claude_times) if claude_times else 0

    print(f"Avg Apple FM time  : {avg_apple:.2f}s")
    print(f"Avg Claude time    : {avg_claude:.2f}s")
    print()
    print("Key observation: Claude typically produces longer, more structured")
    print("reasoning chains for math, code, and logic tasks. Apple FM excels")
    print("at low-latency on-device inference and structured extraction.")


if __name__ == "__main__":
    run_comparison()
