"""Fetch package metadata from PyPI."""
from __future__ import annotations
import requests
from scientia.strategies.base import StrategyError

_PYPI_URL = "https://pypi.org/pypi/{package}/json"


def fetch_pypi(package: str, timeout: int = 30) -> str:
    package = package.strip().lstrip("pypi:")
    url = _PYPI_URL.format(package=package)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        info = resp.json().get("info", {})
    except requests.RequestException as exc:
        raise StrategyError(f"Failed to fetch PyPI package {package!r}: {exc}") from exc

    parts = [
        f"Package: {info.get('name', package)}",
        f"Version: {info.get('version', 'unknown')}",
        f"Summary: {info.get('summary', '')}",
    ]
    description = info.get("description", "")
    if description:
        parts.append(f"Description:\n{description[:3000]}")

    project_urls = info.get("project_urls") or {}
    if project_urls:
        urls_text = ", ".join(f"{k}: {v}" for k, v in list(project_urls.items())[:3])
        parts.append(f"Links: {urls_text}")

    return "\n".join(parts)
