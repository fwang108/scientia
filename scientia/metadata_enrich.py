"""Post-process :class:`ToolMetadata` after LLM extraction (deterministic hints)."""
from __future__ import annotations
from dataclasses import replace

from scientia.arxiv_util import extract_first_arxiv_abs_url, normalize_github_repo_url
from scientia.models import ToolMetadata
from scientia.strategies.doi import resolve_datacite_resource_url


def enrich_metadata(
    meta: ToolMetadata,
    source: str,
    source_type: str,
    content: str | None = None,
) -> ToolMetadata:
    """Fill missing fields from authoritative sources (e.g. DataCite landing URL for DOIs)."""
    if source_type == "doi":
        if not (meta.reference_url and str(meta.reference_url).strip()):
            url = resolve_datacite_resource_url(source)
            if url:
                return replace(meta, reference_url=url)
        return meta

    if source_type == "github":
        out = meta
        repo = normalize_github_repo_url(source)
        if repo and not (out.repository_url and str(out.repository_url).strip()):
            out = replace(out, repository_url=repo)
        if content and not (out.reference_url and str(out.reference_url).strip()):
            arx = extract_first_arxiv_abs_url(content)
            if arx:
                out = replace(out, reference_url=arx)
        return out

    # For any source type: scan content for a GitHub URL if repo not yet set
    if content and not (meta.repository_url and str(meta.repository_url).strip()):
        import re as _re
        gh_match = _re.search(r"https?://github\.com/[^\s/\"'<>]+/[^\s/\"'<>]+", content)
        if gh_match:
            repo = normalize_github_repo_url(gh_match.group(0))
            if repo:
                meta = replace(meta, repository_url=repo)

    return meta
