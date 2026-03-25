"""Fetch paper metadata via Crossref, with DataCite fallback (e.g. arXiv DOIs)."""
from __future__ import annotations
import re
import urllib.parse

import requests
from scientia.strategies.base import StrategyError

_CROSSREF_URL = "https://api.crossref.org/works/{doi}"
_DATACITE_URL = "https://api.datacite.org/dois/{doi}"


def _crossref_payload(doi: str, timeout: int) -> dict | None:
    """Return Crossref *message* dict, or None if not found."""
    enc = urllib.parse.quote(doi, safe="")
    url = _CROSSREF_URL.format(doi=enc)
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Scientia/1.0"})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json().get("message", {})


def _datacite_payload(doi: str, timeout: int) -> dict:
    enc = urllib.parse.quote(doi, safe="")
    url = _DATACITE_URL.format(doi=enc)
    resp = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Scientia/1.0",
            "Accept": "application/vnd.api+json",
        },
    )
    resp.raise_for_status()
    return resp.json()


def _text_from_crossref(data: dict) -> str:
    parts = []
    titles = data.get("title", [])
    if titles:
        parts.append(f"Title: {titles[0]}")

    abstracts = data.get("abstract", [])
    if abstracts:
        parts.append(f"Abstract: {abstracts[0]}")

    authors = data.get("author", [])
    if authors:
        names = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors[:5]
        )
        parts.append(f"Authors: {names}")

    container = data.get("container-title", [])
    if container:
        parts.append(f"Journal: {container[0]}")

    landing = data.get("URL")
    if landing:
        parts.append(f"Primary resource / landing page URL: {landing}")

    return "\n".join(parts)


def _text_from_datacite(payload: dict) -> str:
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}
    parts = []
    titles = attrs.get("titles") or []
    if titles and titles[0].get("title"):
        parts.append(f"Title: {titles[0]['title']}")

    for desc in attrs.get("descriptions") or []:
        text = desc.get("description")
        if text:
            label = desc.get("descriptionType") or "Description"
            parts.append(f"{label}: {text}")

    creators = attrs.get("creators") or []
    if creators:
        names = ", ".join(
            c.get("name", "").strip()
            for c in creators[:8]
            if c.get("name")
        )
        if names:
            parts.append(f"Authors: {names}")

    publisher = attrs.get("publisher")
    if publisher:
        parts.append(f"Publisher: {publisher}")

    landing = attrs.get("url")
    if landing:
        parts.append(f"Primary resource / landing page URL: {landing}")

    for rel in attrs.get("relatedIdentifiers") or []:
        rid = (rel.get("relatedIdentifier") or "").strip()
        rtype = (rel.get("relatedIdentifierType") or "").strip()
        relation = (rel.get("relationType") or "").strip()
        if rid and rtype.upper() == "URL":
            parts.append(f"Related URL ({relation or 'related'}): {rid}")

    return "\n".join(parts)


def normalize_doi_from_source(source: str) -> str | None:
    """Extract a DOI string from a free-form *source* (URL, ``doi:…``, or bare DOI)."""
    s = (source or "").strip()
    if not s:
        return None
    m = re.search(r"(?i)doi\.org/([^\s\]>]+)", s)
    if m:
        return m.group(1).rstrip(".,;)")
    m = re.search(r"(?i)\bdoi:\s*([^\s\]>]+)", s)
    if m:
        return m.group(1).rstrip(".,;)")
    m = re.search(r"\b(10\.\d{4,9}/[^\s\]>]+)\b", s)
    if m:
        return m.group(1).rstrip(".,;)")
    return None


def resolve_datacite_resource_url(source: str, timeout: int = 30) -> str | None:
    """Return DataCite ``attributes.url`` (e.g. arXiv abs link) for *source*, if any."""
    doi = normalize_doi_from_source(source)
    if not doi:
        return None
    try:
        payload = _datacite_payload(doi, timeout)
        attrs = payload.get("data", {}).get("attributes", {})
        u = attrs.get("url")
        return str(u).strip() if u else None
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None


def fetch_doi(doi_source: str, timeout: int = 30) -> str:
    doi = normalize_doi_from_source(doi_source)
    if not doi:
        doi = doi_source.strip().lstrip("https://doi.org/").lstrip("doi:")

    try:
        crossref = _crossref_payload(doi, timeout)
        if crossref:
            text = _text_from_crossref(crossref)
            if text:
                return text
    except requests.RequestException:
        pass  # fall through to DataCite

    try:
        payload = _datacite_payload(doi, timeout)
        text = _text_from_datacite(payload)
        if text:
            return text
    except requests.RequestException as exc:
        raise StrategyError(f"Failed to fetch DOI {doi!r}: {exc}") from exc

    raise StrategyError(
        f"Failed to fetch DOI {doi!r}: no metadata from Crossref or DataCite"
    )
