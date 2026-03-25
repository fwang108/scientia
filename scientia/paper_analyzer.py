"""Extract structured MethodSpec from ToolMetadata + raw paper text."""
from __future__ import annotations

import re

from scientia.models import EnvSpec, MethodSpec, ToolMetadata

# Section header patterns used to carve implementation_notes into sections.
_SECTION_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)

# Lines that look like shell commands (pip, conda, python, bash, git, etc.)
_INSTALL_CMD_RE = re.compile(
    r"^\s*(pip\s+install|conda\s+install|pip3\s+install|poetry\s+add|uv\s+add)",
    re.IGNORECASE,
)
_RUN_CMD_RE = re.compile(
    r"^\s*(python\s+|python3\s+|bash\s+|sh\s+|\.\/|torchrun\s+|accelerate\s+launch)",
    re.IGNORECASE,
)
_GPU_RE = re.compile(r"\bgpu\b", re.IGNORECASE)


def _split_sections(notes: str) -> dict[str, list[str]]:
    """Return {section_title_lower: [lines]} from Markdown notes."""
    sections: dict[str, list[str]] = {}
    current: str = "__preamble__"
    sections[current] = []
    for line in notes.splitlines():
        m = _SECTION_RE.match(line)
        if m:
            current = m.group(1).lower()
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return sections


def _extract_commands(lines: list[str], pattern: re.Pattern) -> list[str]:
    """Return non-empty lines matching *pattern*."""
    cmds = []
    for line in lines:
        stripped = line.strip()
        if stripped and pattern.match(stripped):
            cmds.append(stripped)
    return cmds


def analyze_paper(meta: ToolMetadata, paper_text: str = "") -> MethodSpec:
    """Build a :class:`MethodSpec` from *meta* and optional raw *paper_text*.

    Parses ``implementation_notes`` for install/run commands and GPU hints.
    Falls back gracefully when fields are absent.
    """
    notes = meta.implementation_notes or ""
    sections = _split_sections(notes) if notes else {}

    # Collect all lines from installation-related sections
    install_lines: list[str] = []
    run_lines: list[str] = []
    prereq_lines: list[str] = []
    all_lines: list[str] = []

    for title, lines in sections.items():
        all_lines.extend(lines)
        if "install" in title:
            install_lines.extend(lines)
        if "run" in title or "usage" in title or "how to" in title:
            run_lines.extend(lines)
        if "prerequisite" in title or "requirement" in title:
            prereq_lines.extend(lines)

    install_commands = _extract_commands(install_lines, _INSTALL_CMD_RE)
    run_commands = _extract_commands(run_lines, _RUN_CMD_RE)

    # GPU detection: scan prerequisites and all notes
    gpu_text = "\n".join(prereq_lines + all_lines)
    gpu_required = bool(_GPU_RE.search(gpu_text))

    env_spec = EnvSpec(gpu_required=gpu_required)

    # Prerequisites: non-empty lines from prerequisites section
    prerequisites = [l.strip() for l in prereq_lines if l.strip()]

    return MethodSpec(
        name=meta.tool_name,
        description=meta.description,
        input_spec="",
        output_spec="",
        install_commands=install_commands,
        run_commands=run_commands,
        prerequisites=prerequisites,
        repository_url=meta.repository_url,
        env_spec=env_spec,
    )
