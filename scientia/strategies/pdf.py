"""Extract text from PDF bytes or from a local path / https URL."""
from __future__ import annotations
import io
from pathlib import Path

import requests
from scientia.strategies.base import StrategyError


def load_pdf_bytes(source: str, timeout: int = 120) -> bytes:
    """Load raw PDF bytes from a URL or filesystem path."""
    s = source.strip()
    if s.startswith(("http://", "https://")):
        resp = requests.get(
            s,
            timeout=timeout,
            headers={"User-Agent": "Scientia/1.0 (arxiv/pdf fetch)"},
        )
        resp.raise_for_status()
        return resp.content
    path = Path(s).expanduser()
    if not path.is_file():
        raise StrategyError(f"PDF path does not exist or is not a file: {path}")
    return path.read_bytes()


def _extract_text(pdf_bytes: bytes) -> str:
    import pypdf  # optional dependency

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def fetch_pdf(pdf_bytes: bytes) -> str:
    try:
        return _extract_text(pdf_bytes)
    except Exception as exc:
        raise StrategyError(f"Failed to extract text from PDF: {exc}") from exc


def fetch_pdf_source(source: str, timeout: int = 120) -> str:
    """Download or read *source* (URL or path), then extract text."""
    return fetch_pdf(load_pdf_bytes(source, timeout=timeout))
