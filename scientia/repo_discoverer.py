"""Discover code repositories associated with a scientific paper."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

_GITHUB_URL_RE = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+")


@dataclass
class RepoCandidate:
    url: str
    source: str
    confidence: float = 0.5


def extract_repos_from_text(text: str) -> list[RepoCandidate]:
    """Extract GitHub repository URLs from free text (e.g. paper body)."""
    matches = _GITHUB_URL_RE.findall(text)
    # Normalise: strip trailing punctuation, deduplicate preserving order
    seen: set[str] = set()
    results: list[RepoCandidate] = []
    for url in matches:
        url = url.rstrip(".,;)")
        if url not in seen:
            seen.add(url)
            results.append(RepoCandidate(url=url, source="pdf_links", confidence=0.7))
    return results


def query_papers_with_code(arxiv_id: str) -> list[RepoCandidate]:
    """Query the Papers With Code API for repositories linked to *arxiv_id*."""
    base = "https://paperswithcode.com/api/v1"
    try:
        # Search for the paper
        papers_resp = requests.get(
            f"{base}/papers/",
            params={"arxiv_id": arxiv_id},
            timeout=15,
        )
        papers_resp.raise_for_status()
        papers_data = papers_resp.json()
        results_list = papers_data.get("results", [])
        if not results_list:
            return []

        paper_id = results_list[0]["id"]

        # Fetch repos for that paper
        repos_resp = requests.get(
            f"{base}/papers/{paper_id}/repositories/",
            timeout=15,
        )
        repos_resp.raise_for_status()
        repos_data = repos_resp.json()
        repo_results = repos_data.get("results", [])
        if not repo_results:
            return []

        candidates = []
        for repo in repo_results:
            url = repo.get("url", "")
            if url:
                stars = repo.get("stars", 0) or 0
                # Confidence scaled by stars (capped at 0.95)
                confidence = min(0.5 + stars / 10_000, 0.95)
                candidates.append(RepoCandidate(url=url, source="pwc", confidence=confidence))
        return candidates

    except Exception:
        return []


def discover_repo(
    arxiv_id: str,
    paper_text: str = "",
    title: str = "",
) -> list[RepoCandidate]:
    """Combine multiple sources to discover repos; return sorted by confidence desc."""
    pwc = query_papers_with_code(arxiv_id)
    text_hits = extract_repos_from_text(paper_text) if paper_text else []

    # Merge, deduplicating by URL (keep highest confidence)
    by_url: dict[str, RepoCandidate] = {}
    for c in pwc + text_hits:
        existing = by_url.get(c.url)
        if existing is None or c.confidence > existing.confidence:
            by_url[c.url] = c

    return sorted(by_url.values(), key=lambda c: c.confidence, reverse=True)
