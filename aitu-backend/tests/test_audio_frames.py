"""The selected region: cuts as 10 ms frames, the frame table, the joined audio (implementation 08,
Phase 4, plan section 9.2)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from scipy.io import wavfile

from aitu_backend.audio import formats, ingest, store
from aitu_backend.audio.frames import (
    SAMPLES_PER_FRAME,
    FrameTable,
    frame_count,
    frame_peaks,
    join_kept,
    normalize_cuts,
)
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

needs_ffmpeg = pytest.mark.skipif(
    not formats.ffmpeg_available(), reason="ffmpeg is not installed"
)


# ------------------------------------------------------------------ the cuts


def test_cuts_are_sorted_clipped_and_merged() -> None:
    assert normalize_cuts(
        [(50, 60), (10, 20), (15, 30), (30, 35), (90, 200), (5, 5)], 100
    ) == [
        (10, 35),
        (50, 60),
        (90, 100),
    ]
    assert normalize_cuts([(-5, 3)]) == [(0, 3)]


def test_one_frame_is_160_samples_and_a_partial_frame_counts() -> None:
    assert SAMPLES_PER_FRAME == 160
    assert frame_count(160) == 1
    assert frame_count(161) == 2
    assert frame_count(0) == 0


def test_the_metadata_refuses_cuts_that_are_not_normalized() -> None:
    base = {"uuid": "u", "alias": "a", "source": "upload", "format": "wav"}
    assert AudioMetadata.model_validate({**base, "cuts": [[1, 5], [7, 9]]}).cuts == [
        (1, 5),
        (7, 9),
    ]
    for cuts in ([[5, 1]], [[1, 5], [5, 9]], [[7, 9], [1, 5]], [[-1, 2]]):
        with pytest.raises(ValidationError):
            AudioMetadata.model_validate({**base, "cuts": cuts})


def test_an_old_metadata_file_reads_with_no_cut_and_revision_0() -> None:
    old = AudioMetadata.model_validate(
        {"uuid": "u", "alias": "a", "source": "upload", "format": "wav"}
    )
    assert old.cuts == [] and old.audio_revision == 0


# ------------------------------------------------------------- the frame table


def table() -> FrameTable:
    # 1000 frames (10 s); cut 100..300 and 500..550. Kept: 0..100, 300..500, 550..1000.
    return FrameTable.from_cuts([(100, 300), (500, 550)], 1000)


def test_the_table_has_one_row_per_kept_range() -> None:
    assert table().rows() == [
        {"pieceStart": 0, "originalStart": 0, "length": 100},
        {"pieceStart": 100, "originalStart": 300, "length": 200},
        {"pieceStart": 300, "originalStart": 550, "length": 450},
    ]
    assert table().piece_frames == 750
    assert table().cuts() == [(100, 300), (500, 550)]


def test_a_frame_of_the_piece_maps_to_the_original_and_back() -> None:
    t = table()
    assert t.to_original(0) == 0
    assert t.to_original(99) == 99
    assert t.to_original(100) == 300  # the first frame after the first cut
    assert t.to_original(299) == 499
    assert t.to_original(300) == 550
    assert t.to_original(749) == 999
    assert (
        t.to_original(750) == 1000
    )  # the end of the piece is the end of the last kept range
    frames = np.arange(750)
    assert np.array_equal(t.to_piece(t.to_original(frames)), frames)


def test_a_frame_inside_a_cut_maps_to_the_first_kept_frame_after_it() -> None:
    t = table()
    assert t.to_piece(150) == 100
    assert t.to_piece(520) == 300
    starts_with_a_cut = FrameTable.from_cuts([(0, 10)], 100)
    assert starts_with_a_cut.to_piece(5) == 0
    assert starts_with_a_cut.to_original(0) == 10
    ends_with_a_cut = FrameTable.from_cuts([(90, 100)], 100)
    assert ends_with_a_cut.to_piece(95) == 90


def test_a_range_of_the_piece_is_one_range_per_kept_range_it_covers() -> None:
    assert table().range_to_original(50, 350) == [(50, 100), (300, 500), (550, 600)]
    assert table().range_to_original(120, 130) == [(320, 330)]
    assert table().range_to_original(10, 10) == []


def test_no_cut_is_the_whole_audio() -> None:
    whole = FrameTable.from_cuts([], 400)
    assert whole.is_whole and whole.piece_frames == 400
    assert whole.to_original(123) == 123


def test_a_lookup_is_one_search_whatever_the_length() -> None:
    """A thousand cuts over an hour of frames: every frame maps back in one vector call."""
    cuts = [(start, start + 10) for start in range(100, 360_000, 360)]
    big = FrameTable.from_cuts(cuts, 360_000)
    frames = np.arange(big.piece_frames)
    back = big.to_piece(big.to_original(frames))
    assert np.array_equal(back, frames)


# ------------------------------------------------------------ the joined audio


def test_the_joined_audio_has_exactly_the_kept_frames() -> None:
    samples = np.ones(1000 * SAMPLES_PER_FRAME, dtype=np.float32)
    joined = join_kept(samples, table())
    assert len(joined) == table().piece_frames * SAMPLES_PER_FRAME


def test_each_join_fades_out_and_in_over_5_ms() -> None:
    samples = np.ones(1000 * SAMPLES_PER_FRAME, dtype=np.float32)
    joined = join_kept(samples, table())
    join = 100 * SAMPLES_PER_FRAME
    fade = 80  # 5 ms at 16 kHz
    assert joined[join - fade] == pytest.approx(1 - 1 / fade)  # the fade out starts
    assert joined[join - 1] == 0.0  # silence on both sides of the join: no click
    assert joined[join] == 0.0
    assert np.all(np.diff(joined[join - fade : join]) < 0)
    assert np.all(np.diff(joined[join : join + fade]) > 0)
    assert np.all(joined[fade : join - fade] == 1.0)  # nothing else is touched
    assert joined[0] == 1.0  # no fade at the start of the piece


def test_without_a_cut_the_audio_is_untouched() -> None:
    samples = np.linspace(-1, 1, 3000, dtype=np.float32)
    assert np.array_equal(
        join_kept(samples, FrameTable.from_cuts([], frame_count(3000))), samples
    )


# --------------------------------------------------------- stored, and the route


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_database_tree()
    return tmp_path / "data"


def ingested(tmp_path: Path, seconds: float = 10.0) -> str:
    rate = 16_000
    samples = (
        0.3 * np.sin(2 * np.pi * 220 * np.arange(int(rate * seconds)) / rate) * 32767
    ).astype(np.int16)
    source = tmp_path / "tone.wav"
    wavfile.write(source, rate, samples)
    with source.open("rb") as handle:
        return ingest.ingest_file(handle, "tone.wav", AudioSource.UPLOAD).uuid


@needs_ffmpeg
def test_saving_the_same_cuts_again_is_not_a_change(
    data_dir: Path, tmp_path: Path
) -> None:
    uuid = ingested(tmp_path, seconds=1.0)
    assert store.set_cuts(uuid, [(10, 20)]).audio_revision == 1
    assert store.set_cuts(uuid, [(10, 20)]).audio_revision == 1
    assert store.set_cuts(uuid, []).audio_revision == 2
    assert store.read_metadata(uuid).cuts == []


@needs_ffmpeg
def test_the_cuts_route_normalizes_counts_and_protects_a_newer_revision(
    data_dir: Path, tmp_path: Path
) -> None:
    client = TestClient(create_app())
    uuid = ingested(tmp_path, seconds=10.0)

    first = client.get(f"/audio/{uuid}/cuts").json()
    assert first["totalFrames"] == 1000 and first["pieceFrames"] == 1000
    assert (
        first["cuts"] == [] and first["audioRevision"] == 0 and first["frameMs"] == 10
    )

    saved = client.put(
        f"/audio/{uuid}/cuts",
        json={"cuts": [[500, 550], [100, 300], [290, 310]], "baseRevision": 0},
    ).json()
    assert saved["cuts"] == [[100, 310], [500, 550]]
    assert saved["pieceFrames"] == 740
    assert saved["audioRevision"] == 1
    assert saved["kept"][1] == {"pieceStart": 100, "originalStart": 310, "length": 190}

    stale = client.put(f"/audio/{uuid}/cuts", json={"cuts": [], "baseRevision": 0})
    assert stale.status_code == 409
    everything = client.put(f"/audio/{uuid}/cuts", json={"cuts": [[0, 1000]]})
    assert everything.status_code == 422


@needs_ffmpeg
def test_a_cut_after_a_transcription_makes_the_notes_stale(
    data_dir: Path, tmp_path: Path
) -> None:
    """Q-2: the notes are not reused; the next transcription transcribes again."""

    class Counting:
        name = "counting"
        calls = 0

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            Counting.calls += 1
            return [NoteEvent(midi_note=60, start=0.5, end=1.0)]

    uuid = ingested(tmp_path, seconds=4.0)
    pipeline.run_pipeline(uuid, engine=Counting())
    pipeline.run_pipeline(uuid, engine=Counting())
    assert Counting.calls == 1
    assert not pipeline.notes_are_stale(uuid)

    store.set_cuts(uuid, [(100, 200)])
    assert pipeline.notes_are_stale(uuid)
    assert pipeline.current_events(uuid) is None
    assert (
        TestClient(create_app()).get(f"/audio/{uuid}/cuts").json()["notesStale"] is True
    )

    pipeline.run_pipeline(uuid, engine=Counting())
    assert Counting.calls == 2
    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert stored.header.audio_revision == 1
    assert stored.duration_seconds == pytest.approx(3.0)  # 4 s minus the 1 s cut
    assert not pipeline.notes_are_stale(uuid)


@needs_ffmpeg
def test_an_engine_that_reads_a_file_gets_the_joined_audio(
    data_dir: Path, tmp_path: Path
) -> None:
    """ByteDance and Transkun read a WAV: with a cut they get a temporary one of the piece."""
    heard: dict[str, int] = {}

    class Listening:
        name = "listening"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            rate, samples = formats.read_wav(wav_path)
            heard["rate"], heard["samples"] = rate, len(samples)
            return []

    uuid = ingested(tmp_path, seconds=4.0)
    store.set_cuts(uuid, [(0, 50), (300, 350)])
    pipeline.transcribe_audio(uuid, engine=Listening())
    assert heard == {"rate": 16_000, "samples": 300 * SAMPLES_PER_FRAME}


# ------------------------------------------------------------ the waveform per frame (Phase 6)


def test_the_peaks_are_one_pair_per_frame_scaled_to_the_loudest_sample() -> None:
    samples = np.zeros(SAMPLES_PER_FRAME * 3 + 10, dtype=np.float32)
    samples[5] = 0.5  # frame 0
    samples[SAMPLES_PER_FRAME + 7] = -0.25  # frame 1
    samples[-1] = 0.1  # the last, partial frame
    low, high, peak = frame_peaks(samples)
    assert len(low) == len(high) == frame_count(len(samples)) == 4
    assert peak == pytest.approx(0.5)
    assert high.tolist() == [127, 0, 0, 25]
    assert low.tolist() == [0, -64, 0, 0]
    assert low.dtype == np.int8


def test_silence_has_flat_peaks() -> None:
    low, high, peak = frame_peaks(np.zeros(SAMPLES_PER_FRAME * 2, dtype=np.float32))
    assert peak == 0.0 and low.tolist() == high.tolist() == [0, 0]
    assert len(frame_peaks(np.zeros(0, dtype=np.float32))[0]) == 0


@needs_ffmpeg
def test_the_peaks_route_has_as_many_frames_as_the_cuts_route(
    data_dir: Path, tmp_path: Path
) -> None:
    import base64

    client = TestClient(create_app())
    uuid = ingested(tmp_path, seconds=3.0)
    answer = client.get(f"/audio/{uuid}/frames/peaks").json()
    frames = client.get(f"/audio/{uuid}/cuts").json()["totalFrames"]
    assert answer["totalFrames"] == frames == 300 and answer["frameMs"] == 10
    high = np.frombuffer(base64.b64decode(answer["max"]), dtype=np.int8)
    low = np.frombuffer(base64.b64decode(answer["min"]), dtype=np.int8)
    assert len(high) == len(low) == 300
    assert (
        high.max() == 127 and low.min() <= -126
    )  # a steady tone reaches the peak both ways
    assert 0.25 < answer["peak"] <= 0.31


# ------------------------------------------- the audio of the piece (Phase 6, the user's rule)


def test_joined_samples_keep_the_channels_and_land_on_the_frames() -> None:
    from aitu_backend.audio.piece_audio import join_samples

    rate = 44_100
    stereo = np.stack(
        [np.arange(rate, dtype=np.float32), -np.arange(rate, dtype=np.float32)], 1
    )
    table = FrameTable.from_cuts([(10, 30)], 100)  # 1 s of audio, 0.1 to 0.3 s cut
    joined = join_samples(stereo, rate, table)
    assert joined.shape == (80 * 441, 2)
    # Frame 50 of the piece is frame 70 of the original, far from any fade.
    assert joined[50 * 441, 0] == 70 * 441 and joined[50 * 441, 1] == -70 * 441
    # The 5 ms fades sit inside the kept samples, on both sides of the join.
    assert joined[10 * 441 - 1, 0] < 10 * 441 - 1 and joined[10 * 441, 0] == 0.0
    assert np.array_equal(
        join_samples(stereo, rate, FrameTable.from_cuts([], 100)), stereo
    )


def _decode(content: bytes, tmp_path: Path, name: str) -> tuple[int, np.ndarray]:
    import subprocess

    source = tmp_path / name
    source.write_bytes(content)
    target = tmp_path / f"{name}.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source), str(target)], check=True
    )
    rate, samples = wavfile.read(target)
    return int(rate), samples


@needs_ffmpeg
def test_once_cuts_are_saved_every_player_gets_the_edited_audio(
    data_dir: Path, tmp_path: Path
) -> None:
    """The user's rule: after Save, the edited audio is the audio of the piece. The original stays
    for the Audio tab only (`?original=true`)."""
    client = TestClient(create_app())
    rate = 44_100
    time = np.arange(rate * 10) / rate
    left = 0.3 * np.sin(2 * np.pi * 220 * time)
    right = 0.3 * np.sin(2 * np.pi * 330 * time)
    source = tmp_path / "stereo.wav"
    wavfile.write(source, rate, (np.stack([left, right], 1) * 32767).astype(np.int16))
    with source.open("rb") as handle:
        uuid = ingest.ingest_file(handle, "stereo.wav", AudioSource.UPLOAD).uuid

    whole = client.get(f"/audio/{uuid}/file")
    assert _decode(whole.content, tmp_path, "whole")[1].shape == (rate * 10, 2)

    client.put(f"/audio/{uuid}/cuts", json={"cuts": [[100, 300]]})
    listen = client.get(f"/audio/{uuid}/file")
    assert listen.headers["content-type"] == "audio/flac"
    assert listen.headers["cache-control"] == "no-cache"
    got_rate, piece = _decode(listen.content, tmp_path, "piece.flac")
    assert got_rate == rate and piece.shape == (800 * 441, 2)
    # Second 5 of the piece is second 7 of the original, sample for sample (16-bit rounding apart).
    original = (np.stack([left, right], 1) * 32767).astype(np.int16)
    assert (
        np.abs(piece[5 * rate].astype(int) - original[7 * rate].astype(int)).max() <= 1
    )

    engine = _decode(
        client.get(f"/audio/{uuid}/file?normalized=true").content, tmp_path, "n.wav"
    )
    assert engine[0] == 16_000 and len(engine[1]) == 800 * 160
    untouched = client.get(f"/audio/{uuid}/file?original=true")
    assert _decode(untouched.content, tmp_path, "o.wav")[1].shape == (rate * 10, 2)

    entry = client.get(f"/audio/{uuid}").json()
    assert entry["durationSeconds"] == pytest.approx(8.0)
    assert entry["originalDurationSeconds"] == pytest.approx(10.0)
    assert client.get(f"/audio/{uuid}/waveform?points=100").json()[
        "durationSeconds"
    ] == (pytest.approx(8.0))
    segment = client.post(
        f"/audio/{uuid}/trim", json={"startSeconds": 1, "endSeconds": 2}
    )
    assert segment.status_code == 422 and "Audio tab" in segment.json()["detail"]

    # No cut any more: the original is the audio of the piece again, and the files are gone.
    client.put(f"/audio/{uuid}/cuts", json={"cuts": []})
    assert _decode(client.get(f"/audio/{uuid}/file").content, tmp_path, "w2")[
        1
    ].shape == (
        rate * 10,
        2,
    )
    assert not list((data_dir / "audio" / uuid).glob("piece-r*"))
