"""Source-type-specific prompt templates for LLM metadata extraction and code generation."""
from __future__ import annotations

SUPPORTED_TYPES = ("openapi", "pypi", "doi", "cli", "html", "text")

_JSON_SCHEMA = """\
Return ONLY valid JSON with these exact keys:
{{
  "tool_name": "snake_case_name",
  "description": "one-line description",
  "base_url": "https://... or null",
  "auth_required": true or false,
  "parameters": [
    {{"name": "param_name", "type": "str", "description": "...", "required": true, "default": null}}
  ],
  "example_call": "--param value",
  "example_output_shape": "{{\"key\": \"value\"}}",
  "source_type": "{source_type}",
  "reference_url": "https://paper-or-dataset-landing-page or null",
  "repository_url": "https://github.com/org/repo or null if not stated",
  "implementation_notes": "Markdown string or null — see field instructions in the prompt"
}}"""

_OPENAPI_TEMPLATE = """\
You are a scientific API tool metadata extractor.

Given the following OpenAPI specification (type: openapi), extract structured metadata.
Focus on:
- The primary endpoint paths and HTTP methods (GET/POST)
- Required and optional path/query parameters with their types
- The base URL from the `servers` field
- Authentication requirements (look for `securitySchemes`)
- A concrete example_call showing the most important endpoint parameters
- **implementation_notes:** Markdown with how to call the API (auth, base URL, curl example) or ``null``

{json_schema}

OpenAPI source content:
{content}
"""

_PYPI_TEMPLATE = """\
You are a Python package tool metadata extractor.

Given the following PyPI package documentation (type: pypi), extract structured metadata.
Focus on:
- The main public functions and classes the package exposes
- Key import statements (e.g. `from package import function`)
- Function arguments: name, type, whether required, default value
- What JSON-serialisable output the main function produces
- Set base_url to null (PyPI packages are imported, not called via HTTP)
- **implementation_notes:** Markdown with ``pip install``, import example, minimal usage

{json_schema}

PyPI package content:
{content}
"""

_DOI_TEMPLATE = """\
You are a scientific paper tool metadata extractor.

Given the following paper or dataset description (type: doi), extract structured metadata.
Focus on:
- The datasets, databases, or computational methods described
- Any web APIs or data access endpoints mentioned
- Key parameters for reproducing the method or accessing the data

**URLs (critical):**
- ``reference_url``: landing page readers open (arXiv abs, journal HTML, Zenodo record, GitHub repo home) when the content includes "Primary resource / landing page URL:" or similar — copy that URL here.
- ``repository_url``: official **code** URL if the paper mentions GitHub/GitLab/etc.; else ``null``.
- ``base_url``: **only** if there is a clear **machine JSON HTTP API** base (REST root returning JSON). Paper homepages, arXiv abstract pages, and PDF links are **not** APIs — use ``null`` for ``base_url`` in those cases.

**implementation_notes (critical for skill users):**
Multi-line **Markdown** so someone can try to run the method. Use short ``##`` sections when you have content, e.g.:
- ``## Prerequisites`` — OS, GPU, Python version, API keys, datasets named in the paper
- ``## Installation`` — ``git clone``, ``pip install``, conda, or "see repository README" with URL
- ``## How to run`` — **verbatim or paraphrased** commands/steps from the paper or supplement (training, inference, evaluation)
- ``## Limitations`` — what this skill does **not** automate

If the source gives almost no runnable detail, set ``implementation_notes`` to a short honest note and still list any URLs found. Use ``null`` only if there is truly nothing to say.

Output rules: respond with ONLY the JSON object — no markdown code fences, no commentary before or after.

{json_schema}

Paper/dataset content:
{content}
"""

_CLI_TEMPLATE = """\
You are a CLI tool metadata extractor.

Given the following CLI tool documentation (type: cli), extract structured metadata.
Focus on:
- The main commands, subcommands, flags, and arguments
- Required vs optional arguments with their types and default values
- Example command invocations
- Set base_url to null (CLI tools are invoked directly, not via HTTP)
- In example_call, show the most important flags and arguments

**implementation_notes:** Markdown with ``## Installation`` and ``## How to run`` summarising how to install and invoke this CLI (from the docs). ``repository_url`` null unless a repo URL appears.

{json_schema}

CLI tool documentation:
{content}
"""

