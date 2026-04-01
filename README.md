<p align="center">
  <h1 align="center">Scientia</h1>
  <div align="center" style="font-size: 1.15em; margin-bottom: 10px;">
    <strong>
      Skill anything scientific—papers, APIs, repos, packages—into agent-ready folders for
      <a href="https://github.com/lamm-mit/scienceclaw/tree/main" target="_blank" style="text-decoration: underline;">
        ScienceClaw
      </a>
      and beyond.
    </strong>
  </div>
  <img src="scientia.png" alt="Scientia cover" width="880">
</p>

**One pipeline, many sources.** Point Scientia at an OpenAPI spec, a DOI or PDF, a PyPI name, a GitHub URL, a web page, a CLI, or plain text—**out comes a skill folder** your LLM can actually use: the same layout as **ScienceClaw** and the usual **Anthropic** / **OpenAI** agent pattern—`SKILL.md` for the model, `scripts/<tool>_client.py` that prints **JSON on stdout** for harnesses, `scripts/USAGE.md` for humans who peek under the hood, plus a local registry entry.

No guessing the interface: parameters, examples, and caveats live in prose and flags so you map them to **tools / functions** or shell straight to the client.

### Skills that teach, not just wrap

Each artifact is meant to carry **how to run the real method**, not a hollow JSON shell:

- **`SKILL.md`** — story, links (paper, repo), parameters, and **“How to run the method (from the source)”** when extraction can fill it (install, commands, prerequisites). Thin extraction? Edit this section by hand.
- **`scripts/USAGE.md`** — the same operational notes beside the code.
- **`scripts/<tool>_client.py`** — structured JSON for harnesses; extend with `subprocess` or imports once `USAGE.md` commands are validated.

Extraction asks for **`implementation_notes`** (Markdown). GitHub sources use a dedicated template so README install/run lines land in the skill. Scientia **generates** these files; command correctness still rides on upstream docs and your review.

### What “it runs” really means

`scientia add` verification is deliberately minimal: **exit 0 + valid JSON on stdout**. Great for agents and CI—**not** a guarantee that a paper’s code or a vendor API fired for real.

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

## License

Apache-2.0. See `LICENSE`.

## Publish to ClawHub

Skills are normal folders with `SKILL.md`. Ship one to [ClawHub](https://clawhub.ai):

```bash
npm i -g clawhub
clawhub login
scientia push-clawhub YOUR_TOOL_NAME --version 1.0.0 --changelog "Notes here"
```

See the **`scientia push-clawhub`** section in [SCIENTIA_CLI.md](SCIENTIA_CLI.md) for `--skill-path`, `--slug`, `--dry-run`, and other options.
