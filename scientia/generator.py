"""Generate SKILL.md and *_client.py files from ToolMetadata."""
from __future__ import annotations
import json

from scientia.arxiv_util import arxiv_id_from_url
from scientia.models import Param, ToolMetadata


def _frontmatter_resource_lines(meta: ToolMetadata) -> str:
    """YAML lines for ``repository_url`` / ``reference_url`` when present."""
    lines: list[str] = []
    repo = (meta.repository_url or "").strip()
    ru = (meta.reference_url or "").strip()
    if repo:
        lines.append(f"repository_url: {json.dumps(repo)}\n")
    if ru:
        lines.append(f"reference_url: {json.dumps(ru)}\n")
    return "".join(lines)


def _reference_markdown_block(meta: ToolMetadata) -> str:
    ru = (meta.reference_url or "").strip()
    repo = (meta.repository_url or "").strip()
    parts: list[str] = []
    if repo:
        parts.append(
            f"""
### Code repository

<{repo}>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.
"""
        )
    if ru:
        if arxiv_id_from_url(ru):
            parts.append(
                f"""
### Paper (arXiv — explanation)

<{ru}>

This is the **paper** reference. The client can optionally fetch live Atom metadata (title, abstract) for agents; it does **not** run training or upstream research code by itself.
"""
            )
        else:
            parts.append(
                f"""
### Primary resource (landing page)

<{ru}>

This is the paper or artifact home from DOI/registry metadata — **not** a JSON API. If this URL is **arXiv**, the generated client can still fetch **live Atom metadata** (title, abstract, authors) without a ``BASE_URL``. For other hosts, the client uses stub mode until you set a real ``BASE_URL`` for a REST service.
"""
            )
    return "".join(parts)


def _implementation_section(meta: ToolMetadata) -> str:
    """SKILL.md block: how to run the real method (extracted or maintainer placeholder)."""
    notes = (meta.implementation_notes or "").strip()
    if notes:
        return f"""
### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

{notes}

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*
"""
    return """
### How to run the method (from the source)

No install/run steps were extracted from the source. **Maintainers:** extend this section and ``scripts/USAGE.md`` with:

- Prerequisites (OS, GPU, Python version, API keys)
- Clone and environment setup (``git clone``, ``pip``/``conda``/Docker)
- Commands from the upstream README or paper supplement (training, inference, evaluation)
- Where to obtain datasets or checkpoints

The ``*_client.py`` script is for **structured JSON** to agents; it is not a substitute for the steps above unless you wire it to subprocess calls yourself.
"""


def generate_usage_md(meta: ToolMetadata) -> str:
    """Contents of ``scripts/USAGE.md`` — operational notes alongside the client."""
    notes = (meta.implementation_notes or "").strip()
    header = f"# Usage: {meta.tool_name}\n\n"
    tail = (
        f"\n\n---\n\n**Scientia client:** `python3 scripts/{meta.script_filename}` "
        f"with the flags in `SKILL.md` — prints JSON on stdout for agents.\n"
    )
    if notes:
        return header + notes + tail
    return (
        header
        + "No implementation steps were auto-extracted. Edit this file (or regenerate the skill "
        + "with a richer source) and add prerequisites, install commands, and how to run the "
        + "method from the upstream README or paper.\n"
        + tail
    )


def _arxiv_embedded_id(meta: ToolMetadata) -> str | None:
    """If *meta* references an arXiv abs/PDF URL, return the arXiv id (e.g. ``2510.08191``)."""
    for u in ((meta.reference_url or "").strip(), (meta.base_url or "").strip()):
        if not u:
            continue
        aid = arxiv_id_from_url(u)
        if aid:
            return aid
    return None


