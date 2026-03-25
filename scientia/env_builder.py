"""Build an EnvSpec from a MethodSpec by parsing install commands and prerequisites."""
from __future__ import annotations

import re

from scientia.models import EnvSpec, MethodSpec

_GPU_RE = re.compile(r"\bgpu\b", re.IGNORECASE)
_PYTHON_VER_RE = re.compile(r"python\s+(\d+\.\d+)", re.IGNORECASE)
# Match: pip install pkg1 pkg2  OR  pip install pkg1==1.0 pkg2>=2.0
_PIP_INSTALL_RE = re.compile(r"pip\d*\s+install\s+(.+)", re.IGNORECASE)


def _extract_python_version(texts: list[str]) -> str | None:
    for text in texts:
        m = _PYTHON_VER_RE.search(text)
        if m:
            return m.group(1)
    return None


def _extract_pip_deps(install_commands: list[str]) -> list[str]:
    deps: list[str] = []
    for cmd in install_commands:
        m = _PIP_INSTALL_RE.match(cmd.strip())
        if m:
            raw = m.group(1)
            # Split on whitespace; strip version specifiers
            for token in raw.split():
                if token.startswith("-"):
                    continue  # skip flags like -r, --quiet
                pkg = re.split(r"[=<>!@;]", token)[0].strip()
                if pkg:
                    deps.append(pkg)
    return deps


def build_env_spec(method_spec: MethodSpec) -> EnvSpec:
    """Infer an :class:`EnvSpec` from *method_spec* install commands and prerequisites."""
    all_text = method_spec.prerequisites + method_spec.install_commands + method_spec.run_commands

    python_version = _extract_python_version(all_text)
    dependencies = _extract_pip_deps(method_spec.install_commands)
    gpu_required = any(_GPU_RE.search(t) for t in all_text)

    return EnvSpec(
        python_version=python_version,
        dependencies=dependencies,
        gpu_required=gpu_required,
    )
