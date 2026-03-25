"""Synthesize working Python implementations from MethodSpec + paper notes."""
from __future__ import annotations
import re

from scientia.models import MethodSpec
from scientia.llm import llm_complete

_SONNET_MODEL = "claude-sonnet-4-6"

_SYNTHESIS_PROMPT = """\
You are an expert Python programmer. Generate a complete, runnable Python script \
that implements the following computational method described in a research paper.

## Method Name
{name}

## Description
{description}

## Method Overview
{overview}

## Input Specification
{input_spec}

## Output Specification
{output_spec}

## Prerequisites
{prerequisites}

## Requirements

Write a complete Python script that:
1. Has a `#!/usr/bin/env python3` shebang line
2. Uses `argparse` for CLI arguments matching the input spec
3. Implements `def main()` as the entry point
4. Outputs results as JSON via `json.dumps()`
5. Is fully self-contained and runnable
6. Includes all necessary imports
7. Handles errors gracefully

Return ONLY the Python source code, no explanation or markdown fences.
"""


def _extract_overview(notes: str) -> str:
    """Extract content of the ## Method Overview section from notes."""
    match = re.search(
        r"^##\s+Method Overview\s*\n(.*?)(?=^##|\Z)",
        notes,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ""
    return match.group(1).strip()


def needs_synthesis(spec: MethodSpec) -> bool:
    """Return True when no repo and no run commands exist — code must be synthesized."""
    return not spec.repository_url and not spec.run_commands


def synthesize_method(
    spec: MethodSpec,
    implementation_notes: str,
    *,
    model: str = _SONNET_MODEL,
) -> str:
    """Generate a working Python script from a MethodSpec and paper notes.

    Parameters
    ----------
    spec:
        Structured method description extracted from the paper.
    implementation_notes:
        Raw Markdown implementation notes (from ``_ARXIV_TEMPLATE``).
    model:
        LLM model to use.  Defaults to Sonnet for synthesis complexity.

    Returns
    -------
    str
        Executable Python source code.
    """
    overview = _extract_overview(implementation_notes)

    prompt = _SYNTHESIS_PROMPT.format(
        name=spec.name,
        description=spec.description,
        overview=overview or implementation_notes,
        input_spec=spec.input_spec,
        output_spec=spec.output_spec,
        prerequisites=", ".join(spec.prerequisites) if spec.prerequisites else "None",
    )

    raw = llm_complete(prompt, model=model)

    # Strip markdown fences if LLM wrapped the code
    raw = re.sub(r"^```(?:python)?\s*\n", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\n```\s*$", "", raw.strip(), flags=re.MULTILINE)

    return raw.strip()
