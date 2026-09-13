"""What a reader decided about a piece, kept so they do not decide it twice.

Everything else about a score is derived: the columns come from the recorded
notes, the figures come from the ladder, the beams come from the figures. This
file holds the only things that are **not** derived, because a person chose them
and nothing in the recording implies them:

* which pile of gaps is the beat, and what it is called (D-09, D-10)
* which signature the piece is written in, and where a passage leaves it
* where the piece changes speed, and what a gap is worth after each change
  (D-19, D-20)
* the notes drawn as a different figure by hand (D-17)
* the notes the reader asked to start a new beam (D-34)
* the notes taken off the page
* which finger plays which note
* the stretches printed as one held note with ``tr`` over them
* the words written under the staff, and the stretches printed small

Those two are readings of the page, not corrections to the recording. A note the
transcriber invented out of a pedal blur is still in the matrix after the reader
stops drawing it; the hidden set is held beside the matrix and folded in on the
way to the drawing, so undoing it restores the note exactly.

**Which hand plays a note is not here.** That one is a fact about the playing
rather than about this page: it survives a change of column length, it decides
the printed length of its neighbours, and everything downstream is derived from
it. So it is written onto the note event and the matrix is built with it — see
``pin_hands`` — and nothing about it is stored in this file.

None of it changes the music. Losing it costs a person their reading of the
piece, which they then have to do again from the plot, and that is the whole
reason it is stored.

**The frame length is part of it.** A rhythm named at 40 ms is a set of column
numbers, and the same columns mean different moments at 20 ms. Storing the frame
length beside them is what lets a reload know whether the numbers it is holding
still refer to what they referred to.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aitu_backend.matrix.keys import KEY_COUNT
from aitu_backend.schemas.time_matrix import (
    DEFAULT_FRAME_MS,
    BeamBreak,
    FigureName,
    FigureOverride,
    PrintedHand,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SpeedChange(BaseModel):
    """A place the piece changes speed, and what a gap is worth from there on.

    Keyed by column, which is absolute wall clock, so a boundary never moves when
    anything else about the reading changes (D-19).
    """

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)


class KeyChange(BaseModel):
    """Where the piece leaves its main signature, and what it changes to.

    A transition rather than a range: at any column exactly one signature is
    sounding, so two edits cannot disagree about what a reader is looking at.
    Giving a passage its own key writes two of these, one where it starts and one
    where the piece goes back to what it was.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_column: int = Field(..., alias="fromColumn", ge=0)
    key_signature: str = Field(..., alias="keySignature")


class HiddenNote(BaseModel):
    """A note the reader took off the page.

    Addressed without a hand. The two hands can never strike the same key in the
    same frame — the matrix is rejected if they do — so ``(start_frame, row)``
    already names one note, and leaving the hand out is what lets the address
    survive a move to the other staff.
    """

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    row: int = Field(..., ge=0, lt=KEY_COUNT)


class Trill(BaseModel):
    """A stretch the reader asked to print as one held note with ``tr`` over it.

    A reading of the page, like every other model in this file: the alternations are all still in
    ``events.json``, playback still sounds every one of them (D-29), and removing the mark prints
    them again. What the mark changes is only which noteheads are drawn.

    ``row`` is the note that stays — the lower of the two, because ``tr`` means "alternate with the
    note above". It is stored rather than re-derived so that accepting a suggestion and then editing
    the notes underneath cannot silently move the mark to a different pitch.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    start_frame: int = Field(..., alias="startFrame", ge=0)
    #: One past the column of the run's last onset.
    end_frame: int = Field(..., alias="endFrame", gt=0)
    row: int = Field(..., ge=0, lt=KEY_COUNT)

    @model_validator(mode="after")
    def _check_range(self) -> "Trill":
        if self.end_frame <= self.start_frame:
            raise ValueError(
                f"a trill ending at frame {self.end_frame} does not come after its start "
                f"frame {self.start_frame}"
            )
        return self


class Lyric(BaseModel):
    """A line of words written under the staff, across a stretch of columns.

    Hand-independent: words belong to the piece rather than to a staff, and they are drawn under
    the lower staff whichever hand is singing them.

    The range is what the reader marked, and nothing about the drawing depends on it being tidy: a
    lyric never widens the layout, because the spacing of the page comes from the notes and never
    from an annotation (D-22, D-23). A line over a long rest keeps its start and stays there.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive.
    to_column: int = Field(..., alias="toColumn", gt=0)
    text: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_range(self) -> "Lyric":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"a lyric ending at column {self.to_column} does not come after its start "
                f"column {self.from_column}"
            )
        return self


