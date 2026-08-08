"""`GET /scores` and `POST /sequence` — the text-notation MVP endpoints.

These are the original endpoints the current frontend page renders from.
They stay at their unprefixed URLs so nothing breaks; `data/example-scores.json`
is the seed of the future library (Epic 10) and `/sequence` remains the text
notation entry point reused by the Playground Input tab (Epic 6).
"""

import json

from fastapi import APIRouter, HTTPException

from aitu_backend.matrix.text_notation import sequence_to_score
from aitu_backend.schemas.score import MatrixScore, SequenceRequest
from aitu_backend.storage.paths import scores_json_path

router = APIRouter(tags=["scores"])


@router.get(
    "/scores",
    response_model=list[MatrixScore],
    response_model_by_alias=True,
    response_model_exclude_none=True,
)
def list_scores() -> list[MatrixScore]:
    """Scores persisted by the notebook at `data/example-scores.json`."""
    path = scores_json_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Scores file missing: run `notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` "
                "or create data/example-scores.json"
            ),
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise HTTPException(
            status_code=500,
            detail=f"Expected a JSON array of scores in {path}",
        )
    try:
        return [MatrixScore.model_validate(item) for item in raw]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Score validation failed: {exc}") from exc


@router.post(
    "/sequence",
    response_model=MatrixScore,
    response_model_by_alias=True,
    response_model_exclude_none=True,
)
def build_sequence(request: SequenceRequest) -> MatrixScore:
    """Convert a written time-frame sequence into a sparse 88-key score.

    Lets a caller render an arbitrary passage: it sends the sequence notation
    plus how long one frame lasts, and gets back the same payload shape as
    `/scores` so the renderer is reused unchanged.
    """
    try:
        payload = sequence_to_score(
            sequence=request.sequence,
            frame_ms=request.frame_ms,
            title=request.title,
            lyrics=request.lyrics,
            key_signature=request.key_signature,
            left_sequence=request.left_sequence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MatrixScore.model_validate(payload)
