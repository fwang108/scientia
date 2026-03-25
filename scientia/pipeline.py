"""High-level build_skill pipeline — ties fetch → extract → install together."""
from __future__ import annotations
import dataclasses
from pathlib import Path
from typing import Optional

from scientia.strategies import fetch_source
from scientia.extractor import extract_metadata
from scientia.metadata_enrich import enrich_metadata
from scientia.installer import install_skill, InstallError
from scientia.detector import detect_source_type as _detect_source_type
from scientia.paper_analyzer import analyze_paper
from scientia.repo_analyzer import analyze_repo
from scientia.env_builder import build_env_spec
from scientia.executable_generator import generate_executable_script
from scientia.method_synthesizer import needs_synthesis, synthesize_method


class BuildError(Exception):
    """Raised when build_skill fails and raise_on_failure is True."""


def detect_source_type(source: str) -> str:
    """Infer source type from the source string."""
    return _detect_source_type(source)


def build_skill(
    source: str,
    *,
    source_type: Optional[str] = None,
    install_to: Optional[Path] = None,
    registry=None,
    raise_on_failure: bool = True,
    verifier_config=None,
) -> dict:
    """Full pipeline: fetch → extract → install → return result dict.

    Parameters
    ----------
    source:
        URL, package name, DOI, CLI command, or raw text.
    source_type:
        If omitted, auto-detected from *source*.
    install_to:
        Skills root directory.  Defaults to ``~/.scientia/skills``.
    registry:
        Optional Registry instance.  If provided, the skill is persisted.
    raise_on_failure:
        If True (default), raise BuildError on verification failure.
    verifier_config:
        Passed through to install_skill.
    """
    if source_type is None:
        source_type = detect_source_type(source)

    skills_root = Path(install_to) if install_to else Path.home() / ".scientia" / "skills"

    content = fetch_source(source, source_type)
    meta = extract_metadata(content, source_type)
    meta = enrich_metadata(meta, source, source_type, content=content)

    try:
        result = install_skill(
            meta,
            skills_root=skills_root,
            registry=registry,
            raise_on_failure=True,
            verifier_config=verifier_config,
        )
    except InstallError as exc:
        if raise_on_failure:
            raise BuildError(str(exc)) from exc
        return {
            "status": "failed",
            "tool_name": meta.tool_name,
            "skill_dir": str(skills_root / meta.skill_dir_name),
            "error": str(exc),
        }

    return {
        "status": "verified",
        "tool_name": meta.tool_name,
        "skill_dir": str(skills_root / meta.skill_dir_name),
        "retry_count": result.retry_count,
        "sample_output": result.stdout[:500] if result.stdout else None,
    }


def build_skill_deep(
    source: str,
    *,
    source_type: Optional[str] = None,
    install_to: Optional[Path] = None,
    registry=None,
    raise_on_failure: bool = True,
    verifier_config=None,
) -> dict:
    """Like :func:`build_skill` but additionally enriches via repo README analysis
    and writes a runnable ``executable_script.py`` alongside the client.

    Returns the standard result dict plus a ``method_spec`` key.
    """
    if source_type is None:
        source_type = detect_source_type(source)

    skills_root = Path(install_to) if install_to else Path.home() / ".scientia" / "skills"

    content = fetch_source(source, source_type)
    meta = extract_metadata(content, source_type)
    meta = enrich_metadata(meta, source, source_type, content=content)

    # Deep enrichment: parse paper notes into a MethodSpec, then enrich from repo README
    method_spec = analyze_paper(meta)
    if meta.repository_url:
        method_spec = analyze_repo(meta.repository_url, method_spec)
    env = build_env_spec(method_spec)
    if dataclasses.is_dataclass(method_spec) and not isinstance(method_spec, type):
        method_spec_with_env = dataclasses.replace(method_spec, env_spec=env)
    else:
        method_spec_with_env = method_spec

    # Write executable script — synthesize from paper notes if no repo/run_commands
    scripts_dir = skills_root / meta.skill_dir_name / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    exec_script_path = scripts_dir / "executable_script.py"
    if needs_synthesis(method_spec_with_env) and meta.implementation_notes:
        exec_script_path.write_text(
            synthesize_method(method_spec_with_env, meta.implementation_notes)
        )
    else:
        exec_script_path.write_text(generate_executable_script(method_spec_with_env))

    # Standard install
    try:
        result = install_skill(
            meta,
            skills_root=skills_root,
            registry=registry,
            raise_on_failure=True,
            verifier_config=verifier_config,
        )
    except InstallError as exc:
        if raise_on_failure:
            raise BuildError(str(exc)) from exc
        return {
            "status": "failed",
            "tool_name": meta.tool_name,
            "skill_dir": str(skills_root / meta.skill_dir_name),
            "error": str(exc),
            "method_spec": method_spec_with_env,
        }

    return {
        "status": "verified",
        "tool_name": meta.tool_name,
        "skill_dir": str(skills_root / meta.skill_dir_name),
        "retry_count": result.retry_count,
        "sample_output": result.stdout[:500] if result.stdout else None,
        "method_spec": method_spec_with_env,
    }
