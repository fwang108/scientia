"""Fetch and analyze a GitHub repository to enrich a MethodSpec."""
from __future__ import annotations

import base64
import re
from dataclasses import replace

import requests

from scientia.models import EnvSpec, MethodSpec, RepoInfo
from scientia.paper_analyzer import _extract_commands, _GPU_RE, _INSTALL_CMD_RE, _RUN_CMD_RE, _split_sections

_OWNER_REPO_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)")


def _parse_owner_repo(url: str) -> tuple[str, str] | None:
    m = _OWNER_REPO_RE.search(url)
    if m:
        return m.group(1), m.group(2)
    return None


def fetch_repo_readme(repo_url: str) -> str:
    """Return decoded README text for *repo_url*, or empty string on failure."""
    parsed = _parse_owner_repo(repo_url)
    if not parsed:
        return ""
    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        resp = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_repo_meta(repo_url: str) -> RepoInfo | None:
    """Return a :class:`RepoInfo` for *repo_url*, or ``None`` on failure."""
    parsed = _parse_owner_repo(repo_url)
    if not parsed:
        return None
    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        resp = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return RepoInfo(
            url=repo_url,
            stars=data.get("stargazers_count", 0) or 0,
            language=data.get("language"),
            description=data.get("description"),
        )
    except Exception:
        return None


def analyze_repo(repo_url: str, method_spec: MethodSpec) -> MethodSpec:
    """Enrich *method_spec* with install/run commands parsed from the repo README.

    Existing commands on *method_spec* are preserved; new ones are appended.
    Returns a new :class:`MethodSpec` (immutable update pattern).
    """
    readme = fetch_repo_readme(repo_url)
    sections = _split_sections(readme) if readme else {}

    install_lines: list[str] = []
    run_lines: list[str] = []
    all_lines: list[str] = []

    for title, lines in sections.items():
        all_lines.extend(lines)
        if "install" in title:
            install_lines.extend(lines)
        if "run" in title or "usage" in title or "how to" in title:
            run_lines.extend(lines)

    new_install = _extract_commands(install_lines, _INSTALL_CMD_RE)
    new_run = _extract_commands(run_lines, _RUN_CMD_RE)

    # Merge deduplicating by command string
    existing_install = list(method_spec.install_commands)
    existing_run = list(method_spec.run_commands)
    for cmd in new_install:
        if cmd not in existing_install:
            existing_install.append(cmd)
    for cmd in new_run:
        if cmd not in existing_run:
            existing_run.append(cmd)

    gpu_required = method_spec.env_spec.gpu_required or bool(_GPU_RE.search("\n".join(all_lines)))

    env_spec = EnvSpec(
        python_version=method_spec.env_spec.python_version,
        dependencies=list(method_spec.env_spec.dependencies),
        env_vars=dict(method_spec.env_spec.env_vars),
        gpu_required=gpu_required,
    )

    return MethodSpec(
        name=method_spec.name,
        description=method_spec.description,
        input_spec=method_spec.input_spec,
        output_spec=method_spec.output_spec,
        hyperparameters=dict(method_spec.hyperparameters),
        prerequisites=list(method_spec.prerequisites),
        install_commands=existing_install,
        run_commands=existing_run,
        datasets=list(method_spec.datasets),
        checkpoints=list(method_spec.checkpoints),
        limitations=list(method_spec.limitations),
        repository_url=method_spec.repository_url,
        env_spec=env_spec,
    )
