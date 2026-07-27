"""Every metadata file the storage layer writes, as Pydantic models.

Four files, four models:

| File | Model | Lives in |
|------|-------|----------|
| ``metadata.json`` | :class:`VersionMetadata` | a ``vN_gX`` version folder |
| ``metadata_track.json`` | :class:`TrackMetadata` | a playground track folder |
| ``metadata_library_track.json`` | :class:`LibraryTrackMetadata` | a library track folder |
| ``metadata.json`` (audio) | :class:`AudioMetadata` | an ``audio/<uuid>`` folder |

Defined now, before any epic writes one, so every writer produces compatible
files. camelCase on the wire and on disk, matching the rest of the project.

Annotations are addressed by **matrix indices** (hand, column range, rows), never
by rendered position: they must survive a re-render, a transposition or a
responsive re-wrap.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aitu_backend.schemas.matrix import Granularity, Hand, MatrixProcessingStep
from aitu_backend.schemas.naming import version_folder


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CamelModel(BaseModel):
    """Base: camelCase aliases, populate by either name."""

    model_config = ConfigDict(populate_by_name=True)


# --------------------------------------------------------------------- source


class AudioSource(str, Enum):
    """How an audio file entered the store."""

    UPLOAD = "upload"
    RECORDING = "recording"
    YOUTUBE = "youtube"


class TimeRange(CamelModel):
    """A closed range of the source audio, in seconds."""

    start_seconds: float = Field(..., alias="startSeconds", ge=0)
    end_seconds: float = Field(..., alias="endSeconds", gt=0)

    @model_validator(mode="after")
    def _check_order(self) -> "TimeRange":
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"endSeconds must be after startSeconds ({self.end_seconds} <= {self.start_seconds})"
            )
        return self

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class AudioReference(CamelModel):
    """Which audio a matrix came from, and which slice of it."""

    audio_uuid: str = Field(..., alias="audioUuid")
    #: Omitted when the whole file was transcribed.
    time_range: TimeRange | None = Field(None, alias="timeRange")


class AudioMetadata(CamelModel):
    """``data/audio/<uuid>/metadata.json`` — Epic 3 writes it."""

    uuid: str
    #: Editable display name; defaults to the original file name.
    alias: str
    source: AudioSource
    #: Container/codec suffix without the dot, e.g. ``mp3``.
    format: str
    original_filename: str | None = Field(None, alias="originalFilename")
    duration_seconds: float | None = Field(None, alias="durationSeconds", ge=0)
    sample_rate: int | None = Field(None, alias="sampleRate", gt=0)
    #: Source URL when `source` is `youtube`.
    source_url: str | None = Field(None, alias="sourceUrl")
    created_at: datetime = Field(default_factory=_now, alias="createdAt")


# ---------------------------------------------------------------- annotations


class ColumnRange(CamelModel):
    """Half-open column range ``[from, to)`` of a matrix."""

    from_column: int = Field(..., alias="fromColumn", ge=0)
    to_column: int = Field(..., alias="toColumn", gt=0)

    @model_validator(mode="after")
    def _check_order(self) -> "ColumnRange":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"toColumn must be greater than fromColumn ({self.to_column} <= {self.from_column})"
            )
        return self


class MatrixAnchor(CamelModel):
    """Where an annotation attaches: a hand, a column range, and optional rows."""

    hand: Hand = Hand.SINGLE
    columns: ColumnRange
    #: Matrix row indices the annotation applies to; empty = the whole range.
    rows: list[int] = Field(default_factory=list)


class LyricAnnotation(CamelModel):
    """One syllable or word over a column range (Epic 12, Story 12.1)."""

    anchor: MatrixAnchor
    text: str


class FingerAnnotation(CamelModel):
    """Finger number 1-5 on one note (Epic 12, Story 12.2)."""

    anchor: MatrixAnchor
    finger: int = Field(..., ge=1, le=5)


class PassageAnnotation(CamelModel):
    """A passage-scoped mark: cue-size notes, tuplets, trills, grace notes."""

    kind: Literal["cue-size", "tuplet", "trill", "acciaccatura", "appoggiatura"]
    anchor: MatrixAnchor
    #: Kind-specific payload, e.g. `{"ratio": [3, 2]}` for a tuplet.
    options: dict[str, Any] = Field(default_factory=dict)


class KeySignatureChange(CamelModel):
    """A key change starting at a column (Epic 9, Story 9.4)."""

    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: VexFlow key spec: `C`, `G`, `Bb`, …
    key_signature: str = Field(..., alias="keySignature")


class Annotations(CamelModel):
    """Overlay that never touches the matrix itself.

    Empty for now; Epics 9 and 12 fill it. Everything here is addressed by
    matrix indices so it survives re-rendering and re-wrapping.
    """

    lyrics: list[LyricAnnotation] = Field(default_factory=list)
    fingers: list[FingerAnnotation] = Field(default_factory=list)
    passages: list[PassageAnnotation] = Field(default_factory=list)
    key_changes: list[KeySignatureChange] = Field(default_factory=list, alias="keyChanges")

    def is_empty(self) -> bool:
        return not (self.lyrics or self.fingers or self.passages or self.key_changes)


# ------------------------------------------------------------------- versions


class ParentMatrix(CamelModel):
    """Pointer to the matrix a version was derived from.

    A collapsed matrix points at the raw one, a clean matrix at the collapsed
    one, and so on — which is what makes a sub-second recompute possible.
    """

    #: Version folder of the parent, e.g. ``v1_gf``. Absent for a first import.
    version_folder: str | None = Field(None, alias="versionFolder")
    matrix_processing_step: MatrixProcessingStep = Field(..., alias="matrixProcessingStep")
    #: Relative path of the parent `.npz`, when it lives in another folder.
    path: str | None = None


class VersionMetadata(CamelModel):
    """``metadata.json`` inside one ``vN_gX`` folder.

    Everything needed to re-render that saved matrix state, without reading the
    matrix itself.
    """

    version: int = Field(..., ge=1)
    tempo_bpm: float = Field(..., alias="tempoBpm", gt=0)
    granularity: Granularity
    matrix_processing_step: MatrixProcessingStep = Field(..., alias="matrixProcessingStep")
    time_step_seconds: float | None = Field(None, alias="timeStepSeconds", gt=0)

    parent_matrix: ParentMatrix | None = Field(None, alias="parentMatrix")
    audio: AudioReference | None = None
    key_signature: str | None = Field(None, alias="keySignature")

    annotations: Annotations = Field(default_factory=Annotations)
    comment: str | None = None
    created_at: datetime = Field(default_factory=_now, alias="createdAt")

    @property
    def folder(self) -> str:
        """The folder name this metadata belongs in, e.g. ``v2_gn``."""
        return version_folder(self.version, self.granularity)


class VersionHistoryEntry(CamelModel):
    """One line of a track's version history."""

    folder: str
    comment: str | None = None
    created_at: datetime = Field(default_factory=_now, alias="createdAt")
    #: Folder name of the version this one was branched from.
    parent_version: str | None = Field(None, alias="parentVersion")
    granularity: Granularity
    matrix_processing_step: MatrixProcessingStep = Field(..., alias="matrixProcessingStep")


