"""`/notation` — matrix to VexFlow-ready score document (Epic 9)."""

from typing import Any

from fastapi import APIRouter

from aitu_backend.api._placeholders import not_implemented

router = APIRouter(prefix="/notation", tags=["notation"])

_EPIC = "Epic 9 (Music notation)"


@router.get("/{artifact_id}")
def get_score_document(artifact_id: str) -> dict[str, Any]:
    """Pre-generated score format (measures, voices, durations, annotations)."""
    raise not_implemented(_EPIC, "the VexFlow score format builder")


@router.post("/{artifact_id}/annotations")
def save_annotations(artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist the annotation overlay (lyrics, fingers, keys, ornaments)."""
    raise not_implemented(_EPIC, "annotation persistence")


@router.post("/{artifact_id}/preview")
def preview_range(artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Render-only preview of a column range (transposition, key changes)."""
    raise not_implemented(_EPIC, "short-range render preview")
