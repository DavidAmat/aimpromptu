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

from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.schemas.time_matrix import (
    DEFAULT_FRAME_MS,
    BeamBreak,
    FigureName,
    FigureOverride,
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


class Ottava(BaseModel):
    """A stretch over which one hand is written an octave or two from where it sounds.

    Part of the reading rather than of the recording. A passage far outside its
    own staff prints as a stack of ledger lines nobody counts accurately; under
    a bracket it prints inside the staff and the bracket says how to read it.
    The screen proposes these from how far outside its staff each hand runs, and
    the reader keeps, moves or clears them — which is exactly why they are
    stored: a cleared bracket that came back on the next visit would make the
    suggestion impossible to disagree with (D-38).
    """

    model_config = ConfigDict(populate_by_name=True)

    #: ``8va``, ``8vb``, ``15ma`` or ``15mb``.
    kind: str
    #: ``right`` or ``left``. Either hand takes either direction: a left hand
    #: crossing high asks for ``8va`` exactly as a right hand does.
    hand: str
    from_column: int = Field(..., alias="fromColumn", ge=0)
    to_column: int = Field(..., alias="toColumn", ge=0)


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

    #: The octave brackets on the page. ``None`` on a reading saved before they
    #: existed, which the screen reads as "never decided" and answers with its
    #: own suggestion; an empty list means the reader decided on none.
    ottavas: list[Ottava] | None = None

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
        if self.ottavas:
            parts.append(f"{len(self.ottavas)} octave bracket(s)")
        return ", ".join(parts) + "."