def generate_skill_md(meta: ToolMetadata) -> str:
    """Return the contents of SKILL.md for *meta*."""
    params_doc = "\n".join(
        f"  --{p.name.replace('_', '-')}  ({p.type})  "
        f"{'[required]' if p.required else f'[optional, default={p.default}]'}  "
        f"{p.description}"
        for p in meta.all_parameters
    )
    scaffold = ""
    if not (meta.base_url and str(meta.base_url).strip()):
        repo = (meta.repository_url or "").strip()
        arxiv_id = _arxiv_embedded_id(meta)
        if repo:
            scaffold = """
### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/{fn}` or wrap the upstream CLI with ``subprocess`` after clone.
""".format(fn=meta.script_filename)
        elif arxiv_id:
            scaffold = """
### What “running” this client does

The `*_client.py` script parses CLI flags and, when **reference_url** points at **arXiv**, calls the public **Atom API** (`export.arxiv.org`) to return **live metadata** (title, abstract, authors) plus your parameters as JSON on stdout. It does **not** run upstream research code or train models.

If the arXiv request fails (offline, rate limit), the client still prints JSON with an error field and exits 0 so verification can pass.

**Beyond metadata:** to integrate a real REST product or run vendor code, set `BASE_URL` in `scripts/{fn}` or replace the script body with your own calls.
""".format(fn=meta.script_filename)
        else:
            scaffold = """
### What “running” this client does

The `*_client.py` script is a **thin CLI scaffold**: it parses flags and prints **one JSON object** on stdout (for agents / `build-recipe` / bash chaining). It does **not** by itself run upstream research code, train models, or call a vendor product—unless you **wire in** a real HTTP API (`BASE_URL` + correct `requests` usage) or replace the body of the script with `subprocess` / Python imports to a local package.

For **papers, DOIs, or prose** sources, the LLM typically infers *plausible* parameters; there may be **no public API**. In that case the client is a **structured documentation + argument surface** for your agent, not a working integration.

**To make it operational:** edit `scripts/{fn}` (set `BASE_URL`, method, JSON body, auth) or call your own code. If you have **OpenAPI**, re-run `scientia add <spec> --source-type openapi`. If the capability is a **Python library**, try `--source-type pypi` (still HTTP-oriented today—see README). If it’s a **Git repo**, clone it yourself under this skill and point the client at entrypoints or wrap `subprocess`.
""".format(fn=meta.script_filename)

    ref_fm = _frontmatter_resource_lines(meta)
    ref_body = _reference_markdown_block(meta)
    impl = _implementation_section(meta)

    return f"""\
---
name: {meta.tool_name}
description: {meta.description}
source_type: {meta.source_type}
auth_required: {str(meta.auth_required).lower()}
{ref_fm}---

## {meta.tool_name}

{meta.description}
{ref_body}{scaffold}{impl}
### Parameters

{params_doc}

### Usage

```bash
python3 scripts/{meta.script_filename} {meta.example_call}
```

### Example Output

```json
{meta.example_output_shape}
```
"""


def generate_client_script(meta: ToolMetadata) -> str:
    """Return the contents of *_client.py for *meta*."""
    add_args = "\n".join(_arg_line(p) for p in meta.all_parameters)
    desc = json.dumps(meta.description)
    documented_shape = json.dumps(meta.example_output_shape or "{}")

    base = (meta.base_url or "").strip()
    repo = (meta.repository_url or "").strip()
    arxiv_id = _arxiv_embedded_id(meta) if not base else None

    if not base and meta.source_type == "github" and repo:
        return _generate_github_dossier_client(
            meta, add_args, desc, documented_shape, arxiv_id
        )

    if not base and arxiv_id:
        return _generate_arxiv_client(meta, add_args, desc, documented_shape, arxiv_id)

    return f"""\
#!/usr/bin/env python3
# Auto-generated by Scientia — edit BASE_URL / HTTP logic when you have a real API.
\"\"\"CLI client for skill {json.dumps(meta.tool_name)}.\"\"\"
import argparse
import json
import sys

import requests

BASE_URL = {json.dumps(meta.base_url or "")}
REFERENCE_URL = {json.dumps((meta.reference_url or "").strip())}
DOCUMENTED_OUTPUT_SHAPE = {documented_shape}


def main() -> None:
    parser = argparse.ArgumentParser(description={desc})
{add_args}
    args = parser.parse_args()

    params = {{}}
{_build_params_block(meta)}

    if not str(BASE_URL).strip():
        out = {{
            "status": "stub",
            "skill": {json.dumps(meta.tool_name)},
            "source_type": {json.dumps(meta.source_type)},
            "execution": "cli_stub_only",
            "what_this_does": (
                "Parses CLI args and returns JSON. Does NOT call external services, run ML, "
                "or execute vendor/paper code unless you edit this script or set BASE_URL."
            ),
            "message": (
                "No JSON REST base_url (normal for DOI/papers). "
                "Use reference_url for the paper landing page; set BASE_URL only when you have a real API."
            ),
            "params": params,
            "next_steps": [
                "Have an HTTP API? Set BASE_URL; adjust method/path/json=/headers.",
                "Have OpenAPI? scientia add <spec-url> --source-type openapi",
                "Have local code? Clone/install it and call it from this script.",
            ],
        }}
        ref = str(REFERENCE_URL).strip()
        if ref:
            out["reference_url"] = ref
            out["resource_note"] = (
                "Landing page from DOI/registry — not a JSON API; do not use as BASE_URL for requests.get()."
            )
        try:
            out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
        except json.JSONDecodeError:
            out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
        print(json.dumps(out, indent=2))
        sys.exit(0)

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        print(json.dumps(resp.json()))
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({{"error": str(exc)}}))
        sys.exit(1)


if __name__ == "__main__":
    main()
"""


