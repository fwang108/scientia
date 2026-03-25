"""Fetch README from a GitHub repository."""
from __future__ import annotations
import re
import requests
from scientia.strategies.base import StrategyError

_RAW_TEMPLATE = "https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"


def fetch_github(url: str, timeout: int = 30) -> str:
    match = re.search(r"github\.com/([^/]+)/([^/\s]+)", url)
    if not match:
        raise StrategyError(f"Cannot parse GitHub URL: {url!r}")

    owner, repo = match.group(1), match.group(2).rstrip("/")
    raw_url = _RAW_TEMPLATE.format(owner=owner, repo=repo)

    try:
        resp = requests.get(raw_url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        raise StrategyError(f"Failed to fetch README from {raw_url!r}: {exc}") from exc
