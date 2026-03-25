"""Publish a Scientia-installed skill folder via the ClawHub CLI (npm: clawhub)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
class ClawhubPublishError(Exception):
    """ClawHub publish setup or invocation failed."""


def find_clawhub_executable() -> str | None:
    """Return ``clawhub`` or ``clawdhub`` on PATH (same npm package exposes both)."""
    for name in ("clawhub", "clawdhub"):
        path = shutil.which(name)
        if path:
            return path
    return None


def ensure_skill_folder(path: Path) -> Path:
    """Resolve *path* and require ``SKILL.md`` (ClawHub requirement)."""
    root = path.expanduser().resolve()
    if not root.is_dir():
        raise ClawhubPublishError(f"Skill path is not a directory: {root}")
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        alt = root / "skills.md"
        if not alt.is_file():
            raise ClawhubPublishError(
                f"ClawHub requires SKILL.md in the folder; missing in {root}"
            )
    return root


def build_publish_argv(
    clawhub_bin: str,
    skill_dir: Path,
    *,
    slug: str | None,
    display_name: str | None,
    version: str,
    changelog: str | None,
    tags: str | None,
    fork_of: str | None,
) -> list[str]:
    """Build argument vector for ``clawhub publish``."""
    argv: list[str] = [clawhub_bin, "publish", str(skill_dir)]
    if slug:
        argv.extend(["--slug", slug])
    if display_name:
        argv.extend(["--name", display_name])
    argv.extend(["--version", version])
    if changelog:
        argv.extend(["--changelog", changelog])
    if tags:
        argv.extend(["--tags", tags])
    if fork_of:
        argv.extend(["--fork-of", fork_of])
    return argv


def publish_skill(
    skill_dir: Path,
    *,
    slug: str | None = None,
    display_name: str | None = None,
    version: str = "1.0.0",
    changelog: str | None = None,
    tags: str | None = "latest",
    fork_of: str | None = None,
    dry_run: bool = False,
) -> int:
    """Run ``clawhub publish`` for *skill_dir*; return subprocess exit code.

    Requires the `clawhub` npm CLI on PATH and a prior `clawhub login`.
    """
    exe = find_clawhub_executable()
    if not exe:
        raise ClawhubPublishError(
            "ClawHub CLI not found. Install with: npm i -g clawhub\n"
            "Then run: clawhub login"
        )

    root = ensure_skill_folder(skill_dir)
    argv = build_publish_argv(
        exe,
        root,
        slug=slug,
        display_name=display_name,
        version=version,
        changelog=changelog,
        tags=tags,
        fork_of=fork_of,
    )

    if dry_run:
        print("Would run:", subprocess.list2cmdline(argv), file=sys.stderr)
        return 0

    proc = subprocess.run(argv)
    return int(proc.returncode)


def publish_from_registry_tool_name(
    tool_name: str,
    db_path: Path,
    **kwargs,
) -> int:
    """Look up *tool_name* in the Scientia SQLite registry and publish that folder."""
    from scientia.registry import Registry

    reg = Registry(db_path)
    record = reg.get_by_tool_name(tool_name)
    if record is None:
        raise ClawhubPublishError(f"No skill named {tool_name!r} in registry {db_path}")
    return publish_skill(Path(record.skill_dir), **kwargs)
