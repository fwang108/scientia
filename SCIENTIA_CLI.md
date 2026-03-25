# Scientia CLI — Skill Creation Guide

Scientia turns any external tool description into a verified, installed ScienceClaw skill.
You point it at a source (an OpenAPI spec, a GitHub repo, a PyPI package, a webpage, a PDF, or
plain text), it fetches the content, uses an LLM to extract the tool's interface, generates a
Python client script, runs it, and registers the result.

### Agent runtimes (Anthropic, OpenAI, and similar)

Generated skills are **meant to be passed into agent products and harnesses** (e.g. Anthropic’s agent/skill flows, OpenAI-style assistants or tool-calling pipelines, Claude Code / Codex-style repos that load folder-based skills):

- **`SKILL.md`** — instructions and context for the model: what the capability is, parameters, example invocations, links, and how to run the underlying method when that was extracted.
- **`scripts/<tool>_client.py`** — a stable CLI with **valid JSON on stdout** so the runtime can parse results without ad-hoc scraping.
- **`scripts/USAGE.md`** — operator-oriented steps (install, run commands) the agent or human can follow.

How you **mount** the folder (zip upload, git submodule, MCP, or a custom tool definition) depends on the vendor; Scientia standardizes the **contents** so the same skill can be wired once and reused across those stacks.

---

## Installation

```bash
git clone <repository-url>
cd scientia
pip install -e .
```

Confirm it works:

```bash
scientia --help
```

---

## Quick start — add your first skill

```bash
scientia add "https://raw.githubusercontent.com/some-org/some-tool/main/openapi.json" \
    --source-type openapi
```

That one command:
1. Fetches the OpenAPI spec
2. Extracts the tool name, description, endpoints, and parameters via LLM
3. Generates `~/.scientia/skills/<tool_name>/scripts/<tool_name>_client.py`
4. Runs the script to verify it produces valid JSON
5. Saves a registry entry to `~/.scientia/registry.db`

---

## Commands

### `scientia add` — create and install a skill

```
scientia add SOURCE [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--source-type` | `text` | One of: `openapi`, `github`, `doi`, `pypi`, `webpage`, `cli`, `pdf`, `text` |
| `--skills-root` | `~/.scientia/skills` | Where to write generated skill files |
| `--db` | `~/.scientia/registry.db` | Path to the registry SQLite database |

**Source type guide:**

| Type | What to pass as SOURCE | Best for |
|---|---|---|
| `openapi` | URL or file path to a JSON/YAML OpenAPI spec | REST APIs with a machine-readable spec |
| `github` | GitHub repo URL (`https://github.com/org/repo`) | Tools with a README and CLI interface |
| `pypi` | Package name (`rdkit`, `biopython`) | Python library wrappers |
| `doi` | DOI string (`10.1038/s41586-...`) | Turning a paper's method into a tool |
| `webpage` | Any URL | Documentation pages, tool homepages |
| `pdf` | File path to a PDF | Papers, technical manuals |
| `cli` | Shell command string (`blastn --help`) | Local CLI tools |
| `text` | Free-form description (quoted string) | Anything else |

**Examples:**

```bash
# From an OpenAPI spec URL
scientia add "https://api.ncbi.nlm.nih.gov/datasets/openapi.yaml" --source-type openapi

# From a GitHub repo
scientia add "https://github.com/deepmind/alphafold" --source-type github

# From a PyPI package
scientia add "biopython" --source-type pypi

# From a DOI (paper method)
scientia add "10.1093/bioinformatics/bty315" --source-type doi

# From a local PDF
scientia add "./rosetta_manual.pdf" --source-type pdf

# From a local CLI tool
scientia add "hmmbuild --help" --source-type cli

# Free-text description
scientia add "A tool that queries the UniProt REST API for a given accession and
returns the protein's name, organism, sequence length, and GO terms." --source-type text

# Custom install location (e.g. a monorepo skills tree)
scientia add "biopython" --source-type pypi \
    --skills-root ./scienceclaw/skills \
    --db ./scienceclaw/registry.db
```

