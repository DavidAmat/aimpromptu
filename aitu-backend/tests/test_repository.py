"""The playground repository and library promotion.

The scenario tests mirror the `avicii/levels` tree from `project-features.md`.
"""

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.matrix.granularity import collapse_to
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.storage import paths, promotion, repository
from aitu_backend.storage.promotion import (
    LibraryTrackNotFound,
    NothingToRollBackTo,
    default_promotion_name,
)
from aitu_backend.storage.repository import TrackNotFound, VersionNotFound

DO4 = note_to_row("Do-4")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def matrix(
    granularity: Granularity = Granularity.SEMICORCHEA,
    frames: int = 8,
    step: MatrixProcessingStep = MatrixProcessingStep.CLEAN,
) -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    grid[DO4, 0] = 1
    grid[DO4, 1] = -1
    grid[note_to_row("Sol-3"), 2] = 1
    return PianoMatrix.from_dense(grid, granularity=granularity, tempo_bpm=72, processing_step=step)


# ------------------------------------------------------------------ the tree


def test_the_avicii_levels_scenario(temp_store: Path) -> None:
    """v1_gsc, v1_gn, v2_gn — the example tree from the features doc.

    Two granularities of v1 (same take, collapsed differently) then a real
    second version.
    """
    fine = matrix(Granularity.SEMICORCHEA)
    coarse = collapse_to(
        matrix(Granularity.SEMICORCHEA, step=MatrixProcessingStep.RAW), Granularity.NEGRA
    )

    v1_gsc = repository.save_version("Avicii", "Levels", fine, comment="First transcription")
    assert v1_gsc.folder == "v1_gsc"

    # Same musical state, second granularity: the version number is pinned.
    v1_gn = repository.save_version("Avicii", "Levels", coarse, version=1, comment="At negra")
    assert v1_gn.folder == "v1_gn"

    v2_gn = repository.save_version(
        "Avicii",
        "Levels",
        coarse,
        comment="Cleaned the intro",
        parent=repository.parent_pointer(v1_gn),
    )
    assert v2_gn.folder == "v2_gn"

    track = repository.read_track("avicii", "levels")
    assert track.version_folders() == ["v1_gsc", "v1_gn", "v2_gn"]
    assert track.artist_name == "Avicii"

    tree = paths.playground_track_dir("avicii", "levels")
    assert (tree / "metadata_track.json").is_file()
    assert (tree / "v1_gsc" / "piano_matrix_v1_gsc.npz").is_file()
    assert (tree / "v1_gsc" / "metadata.json").is_file()
    assert (tree / "v2_gn" / "piano_matrix_v2_gn.npz").is_file()


def test_a_saved_version_round_trips(temp_store: Path) -> None:
    original = matrix()
    saved = repository.save_version("Avicii", "Levels", original, comment="take one")

    loaded = repository.load_version("avicii", "levels", saved.folder)
    assert np.array_equal(loaded.matrix.grid, original.grid)
    assert loaded.matrix.granularity is original.granularity
    assert loaded.matrix.tempo_bpm == original.tempo_bpm
    assert loaded.metadata.comment == "take one"


def test_version_numbers_advance(temp_store: Path) -> None:
    for expected in ("v1_gsc", "v2_gsc", "v3_gsc"):
        assert repository.save_version("A", "B", matrix()).folder == expected


def test_saving_over_a_version_needs_the_overwrite_flag(temp_store: Path) -> None:
    repository.save_version("A", "B", matrix(), version=1)
    with pytest.raises(FileExistsError, match="overwrite=True"):
        repository.save_version("A", "B", matrix(), version=1)

    replaced = repository.save_version(
        "A", "B", matrix(), version=1, overwrite=True, comment="redo"
    )
    assert replaced.folder == "v1_gsc"
    # Overwriting replaces the history entry rather than appending a second one.
    history = repository.list_versions("a", "b")
    assert [entry.folder for entry in history] == ["v1_gsc"]
    assert history[0].comment == "redo"


