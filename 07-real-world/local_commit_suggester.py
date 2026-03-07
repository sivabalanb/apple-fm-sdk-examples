"""
Git commit message suggester using Apple FM SDK.

Reads the staged diff via subprocess, then generates a structured conventional
commit suggestion. Falls back gracefully when no staged changes are found or
when the diff exceeds the context window.
"""

import subprocess
import sys
from pathlib import Path

import FoundationModels

# ---------------------------------------------------------------------------
# Conventional commit types (subset for structured output)
# ---------------------------------------------------------------------------

COMMIT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "chore",
    "perf",
    "ci",
    "revert",
]

# ---------------------------------------------------------------------------
# @generable schema
# ---------------------------------------------------------------------------


@FoundationModels.generable
class CommitSuggestion:
    """A structured conventional commit message suggestion."""

    type: str = FoundationModels.GenerationSchema(
        description="Conventional commit type",
        anyOf=COMMIT_TYPES,
    )
    scope: str = FoundationModels.GenerationSchema(
        description=(
            "Optional scope in parentheses (e.g. 'auth', 'api', 'ui'). "
            "Use empty string if not applicable."
        ),
    )
    message: str = FoundationModels.GenerationSchema(
        description=(
            "Short imperative commit message, max 72 characters, no trailing period"
        ),
    )
    body: str = FoundationModels.GenerationSchema(
        description=(
            "Optional longer explanation of what changed and why, "
            "or empty string if the subject line is sufficient"
        ),
    )
    breaking_change: str = FoundationModels.GenerationSchema(
        description=(
            "Description of any breaking changes introduced, "
            "or empty string if none"
        ),
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def get_staged_diff(repo_path: str | None = None) -> str | None:
    """Return the staged diff, or None if nothing is staged."""
    cmd = ["git", "diff", "--cached"]
    cwd = repo_path or "."
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(f"[ERROR] git diff failed: {result.stderr.strip()}")
            return None
        return result.stdout.strip() or None
    except FileNotFoundError:
        print("[ERROR] git not found. Is git installed and on PATH?")
        return None
    except subprocess.TimeoutExpired:
        print("[ERROR] git diff timed out.")
        return None


def get_repo_root() -> str | None:
    """Return the root of the current git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------------------------
# Suggestion logic
# ---------------------------------------------------------------------------


def suggest_commit(diff: str) -> CommitSuggestion | None:
    """Generate a commit suggestion for the given diff."""
    session = FoundationModels.LanguageModelSession(
        instructions=(
            "You are an expert at writing clean, conventional commit messages. "
            "Given a git diff, produce a precise commit message following the "
            "Conventional Commits specification (https://www.conventionalcommits.org). "
            "Focus on the intent and impact of the changes, not just what files changed."
        ),
        configuration=FoundationModels.LanguageModelSessionConfiguration(
            mode=FoundationModels.LanguageModelSessionMode.CONTENT_TAGGING,
        ),
    )

    prompt = (
        "Analyze this staged git diff and suggest a conventional commit message:\n\n"
        f"```diff\n{diff}\n```"
    )

    try:
        result = session.respond(prompt, generating=CommitSuggestion)
        return result
    except FoundationModels.ExceededContextWindowSizeError:
        print(
            "[ERROR] The staged diff is too large for the context window.\n"
            "Tip: Try staging fewer files at once, or break your changes into "
            "smaller, focused commits."
        )
        return None


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def format_commit_message(suggestion: CommitSuggestion) -> str:
    """Format the suggestion as a conventional commit message string."""
    scope_part = f"({suggestion.scope})" if suggestion.scope.strip() else ""
    subject = f"{suggestion.type}{scope_part}: {suggestion.message}"

    parts = [subject]
    if suggestion.body.strip():
        parts.append("")
        parts.append(suggestion.body.strip())
    if suggestion.breaking_change.strip():
        parts.append("")
        parts.append(f"BREAKING CHANGE: {suggestion.breaking_change.strip()}")

    return "\n".join(parts)


def print_suggestion(suggestion: CommitSuggestion, diff_lines: int) -> None:
    """Print the suggestion in a readable format."""
    print("=" * 60)
    print("Commit Suggestion")
    print("=" * 60)
    print(f"Type      : {suggestion.type}")
    print(f"Scope     : {suggestion.scope or '(none)'}")
    print(f"Message   : {suggestion.message}")
    if suggestion.breaking_change.strip():
        print(f"Breaking  : {suggestion.breaking_change}")
    print()
    print("Formatted commit message:")
    print("-" * 40)
    print(format_commit_message(suggestion))
    print("-" * 40)
    print()
    print(f"Diff analyzed: {diff_lines} lines")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Accept optional repo path argument
    repo_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("Git Commit Message Suggester (Apple FM SDK)")
    print()

    root = get_repo_root() if repo_path is None else repo_path
    if root:
        print(f"Repository: {root}")

    print("Fetching staged diff...")
    diff = get_staged_diff(repo_path)

    if diff is None:
        print()
        print("No staged changes found.")
        print("Stage your changes with `git add <files>` then re-run this script.")
        return

    diff_lines = diff.count("\n") + 1
    print(f"Staged diff: {diff_lines} lines")
    print("Generating commit suggestion...")
    print()

    suggestion = suggest_commit(diff)

    if suggestion is None:
        return

    print_suggestion(suggestion, diff_lines)


if __name__ == "__main__":
    main()