---

### `scientia list` — show installed skills

```bash
scientia list
```

Prints all skills in the registry with their verification status and source type:

```
blast_search                   verified    openapi
uniprot_lookup                 verified    pypi
alphafold_predict              failed      github
```

Use a custom database:

```bash
scientia list --db /path/to/registry.db
```

---

### `scientia info` — inspect a skill

```bash
scientia info TOOL_NAME
```

Shows full details for one skill:

```
Tool:    blast_search
Source:  https://api.ncbi.nlm.nih.gov/blast/openapi.yaml
Type:    openapi
Status:  verified
Retries: 0
Dir:     ~/.scientia/skills/blast_search
Sample:  {"results": [{"accession": "NP_001346897.1", "score": 412, ...}]}
```

---

### `scientia search` — filter skills

```bash
scientia search [OPTIONS]
```

| Option | Description |
|---|---|
| `--tag TAG` | Only skills tagged with TAG |
| `--min-score N` | Only skills with quality score ≥ N (0–100) |
| `--verified-only` | Only skills that passed verification |
| `--db PATH` | Custom registry database |

**Examples:**

```bash
# All verified skills
scientia search --verified-only

# Biology tools with quality score ≥ 70
scientia search --tag biology --min-score 70

# Everything tagged "chemistry"
scientia search --tag chemistry
```

Output format:

```
blast_search                   verified    score= 88  [biology,sequence]
pubchem_lookup                 verified    score= 75  [chemistry,openapi]
alphafold_predict              failed      score=  -  [biology]
```

---

### `scientia build-recipe` — chain skills into a pipeline

A **recipe** is a JSON file that describes an ordered sequence of skill invocations.
`build-recipe` turns it into a single runnable Python script.

```bash
scientia build-recipe RECIPE_FILE [--output OUTPUT_SCRIPT]
```

| Argument/Option | Description |
|---|---|
| `RECIPE_FILE` | Path to a recipe JSON file |
| `--output`, `-o` | Where to write the generated script (default: `<name>.py`) |

**Recipe JSON format:**

```json
{
    "name": "protein_admet_pipeline",
    "description": "Search PubMed for a target, get the protein from UniProt, predict ADMET properties.",
    "steps": [
        {
            "skill": "pubmed_search",
            "args": {
                "query": "BACE1 inhibitor",
                "max_results": 5
            }
        },
        {
            "skill": "uniprot_lookup",
            "args": {
                "accession": "P56817"
            }
        },
        {
            "skill": "tdc_predict",
            "args": {
                "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "model": "BBB_Martins-AttentiveFP"
            }
        }
    ],
    "output": "tdc_predict"
}
```

Fields:

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Identifier for the pipeline (used as default output filename) |
| `description` | Yes | Human-readable description |
| `steps` | Yes | List of steps; each must have a `skill` key |
| `steps[].skill` | Yes | Tool name (must match an installed skill) |
| `steps[].args` | No | Key-value pairs passed as CLI flags to the skill script |
| `output` | No | Which step's result to surface as the final return value |

**Example:**

```bash
# Save the recipe
cat > protein_pipeline.json << 'EOF'
{
    "name": "protein_pipeline",
    "description": "Fetch protein data and predict properties.",
    "steps": [
        {"skill": "uniprot_lookup", "args": {"accession": "P56817"}},
        {"skill": "tdc_predict", "args": {"smiles": "CC1=CC=CC=C1", "model": "BBB_Martins-AttentiveFP"}}
    ]
}
EOF

# Build the composite script
scientia build-recipe protein_pipeline.json --output pipeline.py

# Run it
python pipeline.py
```

The generated script runs each step in order using `subprocess`, passes the
specified args as CLI flags, parses each step's JSON output, and returns a
dict of all results (or just the `output` step if specified).

---

### `scientia push-clawhub` — publish a skill to [ClawHub](https://clawhub.ai)

