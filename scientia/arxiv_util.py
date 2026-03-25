"""arXiv Atom API helpers (export.arxiv.org) — used by generated DOI skills."""
from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import requests


_ARXIV_ABS_URL_RE = re.compile(
    r"https?://arxiv\.org/abs/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.I,
)


def extract_first_arxiv_abs_url(text: str) -> str | None:
    """Return the first canonical arXiv abs URL found in *text* (README, etc.), or ``None``."""
    if not text:
        return None
    m = _ARXIV_ABS_URL_RE.search(text)
    if not m:
        return None
    return f"https://arxiv.org/abs/{m.group('id')}"


def normalize_github_repo_url(url: str) -> str | None:
    """Extract canonical ``https://github.com/owner/repo`` from a GitHub URL, or ``None``."""
    if not url or not isinstance(url, str):
        return None
    m = re.search(r"https?://github\.com/([^/\s#?]+)/([^/\s#?]+)", url.strip())
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).rstrip("/")
    return f"https://github.com/{owner}/{repo}"


def suggested_git_clone_command(repo_url: str) -> str:
    """Return a typical ``git clone`` line for a GitHub HTTPS repo URL."""
    u = (repo_url or "").strip().rstrip("/")
    if not u:
        return "git clone <repository-url>"
    if u.endswith(".git"):
        return f"git clone {u}"
    return f"git clone {u}.git"


def arxiv_id_from_url(url: str) -> str | None:
    """Extract arXiv id (e.g. ``2510.08191``) from an abs or PDF URL."""
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    # New-style: 1234.56789
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", u, re.I)
    if m:
        return m.group(1)
    # Legacy: math/1234567 or cs.AI/1234
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([a-z.-]+/\d{7})(?:v\d+)?", u, re.I)
    if m:
        return m.group(1)
    return None


def _localname(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_arxiv_atom_xml(content: bytes) -> dict[str, Any]:
    """Parse arXiv Atom API XML into a plain dict."""
    root = ET.fromstring(content)
    entry_el = None
    for el in root.iter():
        if _localname(el.tag) == "entry":
            entry_el = el
            break
    if entry_el is None:
        return {}

    title = summary = published = arxiv_id = None
    authors: list[str] = []
    links: dict[str, str] = {}

    for child in entry_el:
        ln = _localname(child.tag)
        text = (child.text or "").strip()
        if ln == "title" and text:
            title = text
        elif ln == "summary" and text:
            summary = text
        elif ln == "published" and text:
            published = text
        elif ln == "id" and text:
            arxiv_id = text
        elif ln == "link":
            href = child.attrib.get("href")
            rel = child.attrib.get("rel", "alternate")
            title_attr = child.attrib.get("title", "")
            if href:
                if "pdf" in title_attr.lower() or rel == "related":
                    links["pdf"] = href
                elif rel == "alternate" or not links.get("html"):
                    links["html"] = href
        elif ln == "author":
            for sub in child.iter():
                if _localname(sub.tag) == "name" and sub.text:
                    authors.append(sub.text.strip())
                    break

    return {
        "title": title,
        "summary": summary,
        "published": published,
        "atom_id": arxiv_id,
        "authors": authors,
        "links": links,
    }


def fetch_arxiv_metadata(arxiv_id: str, *, timeout: int = 60) -> dict[str, Any]:
    """Fetch one entry from ``export.arxiv.org/api/query``."""
    arxiv_id = arxiv_id.strip()
    if not arxiv_id:
        raise ValueError("empty arxiv_id")

    query = urllib.parse.urlencode({"id_list": arxiv_id, "max_results": 1})
    url = f"http://export.arxiv.org/api/query?{query}"
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Scientia/1.0 (arxiv skill client; +https://github.com)"},
    )
    resp.raise_for_status()
    meta = parse_arxiv_atom_xml(resp.content)
    if not meta.get("title"):
        raise ValueError(f"No arXiv entry found for id_list={arxiv_id!r}")
    meta["arxiv_id"] = arxiv_id
    meta["query_url"] = url
    return meta
