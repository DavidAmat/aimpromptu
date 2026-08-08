"""`/library` — the playground repository and library promotion (Epics 5, 10)."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.api._placeholders import not_implemented
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import (
    MatrixProcessingStep,
    PianoMatrixEnvelope,
)
from aitu_backend.schemas.metadata import (
    AudioReference,
    LibraryTrackMetadata,
    TrackMetadata,
    VersionMetadata,
)
from aitu_backend.storage import promotion, repository
from aitu_backend.storage.promotion import (
    LibraryTrackNotFound,
    NothingToRollBackTo,
    PromotionNotFound,
)
from aitu_backend.storage.repository import TrackNotFound, VersionNotFound

router = APIRouter(prefix="/library", tags=["library"])

_PLAYLIST_EPIC = "Epic 10 (Piano Library), Story 10.3"


class SaveVersionRequest(BaseModel):
    """Body of `POST /library/playground`."""

    model_config = ConfigDict(populate_by_name=True)

    artist_name: str = Field(..., alias="artistName")
    track_name: str = Field(..., alias="trackName")
    #: The matrix to save, in the standard envelope.
    matrix: PianoMatrixEnvelope
    comment: str | None = None
    #: Rewrite the existing folder instead of creating a new version.
    overwrite: bool = False
    #: Pin the version number — how the same state is saved on a second grid.
    version: int | None = None
    #: Folder of the version this one was derived from.
    parent_version: str | None = Field(None, alias="parentVersion")
    audio_uuid: str | None = Field(None, alias="audioUuid")


class SavedVersion(BaseModel):
    """What a save returns."""

    model_config = ConfigDict(populate_by_name=True)

    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    folder: str
    metadata: VersionMetadata


class RenameTrackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    artist_name: str | None = Field(None, alias="artistName")
    track_name: str | None = Field(None, alias="trackName")


class PromoteRequest(BaseModel):
    """Body of `POST /library/promote` — the promotion dialog's fields."""

    model_config = ConfigDict(populate_by_name=True)

    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    version_folder: str = Field(..., alias="versionFolder")
    #: Defaults to "<Track> - <Artist>"; the dialog pre-fills and lets you edit it.
    promotion_name: str | None = Field(None, alias="promotionName")
    #: The dialog's "keep the current one too" checkbox.
    as_additional: bool = Field(False, alias="asAdditional")


class RollbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")


class TagsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    artist_slug: str = Field(..., alias="artistSlug")
    track_slug: str = Field(..., alias="trackSlug")
    tags: list[str] = Field(default_factory=list)


class PromotionSuggestion(BaseModel):
    """What the dialog shows before you confirm."""

    model_config = ConfigDict(populate_by_name=True)

    suggested_name: str = Field(..., alias="suggestedName")
    current_promotions: list[str] = Field(default_factory=list, alias="currentPromotions")


# ------------------------------------------------------------------ playground


@router.get("/playground", response_model=list[TrackMetadata], response_model_by_alias=True)
def list_playground_tracks(search: str | None = None) -> list[TrackMetadata]:
    """Every playground track with its version history.

    `search` matches the **real** artist and track names, never the slugs.
    """
    return repository.find_tracks(search) if search else repository.list_tracks()


@router.get(
    "/playground/{artist_slug}/{track_slug}",
    response_model=TrackMetadata,
    response_model_by_alias=True,
)
def get_playground_track(artist_slug: str, track_slug: str) -> TrackMetadata:
    try:
        return repository.read_track(artist_slug, track_slug)
    except TrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/playground/{artist_slug}/{track_slug}",
    response_model=TrackMetadata,
    response_model_by_alias=True,
)
def rename_playground_track(
    artist_slug: str, track_slug: str, body: RenameTrackRequest
) -> TrackMetadata:
    """Change the display names. Slugs and folders never move."""
    try:
        return repository.rename_track(
            artist_slug,
            track_slug,
            artist_name=body.artist_name,
            track_name=body.track_name,
        )
    except TrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/playground", response_model=SavedVersion, response_model_by_alias=True, status_code=201
)
def save_playground_version(request: SaveVersionRequest) -> SavedVersion:
    """Save a matrix as a new `vN_gX` version (or overwrite an existing one)."""
    matrix = PianoMatrix.from_envelope(request.matrix)

    parent = None
    if request.parent_version:
        try:
            source = repository.load_version(
                *_slugs(request.artist_name, request.track_name), request.parent_version
            )
            parent = repository.parent_pointer(source)
        except (TrackNotFound, VersionNotFound) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # A clean matrix is split once, here, and stored with its hand map. Doing it
    # at save time rather than at render time is what lets the notation, piano
    # roll and falling-note views read one decision instead of each inferring
    # their own — and keeps the saved folder self-contained.
    hands = split_hands(matrix) if matrix.processing_step is MatrixProcessingStep.CLEAN else None

    common = {
        "comment": request.comment,
        "overwrite": request.overwrite,
        "version": request.version,
        "parent": parent,
        "audio": AudioReference(audio_uuid=request.audio_uuid) if request.audio_uuid else None,
    }
    try:
        if hands is not None:
            saved = repository.save_two_hands(
                request.artist_name,
                request.track_name,
                hands.right,
                hands.left,
                single=matrix,
                hand_assignments=hands.to_metadata(),
                **common,
            )
        else:
            saved = repository.save_version(
                request.artist_name, request.track_name, matrix, **common  # type: ignore[arg-type]
            )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SavedVersion(
        artist_slug=saved.artist_slug,
        track_slug=saved.track_slug,
        folder=saved.folder,
        metadata=saved.metadata,
    )


