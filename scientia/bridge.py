"""ScienceClaw integration bridge.

SkillExpander is the entry point that ScienceClaw agents call when they
detect a tool gap.  It wraps the Scientia pipeline and returns the
information agents need to immediately invoke the newly-installed skill.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional

from scientia.pipeline import build_skill, BuildError


class BridgeError(Exception):
    """Raised when the bridge cannot process a request."""


class SkillExpander:
    """Expand an agent's skill set by generating and installing a new skill.

    Parameters
    ----------
    skills_root:
        Directory where skills will be installed.
    registry:
        Optional Registry instance for persistence.
    """

    def __init__(self, skills_root: Optional[Path] = None, registry=None):
        self.skills_root = Path(skills_root) if skills_root else Path.home() / ".scientia" / "skills"
        self.registry = registry

    def expand(
        self,
        source: str,
        source_type: Optional[str] = None,
        raise_on_failure: bool = True,
    ) -> dict:
        """Fetch *source*, generate a verified skill, return result with script path.

        Returns a dict with keys:
            status, tool_name, skill_dir, script_path, retry_count, sample_output
        """
        result = build_skill(
            source,
            source_type=source_type,
            install_to=self.skills_root,
            registry=self.registry,
            raise_on_failure=raise_on_failure,
        )
        result["script_path"] = self._find_script(result["skill_dir"], result["tool_name"])
        return result

    def expand_from_signal(self, needs_signal: dict, raise_on_failure: bool = True) -> dict:
        """Parse a ScienceClaw NeedsSignal dict and expand the required skill.

        Expected keys in *needs_signal*:
            suggested_source (required): URL or identifier for the tool.
            source_type (optional): Hint for the fetch strategy.
            gap (optional): Human-readable description of the gap.
        """
        source = needs_signal.get("suggested_source")
        if not source:
            raise BridgeError(
                "NeedsSignal must contain 'suggested_source'. "
                f"Got keys: {list(needs_signal.keys())}"
            )
        source_type = needs_signal.get("source_type")
        return self.expand(source, source_type=source_type, raise_on_failure=raise_on_failure)

    async def expand_async(
        self,
        source: str,
        source_type: Optional[str] = None,
        raise_on_failure: bool = True,
    ) -> dict:
        """Non-blocking version of :meth:`expand` — runs in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.expand(source, source_type=source_type, raise_on_failure=raise_on_failure),
        )

    async def expand_async_from_signal(self, needs_signal: dict, raise_on_failure: bool = True) -> dict:
        """Async version of :meth:`expand_from_signal`."""
        source = needs_signal.get("suggested_source")
        if not source:
            raise BridgeError(
                "NeedsSignal must contain 'suggested_source'. "
                f"Got keys: {list(needs_signal.keys())}"
            )
        source_type = needs_signal.get("source_type")
        return await self.expand_async(source, source_type=source_type, raise_on_failure=raise_on_failure)

    # ------------------------------------------------------------------
    def _find_script(self, skill_dir: str, tool_name: str) -> Optional[str]:
        scripts_dir = Path(skill_dir) / "scripts"
        if not scripts_dir.exists():
            return None
        candidates = list(scripts_dir.glob(f"{tool_name}*.py"))
        if not candidates:
            candidates = list(scripts_dir.glob("*.py"))
        return str(candidates[0]) if candidates else None
