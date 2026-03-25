"""Source type detection for Scientia."""
from __future__ import annotations
import re


def detect_source_type(source: str) -> str:
    """Return the source type string for *source*.

    Priority order (first match wins):
      openapi → github → doi → pdf → pypi → cli → webpage → text
    """
    s = source.strip()

    # OpenAPI / Swagger
    if re.search(r"(openapi|swagger)\.(json|yaml|yml)(\?.*)?$", s, re.IGNORECASE):
        return "openapi"

    # GitHub
    if re.search(r"(github\.com|raw\.githubusercontent\.com)", s, re.IGNORECASE):
        return "github"

    # arXiv — must come before generic DOI check
    if re.search(r"arxiv\.org/(abs|pdf)/", s, re.IGNORECASE):
        return "arxiv"

    # DOI / preprint servers
    if re.search(
        r"(doi\.org|pubmed\.ncbi\.nlm\.nih\.gov|biorxiv\.org|medrxiv\.org|arxiv\.org)",
        s,
        re.IGNORECASE,
    ):
        return "doi"

    # PDF (URL ending .pdf or local path ending .pdf)
    if re.search(r"\.pdf(\?.*)?$", s, re.IGNORECASE):
        return "pdf"

    # PyPI
    if s.startswith("pypi:") or re.search(r"pypi\.org/project/", s, re.IGNORECASE):
        return "pypi"

    # CLI binary / explicit prefix
    if s.startswith("cli:") or re.match(r"^/[^\s]+$", s):
        return "cli"

    # Generic HTTP(S) URL → webpage
    if re.match(r"https?://", s, re.IGNORECASE):
        return "webpage"

    # Everything else → plain text description
    return "text"
