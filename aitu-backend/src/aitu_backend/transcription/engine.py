"""Piano transcription engines behind one stable interface.

The plan is explicit that engines will be swapped when results disappoint, so
nothing outside this module knows which model produced a note. Everything
downstream takes a ``list[NoteEvent]``.

Engines available:

| Name | Package | Notes |
|------|---------|-------|
| ``bytedance`` | ``piano_transcription_inference`` | default; the research doc's first pick |
| ``transkun``  | ``transkun``                      | neural semi-CRF, no thresholds, weights ship with the package |
| ``basic-pitch`` | ``basic_pitch`` | Spotify's model, kept as benchmark/fallback |
| ``silent`` | — | returns nothing; for tests and for wiring the UI without a model |

Both real engines import their package **lazily, inside the constructor**, so
the backend starts, the API serves and the whole test suite runs on a machine
where neither is installed. Asking for an engine that is not installed raises
:class:`EngineUnavailable` naming the install command.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Default engine name. Swap here, not at every call site.
DEFAULT_ENGINE = "bytedance"

#: ``device`` value for this Mac. Kept parameterized for future CUDA hosts.
DEFAULT_DEVICE = "cpu"


class NoteEvent(BaseModel):
    """One transcribed note, before it meets the matrix grid.

    Times are seconds from the start of the transcribed audio (or of the
    selected range — the caller offsets them).
    """

    model_config = ConfigDict(populate_by_name=True)

    midi_note: int = Field(..., alias="midiNote", ge=0, le=127)
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    velocity: int = Field(64, ge=0, le=127)

    @model_validator(mode="after")
    def _check_order(self) -> "NoteEvent":
        if self.end <= self.start:
            raise ValueError(f"A note must end after it starts ({self.end} <= {self.start})")
        return self

    @property
    def duration(self) -> float:
        return self.end - self.start


@runtime_checkable
class TranscriptionEngine(Protocol):
    """What every engine must provide."""

    #: Stable identifier used in config and in artifact metadata.
    name: str

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        """Transcribe a mono WAV into note events, ordered by start time."""


class EngineUnavailable(RuntimeError):
    """The requested engine's package is not installed."""

    def __init__(self, engine: str, package: str, install: str) -> None:
        self.engine = engine
        super().__init__(
            f"The '{engine}' transcription engine needs the '{package}' package, which is not "
            f"installed. Install it with: {install}"
        )


@dataclass
class SilentEngine:
    """Transcribes everything as silence.

    Not a joke: it lets the pipeline, the API, the artifacts and the whole UI be
    exercised end to end on a machine with no model installed, and it is what
    the tests use so they stay fast and deterministic.
    """

    name: str = "silent"

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        if not wav_path.is_file():
            raise FileNotFoundError(f"No audio at {wav_path}")
        return []


#: Where `piano_transcription_inference` expects its checkpoint, and where it
#: fetches it from. Both are hardcoded in the package (`inference.py`), so they
#: are mirrored here rather than imported.
CHECKPOINT_DIR = Path.home() / "piano_transcription_inference_data"
CHECKPOINT_NAME = "note_F1=0.9677_pedal_F1=0.9186.pth"
CHECKPOINT_URL = (
    "https://zenodo.org/record/4034264/files/"
    "CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"
)
#: The package's own sanity check: anything smaller is a failed download.
CHECKPOINT_MIN_BYTES = 160_000_000


def checkpoint_path() -> Path:
    return CHECKPOINT_DIR / CHECKPOINT_NAME


def checkpoint_present() -> bool:
    path = checkpoint_path()
    return path.is_file() and path.stat().st_size >= CHECKPOINT_MIN_BYTES


