"""Install a generated skill into a ScienceClaw-compatible skills directory."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import uuid
from datetime import datetime, timezone

from scientia.generator import generate_client_script, generate_skill_md, generate_usage_md
from scientia.models import SkillRecord, ToolMetadata, VerificationResult
from scientia.verifier import VerifierConfig, verify_script, build_verify_argv


class InstallError(Exception):
    """Raised when a skill fails verification and raise_on_failure is True."""


def _cleanup_orphan_verify_scripts(scripts_dir: Path, keep_client_name: str) -> None:
    """Remove leftover verifier temp modules (historical ``tmp*.py`` / ``sci_verify_*.py``)."""
    for path in list(scripts_dir.iterdir()):
        if not path.is_file() or path.suffix != ".py":
            continue
        if path.name == keep_client_name:
            continue
        if path.name.startswith("tmp") or path.name.startswith("sci_verify_"):
            try:
                path.unlink()
            except OSError:
                pass


def install_skill(
    meta: ToolMetadata,
    skills_root: Path,
    registry=None,
    raise_on_failure: bool = True,
    verifier_config: Optional[VerifierConfig] = None,
) -> VerificationResult:
    """Generate skill files, verify the client script, and optionally register.

    Parameters
    ----------
    meta:
        Extracted tool metadata.
    skills_root:
        Root directory for skills (e.g. ``scienceclaw/skills/``).
    registry:
        Optional ``Registry`` instance.  If provided, the skill is saved.
    raise_on_failure:
        If True (default), raise ``InstallError`` when verification fails.
    verifier_config:
        Optional verifier settings (timeout, max_retries, fix_callback).
    """
    skill_dir = Path(skills_root) / meta.skill_dir_name
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_orphan_verify_scripts(scripts_dir, meta.script_filename)

    # Write SKILL.md
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(generate_skill_md(meta))

    # Write client script
    script_content = generate_client_script(meta)
    script_path = scripts_dir / meta.script_filename
    script_path.write_text(script_content)

    usage_path = scripts_dir / "USAGE.md"
    usage_path.write_text(generate_usage_md(meta))

    # Verify
    if verifier_config is None:
        verifier_config = VerifierConfig()

    result = verify_script(
        script_content,
        work_dir=scripts_dir,
        config=verifier_config,
        example_args=build_verify_argv(meta),
    )

    # Persist to registry if provided
    if registry is not None:
        status = "verified" if result.passed else "failed"
        now = datetime.now(timezone.utc).isoformat()
        record = SkillRecord(
            skill_id=str(uuid.uuid4()),
            tool_name=meta.tool_name,
            source=meta.base_url or "",
            source_type=meta.source_type,
            verification_status=status,
            retry_count=result.retry_count,
            sample_output=result.stdout[:500] if result.stdout else None,
            skill_dir=str(skill_dir),
            generated_at=now,
            last_verified_at=now if result.passed else None,
        )
        registry.save(record)

    if not result.passed and raise_on_failure:
        raise InstallError(
            f"Skill '{meta.tool_name}' failed verification: {result.error_summary}"
        )

    return result
