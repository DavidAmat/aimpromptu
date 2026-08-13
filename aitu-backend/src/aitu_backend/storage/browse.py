"""Computed fields the Piano Library lists need, filled at read time.

Whether a rhythm exists and whether a piece is flagged ``needsRederivation`` live
on the audio folder, not in ``metadata_track.json``. Writing them there would
drift the moment someone named a gap or re-transcribed. The list endpoints peek
``metadata.json`` (never the ``.npz``) for the audio uuid and ask the pipeline.

Old ``v2_gn`` folders are omitted, not guessed at: ``parse_version_folder``
already refuses them, and a list that invented a clock for them would be worse
than hiding them.
"""

from __future__ import annotations

from pydantic import Field

from aitu_backend.schemas.metadata import (
    LibraryTrackMetadata,
    Promotion,
    TrackMetadata,
    VersionHistoryEntry,
)
from aitu_backend.schemas.naming import is_version_folder
from aitu_backend.storage import repository
from aitu_backend.transcription import pipeline


class PlaygroundVersionEntry(VersionHistoryEntry):
    """One playground version on the library page."""

    audio_uuid: str | None = Field(None, alias="audioUuid")
    needs_rederivation: str | None = Field(None, alias="needsRederivation")


class PlaygroundTrackEntry(TrackMetadata):
    """A playground track with live flags the stored metadata does not carry."""

    versions: list[PlaygroundVersionEntry] = Field(default_factory=list)  # type: ignore[assignment]
    needs_rederivation: str | None = Field(None, alias="needsRederivation")


class PromotionEntry(Promotion):
    """One promotion, plus whether that version can be played from."""

    audio_uuid: str | None = Field(None, alias="audioUuid")
    has_saved_rhythm: bool = Field(False, alias="hasSavedRhythm")
    needs_rederivation: str | None = Field(None, alias="needsRederivation")


class LibraryTrackEntry(LibraryTrackMetadata):
    """A library track as the browse page sees it."""

    promotions: list[PromotionEntry] = Field(default_factory=list)  # type: ignore[assignment]
    has_saved_rhythm: bool = Field(False, alias="hasSavedRhythm")
    needs_rederivation: str | None = Field(None, alias="needsRederivation")


def playground_entry(track: TrackMetadata) -> PlaygroundTrackEntry:
    """Drop unparseable version folders and attach live audio flags."""
    versions = [
        _playground_version(track.artist_slug, track.track_slug, entry)
        for entry in track.versions
        if is_version_folder(entry.folder)
    ]
    flagged = next((item.needs_rederivation for item in versions if item.needs_rederivation), None)
    return PlaygroundTrackEntry(
        **track.model_dump(exclude={"versions"}),
        versions=versions,
        needs_rederivation=flagged,
    )


def library_entry(track: LibraryTrackMetadata) -> LibraryTrackEntry:
    """Attach rhythm and rederivation flags without writing them to disk."""
    promotions = [_promotion_entry(item) for item in track.promotions]
    visible = [item for item in promotions if item.active] or promotions
    flagged = next((item.needs_rederivation for item in visible if item.needs_rederivation), None)
    return LibraryTrackEntry(
        **track.model_dump(exclude={"promotions"}),
        promotions=promotions,
        has_saved_rhythm=any(item.has_saved_rhythm for item in visible),
        needs_rederivation=flagged,
    )


def _playground_version(
    artist_slug: str, track_slug: str, entry: VersionHistoryEntry
) -> PlaygroundVersionEntry:
    meta = repository.peek_version_metadata(artist_slug, track_slug, entry.folder)
    audio_uuid = meta.audio.audio_uuid if meta is not None and meta.audio is not None else None
    return PlaygroundVersionEntry(
        **entry.model_dump(),
        audio_uuid=audio_uuid,
        needs_rederivation=pipeline.needs_rederivation(audio_uuid) if audio_uuid else None,
    )


def _promotion_entry(promotion: Promotion) -> PromotionEntry:
    audio_uuid = _audio_uuid(promotion)
    return PromotionEntry(
        **promotion.model_dump(),
        audio_uuid=audio_uuid,
        has_saved_rhythm=pipeline.load_rhythm(audio_uuid) is not None if audio_uuid else False,
        needs_rederivation=pipeline.needs_rederivation(audio_uuid) if audio_uuid else None,
    )


def _audio_uuid(promotion: Promotion) -> str | None:
    meta = promotion.version_metadata
    if meta is None or meta.audio is None:
        return None
    return meta.audio.audio_uuid
