"""The five-step pipeline: audio -> raw -> collapsed -> clean -> two-hands.

One entry point for the UI, and one rule that shapes everything else:

    **The raw matrix is transcribed once and kept forever. Every later
    granularity or BPM is recomputed from it, never from an intermediate.**

That is what makes the Matrix tab's in-situ switching instant — steps 3-5 are
pure numpy over a few thousand columns, so a granularity change is milliseconds
while a transcription is tens of seconds.

Artifacts land under ``data/audio/<uuid>/matrices/`` so every Playground tab
reads the same files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aitu_backend.audio import store
from aitu_backend.matrix.cleaning import clean_sustains
from aitu_backend.matrix.granularity import collapse_to
from aitu_backend.matrix.hands import TwoHands, split_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.storage.matrix_store import load_matrix, save_matrix
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    NoteEvent,
    TranscriptionEngine,
    create_engine,
)
from aitu_backend.transcription.events_to_matrix import (
    RAW_GRANULARITY,
    BuildReport,
    events_to_raw_matrix,
    shift_events,
)

#: Subfolder of an audio's uuid folder holding its matrices.
MATRICES_DIR = "matrices"

#: File names inside it. The raw one is keyed by nothing but "raw": there is
#: only ever one, and it is the source of everything else.
RAW_FILE = "raw.npz"


@dataclass(frozen=True)
class PipelineResult:
    """Every artifact one run produced, in memory and on disk."""

    audio_uuid: str
    raw: PianoMatrix
    collapsed: PianoMatrix
    clean: PianoMatrix
    hands: TwoHands
    tempo_bpm: float
    granularity: Granularity
    #: Only present when the run actually transcribed.
    build: BuildReport | None = None
    engine_name: str | None = None

    @property
    def frame_count(self) -> int:
        return self.clean.frame_count

    def step(self, name: MatrixProcessingStep | str) -> PianoMatrix:
        """Fetch one processing step by name — what `GET /matrix/{id}?step=` needs."""
        step = MatrixProcessingStep(name)
        if step is MatrixProcessingStep.RAW:
            return self.raw
        if step is MatrixProcessingStep.COLLAPSED:
            return self.collapsed
        if step is MatrixProcessingStep.CLEAN:
            return self.clean
        return self.hands.right


# ------------------------------------------------------------------- storage


def matrices_dir(audio_uuid: str) -> Path:
    return store.get(audio_uuid).directory / MATRICES_DIR


def raw_path(audio_uuid: str) -> Path:
    return matrices_dir(audio_uuid) / RAW_FILE


def derived_path(audio_uuid: str, step: MatrixProcessingStep, granularity: Granularity) -> Path:
    """Derived artifacts are keyed by step **and** granularity.

    Two granularities of the same piece coexist on disk, so switching back to
    one you already looked at is a file read rather than a recompute.
    """
    return matrices_dir(audio_uuid) / f"{step.value}_{granularity.value}.npz"


def hands_paths(audio_uuid: str, granularity: Granularity) -> tuple[Path, Path]:
    folder = matrices_dir(audio_uuid)
    return (
        folder / f"two-hands_{granularity.value}_right.npz",
        folder / f"two-hands_{granularity.value}_left.npz",
    )


def has_raw(audio_uuid: str) -> bool:
    return raw_path(audio_uuid).is_file()


def load_raw(audio_uuid: str, tempo_bpm: float) -> PianoMatrix:
    """Read the stored raw matrix.

    ``tempo_bpm`` is supplied rather than stored because the raw matrix's *cells*
    do not depend on it — only the wall-clock meaning of a column does. Changing
    BPM reinterprets the same grid.
    """
    return PianoMatrix.from_coo_payload(
        load_matrix(raw_path(audio_uuid)),
        granularity=RAW_GRANULARITY,
        tempo_bpm=tempo_bpm,
        processing_step=MatrixProcessingStep.RAW,
    )


def _persist(result: PipelineResult) -> None:
    uuid = result.audio_uuid
    save_matrix(raw_path(uuid), result.raw.to_coo_payload())
    save_matrix(
        derived_path(uuid, MatrixProcessingStep.COLLAPSED, result.granularity),
        result.collapsed.to_coo_payload(),
    )
    save_matrix(
        derived_path(uuid, MatrixProcessingStep.CLEAN, result.granularity),
        result.clean.to_coo_payload(),
    )
    right_path, left_path = hands_paths(uuid, result.granularity)
    save_matrix(right_path, result.hands.right.to_coo_payload())
    save_matrix(left_path, result.hands.left.to_coo_payload())


# ------------------------------------------------------------------ the steps


def derive(
    raw: PianoMatrix,
    audio_uuid: str,
    tempo_bpm: float,
    granularity: Granularity,
    *,
    build: BuildReport | None = None,
    engine_name: str | None = None,
    reporter: BaseProgress | None = None,
) -> PipelineResult:
    """Steps 3-5: collapse, clean, split. Pure numpy, no transcription.

    This is the whole of a recompute, and the reason one is sub-second.
    """
    progress = default_reporter(reporter)

    # The raw matrix's cells are BPM-independent; only its interpretation moves.
    source = raw.with_grid(raw.grid, tempo_bpm=tempo_bpm)

    collapsed = collapse_to(source, granularity, reporter=progress)
    clean = clean_sustains(collapsed, reporter=progress)
    with progress.stage("two-hands", total=1) as stage:
        hands = split_hands(clean)
        stage.advance()

    return PipelineResult(
        audio_uuid=audio_uuid,
        raw=source,
        collapsed=collapsed,
        clean=clean,
        hands=hands,
        tempo_bpm=tempo_bpm,
        granularity=granularity,
        build=build,
        engine_name=engine_name,
    )


def transcribe_audio(
    audio_uuid: str,
    tempo_bpm: float,
    *,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    reporter: BaseProgress | None = None,
) -> tuple[PianoMatrix, BuildReport, str]:
    """Steps 1-2: audio -> note events -> raw matrix.

    A time range transcribes only that slice: the WAV is cut first, so the
    engine never sees the rest of the piece and the events come back already
    relative to the range start.
    """
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        from aitu_backend.audio import ingest  # noqa: PLC0415 - avoids a cycle at import time

        ingest.finalize(audio_uuid)
        entry = store.get(audio_uuid)

    model = create_engine(engine) if isinstance(engine, str) else engine
    progress = default_reporter(reporter)

    source_wav = entry.normalized_path
    duration = entry.metadata.duration_seconds or 0.0
    offset = 0.0

    if start_seconds is not None and end_seconds is not None:
        from aitu_backend.audio import formats  # noqa: PLC0415

        clip = entry.directory / "transcribe_range.wav"
        formats.slice_wav(source_wav, clip, start_seconds, end_seconds)
        source_wav = clip
        duration = end_seconds - start_seconds
        offset = start_seconds

    with progress.stage("transcribe", total=1, message=model.name) as stage:
        events: list[NoteEvent] = model.transcribe(source_wav)
        stage.advance()

    if offset and events and min(event.start for event in events) >= offset:
        # Defensive: an engine that reports absolute times despite the clip.
        events = shift_events(events, offset)

    report = events_to_raw_matrix(
        events,
        duration_seconds=max(duration, 0.001),
        tempo_bpm=tempo_bpm,
        title=entry.metadata.alias,
        reporter=progress,
    )
    return report.matrix, report, model.name


def run_pipeline(
    audio_uuid: str,
    tempo_bpm: float,
    target_granularity: Granularity | str,
    *,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    reuse_raw: bool = True,
    reporter: BaseProgress | None = None,
) -> PipelineResult:
    """The full five steps, persisting every artifact.

    ``reuse_raw`` (default) skips transcription when a raw matrix already exists
    for this audio — the common case when only BPM or granularity changed.
    Pass ``False`` to force a re-transcription, e.g. after switching engines.
    """
    granularity = Granularity(target_granularity)
    ranged = start_seconds is not None and end_seconds is not None

    if reuse_raw and not ranged and has_raw(audio_uuid):
        return recompute(audio_uuid, tempo_bpm, granularity, reporter=reporter)

    raw, build, engine_name = transcribe_audio(
        audio_uuid,
        tempo_bpm,
        engine=engine,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        reporter=reporter,
    )
    result = derive(
        raw,
        audio_uuid,
        tempo_bpm,
        granularity,
        build=build,
        engine_name=engine_name,
        reporter=reporter,
    )
    _persist(result)
    return result


def recompute(
    audio_uuid: str,
    tempo_bpm: float,
    target_granularity: Granularity | str,
    *,
    reporter: BaseProgress | None = None,
) -> PipelineResult:
    """Re-run steps 3-5 from the stored raw matrix. Never re-transcribes.

    This is what a BPM or granularity change calls, and what has to stay under
    a second for the Matrix tab to feel instant.
    """
    if not has_raw(audio_uuid):
        raise FileNotFoundError(
            f"Audio {audio_uuid} has no raw matrix yet — run the pipeline once first."
        )
    granularity = Granularity(target_granularity)
    raw = load_raw(audio_uuid, tempo_bpm)
    result = derive(raw, audio_uuid, tempo_bpm, granularity, reporter=reporter)
    _persist(result)
    return result


def stored_granularities(audio_uuid: str) -> list[Granularity]:
    """Granularities already computed for this audio, coarsest first."""
    folder = matrices_dir(audio_uuid)
    if not folder.is_dir():
        return []
    found = {
        Granularity(path.stem.split("_", 1)[1])
        for path in folder.glob(f"{MatrixProcessingStep.CLEAN.value}_*.npz")
    }
    from aitu_backend.schemas.matrix import GRANULARITY_HIERARCHY  # noqa: PLC0415

    return [gran for gran in GRANULARITY_HIERARCHY if gran in found]