def test_two_hands_are_saved_beside_their_version(temp_store: Path) -> None:
    hands = split_hands(matrix())
    saved = repository.save_two_hands("A", "B", hands.right, hands.left, comment="split")

    directory = paths.playground_version_dir("a", "b", 1, Granularity.SEMICORCHEA)
    assert (directory / "piano_matrix_v1_gsc_right.npz").is_file()
    assert (directory / "piano_matrix_v1_gsc_left.npz").is_file()
    assert saved.folder == "v1_gsc"


def test_mismatched_hands_are_refused(temp_store: Path) -> None:
    hands = split_hands(matrix())
    with pytest.raises(ValueError, match="same shape"):
        repository.save_two_hands("A", "B", hands.right, PianoMatrix.empty(2))


# ------------------------------------------------------------------- lineage


def test_an_edit_records_its_parent_and_leaves_the_original_alone(temp_store: Path) -> None:
    base = repository.save_version("A", "B", matrix(), comment="original")

    edited = matrix()
    edited.grid[note_to_row("Mi-4"), 4] = 1
    child = repository.save_version(
        "A", "B", edited, comment="added a note", parent=repository.parent_pointer(base)
    )

    assert child.metadata.parent_matrix is not None
    assert child.metadata.parent_matrix.version_folder == "v1_gsc"

    # "Back to the original" loads the parent; it is untouched.
    parent = repository.load_parent(child)
    assert parent.folder == base.folder
    assert parent.matrix.cell(note_to_row("Mi-4"), 4) == 0


def test_a_version_without_a_parent_says_so(temp_store: Path) -> None:
    saved = repository.save_version("A", "B", matrix())
    with pytest.raises(VersionNotFound, match="no parent"):
        repository.load_parent(saved)


# -------------------------------------------------------------------- tracks


