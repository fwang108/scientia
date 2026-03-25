"""Source-type fetch strategies for Scientia."""
from scientia.strategies.base import StrategyError


def fetch_source(source: str, source_type: str = "text") -> str:
    """Dispatch to the appropriate strategy based on *source_type*.

    Falls back to returning *source* unchanged for 'text' or unknown types.
    """
    if source_type == "text":
        return source
    if source_type == "openapi":
        from scientia.strategies.openapi import fetch_openapi
        return fetch_openapi(source)
    if source_type == "github":
        from scientia.strategies.github import fetch_github
        return fetch_github(source)
    if source_type == "doi":
        from scientia.strategies.doi import fetch_doi
        return fetch_doi(source)
    if source_type == "pypi":
        from scientia.strategies.pypi import fetch_pypi
        return fetch_pypi(source)
    if source_type == "webpage":
        from scientia.strategies.webpage import fetch_webpage
        return fetch_webpage(source)
    if source_type == "cli":
        from scientia.strategies.cli import fetch_cli
        return fetch_cli(source)
    if source_type == "pdf":
        from scientia.strategies.pdf import fetch_pdf_source
        return fetch_pdf_source(source)
    if source_type == "arxiv":
        from scientia.strategies.arxiv import fetch_arxiv
        return fetch_arxiv(source)
    # Unknown type — treat as plain text
    return source


__all__ = ["fetch_source", "StrategyError"]
