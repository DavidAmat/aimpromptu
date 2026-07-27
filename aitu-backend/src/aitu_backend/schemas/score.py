"""API payloads aligned with `MatrixScore` in aitu-frontend."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SparseMatrix(BaseModel):
    """Binary matrix in COO form, sorted by (column, row).

    Only active cells travel: `rows[i]`/`cols[i]` mark cell value 1, every
    other cell is 0. `shape` is `[rowCount, columnCount]` (rowCount is 88).

    `onset[i]` disambiguates a held note from repeated strikes: it equals
    `rows[i]` when the cell is a struck onset, or `-1` when the cell is a
    sustain (the note keeps sounding without being struck again).
    """

    format: Literal["binary-coo"] = "binary-coo"
    shape: list[int]
    rows: list[int]
    cols: list[int]
    onset: list[int]


class MatrixScore(BaseModel):
    """Sparse 88-key score plus rendering metadata for the notation app.

    `rows` (the row index -> note-name table) is intentionally optional: the
    88-key grand-piano order is canonical and the frontend rebuilds it, so it
    no longer needs to ship in every payload.

    Hands. A score is either **one hand** — `matrix` only, rendered on a
    single treble clef — or **two hands** — `r_matrix` (right hand, treble)
    plus `l_matrix` (left hand, always bass clef), rendered as a grand staff.
    The two are mutually exclusive, and the two-hand matrices must span the
    same number of time frames so the hands stay vertically aligned.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    tempo_bpm: float = Field(..., alias="tempoBpm")
    time_step_seconds: float = Field(..., alias="timeStepSeconds")
    rows: list[str] | None = None
    matrix_encoding: str = Field("sparse-coo", alias="matrixEncoding")
    matrix: SparseMatrix | None = None
    r_matrix: SparseMatrix | None = None
    l_matrix: SparseMatrix | None = None
    lyrics: list[str] | None = None
    key_signature: str | None = Field(None, alias="keySignature")

    @model_validator(mode="after")
    def _check_hands(self) -> "MatrixScore":
        right, left = self.r_matrix, self.l_matrix
        one_hand = self.matrix is not None
        two_hand = right is not None and left is not None
        if one_hand == two_hand:
            raise ValueError(
                "Provide either `matrix` (one hand) or both `r_matrix` and "
                "`l_matrix` (two hands), never both or neither."
            )
        if right is not None and left is not None:
            r_cols = right.shape[1]
            l_cols = left.shape[1]
            if r_cols != l_cols:
                raise ValueError(
                    "r_matrix and l_matrix must span the same number of time "
                    f"frames so the hands align (got {r_cols} vs {l_cols})."
                )
        return self


class SequenceRequest(BaseModel):
    """Request body for `POST /sequence`.

    `sequence` is one entry per time frame. `||` separates simultaneous
    notes; an empty string is a silent frame. Example::

        ["Do-3 || Mi-3", "Re-3", "", "Mi-4", "Fa#-5"]

    `left_sequence` is optional. When omitted the score is one hand
    (treble only). When given, `sequence` is the right hand (treble) and
    `left_sequence` is the left hand (bass clef); both must have the same
    number of time frames so the hands stay aligned.
    """

    model_config = ConfigDict(populate_by_name=True)

    sequence: list[str]
    tempo_bpm: float = Field(..., alias="tempoBpm")
    time_step_seconds: float = Field(..., alias="timeStepSeconds")
    title: str | None = None
    lyrics: list[str] | None = None
    key_signature: str | None = Field(None, alias="keySignature")
    left_sequence: list[str] | None = Field(None, alias="leftSequence")
