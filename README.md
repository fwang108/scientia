<p align="center">
  <img src="outputs/scientia.png" alt="Scientia cover" width="880">
</p>

# Scientia

Turn scientific sources (OpenAPI specs, papers/DOIs, PyPI packages, GitHub repos, PDFs, web pages, CLIs, or plain text) into **skill folders** you can **hand to an LLM agent**—the same shape used by **ScienceClaw** and familiar from **Anthropic**- and **OpenAI**-style agent setups: a `SKILL.md` the model reads for instructions, a `scripts/*_client.py` entrypoint that prints **JSON on stdout** (easy for a harness to parse), plus `scripts/USAGE.md` for operational detail and a local registry entry.

Agents do not need to guess the interface: parameters, examples, and limitations are spelled out in prose and flags so you can map them to **tool / function** definitions or let the agent shell out to the client script.

### Skills as operational documentation

The goal is that each skill carries **what people need to use the method**, not only a JSON façade:

- **`SKILL.md`** — description, links (paper, repo), parameters, and a **“How to run the method (from the source)”** section filled from LLM extraction when the source allows it (install steps, commands, prerequisites). Maintainers can edit this section if extraction was thin.
- **`scripts/USAGE.md`** — the same operational notes in the `scripts/` folder for agents and humans who look there first.
- **`scripts/<tool>_client.py`** — structured JSON for agent harnesses; you can extend it to call upstream CLIs with `subprocess` once the commands in `USAGE.md` are validated.

Extraction prompts ask for **`implementation_notes`** (Markdown) and, for **GitHub**, use a dedicated template so README install/run lines are pulled into the skill. Scientia is the **repo that generates those artifacts**; correctness of commands still depends on the upstream source and human review.

### What “running” the client means

Verifying **`scientia add`** only checks: **exit 0 + valid JSON on stdout**. That is enough for agents and pipelines, but it is **not** proof that a paper, product, or GitHub project is actually invoked.

| Source | Typical reality |
|--------|------------------|
| **OpenAPI** with real `servers` | Generated client can hit a **real HTTP API** once the base URL is correct. |
| **GitHub** (`--source-type github`) | Fetches the repo **README**. Scientia sets **`repository_url`** and, if the README links an **arXiv abs URL**, fills **`reference_url`** automatically. The client runs in **`github_repo_dossier`** mode: JSON includes a **suggested `git clone`** plus optional **arXiv Atom metadata** for the paper. **You** still clone the repo and follow its README to execute code—Scientia wires the skill to the repo + paper, not a substitute for `pip install` / training. |
| **DOI / PDF / webpage / text** | Often **no API**; the client is a **stub** (`execution: cli_stub_only`) with plausible flags. **Exception:** if the resolved **reference URL** is **arXiv** (`arxiv.org/abs/...`), the client can **fetch live Atom metadata** (title, abstract, authors) from `export.arxiv.org` (`execution: arxiv_atom_api`)—still not the paper’s code, but real HTTP output. Otherwise **you** wire code or an endpoint. |
| **PyPI** today | Metadata from package/README; same HTTP-shaped client unless you extend it. |

So something like **BioReason** from a paper will **not** “really run” after `scientia add` unless **you** add a real URL, wrap published code, or swap in `subprocess`/`import`. **If the authors ship a GitHub repo**, prefer `scientia add <https://github.com/owner/repo> --source-type github` so the skill carries **`repository_url`** and can auto-link an **arXiv** URL from the README. The generated JSON states limitations explicitly—re-run `scientia add` or regenerate skills to get the updated text.

## Install

```bash
cd /path/to/Scientia
pip install -e .
scientia --help
```

Set `ANTHROPIC_API_KEY` for LLM-powered extraction (`scientia add`).

## Documentation

Full command reference, source types, recipes, troubleshooting: **[SCIENTIA_CLI.md](SCIENTIA_CLI.md)**.

## Publish to ClawHub

Skills are normal folders with `SKILL.md`. To upload one to [ClawHub](https://clawhub.ai):

```bash
npm i -g clawhub
clawhub login
scientia push-clawhub YOUR_TOOL_NAME --version 1.0.0 --changelog "Notes here"
```

See the **`scientia push-clawhub`** section in [SCIENTIA_CLI.md](SCIENTIA_CLI.md) for `--skill-path`, `--slug`, `--dry-run`, and other options.

## Repo layout

- `src/` — core code (`src/scientia`)
- `runs/` — experiments
- `data/` — raw/processed data
- `notebooks/` — exploratory work
- `outputs/` — figures/results (includes `outputs/scientia.png`)
- `paper/` — optional manuscript assets
