"""Storage layout: every path helper, the tree creation, and npz round-trips."""

from pathlib import Path

import pytest

from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.schemas.matrix import Granularity, SparseCooMatrix
from aitu_backend.storage import paths
from aitu_backend.storage import matrix_store
from aitu_backend.storage.matrix_store import (
    from_coo,
    load_matrix,
    matrix_exists,
    save_matrix,
    to_coo,
)


@pytest.fixture()
def temp_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every path helper at a throwaway `data/` tree."""
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


# ------------------------------------------------------------------- the tree


def test_ensure_data_tree_creates_every_root(temp_data: Path) -> None:
    assert (temp_data / "audio").is_dir()
    assert (temp_data / "playground").is_dir()
    assert (temp_data / "library" / "tracks").is_dir()
    assert (temp_data / "library" / "playlists").is_dir()


def test_ensure_data_tree_is_idempotent(temp_data: Path) -> None:
    paths.ensure_data_tree()
    paths.ensure_data_tree()
    assert (temp_data / "audio").is_dir()


def test_backend_root_holds_pyproject() -> None:
    """The real root, not the fixture one — guards the `parents[3]` depth."""
    assert (paths.backend_root() / "pyproject.toml").is_file()
    assert paths.data_dir().name == "data"


# ------------------------------------------------------------------- audio


def test_audio_paths(temp_data: Path) -> None:
    uuid = "4f9c1e6a-2b7d-4c3e-9a10-8d5b6f2c1e77"
    assert paths.audio_dir(uuid) == temp_data / "audio" / uuid
    assert paths.audio_metadata_path(uuid).name == "metadata.json"
    assert paths.audio_original_path(uuid, "mp3").name == "original.mp3"
    # A leading dot on the extension must not double up.
    assert paths.audio_original_path(uuid, ".m4a").name == "original.m4a"


def test_find_audio_original_and_listing(temp_data: Path) -> None:
    uuid = "abc"
    assert paths.find_audio_original(uuid) is None
    assert paths.list_audio_uuids() == []

    paths.audio_dir(uuid).mkdir(parents=True)
    paths.audio_original_path(uuid, "mp3").write_bytes(b"fake")

    assert paths.find_audio_original(uuid) == paths.audio_original_path(uuid, "mp3")
    assert paths.list_audio_uuids() == ["abc"]


# -------------------------------------------------------------- playground


def test_playground_paths(temp_data: Path) -> None:
    track = paths.playground_track_dir("avicii", "levels")
    assert track == temp_data / "playground" / "avicii" / "levels"
    assert paths.playground_track_metadata_path("avicii", "levels").name == "metadata_track.json"

    version = paths.playground_version_dir("avicii", "levels", 2, Granularity.NEGRA)
    assert version == track / "v2_gn"
    assert (
        paths.playground_version_metadata_path("avicii", "levels", 2, Granularity.NEGRA)
        == version / "metadata.json"
    )
    assert (
        paths.playground_matrix_path("avicii", "levels", 2, Granularity.NEGRA)
        == version / "piano_matrix_v2_gn.npz"
    )
    assert (
        paths.playground_matrix_path("avicii", "levels", 2, Granularity.NEGRA, "left").name
        == "piano_matrix_v2_gn_left.npz"
    )


def test_playground_listings(temp_data: Path) -> None:
    assert paths.list_playground_artists() == []
    paths.playground_version_dir("avicii", "levels", 1, Granularity.FUSA).mkdir(parents=True)
    paths.playground_version_dir("avicii", "levels", 2, Granularity.SEMICORCHEA).mkdir(parents=True)

    assert paths.list_playground_artists() == ["avicii"]
    assert paths.list_playground_tracks("avicii") == ["levels"]
    assert paths.list_playground_versions("avicii", "levels") == ["v1_gf", "v2_gsc"]


# ------------------------------------------------------------------ library


def test_library_paths(temp_data: Path) -> None:
    track = paths.library_track_dir("avicii", "levels")
    assert track == temp_data / "library" / "tracks" / "avicii" / "levels"
    assert (
        paths.library_track_metadata_path("avicii", "levels").name == "metadata_library_track.json"
    )
    assert (
        paths.library_matrix_path("avicii", "levels", 2, Granularity.SEMICORCHEA)
        == track / "piano_matrix_v2_gsc.npz"
    )

    assert (
        paths.playlist_dir("sunday-practice")
        == temp_data / "library" / "playlists" / "sunday-practice"
    )
    assert paths.playlist_metadata_path("sunday-practice").name == "metadata_library_playlist.json"


def test_library_listings(temp_data: Path) -> None:
    assert paths.list_library_artists() == []
    assert paths.list_playlists() == []
    paths.library_track_dir("avicii", "levels").mkdir(parents=True)
    paths.playlist_dir("sunday-practice").mkdir(parents=True)

    assert paths.list_library_artists() == ["avicii"]
    assert paths.list_library_tracks("avicii") == ["levels"]
    assert paths.list_playlists() == ["sunday-practice"]


def test_scores_seed_path(temp_data: Path) -> None:
    assert paths.scores_json_path() == temp_data / "example-scores.json"


# --------------------------------------------------------------- npz format


def _sample() -> SparseCooMatrix:
    """Do-4 struck then held, Mi-4 struck at the end."""
    do, mi = note_to_row("Do-4"), note_to_row("Mi-4")
    return SparseCooMatrix(
        shape=[KEY_COUNT, 4],
        rows=[do, do, do, mi],
        cols=[0, 1, 2, 3],
        onset=[do, -1, -1, mi],
    )


def test_scipy_coo_conversion_round_trips() -> None:
    original = _sample()
    assert from_coo(to_coo(original)).model_dump() == original.model_dump()


def test_stored_values_are_int8_ones_and_minus_ones() -> None:
    coo = to_coo(_sample())
    assert coo.dtype.name == "int8"
    assert sorted(set(coo.data.tolist())) == [-1, 1]
    assert coo.shape == (KEY_COUNT, 4)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "piano_matrix_v1_gsc.npz"
    assert not matrix_exists(target)

    save_matrix(target, _sample())
    assert matrix_exists(target)
    assert load_matrix(target).model_dump() == _sample().model_dump()


def test_save_uses_an_atomic_sibling_then_cleans_it_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Readers never see scipy's partially-written zip archive."""
    target = tmp_path / "matrix.npz"
    written_paths: list[Path] = []
    scipy_save = matrix_store.sparse.save_npz

    def record_path(path: Path, *args: object, **kwargs: object) -> None:
        written_paths.append(Path(path))
        scipy_save(path, *args, **kwargs)

    monkeypatch.setattr(matrix_store.sparse, "save_npz", record_path)
    save_matrix(target, _sample())

    assert len(written_paths) == 1
    assert written_paths[0] != target
    assert written_paths[0].parent == target.parent
    assert written_paths[0].suffix == ".npz"
    assert not written_paths[0].exists()
    assert load_matrix(target).model_dump() == _sample().model_dump()


def test_save_rejects_a_non_npz_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"\.npz"):
        save_matrix(tmp_path / "matrix.bin", _sample())


def test_load_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_matrix(tmp_path / "absent.npz")


def test_empty_matrix_survives_a_round_trip(tmp_path: Path) -> None:
    empty = SparseCooMatrix(shape=[KEY_COUNT, 8], rows=[], cols=[], onset=[])
    target = tmp_path / "empty.npz"
    save_matrix(target, empty)
    restored = load_matrix(target)
    assert restored.is_empty()
    assert restored.shape == [KEY_COUNT, 8]


def test_loaded_cells_come_back_sorted_by_column_then_row(tmp_path: Path) -> None:
    do, mi = note_to_row("Do-4"), note_to_row("Mi-4")
    unsorted = SparseCooMatrix(
        shape=[KEY_COUNT, 2],
        rows=[mi, do, do],
        cols=[1, 1, 0],
        onset=[mi, do, do],
    )
    target = tmp_path / "unsorted.npz"
    save_matrix(target, unsorted)
    restored = load_matrix(target)
    pairs = list(zip(restored.cols, restored.rows))
    assert pairs == sorted(pairs)
