"""Fetch and extract text from an arbitrary webpage."""
from __future__ import annotations
import re
import requests
from scientia.strategies.base import StrategyError


def _strip_html(html: str) -> str:
    # Remove scripts and styles
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all other tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_webpage(url: str, timeout: int = 30) -> str:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 Scientia/1.0"},
        )
        resp.raise_for_status()
        return _strip_html(resp.text)
    except requests.RequestException as exc:
        raise StrategyError(f"Failed to fetch webpage {url!r}: {exc}") from exc
