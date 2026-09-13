"""Wire shapes for Epic 11 range editing: a staged session and its preview."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.schemas.time_matrix import FigureName, TimeScorePayload

SlowdownChoice = Literal[1, 2, 4]


class EditWindow(BaseModel):
    """The stretch being replaced, stored as both columns and seconds."""

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    end_frame: int = Field(..., alias="endFrame", gt=0)
    start_seconds: float = Field(..., alias="startSeconds", ge=0)
    end_seconds: float = Field(..., alias="endSeconds", gt=0)
    frame_ms: float = Field(..., alias="frameMs", gt=0)

    @property
    def window_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class DroppedMarks(BaseModel):
    """Editorial marks anchored inside the window, counted by kind."""

    model_config = ConfigDict(populate_by_name=True)

    figure_overrides: int = Field(0, alias="figureOverrides")
    beam_breaks: int = Field(0, alias="beamBreaks")
    hidden_notes: int = Field(0, alias="hiddenNotes")
    fingerings: int = Field(0, alias="fingerings")

    @property
    def total(self) -> int:
        return self.figure_overrides + self.beam_breaks + self.hidden_notes + self.fingerings


class StartEditRequest(BaseModel):
    """Open a disposable session for one window.

    Either pair is enough. Columns are what the reader clicked; seconds are what
    the splice uses. The other pair is computed once and frozen.
    """

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int | None = Field(None, alias="startFrame", ge=0)
    end_frame: int | None = Field(None, alias="endFrame", gt=0)
    start_seconds: float | None = Field(None, alias="startSeconds", ge=0)
    end_seconds: float | None = Field(None, alias="endSeconds", gt=0)
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    slowdown: SlowdownChoice | None = Field(default=1)
    splice_audio: bool = Field(True, alias="spliceAudio")
    click_interval_ms: float | None = Field(None, alias="clickIntervalMs", gt=0)


class PatchEditRequest(BaseModel):
    """Change the speed factor or the trim without recording again."""

    model_config = ConfigDict(populate_by_name=True)

    slowdown: SlowdownChoice | None = None
    #: ``True`` switches to Fit to the window; the factor is measured from the take.
    fit: bool = False
    splice_audio: bool | None = Field(None, alias="spliceAudio")
    click_interval_ms: float | None = Field(None, alias="clickIntervalMs", gt=0)
    #: How much of the take to keep after its first onset. Omit to use the default.
    trim_length_seconds: float | None = Field(None, alias="trimLengthSeconds", gt=0)
    #: Range on the untrimmed take, chosen in the review dialog before transcribing.
    take_start_seconds: float | None = Field(None, alias="takeStartSeconds", ge=0)
    take_end_seconds: float | None = Field(None, alias="takeEndSeconds", gt=0)


class EditSessionOut(BaseModel):
    """What the toolbox needs to draw the session."""

    model_config = ConfigDict(populate_by_name=True)

    session_uuid: str = Field(..., alias="sessionUuid")
    audio_uuid: str = Field(..., alias="audioUuid")
    start_frame: int = Field(..., alias="startFrame")
    end_frame: int = Field(..., alias="endFrame")
    start_seconds: float = Field(..., alias="startSeconds")
    end_seconds: float = Field(..., alias="endSeconds")
    frame_ms: float = Field(..., alias="frameMs")
    window_seconds: float = Field(..., alias="windowSeconds")
    slowdown: int | None = None
    factor: float
    splice_audio: bool = Field(..., alias="spliceAudio")
    click_interval_ms: float | None = Field(None, alias="clickIntervalMs")
    has_take: bool = Field(..., alias="hasTake")
    has_events: bool = Field(..., alias="hasEvents")
    first_onset_seconds: float | None = Field(None, alias="firstOnsetSeconds")
    trim_length_seconds: float | None = Field(None, alias="trimLengthSeconds")
    untrimmed_duration_seconds: float | None = Field(None, alias="untrimmedDurationSeconds")
    expected_take_seconds: float | None = Field(None, alias="expectedTakeSeconds")
    take_start_seconds: float | None = Field(None, alias="takeStartSeconds")
    take_end_seconds: float | None = Field(None, alias="takeEndSeconds")


class ConfirmationOut(BaseModel):
    """What accept will do, said before the button is pressed."""

    model_config = ConfigDict(populate_by_name=True)

    notes_removed: int = Field(..., alias="notesRemoved")
    notes_arriving: int = Field(..., alias="notesArriving")
    dropped_marks: DroppedMarks = Field(..., alias="droppedMarks")
    splice_audio: bool = Field(..., alias="spliceAudio")
    length_unchanged: bool = Field(True, alias="lengthUnchanged")
    window_seconds: float = Field(..., alias="windowSeconds")
    next_version: int = Field(..., alias="nextVersion")


class PeakOut(BaseModel):
    """One pile of gaps, matching the Rhythm tab's peak plot."""

    model_config = ConfigDict(populate_by_name=True)

    centre_ms: float = Field(..., alias="centreMs")
    median_ms: float = Field(..., alias="medianMs")
    mean_ms: float = Field(..., alias="meanMs")
    count: int
    share: float
    lo_ms: float = Field(..., alias="loMs")
    hi_ms: float = Field(..., alias="hiMs")


class LabelledPeakOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    peak: PeakOut
    figure: FigureName
    figure_ms: float = Field(..., alias="figureMs")
    percent_off: float = Field(..., alias="percentOff")
    tresillo_of: FigureName | None = Field(None, alias="tresilloOf")
    name: str


class PreviewOut(BaseModel):
    """The scaled take drawn as a short sheet, with its own peak plot."""

    model_config = ConfigDict(populate_by_name=True)

    session: EditSessionOut
    confirmation: ConfirmationOut
    score: TimeScorePayload
    peaks: list[PeakOut]
    labelled: list[LabelledPeakOut]
    take_note_count: int = Field(..., alias="takeNoteCount")
    scaled_note_count: int = Field(..., alias="scaledNoteCount")


class AcceptOut(BaseModel):
    """What happened when the splice was written."""

    model_config = ConfigDict(populate_by_name=True)

    version: int
    duration_seconds: float = Field(..., alias="durationSeconds")
    notes_removed: int = Field(..., alias="notesRemoved")
    notes_arriving: int = Field(..., alias="notesArriving")
    dropped_marks: DroppedMarks = Field(..., alias="droppedMarks")
    audio_spliced: bool = Field(..., alias="audioSpliced")
    audio_mismatch: bool = Field(..., alias="audioMismatch")