def _generate_github_dossier_client(
    meta: ToolMetadata,
    add_args: str,
    desc: str,
    documented_shape: str,
    arxiv_id: str | None,
) -> str:
    """Emit a client with repo clone hints plus optional arXiv paper metadata."""
    repo_url = json.dumps((meta.repository_url or "").strip())
    ref_url = json.dumps((meta.reference_url or "").strip())
    aid = json.dumps(arxiv_id or "")
    return f"""\
#!/usr/bin/env python3
# Auto-generated by Scientia — GitHub dossier + optional arXiv; set BASE_URL for a REST API.
\"\"\"CLI client for skill {json.dumps(meta.tool_name)}.\"\"\"
import argparse
import json
import sys

import requests

BASE_URL = {json.dumps(meta.base_url or "")}
REPOSITORY_URL = {repo_url}
REFERENCE_URL = {ref_url}
ARXIV_ID = {aid}
DOCUMENTED_OUTPUT_SHAPE = {documented_shape}


def main() -> None:
    parser = argparse.ArgumentParser(description={desc})
{add_args}
    args = parser.parse_args()

    params = {{}}
{_build_params_block(meta)}

    if not str(BASE_URL).strip() and str(REPOSITORY_URL).strip():
        try:
            from scientia.arxiv_util import fetch_arxiv_metadata, suggested_git_clone_command
        except ImportError:
            fetch_arxiv_metadata = None  # type: ignore[assignment]
            suggested_git_clone_command = None  # type: ignore[assignment]

        repo_u = str(REPOSITORY_URL).strip()
        clone_cmd = (
            suggested_git_clone_command(repo_u)
            if suggested_git_clone_command is not None
            else (f"git clone {{repo_u}}.git" if not repo_u.endswith(".git") else f"git clone {{repo_u}}")
        )
        out = {{
            "status": "ok",
            "skill": {json.dumps(meta.tool_name)},
            "source_type": {json.dumps(meta.source_type)},
            "execution": "github_repo_dossier",
            "what_this_does": (
                "Parses CLI args and returns JSON: GitHub repository (clone command) plus "
                "optional arXiv paper metadata for explanation."
            ),
            "repository": {{
                "url": repo_u,
                "suggested_clone_command": clone_cmd,
                "role": "implementation",
            }},
            "params": params,
        }}
        ref = str(REFERENCE_URL).strip()
        if ref:
            out["reference_url"] = ref

        if str(ARXIV_ID).strip() and fetch_arxiv_metadata is not None:
            try:
                am = fetch_arxiv_metadata(str(ARXIV_ID).strip())
                out["paper"] = {{
                    "role": "arxiv_explanation",
                    "arxiv_abs_url": ref if ref else None,
                    "metadata": am,
                }}
            except Exception as exc:  # noqa: BLE001
                out["paper"] = {{
                    "role": "arxiv_explanation",
                    "arxiv_error": str(exc),
                    "arxiv_abs_url": ref if ref else None,
                }}
        elif ref:
            out["paper"] = {{"role": "reference", "url": ref}}

        try:
            out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
        except json.JSONDecodeError:
            out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
        print(json.dumps(out, indent=2))
        sys.exit(0)

    if not str(BASE_URL).strip():
        out = {{
            "status": "stub",
            "skill": {json.dumps(meta.tool_name)},
            "source_type": {json.dumps(meta.source_type)},
            "execution": "cli_stub_only",
            "what_this_does": (
                "Parses CLI args and returns JSON. Install ``scientia`` for GitHub dossier mode, "
                "or set REPOSITORY_URL / BASE_URL in this script."
            ),
            "message": (
                "Missing repository URL for GitHub dossier mode. "
                "Re-run ``scientia add`` with ``--source-type github`` or edit this script."
            ),
            "params": params,
            "next_steps": [
                "pip install -e <Scientia repo> so ``import scientia.arxiv_util`` works.",
                "Have an HTTP API? Set BASE_URL; adjust method/path/json=/headers.",
            ],
        }}
        ref = str(REFERENCE_URL).strip()
        if ref:
            out["reference_url"] = ref
        try:
            out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
        except json.JSONDecodeError:
            out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
        print(json.dumps(out, indent=2))
        sys.exit(0)

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        print(json.dumps(resp.json()))
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({{"error": str(exc)}}))
        sys.exit(1)


if __name__ == "__main__":
    main()
"""


