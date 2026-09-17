"""What a reader decided about a piece, kept so they do not decide it twice.

Everything else about a score is derived: the columns come from the recorded
notes, the figures come from the ladder, the beams come from the figures. This
file holds the only things that are **not** derived, because a person chose them
and nothing in the recording implies them:

* which pile of gaps is the beat, and what it is called (D-09, D-10)
* which signature the piece is written in, and where a passage leaves it
* where the piece changes speed, and what a gap is worth after each change
  (D-19, D-20)
* which clef each hand prints, where that is not the one it normally reads
* the notes drawn as a different figure by hand (D-17)
* the notes the reader asked to start a new beam, and the ones they asked to keep in one (D-34)
* how far apart the notes on the page stand, and the runs set an equal distance apart
* the notes taken off the page
* which finger plays which note
* the stretches printed as one held note with ``tr`` over them
* the words written under the staff, and the stretches printed small
* the small notes leaning on a note

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
from typing import Literal

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


class StaffGap(BaseModel):
    """How far apart the two staves of **one line** are, where the reader has said.

    The handle between the two staves of a line. It is per line rather than per
    page because the reason for wanting it is per line: one wide chord, or one
    passage reaching down, needs room that every other line would only waste.

    Keyed by a column inside the line rather than by its place down the page. A
    place down the page is not an address — the sheet re-wraps to the window, so
    "the third line" is different music at another width — and a column never
    moves, which is what every other mark in this file is keyed by.
    """

    model_config = ConfigDict(populate_by_name=True)

    #: Any column inside the line this applies to.
    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Pixels between the two staves of that line.
    #:
    #: The floor is the drawing package's own ``MIN_STAFF_GAP`` — ``MIN_STAFF_GAP_SPACES`` (3)
    #: times ``STAFF_LINE_SPACING`` (8), so **24**. It read 30 until a reader found what that
    #: costs: the handle between two staves clamps at 24, so a line tightened past 30 made the
    #: whole reading unsaveable, and every later save of that piece failed with a 422 about a
    #: field nobody was editing. A bound here that is tighter than the one the page enforces is
    #: not a validation, it is a trap.
    #:
    #: The ceiling is deliberately looser than the package's ``MAX_STAFF_GAP`` (160). This model
    #: reads stored files as well as requests, and a bound that refuses something already written
    #: takes a reading away from whoever saved it.
    gap: float = Field(..., ge=24, le=200)


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


class ClefChange(BaseModel):
    """Where one hand starts printing a different clef.

    A transition rather than a range, exactly as :class:`KeyChange` is: at any column each hand
    prints exactly one clef, so two edits cannot disagree about what a reader is looking at. Giving
    a passage its own clef writes two of these, one where it starts and one where the hand goes back
    to the clef it normally reads.

    A reading of the page and nothing else. The pitch is untouched and playback is untouched; what
    changes is which lines the noteheads are drawn on. It is the honest answer to a left hand that
    spends a page above middle C — better than an octave bracket, because the notes are then written
    where they sound.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: ``treble`` or ``bass``.
    clef: Literal["treble", "bass"]


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

    Hand-independent: words belong to the piece rather than to a staff. They are drawn above the
    right hand, in a block of their own at the top of the system — where a singer reads them, and
    the one place on the page an octave bracket can never reach, because a bracket's height comes
    from the highest note it covers rather than from a fixed distance off the staff.

    Where the block sits, how wide it is and how large the words are can all be the reader's: one
    line is three words over eight seconds and the next a whole sentence over one, and no rule has
    the answer. All four fields are optional, so a reading saved before they existed draws exactly
    as it did.

    The range is what the reader marked, and nothing about the drawing depends on it being tidy: a
    lyric never widens the layout, because the spacing of the page comes from the notes and never
    from an annotation (D-22, D-23). A line over a long rest keeps its start and stays there.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive.
    to_column: int = Field(..., alias="toColumn", gt=0)
    text: str = Field(..., min_length=1)

    #: Where the reader dragged the block, in pixels from where the page would have put it.
    #:
    #: The columns above are still what the words belong to, so a re-wrap carries them to wherever
    #: that music went and this offset with them. ``None`` is a block nobody has moved.
    offset_x: float | None = Field(default=None, alias="offsetX")
    offset_y: float | None = Field(default=None, alias="offsetY")

    #: How wide the block is drawn, in pixels. The words wrap inside it.
    #:
    #: The bounds are the drawing package's own (``MIN_LYRIC_WIDTH`` … ``MAX_LYRIC_WIDTH``), so a
    #: reading written by hand cannot ask for a block that cannot be drawn.
    width: float | None = Field(default=None, ge=32.0, le=2000.0)

    #: How large the words are drawn, in pixels. ``None`` is the page's own size.
    font_size: float | None = Field(default=None, alias="fontSize", ge=7.0, le=36.0)

    @model_validator(mode="after")
    def _check_range(self) -> "Lyric":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"a lyric ending at column {self.to_column} does not come after its start "
                f"column {self.from_column}"
            )
        return self