@router.get(
    "/playground/{artist_slug}/{track_slug}/{folder}",
    response_model=PianoMatrixEnvelope,
    response_model_by_alias=True,
)
def load_playground_version(artist_slug: str, track_slug: str, folder: str) -> PianoMatrixEnvelope:
    """Read one saved version back."""
    try:
        loaded = repository.load_version(artist_slug, track_slug, folder)
    except (TrackNotFound, VersionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return loaded.matrix.to_envelope()


@router.delete("/playground/{artist_slug}/{track_slug}/{folder}")
def delete_playground_version(artist_slug: str, track_slug: str, folder: str) -> dict[str, str]:
    try:
        repository.delete_version(artist_slug, track_slug, folder)
    except (TrackNotFound, VersionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "folder": folder}


# ------------------------------------------------------------------- promotion


@router.get(
    "/promotion-suggestion/{artist_slug}/{track_slug}",
    response_model=PromotionSuggestion,
    response_model_by_alias=True,
)
def promotion_suggestion(artist_slug: str, track_slug: str) -> PromotionSuggestion:
    """Pre-fill the promotion dialog: a suggested name and what is already live."""
    try:
        playground = repository.read_track(artist_slug, track_slug)
    except TrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    current: list[str] = []
    if promotion.library_track_exists(artist_slug, track_slug):
        current = [
            item.promotion_name
            for item in promotion.read_library_track(artist_slug, track_slug).active_promotions()
        ]

    return PromotionSuggestion(
        suggested_name=promotion.default_promotion_name(
            playground.track_name, playground.artist_name
        ),
        current_promotions=current,
    )


@router.post("/promote", response_model=LibraryTrackMetadata, response_model_by_alias=True)
def promote_version(request: PromoteRequest) -> LibraryTrackMetadata:
    """Promote a playground version into the library."""
    try:
        result = promotion.promote(
            request.artist_slug,
            request.track_slug,
            request.version_folder,
            promotion_name=request.promotion_name,
            as_additional=request.as_additional,
        )
    except (TrackNotFound, VersionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.track


@router.post("/rollback", response_model=LibraryTrackMetadata, response_model_by_alias=True)
def rollback_promotion(request: RollbackRequest) -> LibraryTrackMetadata:
    """Restore the previously promoted version. Never deletes anything."""
    try:
        return promotion.rollback(request.artist_slug, request.track_slug).track
    except LibraryTrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PromotionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NothingToRollBackTo as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tracks", response_model=list[LibraryTrackMetadata], response_model_by_alias=True)
def list_library_tracks(
    tag: str | None = None, search: str | None = None
) -> list[LibraryTrackMetadata]:
    """Library tracks, filterable by tag and free-text name search."""
    return promotion.list_library_tracks(tag=tag, search=search)


@router.get(
    "/tracks/{artist_slug}/{track_slug}",
    response_model=LibraryTrackMetadata,
    response_model_by_alias=True,
)
def get_library_track(artist_slug: str, track_slug: str) -> LibraryTrackMetadata:
    try:
        return promotion.read_library_track(artist_slug, track_slug)
    except LibraryTrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tags", response_model=LibraryTrackMetadata, response_model_by_alias=True)
def set_tags(request: TagsRequest) -> LibraryTrackMetadata:
    """Replace a library track's tags."""
    try:
        return promotion.set_tags(request.artist_slug, request.track_slug, request.tags)
    except LibraryTrackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/playlists")
def list_playlists() -> list[dict[str, Any]]:
    """Playlists with their ordered pieces and selected version names."""
    raise not_implemented(_PLAYLIST_EPIC, "playlists")


def _slugs(artist_name: str, track_name: str) -> tuple[str, str]:
    from aitu_backend.schemas.naming import slugify  # noqa: PLC0415

    return slugify(artist_name), slugify(track_name)


__all__ = ["router", "MatrixProcessingStep"]
