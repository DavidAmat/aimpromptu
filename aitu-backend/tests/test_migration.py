"""The wall-clock migration: what it carries, what it refuses, and what it says.

Success criterion 5 is that every stored artifact either migrates or is explicitly
marked. "Explicitly" is the load-bearing word, so most of these tests are about
what ends up on disk for a piece that could *not* be carried over, and about the
one operation that cannot be undone: the dry run being the default.
"""

from pathlib import Path

import pytest

from aitu_backend.audio import store
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

from scripts.migrate_to_time_matrix import REPLACED_DIR, migrate


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


def audio_with(events: bool, stale: bool) -> str:
    """A stored piece, with or without its recorded notes and its old grids."""
    uuid = store.create("Piece", AudioSource.UPLOAD, "wav").uuid
    folder = pipeline.matrices_dir(uuid)
    folder.mkdir(parents=True, exist_ok=True)
    if events:
        pipeline.save_note_events(
            uuid, [NoteEvent(midi_note=60, start=0.0, end=1.0)], duration_seconds=2.0
        )
    if stale:
        for name in ("raw.npz", "clean_semicorchea.npz", "hands_semicorchea.json"):
            (folder / name).write_bytes(b"old")
        (folder / "raw-granularity.txt").write_text("semifusa\n", encoding="utf-8")
    return uuid


# ------------------------------------------------------- a piece that carries over


def test_a_piece_with_its_recorded_notes_keeps_only_them(data_dir: Path) -> None:
    uuid = audio_with(events=True, stale=True)

    migrate(data_dir, apply=True)

    folder = pipeline.matrices_dir(uuid)
    assert sorted(path.name for path in folder.iterdir()) == [REPLACED_DIR, "events.json"]
    # And the piece still reads, which is the actual point of the migration.
    assert pipeline.load_note_events(uuid) is not None
    assert pipeline.needs_rederivation(uuid) is None


def test_the_old_files_are_moved_and_not_destroyed(data_dir: Path) -> None:
    """The one irreversible operation, and it is not performed."""
    uuid = audio_with(events=True, stale=True)

    migrate(data_dir, apply=True)

    replaced = pipeline.matrices_dir(uuid) / REPLACED_DIR
    assert sorted(path.name for path in replaced.iterdir()) == [
        "clean_semicorchea.npz",
        "hands_semicorchea.json",
        "raw-granularity.txt",
        "raw.npz",
    ]


def test_running_it_twice_changes_nothing_the_second_time(data_dir: Path) -> None:
    uuid = audio_with(events=True, stale=True)
    migrate(data_dir, apply=True)
    before = sorted(path.name for path in (pipeline.matrices_dir(uuid) / REPLACED_DIR).iterdir())

    second = migrate(data_dir, apply=True)

    after = sorted(path.name for path in (pipeline.matrices_dir(uuid) / REPLACED_DIR).iterdir())
    assert after == before
    assert [action.kind for action in second.actions] == ["ok"]


# ----------------------------------------------------- a piece that cannot carry over


def test_a_piece_with_no_recorded_notes_is_flagged_in_words(data_dir: Path) -> None:
    """Never silently reinterpreted. This is success criterion 5."""
    uuid = audio_with(events=False, stale=True)

    migrate(data_dir, apply=True)

    reason = pipeline.needs_rederivation(uuid)
    assert reason is not None
    # Written for a reader, not for a developer: it says what to do.
    assert "Run transcription" in reason


def test_a_flagged_piece_keeps_every_old_file(data_dir: Path) -> None:
    """Nothing is thrown away from something that cannot be rebuilt."""
    uuid = audio_with(events=False, stale=True)

    migrate(data_dir, apply=True)

    names = sorted(path.name for path in pipeline.matrices_dir(uuid).iterdir())
    assert "raw.npz" in names
    assert "clean_semicorchea.npz" in names
    assert REPLACED_DIR not in names