def download_checkpoint(reporter: object | None = None) -> Path:
    """Fetch the ~165 MB model checkpoint, with progress.

    **Why this exists.** `piano_transcription_inference` downloads its own
    checkpoint on first use — with ``os.system('wget ...')``. macOS does not
    ship ``wget``, so on this Mac that call fails silently, leaves a zero-byte
    file, and the next line dies inside ``torch.load`` with an error that says
    nothing about a missing download. Fetching it ourselves with the standard
    library removes the trap and gives a progress bar instead of a long pause.
    """
    import urllib.request  # noqa: PLC0415

    from aitu_backend.progress import BaseProgress, default_reporter  # noqa: PLC0415

    target = checkpoint_path()
    if checkpoint_present():
        return target

    progress = default_reporter(reporter if isinstance(reporter, BaseProgress) else None)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")

    with progress.stage("download model", total=100, message="~165 MB, once only") as stage:
        seen_percent = 0

        def hook(blocks: int, block_size: int, total_size: int) -> None:
            nonlocal seen_percent
            if total_size <= 0:
                return
            percent = min(100, int(blocks * block_size * 100 / total_size))
            if percent > seen_percent:
                stage.advance(percent - seen_percent, message=f"{percent}%")
                seen_percent = percent

        urllib.request.urlretrieve(CHECKPOINT_URL, partial, reporthook=hook)

    if partial.stat().st_size < CHECKPOINT_MIN_BYTES:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"The model checkpoint downloaded from {CHECKPOINT_URL} is too small to be valid. "
            "Check your connection and try again."
        )
    partial.replace(target)
    return target


class ByteDanceEngine:
    """``piano_transcription_inference`` — the default engine.

    Imported **lazily**, inside the constructor, so the backend starts and the
    test suite runs on a machine where torch is not installed.

    **Device.** On Apple Silicon this runs on the **CPU**, whatever you pass.
    The package only calls ``model.to(device)`` when the device string contains
    ``"cuda"`` (see its ``inference.py``), and its forward pass reads the device
    off the model's parameters — so ``"mps"`` would be accepted and then
    ignored. The parameter stays for a future CUDA host, where it does work.
    A one-minute piano clip takes a few seconds on an M-series CPU.
    """

    name = "bytedance"

    def __init__(
        self,
        device: str = DEFAULT_DEVICE,
        checkpoint: str | None = None,
        *,
        auto_download: bool = True,
        reporter: object | None = None,
    ) -> None:
        try:
            from piano_transcription_inference import PianoTranscription  # noqa: PLC0415
        except ImportError as exc:
            raise EngineUnavailable(
                "bytedance",
                "piano_transcription_inference",
                "uv sync --extra transcription   (in aitu-backend/)",
            ) from exc

        if checkpoint is None and auto_download and not checkpoint_present():
            download_checkpoint(reporter)

        self.device = device
        self._model = PianoTranscription(
            device=device,
            checkpoint_path=checkpoint or str(checkpoint_path()),
        )

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        """Transcribe a WAV into note events.

        The package returns ``{'est_note_events': [{'midi_note', 'onset_time',
        'offset_time', 'velocity'}, ...], ...}`` — verified against its
        ``utilities.RegressionPostProcessor`` rather than assumed.
        """
        return self._transcribe(wav_path)

    def transcribe_with_progress(
        self,
        wav_path: Path,
        reporter: object,
    ) -> list[NoteEvent]:
        """Transcribe while publishing the package's real model segments."""
        return self._transcribe(wav_path, reporter)

    def _transcribe(
        self,
        wav_path: Path,
        reporter: object | None = None,
    ) -> list[NoteEvent]:
        """The package's inference path with its mini-batch loop instrumented.

        Upstream prints ``Segment N / total`` from a private helper but exposes
        no callback. Mirroring that small loop here lets the terminal and SSE
        UI consume the same truthful segment count.
        """
        import librosa  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from piano_transcription_inference import sample_rate as model_rate  # noqa: PLC0415
        from piano_transcription_inference.pytorch_utils import (  # noqa: PLC0415
            move_data_to_device,
        )
        from piano_transcription_inference.utilities import (  # noqa: PLC0415
            RegressionPostProcessor,
        )

        from aitu_backend.progress import BaseProgress, default_reporter  # noqa: PLC0415

        if not wav_path.is_file():
            raise FileNotFoundError(f"No audio at {wav_path}")

        # The store's `normalized.wav` is already mono 16 kHz — which is exactly
        # `model_rate` — but resampling defensively costs nothing and makes the
        # engine usable on any WAV.
        audio, _ = librosa.load(str(wav_path), sr=model_rate, mono=True)

        # `midi_path=None` skips the MIDI write; the package guards it with
        # `if midi_path:`, so we keep the events in memory.
        audio_batch = audio[None, :]
        audio_len = audio_batch.shape[1]
        pad_len = (
            int(np.ceil(audio_len / self._model.segment_samples)) * self._model.segment_samples
            - audio_len
        )
        audio_batch = np.concatenate((audio_batch, np.zeros((1, pad_len))), axis=1)
        segments = self._model.enframe(audio_batch, self._model.segment_samples)

        progress = default_reporter(reporter if isinstance(reporter, BaseProgress) else None)
        output_lists: dict[str, list[Any]] = {}
        device = next(self._model.model.parameters()).device
        with progress.stage(
            "transcribe",
            total=len(segments),
            message=f"{len(segments)} model segments",
        ) as stage:
            for index, segment in enumerate(segments, start=1):
                batch = move_data_to_device(segment[None, :], device)
                with torch.no_grad():
                    self._model.model.eval()
                    batch_output = self._model.model(batch)
                for key, value in batch_output.items():
                    output_lists.setdefault(key, []).append(value.data.cpu().numpy())
                stage.advance(message=f"model segment {index}/{len(segments)}")

        output_dict = {key: np.concatenate(values, axis=0) for key, values in output_lists.items()}
        for key, value in output_dict.items():
            output_dict[key] = self._model.deframe(value)[0:audio_len]

        post_processor = RegressionPostProcessor(
            self._model.frames_per_second,
            classes_num=self._model.classes_num,
            onset_threshold=self._model.onset_threshold,
            offset_threshold=self._model.offset_threshod,
            frame_threshold=self._model.frame_threshold,
            pedal_offset_threshold=self._model.pedal_offset_threshold,
        )
        est_note_events, _ = post_processor.output_dict_to_midi_events(output_dict)

        return sorted(
            (
                NoteEvent(
                    midi_note=int(note["midi_note"]),
                    start=float(note["onset_time"]),
                    end=float(note["offset_time"]),
                    velocity=int(note.get("velocity", 64)),
                )
                for note in est_note_events
                if float(note["offset_time"]) > float(note["onset_time"])
            ),
            key=lambda event: (event.start, event.midi_note),
        )


