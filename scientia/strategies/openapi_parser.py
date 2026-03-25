"""OpenAPI spec pre-parser — converts raw JSON/YAML spec into a structured ParsedSpec."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Param:
    name: str
    required: bool
    param_in: str = "query"  # path, query, header, cookie
    type: str = "string"
    description: str = ""


@dataclass
class Endpoint:
    path: str
    method: str
    summary: str = ""
    parameters: List[Param] = field(default_factory=list)


@dataclass
class ParsedSpec:
    base_url: str
    title: str
    endpoints: List[Endpoint] = field(default_factory=list)

    def to_context_string(self) -> str:
        lines = [f"API: {self.title}", f"Base URL: {self.base_url}", ""]
        for ep in self.endpoints:
            lines.append(f"{ep.method.upper()} {ep.path}")
            if ep.summary:
                lines.append(f"  {ep.summary}")
            for p in ep.parameters:
                req = "required" if p.required else "optional"
                lines.append(f"  - {p.name} ({p.type}, {req}, in {p.param_in}): {p.description}")
        return "\n".join(lines)


def parse_openapi_spec(raw: str) -> Optional[ParsedSpec]:
    """Parse a raw OpenAPI 2.0/3.0 JSON or YAML string into a ParsedSpec.

    Returns None if the input cannot be parsed as a valid spec.
    """
    spec = _load(raw)
    if spec is None:
        return None

    base_url = _extract_base_url(spec)
    if base_url is None:
        return None

    title = spec.get("info", {}).get("title", "")
    endpoints = _extract_endpoints(spec)

    return ParsedSpec(base_url=base_url, title=title, endpoints=endpoints)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load(raw: str) -> Optional[dict]:
    """Try JSON then YAML; return None on failure."""
    # JSON first (fast path)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # YAML fallback
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return None


def _extract_base_url(spec: dict) -> Optional[str]:
    """Extract base URL for OpenAPI 3.x (servers) or 2.0 (host+basePath+schemes)."""
    # OpenAPI 3.x
    servers = spec.get("servers")
    if servers and isinstance(servers, list) and servers[0].get("url"):
        return servers[0]["url"].rstrip("/")

    # OpenAPI 2.0
    if "host" in spec:
        host = spec["host"]
        base_path = spec.get("basePath", "")
        schemes = spec.get("schemes", ["https"])
        scheme = schemes[0] if schemes else "https"
        return f"{scheme}://{host}{base_path}".rstrip("/")

    return None


def _extract_endpoints(spec: dict) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(operation, dict):
                continue
            params = _extract_params(operation.get("parameters", []))
            ep = Endpoint(
                path=path,
                method=method.lower(),
                summary=operation.get("summary", ""),
                parameters=params,
            )
            endpoints.append(ep)
    return endpoints


def _extract_params(raw_params: list) -> List[Param]:
    params: List[Param] = []
    for p in raw_params:
        if not isinstance(p, dict) or "name" not in p:
            continue
        # OpenAPI 3.x: type under schema; OpenAPI 2.0: type directly
        schema = p.get("schema", {}) or {}
        ptype = schema.get("type") or p.get("type", "string")
        params.append(Param(
            name=p["name"],
            required=bool(p.get("required", False)),
            param_in=p.get("in", "query"),
            type=ptype,
            description=p.get("description", ""),
        ))
    return params
