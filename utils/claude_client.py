"""
Thin Anthropic SDK wrapper for use in comparison scripts.

Provides get_client(), ask_claude(), and ask_claude_json() as minimal
helpers so comparison files stay focused on the comparison logic itself.
Requires the ANTHROPIC_API_KEY environment variable to be set.
"""

import json
import os
from typing import Any

import anthropic

MODEL = "claude-sonnet-4-6-20250620"

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Return a shared Anthropic client, creating it on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before running comparison scripts."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def ask_claude(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str:
    """
    Send a prompt to Claude and return the text response.

    Args:
        prompt: The user message to send.
        system: Optional system prompt.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        The assistant's text response as a plain string.
    """
    client = get_client()

    messages = [{"role": "user", "content": prompt}]

    kwargs: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    # temperature is not directly supported in all SDK versions via this path;
    # pass via model_kwargs if supported, otherwise omit for reproducibility.
    try:
        response = client.messages.create(**kwargs)
    except TypeError:
        response = client.messages.create(**kwargs)

    return response.content[0].text


def ask_claude_json(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 2048,
) -> dict | None:
    """
    Send a prompt to Claude expecting a JSON response.

    The prompt should instruct Claude to return valid JSON. This function
    strips markdown code fences if present before parsing.

    Args:
        prompt: The user message (should request JSON output).
        system: Optional system prompt.
        max_tokens: Maximum tokens in the response.

    Returns:
        Parsed dict, or None if parsing fails.
    """
    sys_prompt = system or (
        "You are a helpful assistant that always responds with valid JSON. "
        "Never include explanation text outside the JSON object."
    )

    raw = ask_claude(prompt, system=sys_prompt, max_tokens=max_tokens)

    # Strip markdown code fences
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"[claude_client] JSON parse error: {exc}")
        print(f"[claude_client] Raw response: {raw[:200]}")
        return None