def test_tracks_are_found_by_real_name_not_slug(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    repository.save_version("Claude Debussy", "Clair de Lune", matrix())

    assert [track.track_name for track in repository.find_tracks("levels")] == ["Levels"]
    assert [track.artist_name for track in repository.find_tracks("debussy")] == ["Claude Debussy"]
    assert len(repository.find_tracks("")) == 2


def test_renaming_keeps_the_slug_and_the_folder(temp_store: Path) -> None:
    """A folder move would break every parent pointer and every promotion."""
    repository.save_version("Avicii", "Levels", matrix())
    renamed = repository.rename_track("avicii", "levels", track_name="Levels (live)")

    assert renamed.track_name == "Levels (live)"
    assert renamed.track_slug == "levels"
    assert paths.playground_track_dir("avicii", "levels").is_dir()


def test_an_unknown_track_raises(temp_store: Path) -> None:
    with pytest.raises(TrackNotFound):
        repository.read_track("nobody", "nothing")


def test_deleting_a_version_drops_it_from_the_history(temp_store: Path) -> None:
    repository.save_version("A", "B", matrix())
    repository.save_version("A", "B", matrix())
    repository.delete_version("a", "b", "v1_gsc")

    assert [entry.folder for entry in repository.list_versions("a", "b")] == ["v2_gsc"]
    assert not (paths.playground_track_dir("a", "b") / "v1_gsc").exists()


def test_loading_the_latest_version(temp_store: Path) -> None:
    repository.save_version("A", "B", matrix(), comment="first")
    repository.save_version("A", "B", matrix(), comment="second")
    assert repository.load_latest("a", "b").metadata.comment == "second"


# ----------------------------------------------------------------- promotion


def test_the_default_promotion_name() -> None:
    assert default_promotion_name("Levels", "Avicii") == "Levels - Avicii"


def test_promote_copies_the_matrix_and_embeds_the_metadata(temp_store: Path) -> None:
    """The library must survive the playground being cleaned out."""
    repository.save_version("Avicii", "Levels", matrix(), comment="v1")
    result = promotion.promote("avicii", "levels", "v1_gsc")

    assert result.name == "Levels - Avicii"
    library = paths.library_track_dir("avicii", "levels")
    assert (library / "piano_matrix_v1_gsc.npz").is_file()
    assert (library / "metadata_library_track.json").is_file()

    embedded = result.promotion.version_metadata
    assert embedded is not None
    assert embedded.comment == "v1"
    assert embedded.granularity is Granularity.SEMICORCHEA


def test_an_editable_promotion_name(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    result = promotion.promote(
        "avicii", "levels", "v1_gsc", promotion_name="Levels (Chill) - Avicii"
    )
    assert result.name == "Levels (Chill) - Avicii"


def test_re_promoting_replaces_but_keeps_the_history(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix(), comment="first")
    repository.save_version("Avicii", "Levels", matrix(), comment="second")

    promotion.promote("avicii", "levels", "v1_gsc", promotion_name="Take one")
    after = promotion.promote("avicii", "levels", "v2_gsc", promotion_name="Take two").track

    assert [item.promotion_name for item in after.active_promotions()] == ["Take two"]
    assert len(after.promotions) == 2  # nothing was deleted
    assert after.rollback_to == "Take one"


def test_additional_promotions_live_side_by_side(temp_store: Path) -> None:
    """The same piece in two arrangements."""
    repository.save_version("Avicii", "Levels", matrix(), comment="first")
    repository.save_version("Avicii", "Levels", matrix(), comment="second")

    promotion.promote("avicii", "levels", "v1_gsc", promotion_name="Levels (Chill) - Avicii")
    after = promotion.promote(
        "avicii",
        "levels",
        "v2_gsc",
        promotion_name="Levels (Full speed) - Avicii",
        as_additional=True,
    ).track

    assert sorted(item.promotion_name for item in after.active_promotions()) == [
        "Levels (Chill) - Avicii",
        "Levels (Full speed) - Avicii",
    ]


def test_rollback_restores_the_previous_promotion(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix(), comment="first")
    repository.save_version("Avicii", "Levels", matrix(), comment="second")
    promotion.promote("avicii", "levels", "v1_gsc", promotion_name="Take one")
    promotion.promote("avicii", "levels", "v2_gsc", promotion_name="Take two")

    rolled = promotion.rollback("avicii", "levels").track

    assert [item.promotion_name for item in rolled.active_promotions()] == ["Take one"]
    assert len(rolled.promotions) == 2  # nothing deleted
    # Rolling forward again is one more rollback away.
    assert rolled.rollback_to == "Take two"
    assert [
        item.promotion_name
        for item in promotion.rollback("avicii", "levels").track.active_promotions()
    ] == ["Take two"]


def test_rollback_without_a_previous_promotion_is_refused(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    promotion.promote("avicii", "levels", "v1_gsc")
    with pytest.raises(NothingToRollBackTo):
        promotion.rollback("avicii", "levels")


def test_promoting_a_two_hands_version_copies_both_hands(temp_store: Path) -> None:
    hands = split_hands(matrix())
    repository.save_two_hands("Avicii", "Levels", hands.right, hands.left)
    promotion.promote("avicii", "levels", "v1_gsc")

    library = paths.library_track_dir("avicii", "levels")
    assert (library / "piano_matrix_v1_gsc_right.npz").is_file()
    assert (library / "piano_matrix_v1_gsc_left.npz").is_file()


def test_library_tracks_filter_by_tag_and_name(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    repository.save_version("Claude Debussy", "Clair de Lune", matrix())
    promotion.promote("avicii", "levels", "v1_gsc")
    promotion.promote("claude-debussy", "clair-de-lune", "v1_gsc")
    promotion.set_tags("avicii", "levels", ["edm", "easy"])

    assert len(promotion.list_library_tracks()) == 2
    assert [t.track_name for t in promotion.list_library_tracks(tag="edm")] == ["Levels"]
    assert [t.track_name for t in promotion.list_library_tracks(search="lune")] == ["Clair de Lune"]


def test_an_unknown_library_track_raises(temp_store: Path) -> None:
    with pytest.raises(LibraryTrackNotFound):
        promotion.read_library_track("nobody", "nothing")


def test_history_survives_a_reread(temp_store: Path) -> None:
    """Everything is on disk, so a restart changes nothing."""
    repository.save_version("Avicii", "Levels", matrix(), comment="first")
    promotion.promote("avicii", "levels", "v1_gsc", promotion_name="Take one")

    assert repository.read_track("avicii", "levels").versions[0].comment == "first"
    assert (
        promotion.read_library_track("avicii", "levels").promotions[0].promotion_name == "Take one"
    )


# ---------------------------------------------------------------- endpoints


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def envelope() -> dict:
    return matrix().to_envelope().model_dump(by_alias=True, mode="json")


def test_the_full_save_promote_rollback_flow_over_http(client: TestClient) -> None:
    first = client.post(
        "/library/playground",
        json={
            "artistName": "Avicii",
            "trackName": "Levels",
            "matrix": envelope(),
            "comment": "first transcription",
        },
    )
    assert first.status_code == 201
    assert first.json()["folder"] == "v1_gsc"

    second = client.post(
        "/library/playground",
        json={
            "artistName": "Avicii",
            "trackName": "Levels",
            "matrix": envelope(),
            "comment": "cleaned the intro",
            "parentVersion": "v1_gsc",
        },
    )
    assert second.json()["folder"] == "v2_gsc"
    assert second.json()["metadata"]["parentMatrix"]["versionFolder"] == "v1_gsc"

    tracks = client.get("/library/playground").json()
    assert tracks[0]["trackName"] == "Levels"
    assert [entry["folder"] for entry in tracks[0]["versions"]] == ["v1_gsc", "v2_gsc"]

    loaded = client.get("/library/playground/avicii/levels/v1_gsc").json()
    assert loaded["granularity"] == "semicorchea"

    suggestion = client.get("/library/promotion-suggestion/avicii/levels").json()
    assert suggestion["suggestedName"] == "Levels - Avicii"

    promoted = client.post(
        "/library/promote",
        json={
            "artistSlug": "avicii",
            "trackSlug": "levels",
            "versionFolder": "v1_gsc",
            "promotionName": "Levels (Chill) - Avicii",
        },
    ).json()
    assert promoted["promotions"][0]["promotionName"] == "Levels (Chill) - Avicii"

    client.post(
        "/library/promote",
        json={
            "artistSlug": "avicii",
            "trackSlug": "levels",
            "versionFolder": "v2_gsc",
            "promotionName": "Levels (Fast) - Avicii",
        },
    )
    rolled = client.post(
        "/library/rollback", json={"artistSlug": "avicii", "trackSlug": "levels"}
    ).json()
    active = [item["promotionName"] for item in rolled["promotions"] if item["active"]]
    assert active == ["Levels (Chill) - Avicii"]

    tagged = client.post(
        "/library/tags",
        json={"artistSlug": "avicii", "trackSlug": "levels", "tags": ["edm", "easy"]},
    ).json()
    assert tagged["tags"] == ["easy", "edm"]
    assert len(client.get("/library/tracks", params={"tag": "edm"}).json()) == 1


def test_saving_over_a_version_is_a_409(client: TestClient) -> None:
    body = {"artistName": "A", "trackName": "B", "matrix": envelope(), "version": 1}
    assert client.post("/library/playground", json=body).status_code == 201
    assert client.post("/library/playground", json=body).status_code == 409
    assert client.post("/library/playground", json={**body, "overwrite": True}).status_code == 201


def test_unknown_playground_paths_are_404(client: TestClient) -> None:
    assert client.get("/library/playground/nobody/nothing").status_code == 404
    assert client.get("/library/playground/nobody/nothing/v1_gsc").status_code == 404
    assert client.get("/library/tracks/nobody/nothing").status_code == 404
    assert client.get("/library/promotion-suggestion/nobody/nothing").status_code == 404


def test_rolling_back_with_no_history_is_a_409(client: TestClient) -> None:
    client.post(
        "/library/playground",
        json={"artistName": "A", "trackName": "B", "matrix": envelope()},
    )
    client.post(
        "/library/promote",
        json={"artistSlug": "a", "trackSlug": "b", "versionFolder": "v1_gsc"},
    )
    assert (
        client.post("/library/rollback", json={"artistSlug": "a", "trackSlug": "b"}).status_code
        == 409
    )