class Ottava(BaseModel):
    """A stretch written an octave or two away from where it sounds.

    A reading of the page and nothing else: the pitch is untouched, playback is untouched, and
    removing the bracket prints the same notes back where they were. What it changes is how far
    from the staff the noteheads are drawn, which is the difference between a passage a player can
    read and a pile of ledger lines.

    Asked for, never inferred. The page used to suggest a bracket wherever a hand ran far outside
    its own staff and that was wrong often enough to be noise, so a page nobody has touched carries
    none.

    Per hand, because the two hands leave their staves independently. Half-open in columns, like
    every other range in this file, so two brackets that meet do not overlap on one column.
    """

    model_config = ConfigDict(populate_by_name=True)

    #: ``8va`` and ``15ma`` are written above the staff, ``8vb`` and ``15mb`` below it.
    kind: Literal["8va", "8vb", "15ma", "15mb"]
    hand: PrintedHand
    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive.
    to_column: int = Field(..., alias="toColumn", gt=0)
    #: The reader took the bracket off the page and kept the reading.
    #:
    #: Not a removal, and the distinction is the whole of the field: the notes under a hidden
    #: bracket are still written an octave from where they sound, so only the dashed line and the
    #: ``8va`` go. A player who already knows a passage is played an octave up does not need it
    #: said over every bar, and above the right hand is the most crowded strip on the page.
    #:
    #: Absent on a reading saved before a bracket could be hidden, which reads as drawn — the same
    #: answer that reading was saved with.
    hidden: bool = False

    @model_validator(mode="after")
    def _check_range(self) -> "Ottava":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"an octave bracket ending at column {self.to_column} does not come after its "
                f"start column {self.from_column}"
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


class GraceNote(BaseModel):
    """A small note drawn just before a note of the music.

    A mark and not an event. It is not in ``events.json``, it takes no column, nothing plays it,
    and no figure anywhere is measured differently because of it — which is exactly why it can be
    added and removed freely.

    ``row`` is the grace note's own pitch and ``target_row`` is the note it leans on. The two are
    separate because the mark hangs off a note it is not: the target says where to stand, ``row``
    says what to draw.

    ``kind`` is what a player does with it. An **acciaccatura** is crushed, as fast as possible, and
    prints with a slash through its stem. An **appoggiatura** leans, taking its time from the note
    it precedes, and prints without one.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    start_frame: int = Field(..., alias="startFrame", ge=0)
    #: The note it leans on.
    target_row: int = Field(..., alias="targetRow", ge=0, lt=KEY_COUNT)
    #: The grace note's own pitch.
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    kind: Literal["acciaccatura", "appoggiatura"] = "acciaccatura"


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


class SpacingRange(BaseModel):
    """A stretch the reader asked to have set wider or narrower than the page would.

    A reading of the page and nothing else. The columns inside the stretch are drawn at
    ``scale`` times the room they would take, so a crowded run of eighths can be opened up to
    read, or a thin one closed; nothing outside the stretch moves.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive, like every other stretch on the page.
    to_column: int = Field(..., alias="toColumn", ge=1)
    scale: float = Field(..., gt=0.2, le=4.0)


