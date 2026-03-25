"""Quality scorer for generated skill scripts.

score_skill()  -> int 0-100 composite quality score
infer_tags()   -> list[str] domain tags for a skill
"""
from __future__ import annotations

from scientia.models import VerificationResult

# ---------------------------------------------------------------------------
# Domain keyword maps for tag inference
# ---------------------------------------------------------------------------
_DOMAIN_KEYWORDS: list[tuple[list[str], str]] = [
    (["pubmed", "ncbi", "medline", "pmc", "entrez"], "literature"),
    (["pubmed", "ncbi", "bio", "blast", "uniprot", "pdb", "genbank", "ensembl", "gene"], "biology"),
    (["pubchem", "chembl", "rdkit", "smiles", "chebi", "cheminformatics", "molecule"], "chemistry"),
    (["materials", "mp_api", "crystallography", "band_gap", "vasp"], "materials_science"),
    (["tdc", "admet", "bbb", "toxicity", "drug"], "drug_discovery"),
    (["arxiv", "crossref", "doi", "semantic_scholar", "paper"], "research"),
    (["alphafold", "protein", "sequence", "fasta", "amino"], "structural_biology"),
]

_SOURCE_TAGS: dict[str, list[str]] = {
    "openapi": ["openapi"],
    "pypi": ["python", "pypi"],
    "doi": ["research", "doi"],
    "cli": ["cli"],
    "html": ["web"],
    "text": [],
}


def score_skill(
    verification_result: VerificationResult,
    script: str,
    source_type: str,
) -> int:
    """Return a 0-100 quality score for a skill.

    Components:
    - Verification pass (hard gate): 0 if failed
    - JSON output validity: +30
    - Retry penalty: -10 per retry (max -30)
    - Script length (richness proxy): up to +20
    - Base score: 50 if passes all basic checks
    """
    if not verification_result.passed:
        return 0

    score = 50  # base for passing

    # JSON output
    if verification_result.is_valid_json:
        score += 30

    # Retry penalty
    penalty = min(verification_result.retry_count * 10, 30)
    score -= penalty

    # Script richness (lines of non-blank, non-comment code)
    code_lines = [
        ln for ln in script.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    richness = min(len(code_lines), 20)  # cap at 20 lines → +20
    score += richness

    return max(0, min(100, score))


def infer_tags(source_type: str, tool_name: str, script: str) -> list[str]:
    """Infer domain tags from source_type, tool_name, and script content."""
    tags: set[str] = set()

    # Source-type tags
    for tag in _SOURCE_TAGS.get(source_type, []):
        tags.add(tag)

    # HTTP client tag
    if "requests" in script or "httpx" in script or "urllib" in script:
        tags.add("rest_api")

    # Domain tags from tool name
    tool_lower = tool_name.lower()
    for keywords, domain_tag in _DOMAIN_KEYWORDS:
        for kw in keywords:
            if kw in tool_lower:
                tags.add(domain_tag)
                break

    return sorted(tags)
