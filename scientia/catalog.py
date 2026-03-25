"""JSON catalog export/import for the Scientia skill registry."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from scientia.models import SkillRecord
from scientia.registry import Registry


def _record_to_dict(rec: SkillRecord) -> Dict[str, Any]:
    return {
        "skill_id": rec.skill_id,
        "tool_name": rec.tool_name,
        "source": rec.source,
        "source_type": rec.source_type,
        "skill_dir": rec.skill_dir,
        "verification_status": rec.verification_status,
        "retry_count": rec.retry_count,
        "sample_output": rec.sample_output,
        "generated_at": rec.generated_at,
        "last_verified_at": rec.last_verified_at,
        "quality_score": rec.quality_score,
        "tags": rec.tags,
    }


def _dict_to_record(d: Dict[str, Any]) -> SkillRecord:
    return SkillRecord(
        skill_id=d.get("skill_id", ""),
        tool_name=d["tool_name"],
        source=d["source"],
        source_type=d["source_type"],
        skill_dir=d["skill_dir"],
        verification_status=d["verification_status"],
        retry_count=d.get("retry_count", 0),
        sample_output=d.get("sample_output"),
        generated_at=d["generated_at"],
        last_verified_at=d.get("last_verified_at"),
        quality_score=d.get("quality_score"),
        tags=d.get("tags", []),
    )


def export_catalog(registry: Registry) -> List[Dict[str, Any]]:
    """Return all registry records as a list of dicts."""
    return [_record_to_dict(r) for r in registry.list_all()]


def export_catalog_to_file(registry: Registry, path: Path) -> None:
    """Write catalog JSON to *path*."""
    data = export_catalog(registry)
    Path(path).write_text(json.dumps(data, indent=2))


def import_catalog(registry: Registry, catalog: List[Dict[str, Any]]) -> None:
    """Import records from a list of dicts into *registry*."""
    for item in catalog:
        registry.save(_dict_to_record(item))


def import_catalog_from_file(registry: Registry, path: Path) -> None:
    """Load catalog JSON from *path* and import into *registry*."""
    data = json.loads(Path(path).read_text())
    import_catalog(registry, data)