class TranskunEngine:
    """Transkun 2 — a neural semi-CRF that decodes note intervals directly.

    Yan & Duan, *Scoring Time Intervals using Non-Hierarchical Transformer for
    Automatic Piano Transcription* (ISMIR 2024). MIT licensed, `pip install
    transkun`, weights shipped inside the package — no download step and no
    checkpoint path to manage.

    Why it is here alongside ByteDance
    ----------------------------------

    It is **not** strictly better, and it should not be presented as an upgrade.
    Measured on the Mr Blue Sky passage David flagged, against the stored
    ByteDance events over segment 254.3–271.5 s: 122 of the notes agree, Transkun
    finds two ByteDance misses (the D#3 and D3 that complete an octave), and
    loses four A#2 attacks ByteDance got. Differently wrong. It is here so the
    two can be compared by ear on real material, which is the only benchmark
    this project has.

    Two differences that matter downstream:

    * **No thresholds.** The semi-CRF decodes intervals rather than thresholding
      an onset/offset heatmap, so there is nothing to tune and nothing to get
      wrong. ByteDance's 0.3/0.3/0.1 have no counterpart here.
    * **Offsets are key release, not pedal release.** Transkun returns notes of
      30–300 ms where ByteDance returns 200–1700 ms for the same music. Harmless
      for this pipeline — the per-hand sustain rule overwrites durations anyway —
      but it is exactly why :mod:`.artifacts` keeps its floor at 20 ms. A 40 ms
      floor would delete a third of a Transkun transcription.

    Speed: roughly 1.4x realtime on a CPU, i.e. about seven minutes for a
    five-minute piece. Pass ``device="cuda"`` where there is a GPU.
    """

    name = "transkun"

    #: What the shipped weights are called inside the package.
    WEIGHT = "2.0.pt"
    CONF = "2.0.conf"

    def __init__(
        self,
        device: str = DEFAULT_DEVICE,
        checkpoint: str | Path | None = None,
        conf: str | Path | None = None,
        reporter: object | None = None,
    ) -> None:
        try:
            import moduleconf  # noqa: PLC0415
            import torch  # noqa: PLC0415
            import transkun  # noqa: F401, PLC0415
        except ImportError as exc:
            raise EngineUnavailable(
                "transkun", "transkun", "uv sync --extra transkun"
            ) from exc

        from importlib.resources import files  # noqa: PLC0415

        pretrained = files("transkun") / "pretrained"
        conf_path = str(conf) if conf else str(pretrained / self.CONF)
        weight_path = str(checkpoint) if checkpoint else str(pretrained / self.WEIGHT)

        manager = moduleconf.parseFromFile(conf_path)
        model_class = manager["Model"].module.TransKun
        state = torch.load(weight_path, map_location=device)

        model = model_class(conf=manager["Model"].config).to(device)
        # Upstream writes the good weights under `best_state_dict` when it has
        # them and `state_dict` when it does not; both shipped checkpoints have
        # been seen with each key.
        model.load_state_dict(state.get("best_state_dict", state.get("state_dict")), strict=False)
        model.eval()

        self.device = device
        self._model = model
        self._torch = torch
        self._reporter = reporter

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        return self._transcribe(wav_path, self._reporter)

    def transcribe_with_progress(self, wav_path: Path, reporter: object) -> list[NoteEvent]:
        return self._transcribe(wav_path, reporter)

    def _transcribe(self, wav_path: Path, reporter: object | None = None) -> list[NoteEvent]:
        """One `model.transcribe` call, with its segment loop counted.

        **Deliberately not chunked.** The loop inside `TransKun.transcribe`
        threads a `startPos` between consecutive segments — the CRF continues
        its decode across the boundary rather than restarting — so slicing the
        audio and stitching the results is not equivalent to transcribing the
        whole file. Measured on a 40 s excerpt, external chunking also shifted
        every onset by ~10 ms per chunk, which is the same order as the timing
        detail this pipeline now reasons about.

        So the file goes through in one call, and progress comes from wrapping
        `transcribeFrames`, which that loop invokes exactly once per segment.
        Reaching into the model like this is the same bargain
        :meth:`ByteDanceEngine._transcribe` already makes: upstream exposes no
        callback, and a seven-minute silent progress bar reads as a hang. If a
        future version renames that method, this falls back to a single
        indeterminate stage rather than breaking.
        """
        import librosa  # noqa: PLC0415

        from aitu_backend.progress import BaseProgress, default_reporter  # noqa: PLC0415

        if not wav_path.is_file():
            raise FileNotFoundError(f"No audio at {wav_path}")

        torch = self._torch
        model = self._model

        audio, _ = librosa.load(str(wav_path), sr=model.fs, mono=True)
        # `TransKun.transcribe` transposes, so it wants (frames, channels).
        tensor = torch.from_numpy(audio[:, None]).to(self.device)

        step = float(getattr(model, "segmentHopSizeInSecond", 8.0))
        pad = float(getattr(model, "segmentSizeInSecond", 16.0)) - step
        segments = max(1, int((len(audio) / model.fs + 2 * pad) / max(step, 0.001)) + 1)

        progress = default_reporter(reporter if isinstance(reporter, BaseProgress) else None)
        original = getattr(model, "transcribeFrames", None)

        with progress.stage(
            "transcribe",
            total=segments,
            message=f"about {segments} model segments",
        ) as stage:
            if original is not None:
                seen = 0

                def counted(*args: Any, **kwargs: Any) -> Any:
                    nonlocal seen
                    result = original(*args, **kwargs)
                    seen += 1
                    # Clamp: the segment count is derived from the model's own
                    # step size, not read from it, so it can be a segment out.
                    stage.advance(message=f"model segment {min(seen, segments)}/{segments}")
                    return result

                model.transcribeFrames = counted  # type: ignore[method-assign]
            try:
                with torch.no_grad():
                    estimated = model.transcribe(tensor)
            finally:
                if original is not None:
                    model.transcribeFrames = original  # type: ignore[method-assign]

        return sorted(
            (
                NoteEvent(
                    midi_note=int(note.pitch),
                    start=max(0.0, float(note.start)),
                    end=float(note.end),
                    velocity=max(0, min(127, int(note.velocity))),
                )
                # A non-positive pitch is a pedal control change, not a note —
                # upstream encodes CC numbers as negative pitches. Pedals are
                # discarded here exactly as they are for ByteDance.
                for note in estimated
                if note.pitch > 0 and float(note.end) > float(note.start)
            ),
            key=lambda event: (event.start, event.midi_note),
        )