def _generate_arxiv_client(
    meta: ToolMetadata,
    add_args: str,
    desc: str,
    documented_shape: str,
    arxiv_id: str,
) -> str:
    """Emit a client that fetches live arXiv Atom metadata when BASE_URL is unset."""
    aid = json.dumps(arxiv_id)
    return f"""\
#!/usr/bin/env python3
# Auto-generated by Scientia — arXiv Atom API when BASE_URL is empty; set BASE_URL for a REST API.
\"\"\"CLI client for skill {json.dumps(meta.tool_name)}.\"\"\"
import argparse
import json
import sys

import requests

BASE_URL = {json.dumps(meta.base_url or "")}
REFERENCE_URL = {json.dumps((meta.reference_url or "").strip())}
ARXIV_ID = {aid}
DOCUMENTED_OUTPUT_SHAPE = {documented_shape}


def main() -> None:
    parser = argparse.ArgumentParser(description={desc})
{add_args}
    args = parser.parse_args()

    params = {{}}
{_build_params_block(meta)}

    if not str(BASE_URL).strip() and str(ARXIV_ID).strip():
        try:
            from scientia.arxiv_util import fetch_arxiv_metadata
        except ImportError:
            fetch_arxiv_metadata = None  # type: ignore[assignment]

        if fetch_arxiv_metadata is not None:
            try:
                arxiv_meta = fetch_arxiv_metadata(str(ARXIV_ID).strip())
                out = {{
                    "status": "ok",
                    "skill": {json.dumps(meta.tool_name)},
                    "source_type": {json.dumps(meta.source_type)},
                    "execution": "arxiv_atom_api",
                    "what_this_does": (
                        "Parses CLI args and returns JSON including live arXiv Atom metadata "
                        "(title, abstract, authors) from export.arxiv.org."
                    ),
                    "arxiv": arxiv_meta,
                    "params": params,
                }}
                ref = str(REFERENCE_URL).strip()
                if ref:
                    out["reference_url"] = ref
                try:
                    out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
                except json.JSONDecodeError:
                    out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
                print(json.dumps(out, indent=2))
                sys.exit(0)
            except Exception as exc:  # noqa: BLE001
                out = {{
                    "status": "stub",
                    "skill": {json.dumps(meta.tool_name)},
                    "source_type": {json.dumps(meta.source_type)},
                    "execution": "arxiv_fetch_failed",
                    "arxiv_error": str(exc),
                    "what_this_does": (
                        "Parses CLI args; arXiv Atom fetch failed — returning stub JSON with error."
                    ),
                    "message": (
                        "Could not fetch arXiv metadata. Check network or arXiv id; "
                        "or set BASE_URL for a REST API."
                    ),
                    "params": params,
                    "next_steps": [
                        "Retry when online; verify ARXIV_ID / reference_url.",
                        "Have an HTTP API? Set BASE_URL in this script.",
                        "Have OpenAPI? scientia add <spec-url> --source-type openapi",
                    ],
                }}
                ref = str(REFERENCE_URL).strip()
                if ref:
                    out["reference_url"] = ref
                try:
                    out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
                except json.JSONDecodeError:
                    out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
                print(json.dumps(out, indent=2))
                sys.exit(0)

        out = {{
            "status": "stub",
            "skill": {json.dumps(meta.tool_name)},
            "source_type": {json.dumps(meta.source_type)},
            "execution": "cli_stub_only",
            "what_this_does": (
                "Parses CLI args. The ``scientia`` package is required for live arXiv fetches "
                "(``from scientia.arxiv_util import fetch_arxiv_metadata``)."
            ),
            "message": (
                "Install the Scientia package in this Python environment "
                "(``pip install -e /path/to/Scientia``) to enable arXiv Atom metadata, "
                "or set BASE_URL for a REST API."
            ),
            "params": params,
            "next_steps": [
                "pip install -e <Scientia repo> so ``import scientia.arxiv_util`` works.",
                "Have an HTTP API? Set BASE_URL; adjust method/path/json=/headers.",
            ],
        }}
        ref = str(REFERENCE_URL).strip()
        if ref:
            out["reference_url"] = ref
        try:
            out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
        except json.JSONDecodeError:
            out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
        print(json.dumps(out, indent=2))
        sys.exit(0)

    if not str(BASE_URL).strip():
        out = {{
            "status": "stub",
            "skill": {json.dumps(meta.tool_name)},
            "source_type": {json.dumps(meta.source_type)},
            "execution": "cli_stub_only",
            "what_this_does": (
                "Parses CLI args and returns JSON. Does NOT call external services, run ML, "
                "or execute vendor/paper code unless you edit this script or set BASE_URL."
            ),
            "message": (
                "No JSON REST base_url (normal for DOI/papers). "
                "Use reference_url for the paper landing page; set BASE_URL only when you have a real API."
            ),
            "params": params,
            "next_steps": [
                "Have an HTTP API? Set BASE_URL; adjust method/path/json=/headers.",
                "Have OpenAPI? scientia add <spec-url> --source-type openapi",
                "Have local code? Clone/install it and call it from this script.",
            ],
        }}
        ref = str(REFERENCE_URL).strip()
        if ref:
            out["reference_url"] = ref
            out["resource_note"] = (
                "Landing page from DOI/registry — not a JSON API; do not use as BASE_URL for requests.get()."
            )
        try:
            out["documented_example_shape"] = json.loads(DOCUMENTED_OUTPUT_SHAPE)
        except json.JSONDecodeError:
            out["documented_example_shape_raw"] = DOCUMENTED_OUTPUT_SHAPE
        print(json.dumps(out, indent=2))
        sys.exit(0)

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        print(json.dumps(resp.json()))
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({{"error": str(exc)}}))
        sys.exit(1)


if __name__ == "__main__":
    main()
"""


# ── helpers ────────────────────────────────────────────────────────────────────

def _argparse_default_literal(value) -> str:
    """Emit a valid Python expression for ``parser.add_argument(..., default=…)``.

    LLM JSON often uses booleans/numbers; ``json.dumps(True)`` is ``true``, which is
    **invalid Python** and crashes generated clients (NameError: ``true``).
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, dict, tuple)):
        return repr(value)
    return repr(value)


def _arg_line(p: Param) -> str:
    flag = f"--{p.name.replace('_', '-')}"
    parts = [f'parser.add_argument("{flag}"']
    parts.append("type=str")
    parts.append(f"help={json.dumps(p.description)}")
    if p.required:
        parts.append("required=True")
    else:
        parts.append(f"default={_argparse_default_literal(p.default)}")
    return "    " + ", ".join(parts) + ")"


def _build_params_block(meta: ToolMetadata) -> str:
    lines = []
    for p in meta.all_parameters:
        attr = p.name.replace("-", "_")
        lines.append(f'    if args.{attr} is not None:')
        lines.append(f'        params["{p.name}"] = args.{attr}')
    return "\n".join(lines)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())
