"""Fetch OpenAPI/Swagger spec from a URL."""
from __future__ import annotations
import requests
from scientia.strategies.base import StrategyError


def fetch_openapi(url: str, timeout: int = 30) -> str:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        raise StrategyError(f"Failed to fetch OpenAPI spec from {url!r}: {exc}") from exc
