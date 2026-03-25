"""Auto-expand reactor for ScienceClaw NeedsSignals.

When the environment variable ``SCIENTIA_AUTO_EXPAND=true`` is set,
:func:`maybe_auto_expand` will automatically trigger skill generation
for any NeedsSignal that contains a ``suggested_source``.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from scientia.bridge import SkillExpander


def maybe_auto_expand(needs_signal: dict) -> Optional[dict]:
    """Expand a NeedsSignal if auto-expansion is enabled.

    Returns the expansion result dict, or None if:
    - SCIENTIA_AUTO_EXPAND is not set to "true" (case-insensitive)
    - The signal has no ``suggested_source``
    """
    enabled = os.environ.get("SCIENTIA_AUTO_EXPAND", "").strip().lower()
    if enabled != "true":
        return None

    source = needs_signal.get("suggested_source")
    if not source:
        return None

    expander = SkillExpander()
    source_type = needs_signal.get("source_type")
    return expander.expand(source, source_type=source_type, raise_on_failure=False)