def test_transcribing_again_clears_the_flag(data_dir: Path) -> None:
    uuid = audio_with(events=False, stale=True)
    migrate(data_dir, apply=True)
    assert pipeline.needs_rederivation(uuid) is not None

    # What the user does about it: transcribe. Only the storing step is exercised.
    pipeline.save_note_events(
        uuid, [NoteEvent(midi_note=60, start=0.0, end=1.0)], duration_seconds=2.0
    )
    pipeline.clear_needs_rederivation(uuid)

    assert pipeline.needs_rederivation(uuid) is None


def test_a_stale_flag_is_removed_when_the_notes_are_there(data_dir: Path) -> None:
    """A flag that outlived its reason is worse than no flag: it looks authoritative."""
    uuid = audio_with(events=True, stale=False)
    pipeline.mark_needs_rederivation(uuid, "left over from an earlier run")

    result = migrate(data_dir, apply=True)

    assert pipeline.needs_rederivation(uuid) is None
    assert "unflag" in [action.kind for action in result.actions]


# ------------------------------------------------------------------ safety


def test_a_dry_run_is_the_default_and_touches_nothing(data_dir: Path) -> None:
    uuid = audio_with(events=True, stale=True)
    before = sorted(path.name for path in pipeline.matrices_dir(uuid).iterdir())

    result = migrate(data_dir, apply=False)

    assert sorted(path.name for path in pipeline.matrices_dir(uuid).iterdir()) == before
    assert not Path(result.backup or "").exists()
    # It still says what it would have done.
    assert [action.kind for action in result.actions] == ["move"]


def test_applying_copies_the_whole_tree_aside_first(data_dir: Path) -> None:
    """`data/audio/**` is gitignored, so this copy is the only way back."""
    uuid = audio_with(events=True, stale=True)

    result = migrate(data_dir, apply=True)

    backup = Path(result.backup or "")
    assert backup.is_dir()
    assert (backup / "audio" / uuid / "matrices" / "raw.npz").is_file()
    assert (backup / "audio" / uuid / "matrices" / "events.json").is_file()


def test_a_second_apply_does_not_overwrite_the_first_backup(data_dir: Path) -> None:
    audio_with(events=True, stale=True)
    first = Path(migrate(data_dir, apply=True).backup or "")
    second = Path(migrate(data_dir, apply=True).backup or "")

    assert first.is_dir() and second.is_dir()
    assert first != second


def test_an_empty_tree_is_not_an_error(data_dir: Path) -> None:
    result = migrate(data_dir, apply=True)
    assert result.actions == []


# ------------------------------------------------------- what the reader is told


def test_the_rhythm_screen_gets_a_sentence_it_can_show(data_dir: Path) -> None:
    """The message reaches the screen unchanged, so it must not name an endpoint.

    Before P4.5 this answer read "Re-transcribe it (POST /matrix/transcribe)",
    which is an instruction nobody reading the app can follow.
    """
    from fastapi.testclient import TestClient

    from aitu_backend.main import create_app

    uuid = audio_with(events=False, stale=True)
    migrate(data_dir, apply=True)

    detail = (
        TestClient(create_app())
        .get(f"/time/{uuid}/score", params={"anchorMs": 320})
        .json()["detail"]
    )

    assert "Run transcription" in detail
    assert "POST" not in detail and "/matrix" not in detail


def test_the_audio_list_says_which_pieces_can_be_drawn(data_dir: Path) -> None:
    from fastapi.testclient import TestClient

    from aitu_backend.main import create_app

    good = audio_with(events=True, stale=True)
    bad = audio_with(events=False, stale=True)
    migrate(data_dir, apply=True)

    rows = {item["uuid"]: item for item in TestClient(create_app()).get("/audio/").json()}

    assert rows[good]["hasNotes"] is True
    assert rows[good]["needsRederivation"] is None
    assert rows[bad]["hasNotes"] is False
    assert "Run transcription" in rows[bad]["needsRederivation"]