Publishes an installed skill folder using the **ClawHub CLI** (same layout: `SKILL.md` + `scripts/`).
Scientia shells out to `clawhub publish`; you must install and authenticate the Node CLI first.

**Setup:**

```bash
npm i -g clawhub
clawhub login
```

**Usage:**

```
scientia push-clawhub [TOOL_NAME] [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--skill-path` | — | Skill directory containing `SKILL.md` (bypasses registry lookup) |
| `--slug` | folder name | ClawHub slug |
| `--name` | — | Display name on ClawHub |
| `--version` | `1.0.0` | Semver (**required** by ClawHub; bump for updates) |
| `--changelog` | `""` | Release notes |
| `--tags` | `latest` | Comma-separated tags |
| `--fork-of` | — | Parent skill `slug` or `slug@version` |
| `--db` | `~/.scientia/registry.db` | Scientia registry (used with `TOOL_NAME`) |
| `--dry-run` | — | Print the `clawhub` command without running it |

**Examples:**

```bash
# Publish skill registered as `dreams` (uses Dir: from scientia info)
scientia push-clawhub dreams --version 1.0.0 --changelog "Initial publish from Scientia"

# Custom slug / title
scientia push-clawhub dreams --slug dreams-dft --name "DREAMS DFT agent" --version 1.0.0

# Explicit folder (no registry row needed)
scientia push-clawhub --skill-path ~/.scientia/skills/dreams --version 1.0.0

# Preview the command
scientia push-clawhub dreams --version 1.0.0 --dry-run
```

If `clawhub` is not on your `PATH`, install the npm package globally or use `clawdhub` (same binary).

---

## Typical workflow

### 1. Install a new tool from a spec

```bash
scientia add "https://pubchem.ncbi.nlm.nih.gov/rest/pug/openapi.yaml" \
    --source-type openapi \
    --skills-root ./scienceclaw/skills
```

### 2. Verify it installed correctly

```bash
scientia info pubchem_search
```

### 3. Test it directly

```bash
python ~/.scientia/skills/pubchem_search/scripts/pubchem_search_client.py \
    --query "aspirin"
```

### 4. Browse what you have

```bash
scientia search --verified-only --min-score 60
```

### 5. Build a multi-step pipeline

```bash
scientia build-recipe my_pipeline.json -o run_pipeline.py
python run_pipeline.py
```

### 6. (Optional) Publish to ClawHub

```bash
scientia push-clawhub my_tool --version 1.0.0 --changelog "Scientia-generated skill"
```

---

## File layout after install

```
~/.scientia/
├── registry.db                    # SQLite registry of all skills
└── skills/
    └── <tool_name>/
        ├── SKILL.md               # Human-readable tool documentation
        └── scripts/
            └── <tool_name>_client.py   # Generated client (argparse + JSON stdout)
```

The generated script always:
- Uses `argparse` for CLI flags
- Prints a single JSON object to stdout
- Exits 0 on success, non-zero on failure

This makes every skill directly chainable in bash or via `build-recipe`.

---

## Environment variables

| Variable | Description |
|---|---|
| `SCIENTIA_AUTO_EXPAND=true` | Automatically expand NeedsSignals from ScienceClaw agents when a `suggested_source` is present |
| `ANTHROPIC_API_KEY` | Required — used by the LLM extractor |

---

## Troubleshooting

**"Error: no skill named X found"**
The skill wasn't registered. Re-run `scientia add` or check that `--skills-root` and `--db` point to the same location you used during install.

**Skill installed but verification failed**
```bash
scientia info <tool_name>   # check retry count and sample output
```
The script was still saved. You can edit it manually at the path shown in `Dir:` and re-run to test.

**LLM returns invalid JSON**
The extractor retries up to 3 times automatically. If it fails, try a more specific `--source-type` or pass a cleaner source (e.g. the raw OpenAPI JSON rather than an HTML docs page).

**Script runs but output is not valid JSON**
Scientia's verifier checks for valid JSON output. Make sure the tool's API returns structured data. For tools that only return plain text, use `--source-type text` and the generator will wrap the output.
