"""Fetch strategy for arXiv papers: Atom metadata + full PDF text extraction."""
from __future__ import annotations

import time

import requests

from scientia.arxiv_util import arxiv_id_from_url, fetch_arxiv_metadata
from scientia.strategies.base import StrategyError
from scientia.strategies.pdf import fetch_pdf

#: Maximum total content chars returned (keeps within LLM context window).
MAX_CONTENT_CHARS = 60_000

#: Polite delay between arXiv HTTP requests (seconds).
_ARXIV_DELAY = 3.0


def fetch_arxiv(url: str, *, delay: float = _ARXIV_DELAY) -> str:
    """Return a combined string of arXiv metadata + full paper text for *url*.

    Steps:
    1. Extract arXiv ID from URL.
    2. Fetch Atom metadata (title, abstract, authors, links).
    3. Download PDF and extract full text.
    4. Combine and truncate to MAX_CONTENT_CHARS.

    If PDF extraction fails, falls back gracefully to abstract only.
    """
    arxiv_id = arxiv_id_from_url(url)
    if not arxiv_id:
        raise StrategyError(f"Cannot extract arXiv ID from URL: {url!r}")

    # Step 2: Atom metadata
    meta = fetch_arxiv_metadata(arxiv_id)
    title = meta.get("title", "")
    abstract = meta.get("summary", "")
    authors = ", ".join(meta.get("authors", []))
    published = meta.get("published", "")
    pdf_link = meta.get("links", {}).get("pdf", f"https://arxiv.org/pdf/{arxiv_id}")

    header = (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Published: {published}\n"
        f"arXiv ID: {arxiv_id}\n"
        f"Abstract:\n{abstract}\n\n"
        f"--- Full Paper Text ---\n"
    )

    # Step 3: PDF full text
    time.sleep(delay)
    try:
        pdf_resp = requests.get(
            pdf_link,
            timeout=120,
            headers={"User-Agent": "Scientia/1.0 (arxiv full-text fetch)"},
        )
        pdf_resp.raise_for_status()
        full_text = fetch_pdf(pdf_resp.content)
    except StrategyError:
        full_text = "(PDF extraction failed — abstract only)"
    except Exception:
        full_text = "(PDF download failed — abstract only)"

    combined = header + full_text

    # Step 4: Truncate
    if len(combined) > MAX_CONTENT_CHARS:
        combined = combined[:MAX_CONTENT_CHARS]

    return combined