class TrackMetadata(CamelModel):
    """``metadata_track.json`` — one per playground track folder."""

    artist_name: str = Field(..., alias="artistName")
    track_name: str = Field(..., alias="trackName")
    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    created_at: datetime = Field(default_factory=_now, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
    #: Newest last.
    versions: list[VersionHistoryEntry] = Field(default_factory=list)

    def latest(self) -> VersionHistoryEntry | None:
        return self.versions[-1] if self.versions else None

    def version_folders(self) -> list[str]:
        return [entry.folder for entry in self.versions]


# -------------------------------------------------------------------- library


class Promotion(CamelModel):
    """One promoted version inside the library.

    Several promotions can be live at once — the same piece in different
    arrangements — which is why this is a list, not a single pointer.
    """

    #: Human-facing name, e.g. "Levels (Chill) - Avicii".
    promotion_name: str = Field(..., alias="promotionName")
    #: Playground version folder this came from, e.g. ``v3_gsc``.
    source_version_folder: str = Field(..., alias="sourceVersionFolder")
    #: Matrix file inside the library track folder.
    matrix_filename: str = Field(..., alias="matrixFilename")
    promoted_at: datetime = Field(default_factory=_now, alias="promotedAt")
    #: Whether this promotion is currently visible in the library.
    active: bool = True
    #: Snapshot of the promoted version's `metadata.json`, so the library entry
    #: is self-contained even if the playground folder is later deleted.
    version_metadata: VersionMetadata | None = Field(None, alias="versionMetadata")


class LibraryTrackMetadata(CamelModel):
    """``metadata_library_track.json`` — one per library track folder."""

    artist_name: str = Field(..., alias="artistName")
    track_name: str = Field(..., alias="trackName")
    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    tags: list[str] = Field(default_factory=list)
    #: Full promotion history, newest last; several may be `active`.
    promotions: list[Promotion] = Field(default_factory=list)
    #: Promotion name to roll back to when the current one is rejected.
    rollback_to: str | None = Field(None, alias="rollbackTo")
    created_at: datetime = Field(default_factory=_now, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")

    def active_promotions(self) -> list[Promotion]:
        return [promotion for promotion in self.promotions if promotion.active]

    def find_promotion(self, name: str) -> Promotion | None:
        for promotion in reversed(self.promotions):
            if promotion.promotion_name == name:
                return promotion
        return None


class PlaylistItem(CamelModel):
    """One piece in a playlist, pinned to a promotion name."""

    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    promotion_name: str = Field(..., alias="promotionName")


class PlaylistMetadata(CamelModel):
    """``metadata_library_playlist.json`` — one per playlist folder."""

    name: str
    slug: str
    description: str | None = None
    #: Ordered; the playing mode's Next walks this list.
    items: list[PlaylistItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
