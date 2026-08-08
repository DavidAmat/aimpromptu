"""Metadata contracts: slugs, folder codes, and fixture round-trips.

The fixtures in `tests/fixtures/` are committed samples of every metadata file
the storage layer writes. If a model changes shape, these fail — which is the
point: they are the contract every epic writes against.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from aitu_backend.schemas.matrix import Hand, MatrixProcessingStep
from aitu_backend.schemas.metadata import (
    AudioMetadata,
    AudioSource,
    LibraryTrackMetadata,
    PlaylistMetadata,
    TrackMetadata,
    VersionMetadata,
)
from aitu_backend.schemas.naming import (
    frame_code,
    frame_from_code,
    matrix_filename,
    next_version,
    parse_version_folder,
    slugify,
    version_folder,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------- naming


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Avicii", "avicii"),
        ("Levels", "levels"),
        ("Clair de Lune", "clair-de-lune"),
        ("Beyoncé", "beyonce"),
        ("  Für Elise!!  ", "fur-elise"),
        ("AC/DC", "ac-dc"),
        ("Symphony No. 5", "symphony-no-5"),
    ],
)
def test_slugify(value: str, expected: str) -> None:
    assert slugify(value) == expected


def test_slugify_rejects_an_unnameable_value() -> None:
    with pytest.raises(ValueError):
        slugify("...")


def test_frame_codes_round_trip() -> None:
    """A folder suffix is a length of wall clock now, not a note figure (P4.4)."""
    for frame_ms in (10, 20, 40, 100):
        assert frame_from_code(frame_code(frame_ms)) == frame_ms
    assert frame_code(40) == "f40"
    assert frame_code(20) == "f20"
    # A fractional frame keeps its digits, with the point replaced: a dot in a
    # folder name invites a reader to treat what follows as an extension.
    assert frame_code(12.5) == "f12_5"
    assert frame_from_code("f12_5") == 12.5


def test_a_frame_code_must_be_a_frame_code() -> None:
    with pytest.raises(ValueError, match="not a frame code"):
        frame_from_code("gsc")
    with pytest.raises(ValueError, match="positive"):
        frame_code(0)


def test_version_folder_round_trip() -> None:
    assert version_folder(2, 40) == "v2_f40"
    assert parse_version_folder("v2_f40") == (2, 40.0)
    assert parse_version_folder("v11_f20") == (11, 20.0)
    assert parse_version_folder("v1_f12_5") == (1, 12.5)


def test_a_folder_written_under_the_old_scheme_is_not_readable() -> None:
    """`v2_gn` meant "version 2 at negra granularity", which no longer means anything.

    It is refused rather than guessed at, and `next_version` skips it, so a stray
    old folder cannot block a save or be silently reinterpreted.
    """
    with pytest.raises(ValueError, match="not a version folder name"):
        parse_version_folder("v2_gn")
    assert next_version(["v2_gn", "v1_f40"]) == 2


@pytest.mark.parametrize("folder", ["v0_gn", "gn_v2", "v2-gn", "v2_", "notes"])
def test_bad_version_folders_are_rejected(folder: str) -> None:
    with pytest.raises(ValueError):
        parse_version_folder(folder)


def test_version_numbers_start_at_one() -> None:
    with pytest.raises(ValueError):
        version_folder(0, 40)


def test_next_version_ignores_junk_folders() -> None:
    assert next_version([]) == 1
    assert next_version(["v1_f40", "v3_f20", "scratch", "v2_gn"]) == 4


def test_matrix_filename() -> None:
    assert matrix_filename(1, 40) == "piano_matrix_v1_f40.npz"
    assert matrix_filename(1, 40, "left") == "piano_matrix_v1_f40_left.npz"


# ---------------------------------------------------------------- fixtures


def test_version_metadata_fixture_round_trips() -> None:
    raw = load("metadata.json")
    model = VersionMetadata.model_validate(raw)

    assert model.version == 2
    assert model.frame_ms == 40
    assert model.matrix_processing_step is MatrixProcessingStep.TWO_HANDS
    assert model.folder == "v2_f40"
    assert model.parent_matrix is not None
    assert model.parent_matrix.version_folder == "v1_f40"
    assert model.audio is not None
    assert model.audio.time_range is not None
    assert model.audio.time_range.duration_seconds == pytest.approx(35.75)
    assert model.created_at == datetime(2026, 7, 20, 9, 14, tzinfo=timezone.utc)

    annotations = model.annotations
    assert not annotations.is_empty()
    assert annotations.lyrics[0].text == "Ho"
    assert annotations.lyrics[0].anchor.hand is Hand.RIGHT
    assert annotations.fingers[0].finger == 1
    assert annotations.fingers[0].anchor.rows == [39]
    assert annotations.passages[0].kind == "tuplet"
    assert annotations.passages[0].options == {"ratio": [3, 2]}
    assert annotations.key_changes[0].key_signature == "D"

    assert VersionMetadata.model_validate(model.model_dump(by_alias=True, mode="json")) == model


def test_track_metadata_fixture_round_trips() -> None:
    model = TrackMetadata.model_validate(load("metadata_track.json"))

    assert (model.artist_slug, model.track_slug) == ("avicii", "levels")
    assert model.version_folders() == ["v1_f40", "v2_f40"]
    latest = model.latest()
    assert latest is not None
    assert latest.folder == "v2_f40"
    assert latest.parent_version == "v1_f40"
    assert next_version(model.version_folders()) == 3

    assert TrackMetadata.model_validate(model.model_dump(by_alias=True, mode="json")) == model


def test_library_track_fixture_round_trips() -> None:
    model = LibraryTrackMetadata.model_validate(load("metadata_library_track.json"))

    assert model.tags == ["edm", "easy", "practice"]
    assert len(model.promotions) == 2
    assert len(model.active_promotions()) == 2
    chill = model.find_promotion("Levels (Chill) - Avicii")
    assert chill is not None
    assert chill.source_version_folder == "v2_f40"
    # The promoted version's metadata is embedded, so the entry is self-contained.
    assert chill.version_metadata is not None
    assert chill.version_metadata.frame_ms == 40
    assert model.rollback_to == "Levels (Chill) - Avicii"

    assert (
        LibraryTrackMetadata.model_validate(model.model_dump(by_alias=True, mode="json")) == model
    )


def test_audio_metadata_fixture_round_trips() -> None:
    model = AudioMetadata.model_validate(load("metadata_audio.json"))

    assert model.source is AudioSource.YOUTUBE
    assert model.format == "mp3"
    assert model.duration_seconds == pytest.approx(187.4)
    assert AudioMetadata.model_validate(model.model_dump(by_alias=True, mode="json")) == model


def test_playlist_fixture_round_trips() -> None:
    model = PlaylistMetadata.model_validate(load("metadata_library_playlist.json"))

    assert model.slug == "sunday-practice"
    assert [item.promotion_name for item in model.items] == [
        "Levels (Chill) - Avicii",
        "Levels (Full speed) - Avicii",
    ]
    assert PlaylistMetadata.model_validate(model.model_dump(by_alias=True, mode="json")) == model


# -------------------------------------------------------------- validation


def test_time_range_must_move_forward() -> None:
    raw = load("metadata.json")
    raw["audio"]["timeRange"] = {"startSeconds": 30, "endSeconds": 10}
    with pytest.raises(ValidationError, match="endSeconds must be after"):
        VersionMetadata.model_validate(raw)


def test_column_range_must_move_forward() -> None:
    raw = load("metadata.json")
    raw["annotations"]["lyrics"][0]["anchor"]["columns"] = {"fromColumn": 9, "toColumn": 4}
    with pytest.raises(ValidationError, match="toColumn must be greater"):
        VersionMetadata.model_validate(raw)


def test_finger_numbers_are_limited_to_one_through_five() -> None:
    raw = load("metadata.json")
    raw["annotations"]["fingers"][0]["finger"] = 6
    with pytest.raises(ValidationError):
        VersionMetadata.model_validate(raw)


def test_annotations_default_to_empty() -> None:
    model = VersionMetadata(
        version=1,
        matrix_processing_step=MatrixProcessingStep.RAW,
    )
    assert model.annotations.is_empty()
    assert model.folder == "v1_f40"
