"""LLM-based metadata extractor — converts raw source content into ToolMetadata."""
from __future__ import annotations
import json
import re

from scientia.llm import llm_complete
from scientia.models import Param, ToolMetadata
from scientia.prompts import get_prompt


class ExtractionError(Exception):
    """Raised when metadata extraction fails after all retries."""


def _parse_llm_json(raw: str) -> dict:
    """Parse JSON from an LLM reply; strip markdown fences and trailing chatter."""
    s = raw.strip()
    if not s:
        raise json.JSONDecodeError("empty LLM response", "", 0)

    # ```json ... ``` or ``` ... ```
    fence = re.match(r"^```(?:json)?\s*\n?", s, re.IGNORECASE)
    if fence:
        s = s[fence.end() :]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end > start:
        return json.loads(s[start : end + 1])
    raise json.JSONDecodeError("no JSON object found in LLM response", s, 0)


def extract_metadata(
    content: str,
    source_type: str = "text",
    max_retries: int = 3,
) -> ToolMetadata:
    """Extract tool metadata from *content* using the LLM.

    Retries up to *max_retries* times if the LLM returns invalid JSON.
    Raises ExtractionError if all attempts fail.
    """
    prompt = get_prompt(source_type, content)
    last_error: Exception | None = None

    for _ in range(max_retries):
        raw = llm_complete(prompt)
        try:
            data = _parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        params = [
            Param(
                name=p["name"],
                type=p.get("type", "str"),
                description=p.get("description", ""),
                required=p.get("required", False),
                default=p.get("default"),
            )
            for p in data.get("parameters", [])
        ]

        return ToolMetadata(
            tool_name=data["tool_name"],
            description=data["description"],
            base_url=data.get("base_url"),
            auth_required=data.get("auth_required", False),
            parameters=params,
            example_call=data.get("example_call", ""),
            example_output_shape=data.get("example_output_shape", "{}"),
            source_type=data.get("source_type", source_type),
            reference_url=data.get("reference_url"),
            repository_url=data.get("repository_url"),
            implementation_notes=data.get("implementation_notes"),
        )

    raise ExtractionError(
        f"Failed to extract metadata after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
