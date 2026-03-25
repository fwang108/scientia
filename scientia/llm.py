"""Thin wrapper around the Anthropic client for LLM completions."""
from __future__ import annotations
import os


def llm_complete(prompt: str, *, model: str = "claude-haiku-4-5-20251001") -> str:
    """Send *prompt* to the LLM and return the text response."""
    import anthropic  # lazy import — not required for non-LLM usage

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set; export it before running scientia add."
        )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    parts: list[str] = []
    for block in message.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            parts.append(block.text)
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError(
            "Anthropic returned no text blocks in the response. "
            "Try a different model or check API / billing status."
        )
    return text