class BasicPitchEngine:
    """Spotify's Basic Pitch — the benchmark and fallback engine.

    **Not installable alongside the rest of this project.** basic-pitch 0.4.0
    pins ``tensorflow(-macos) <2.15.1``, and cp312 wheels for tensorflow only
    start at 2.16.1 — so it cannot run on Python 3.12 on any platform. It is
    therefore not a project extra; to benchmark against it, install it in a
    separate Python 3.11 environment (see
    ``notebooks/transcription-benchmark/README.md``).

    The class stays because the interface is the point: when basic-pitch
    supports 3.12, or when a run happens in that separate environment, nothing
    else has to change.
    """

    name = "basic-pitch"

    def __init__(self, device: str = DEFAULT_DEVICE) -> None:
        try:
            from basic_pitch.inference import predict  # noqa: PLC0415
        except ImportError as exc:
            raise EngineUnavailable(
                "basic-pitch",
                "basic_pitch",
                "a separate Python 3.11 venv — it pins tensorflow <2.15.1, which has no "
                "Python 3.12 wheels. See notebooks/transcription-benchmark/README.md",
            ) from exc

        self.device = device
        self._predict = predict

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        if not wav_path.is_file():
            raise FileNotFoundError(f"No audio at {wav_path}")

        _, midi_data, _ = self._predict(str(wav_path))
        events = [
            NoteEvent(
                midi_note=int(note.pitch),
                start=float(note.start),
                end=float(note.end),
                velocity=int(note.velocity),
            )
            for instrument in midi_data.instruments
            for note in instrument.notes
            if note.end > note.start
        ]
        return sorted(events, key=lambda event: (event.start, event.midi_note))


