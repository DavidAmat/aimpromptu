"""FastAPI entrypoint for serving generated matrix scores."""

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from aitu_backend.paths import scores_json_path
from aitu_backend.schemas import MatrixScore, SequenceRequest
from aitu_backend.sequence import sequence_to_score

app = FastAPI(
    title="AImpromptu Backend API",
    description="Serves sparse-COO piano scores for the aitu-frontend renderer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
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


@app.post(
    "/sequence",
    response_model=MatrixScore,
    response_model_by_alias=True,
    response_model_exclude_none=True,
)
def build_sequence(request: SequenceRequest) -> MatrixScore:
    """Convert a written time-frame sequence into a sparse 88-key score.

    Lets the frontend render an arbitrary passage: it sends the sequence
    notation plus tempo/time-step, and gets back the same payload shape as
    `/scores` so the renderer is reused unchanged.
    """
    try:
        payload = sequence_to_score(
            sequence=request.sequence,
            tempo_bpm=request.tempo_bpm,
            time_step_seconds=request.time_step_seconds,
            title=request.title,
            lyrics=request.lyrics,
            key_signature=request.key_signature,
            left_sequence=request.left_sequence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MatrixScore.model_validate(payload)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "aitu_backend.main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
    )


if __name__ == "__main__":
    run()
