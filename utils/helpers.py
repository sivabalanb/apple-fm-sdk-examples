"""
Shared utility helpers for Apple FM SDK example scripts.

Provides:
- timer: context manager for measuring elapsed wall-clock time
- truncate: shorten a string with an ellipsis suffix
- print_comparison: side-by-side display of Apple FM vs Claude values
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


# ---------------------------------------------------------------------------
# Timer context manager
# ---------------------------------------------------------------------------


@dataclass
class _TimerResult:
    """Holds elapsed time populated after the context manager exits."""

    elapsed: float = field(default=0.0)


@contextmanager
def timer() -> Generator[_TimerResult, None, None]:
    """
    Context manager that measures elapsed wall-clock time in seconds.

    Usage::

        with timer() as t:
            do_something()
        print(f"Elapsed: {t.elapsed:.3f}s")
    """
    result = _TimerResult()
    start = time.perf_counter()
    try:
        yield result
    finally:
        result.elapsed = time.perf_counter() - start


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------


def truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """
    Return text truncated to max_chars characters.

    If truncation is needed, the string is shortened so that the total
    length including suffix does not exceed max_chars.

    Args:
        text: The input string.
        max_chars: Maximum allowed length including the suffix.
        suffix: String appended when truncation occurs.

    Returns:
        Original string if short enough, otherwise truncated form.
    """
    if len(text) <= max_chars:
        return text
    cut = max(0, max_chars - len(suffix))
    return text[:cut] + suffix


# ---------------------------------------------------------------------------
# Side-by-side comparison display
# ---------------------------------------------------------------------------


def print_comparison(
    label: str,
    apple_value: str,
    claude_value: str,
    col_width: int = 30,
) -> None:
    """
    Print a single labeled row comparing Apple FM and Claude outputs.

    The output is formatted as a fixed-width table row::

        Label            | Apple FM value       | Claude value

    Args:
        label: Row label describing what is being compared.
        apple_value: Value produced by Apple FM SDK.
        claude_value: Value produced by Claude API.
        col_width: Width of each value column (default 30).
    """
    label_width = 20
    apple_display = truncate(str(apple_value), col_width)
    claude_display = truncate(str(claude_value), col_width)

    print(
        f"  {label:<{label_width}} | "
        f"Apple FM: {apple_display:<{col_width}} | "
        f"Claude: {claude_display}"
    )