#: Constructors by name. Add a new engine here and it becomes selectable.
ENGINES = {
    "bytedance": ByteDanceEngine,
    "transkun": TranskunEngine,
    "basic-pitch": BasicPitchEngine,
    "silent": SilentEngine,
}


def create_engine(name: str = DEFAULT_ENGINE, **options: Any) -> TranscriptionEngine:
    """Build an engine by name. Raises :class:`EngineUnavailable` if missing."""
    try:
        factory = ENGINES[name]
    except KeyError as exc:
        known = ", ".join(sorted(ENGINES))
        raise ValueError(f"Unknown transcription engine '{name}'. Known: {known}") from exc
    return factory(**options)


def engine_installed(name: str) -> bool:
    """Is this engine's package importable?

    Deliberately checks the **import**, not a full construction: building the
    ByteDance engine loads a 165 MB checkpoint into memory, which is not
    something an availability probe should do.
    """
    import importlib.util  # noqa: PLC0415

    if name == "silent":
        return True
    module = {
        "bytedance": "piano_transcription_inference",
        "transkun": "transkun",
        "basic-pitch": "basic_pitch",
    }.get(name)
    if module is None:
        return False
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def available_engines() -> dict[str, bool]:
    """Which engines can run here. Powers `GET /matrix/engines` and the UI."""
    return {name: engine_installed(name) for name in ENGINES}