_GITHUB_TEMPLATE = """\
You are a scientific **GitHub repository** skill metadata extractor.

The content is the repository README (type: github). Build a skill that helps users **run the project**, not just describe it.

Focus on:
- What the project does (one line → description, tool_name in snake_case)
- **repository_url**: the canonical ``https://github.com/owner/repo`` URL if inferable from context; else null
- **reference_url**: arXiv / DOI / project paper link if the README mentions one; else null
- **parameters**: CLI flags or config knobs the README documents for the main entrypoint (if none, use a minimal placeholder param or empty list only if truly no CLI)
- **implementation_notes** (critical): Markdown with ``## Prerequisites``, ``## Installation`` (copy exact commands from README: clone, pip/conda, env files), ``## How to run`` (main training/inference/demo commands as written), ``## Configuration`` (env vars, API keys, paths). Quote commands in fenced code blocks when possible.

Set **base_url** to null unless the README documents a **JSON HTTP API** base URL.

{json_schema}

README content:
{content}
"""

_GENERIC_TEMPLATE = """\
You are a tool metadata extractor. Given the following source content (type: {source_type}),
extract structured metadata about the tool/API described.

**implementation_notes:** Markdown with practical install/run steps when the source contains them; else a brief note on what is missing. ``repository_url`` if a repo URL appears.

{json_schema}

Source content:
{content}
"""

_ARXIV_TEMPLATE = """\
You are a scientific paper skill metadata extractor. Your goal is to extract deep,
actionable information so an AI agent can actually **run** the method described in the paper.

Given the following arXiv paper content (title, abstract, and full text), extract:

1. **tool_name** — snake_case name for the method/model (e.g. ``alphafold2``, ``bert_base``)
2. **description** — one-line summary of what the method does
3. **parameters** — the key *inputs* the method takes (e.g. sequence, smiles, image_path, checkpoint_path)
4. **implementation_notes** (critical) — Markdown with:
   - ``## Method Overview`` — the core algorithm/architecture in plain language (not the abstract)
   - ``## Key Hyperparameters`` — important hyperparameters and their typical values from the paper
   - ``## Input / Output`` — what the method takes as input and produces as output
   - ``## Prerequisites`` — Python version, GPU requirements, datasets, model weights/checkpoints
   - ``## Installation`` — git clone, pip/conda commands (from paper's supplementary or mentioned repo)
   - ``## How to run`` — training, inference, or evaluation commands as given in the paper
   - ``## Datasets & Checkpoints`` — named datasets and where to download checkpoints if mentioned
   - ``## Limitations`` — known limitations or things not automated by this skill
5. **repository_url** — GitHub/GitLab URL if mentioned in the paper; else ``null``
6. **reference_url** — the arXiv abs URL for this paper

Focus on the **Methods section** and **supplementary** content for concrete algorithmic detail.
Do not just paraphrase the abstract — extract what someone would need to actually reproduce the work.

Output rules: respond with ONLY the JSON object — no markdown code fences, no commentary.

{json_schema}

Paper content:
{content}
"""

_TEMPLATES = {
    "openapi": _OPENAPI_TEMPLATE,
    "pypi": _PYPI_TEMPLATE,
    "doi": _DOI_TEMPLATE,
    "cli": _CLI_TEMPLATE,
    "github": _GITHUB_TEMPLATE,
    "arxiv": _ARXIV_TEMPLATE,
}


def get_prompt(source_type: str, content: str) -> str:
    """Return the extraction prompt for *source_type* with *content* embedded."""
    json_schema = _JSON_SCHEMA.format(source_type=source_type)
    template = _TEMPLATES.get(source_type, _GENERIC_TEMPLATE)
    return template.format(
        source_type=source_type,
        json_schema=json_schema,
        content=content,
    )