class EvenSpacing(BaseModel):
    """A run of one hand's notes set an equal distance apart, whatever the other hand needs.

    The page measures every column from what is drawn in it, and both staves share the column — so a
    run of even corcheas in the right hand is drawn unevenly wherever the left hand needs room at one
    of those moments. Nothing is wrong with the page when that happens; the space really is being
    used. It still reads as a mistake in the playing, because a beam of equal notes that is not
    equally spaced is what an uneven performance looks like.

    So this is the reader choosing evenness and paying for it in width, and the other hand moves with
    it. A reading of the page and nothing else: no note is renamed and the recording is untouched.

    ``scale`` is a multiple of the widest gap the run already had. One is the tightest spacing at
    which nothing has to give way, because every gap is then the sum of the widths its columns asked
    for. Below one the run is closed tighter than that and the glyphs may touch — which is allowed,
    because the widest gap is usually wide on account of the *other* hand, and a reader looking at
    their own hand's notes with room to spare is right about it. The page draws what it is told and
    the reader can see the result.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    from_column: int = Field(..., alias="fromColumn", ge=0)
    #: Exclusive, like every other stretch on the page.
    to_column: int = Field(..., alias="toColumn", ge=1)
    #: The bounds are the drawing package's own, so a stored answer is always one it can draw.
    scale: float = Field(1.0, ge=0.25, le=4.0)

    @model_validator(mode="after")
    def _check_range(self) -> "EvenSpacing":
        if self.to_column <= self.from_column:
            raise ValueError(
                f"an even-spacing run ending at column {self.to_column} does not come after its "
                f"start column {self.from_column}"
            )
        return self


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

    #: Where one hand starts printing a different clef. Empty for a piece written on the two clefs
    #: a piano score normally uses, which is the common case.
    clef_changes: list[ClefChange] = Field(default_factory=list, alias="clefChanges")

    #: The name given to the anchor pile, and the pile's own length in ms.
    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)

    speed_changes: list[SpeedChange] = Field(default_factory=list, alias="speedChanges")
    overrides: list[FigureOverride] = Field(default_factory=list)
    beam_breaks: list[BeamBreak] = Field(default_factory=list, alias="beamBreaks")

    #: Notes the reader asked to keep inside the beam they are in.
    #:
    #: The other half of ``beam_breaks``, and stored the same way. A break says "start a new group
    #: here" and beats every rule; a join says "do not", and beats the one automatic cut that is a
    #: guess — where a run of notes turns over at its lowest point. Neither can be derived: where a
    #: phrase restarts, and where it does not, are both readings of the music.
    beam_joins: list[BeamBreak] = Field(default_factory=list, alias="beamJoins")

    #: Page readings. None of these touch the matrix; see the module note.
    hidden_notes: list[HiddenNote] = Field(default_factory=list, alias="hiddenNotes")
    fingers: list[Fingering] = Field(default_factory=list)

    #: Stretches printed as one held note with ``tr`` over them.
    trills: list[Trill] = Field(default_factory=list)

    #: Small notes leaning on a note of the music.
    grace_notes: list[GraceNote] = Field(default_factory=list, alias="graceNotes")

    #: Lines of words written under the staff, over a stretch of columns.
    lyrics: list[Lyric] = Field(default_factory=list)

    #: Stretches printed smaller, because the reader offers them rather than asserts them.
    cue_ranges: list[CueRange] = Field(default_factory=list, alias="cueRanges")

    #: Stretches written an octave or two from where they sound.
    #:
    #: ``None`` and ``[]`` mean different things here, which is why this one is optional where the
    #: others are not. A reading saved before brackets were stored has never been asked the
    #: question, and the page may offer its own answer; an empty list is a reader who was asked and
    #: said none, and the page must leave it alone.
    ottavas: list[Ottava] | None = None

    #: Stretches set wider or narrower than the page would set them.
    spacings: list[SpacingRange] = Field(default_factory=list)

    #: Runs of one hand's notes set an equal distance apart, whatever the other hand needs.
    even_spacings: list[EvenSpacing] = Field(default_factory=list, alias="evenSpacings")

    #: Whether the ornaments — a sixteenth or shorter right before an eighth or longer — are
    #: left off the page. A switch on the page, remembered with the reading.
    drop_decorative: bool = Field(False, alias="dropDecorative")

    #: How large the marks over and under the staff are drawn, as a multiple of their normal size.
    #: One piece can be dense enough that fingering crowds it and another airy enough that the same
    #: numbers are hard to read, and the difference is per piece rather than per app.
    annotation_scale: float = Field(1.0, alias="annotationScale", gt=0.3, le=2.0)

    #: How much white space there is between the staves of one line and the staves of the next,
    #: in pixels. Nought puts one pair of staves directly under the pair above it.
    #:
    #: A line of the sheet is a pair of staves under one curly bracket, and a long piece wraps onto
    #: many of them. One fixed gap cannot be right for every piece: most sheets are mostly white
    #: space at it, and on a piece with high notes a low note of the left hand and a high note of
    #: the next line's right hand reach towards each other through it until the two runs of ledger
    #: lines meet. So it is per piece, like the mark size above it.
    #:
    #: ``None`` is a reading that was never asked the question — saved before the control existed —
    #: and the page draws it with its own default. A number is a reader who answered.
    line_spacing: float | None = Field(None, alias="lineSpacing", ge=0, le=240)

    #: Lines spread wider or narrower than the rest, one at a time.
    staff_gaps: list[StaffGap] = Field(default_factory=list, alias="staffGaps")

    #: Extra pixels between one note and the next, everywhere on the page.
    #:
    #: The twin of ``line_spacing``, one axis over. The page measures each column from what is drawn
    #: in it, which is right and can still be tighter than a person wants to play from — so this is
    #: the reader's own answer, charged to the columns carrying a note and to no others. The
    #: silences keep exactly the width the wall clock gives them, because that width is the one
    #: thing this page already says well.
    #:
    #: ``None`` is a reading saved before the control existed, and the page draws with its own.
    note_spacing: float | None = Field(None, alias="noteSpacing", ge=0, le=48)

    saved_at: datetime = Field(default_factory=_now, alias="savedAt")

    def describe(self) -> str:
        parts = [
            f"{self.anchor_figure.value} = {self.anchor_ms:.0f} ms at {self.frame_ms:g} ms/col"
        ]
        if self.key_signature:
            parts.append(f"in {self.key_signature}")
        if self.key_changes:
            parts.append(f"{len(self.key_changes)} key change(s)")
        if self.clef_changes:
            parts.append(f"{len(self.clef_changes)} clef change(s)")
        if self.speed_changes:
            parts.append(f"{len(self.speed_changes)} speed change(s)")
        if self.overrides:
            parts.append(f"{len(self.overrides)} note(s) renamed")
        if self.beam_breaks:
            parts.append(f"{len(self.beam_breaks)} beam break(s)")
        if self.beam_joins:
            parts.append(f"{len(self.beam_joins)} beam join(s)")
        if self.hidden_notes:
            parts.append(f"{len(self.hidden_notes)} note(s) off the page")
        if self.fingers:
            parts.append(f"{len(self.fingers)} fingering(s)")
        if self.trills:
            parts.append(f"{len(self.trills)} trill(s)")
        if self.grace_notes:
            parts.append(f"{len(self.grace_notes)} grace note(s)")
        if self.lyrics:
            parts.append(f"{len(self.lyrics)} lyric line(s)")
        if self.cue_ranges:
            parts.append(f"{len(self.cue_ranges)} cue-size stretch(es)")
        if self.ottavas:
            parts.append(f"{len(self.ottavas)} octave bracket(s)")
        return ", ".join(parts) + "."