class CueRange(BaseModel):
    """A stretch printed smaller than the rest of the page.

    Asked for, never inferred. A florid run in one hand set at full size crowds the other hand off
    the system; set smaller it takes less width and reads as decoration, which is what it is.

    The narrowing is allowed to move the notes **inside** the mark and nothing outside it, which is
    the same locality D-21 gives a ladder change.
    """

    model_config = ConfigDict(populate_by_name=True)

    #: ``"right"``, ``"left"``, or ``"single"`` for both staves at once.
    hand: str = "single"
    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive.
    to_column: int = Field(..., alias="toColumn", gt=0)

    @model_validator(mode="after")
    def _check_range(self) -> "CueRange":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"a cue-size stretch ending at column {self.to_column} does not come after its "
                f"start column {self.from_column}"
            )
        return self


class Fingering(BaseModel):
    """Which finger plays one note.

    Keyed by the staff the note is *drawn* on, so a fingering moves with a note
    the reader sent across. Several on one chord print stacked, in ascending
    order, which is how fingering is written.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    start_frame: int = Field(..., alias="startFrame", ge=0)
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    finger: int = Field(..., ge=1, le=5)


class SavedRhythm(BaseModel):
    """One reader's reading of one piece.

    Stored under the audio it belongs to. There is one per piece: a second
    reading replaces the first, because a rhythm is a decision rather than a
    version, and the thing a reader wants back is the last one they were happy
    with.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field("1.0", alias="schemaVersion")

    #: Which hand's gaps the plot was read from. Not part of the sheet, but it is
    #: what the reader was looking at and returning them to the other hand's plot
    #: would be a small surprise every time.
    hand: str = "right"
    #: The column length the columns below were numbered at.
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)

    #: The signature the whole piece is written in, as its major key: ``C``,
    #: ``Bb``, ``F#`` and so on. Absent on a reading saved before this existed,
    #: and absent means C, which is what those readings were drawn in.
    #:
    #: Part of the reading rather than of the recording. The recorded notes say
    #: which keys were pressed and nothing about whether a black key is an F
    #: sharp or a G flat, so nobody but the reader can answer it.
    key_signature: str | None = Field(None, alias="keySignature")

    #: Where a passage leaves that signature. Empty for a piece written in one
    #: key from beginning to end, which is the common case.
    key_changes: list[KeyChange] = Field(default_factory=list, alias="keyChanges")

    #: The name given to the anchor pile, and the pile's own length in ms.
    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)

    speed_changes: list[SpeedChange] = Field(default_factory=list, alias="speedChanges")
    overrides: list[FigureOverride] = Field(default_factory=list)
    beam_breaks: list[BeamBreak] = Field(default_factory=list, alias="beamBreaks")

    #: Page readings. None of these touch the matrix; see the module note.
    hidden_notes: list[HiddenNote] = Field(default_factory=list, alias="hiddenNotes")
    fingers: list[Fingering] = Field(default_factory=list)

    #: Stretches printed as one held note with ``tr`` over them.
    trills: list[Trill] = Field(default_factory=list)

    #: Lines of words written under the staff, over a stretch of columns.
    lyrics: list[Lyric] = Field(default_factory=list)

    #: Stretches printed smaller, because the reader offers them rather than asserts them.
    cue_ranges: list[CueRange] = Field(default_factory=list, alias="cueRanges")

    #: How large the marks over and under the staff are drawn, as a multiple of their normal size.
    #: One piece can be dense enough that fingering crowds it and another airy enough that the same
    #: numbers are hard to read, and the difference is per piece rather than per app.
    annotation_scale: float = Field(1.0, alias="annotationScale", gt=0.3, le=2.0)

    saved_at: datetime = Field(default_factory=_now, alias="savedAt")

    def describe(self) -> str:
        parts = [
            f"{self.anchor_figure.value} = {self.anchor_ms:.0f} ms at {self.frame_ms:g} ms/col"
        ]
        if self.key_signature:
            parts.append(f"in {self.key_signature}")
        if self.key_changes:
            parts.append(f"{len(self.key_changes)} key change(s)")
        if self.speed_changes:
            parts.append(f"{len(self.speed_changes)} speed change(s)")
        if self.overrides:
            parts.append(f"{len(self.overrides)} note(s) renamed")
        if self.beam_breaks:
            parts.append(f"{len(self.beam_breaks)} beam break(s)")
        if self.hidden_notes:
            parts.append(f"{len(self.hidden_notes)} note(s) off the page")
        if self.fingers:
            parts.append(f"{len(self.fingers)} fingering(s)")
        if self.trills:
            parts.append(f"{len(self.trills)} trill(s)")
        if self.lyrics:
            parts.append(f"{len(self.lyrics)} lyric line(s)")
        if self.cue_ranges:
            parts.append(f"{len(self.cue_ranges)} cue-size stretch(es)")
        return ", ".join(parts) + "."
