"""Every shape the video path puts on the wire or on disk.

This is the contract `04-synthesia-to-notes` Phase 2 builds and Phase 3 extends.
Four groups:

| Group | Models | Written by |
|-------|--------|------------|
| the piano overlay | :class:`Calibration`, :class:`PianoKey`, :class:`KeyLane` | the finder, and the calibration UI |
| what the detector saw | :class:`DetectedRun`, :class:`Detection` | `video/detector.py` |
| the example set | :class:`Annotation`, :class:`FrameExample`, :class:`ExampleScore` | the annotation page |
| one video | :class:`VideoMetadata`, :class:`ScrollSpeed`, :class:`VideoMeasurement`, :class:`FrameLine` | `video/store.py`, `video/motion.py`, `video/reading.py` |

Two rules from the frozen decisions shape all of it:

* **Every geometric threshold is in white key widths, never in pixels** (V-22,
  V-38). Pixels appear here only as coordinates inside one picture; every
  *length* that a rule compares against is a multiple of the median white key
  width, :attr:`Calibration.white_width`, or of the local one.
* **Released is the default and is never written down** (V-19). An annotation and
  a detection both carry onsets and sustains, and nothing else.
"""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from aitu_backend.schemas.metadata import CamelModel

#: The five black keys of an octave, as pitch classes, in pattern order: C#, D#,
#: F#, G#, A#. A black key follows every white key whose pitch class is in
#: :data:`WHITE_WITH_BLACK_AFTER`.
BLACK_PITCH_CLASSES = [1, 3, 6, 8, 10]
WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11]
WHITE_WITH_BLACK_AFTER = {0, 2, 5, 7, 9}


def expected_black_count(first_white_pitch_class: int, white_count: int) -> int:
    """How many black keys the pattern puts between ``white_count`` white keys.

    The pattern of twos and threes is the whole rule (V-10): a black key sits
    between two white keys two semitones apart, and never between Mi and Fa or
    between Si and Do.
    """
    first = WHITE_PITCH_CLASSES.index(first_white_pitch_class)
    return sum(
        1
        for i in range(white_count - 1)
        if WHITE_PITCH_CLASSES[(first + i) % 7] in WHITE_WITH_BLACK_AFTER
    )


# ------------------------------------------------------------ the overlay ---


class PianoRect(CamelModel):
    """The one rectangle the user drags over the piano area (V-37).

    In picture pixels, and the angle in degrees, positive clockwise on the
    screen. The rectangle is rotated about its top left corner, so its top edge
    runs from (x, y) along (cos angle, sin angle); every border of the overlay is
    a distance along that edge.
    """

    x: float
    y: float
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    angle: float = 0.0


class BlackBorder(CamelModel):
    """The two borders of one black key, along the top edge of the rectangle."""

    left: float
    right: float


class Found(CamelModel):
    """What the finder said about its own answer, so a weak one is visible.

    ``corrected`` lists the white key borders the user dragged by hand
    afterwards, by index into :attr:`Calibration.white_borders`; a hand
    correction is never mistaken for the finder's own answer.
    """

    route: str = "A"
    confidence: float = 0.0
    extrapolated: list[int] = Field(default_factory=list)
    confirmed: list[int] = Field(default_factory=list)
    corrected: list[int] = Field(default_factory=list)


class Calibration(CamelModel):
    """The piano overlay of one picture: per-key borders (V-38).

    It is everything the detector needs to know about where the piano is. The
    user drags one rectangle over the piano area and the app finds every key
    inside it (V-37); what is kept is the border of every key, along the top
    edge of that rectangle, and not a grid.

    The picture it describes is always at the working resolution — the width the
    detector reads and the width the browser is served — so a coordinate here
    means the same thing in the UI and in the detector.
    """

    #: Width and height of the picture this calibration was made against.
    image_width: int = Field(..., alias="imageWidth", gt=0)
    image_height: int = Field(..., alias="imageHeight", gt=0)

    #: The one rectangle, kept so it comes back where it was left.
    piano_rect: PianoRect = Field(..., alias="pianoRect")
    #: The top edge of the piano: one horizontal line (V-11). A rectangle tip
    #: crossing it is an onset.
    upper_line: float = Field(..., alias="upperLine")
    #: The white key borders along the top edge of the rectangle, left to right:
    #: one more than the white keys.
    white_borders: list[float] = Field(..., alias="whiteBorders")
    #: The borders of every black key, in pitch order. Their count is fixed by
    #: the pattern, and any other count is refused.
    black_borders: list[BlackBorder] = Field(..., alias="blackBorders")
    #: How far down the rectangle the black keys reach. Drawn, never read by a
    #: detection rule: the detector never looks below the upper line.
    black_depth: float = Field(..., alias="blackDepth", gt=0)
    #: The median white key width, in picture pixels along the top edge. Derived
    #: from the borders when it is left at zero, never set by hand. It is the unit
    #: of V-22 for every length that is not about one key (V-38).
    white_width: float = Field(0.0, alias="whiteWidth", ge=0)

    #: Pitch class of the leftmost white key, 0 = C … 11 = B. It comes from the
    #: black key pattern, never from a colour (V-10).
    first_white_pitch_class: int = Field(9, alias="firstWhitePitchClass", ge=0, le=11)
    #: Octave of that leftmost white key. This is the one thing the user says.
    first_white_octave: int = Field(0, alias="firstWhiteOctave", ge=-1, le=8)

    #: The roll is bounded above as well as below (V-28). Nothing above this row
    #: is music. Zero on a screenshot, where there is no motion to measure it.
    roll_top: float = Field(0.0, alias="rollTop", ge=0)
    #: Rows above the upper line where the strike light makes the picture
    #: unreadable (V-08, V-24). Zero means "use the default of 1.75 white key
    #: widths"; a video measures it.
    guard_band: float = Field(0.0, alias="guardBand", ge=0)

    #: What the finder said about its answer. None on a calibration nobody found.
    found: Found | None = None
    #: Free text — where this calibration came from, or what is odd about it.
    note: str = ""

    @model_validator(mode="after")
    def _check(self) -> "Calibration":
        if self.upper_line <= 0:
            raise ValueError(f"upperLine must be inside the picture (got {self.upper_line})")
        if len(self.white_borders) < 2:
            raise ValueError("whiteBorders needs at least two borders: one white key")
        for a, b in zip(self.white_borders, self.white_borders[1:]):
            if b <= a:
                raise ValueError("whiteBorders must increase from left to right")
        if self.first_white_pitch_class not in WHITE_PITCH_CLASSES:
            raise ValueError(
                f"firstWhitePitchClass {self.first_white_pitch_class} is not a white key"
            )
        expected = expected_black_count(self.first_white_pitch_class, len(self.white_borders) - 1)
        if len(self.black_borders) != expected:
            raise ValueError(
                f"blackBorders must hold one entry per black key the pattern puts between "
                f"{len(self.white_borders) - 1} white keys from pitch class "
                f"{self.first_white_pitch_class} ({expected}), got {len(self.black_borders)}"
            )
        for black in self.black_borders:
            if black.right <= black.left:
                raise ValueError("a black key's right border must be past its left one")
        if self.white_width <= 0:
            widths = sorted(b - a for a, b in zip(self.white_borders, self.white_borders[1:]))
            self.white_width = widths[len(widths) // 2]
        return self


class FindRequest(CamelModel):
    """What the finder needs from the user: the one rectangle, and the two things
    the user decides that the finder only defaults (V-37): the upper line and
    the octave of the leftmost key."""

    piano_rect: PianoRect = Field(..., alias="pianoRect")
    upper_line: float | None = Field(None, alias="upperLine")
    first_white_octave: int | None = Field(None, alias="firstWhiteOctave", ge=-1, le=8)


class PianoKey(CamelModel):
    """One key of the overlay: what it is, and where its borders are in x."""

    midi: int
    kind: Literal["white", "black"]
    #: Name in English and in the project's Spanish solfège, for the UI.
    name_en: str = Field(..., alias="nameEn")
    name_es: str = Field(..., alias="nameEs")
    left: float
    right: float
    #: The midpoint a rectangle is attributed to (V-14).
    mid: float


class KeyLane(CamelModel):
    """The vertical lane of one key: its borders widened by the margin (V-13)."""

    midi: int
    kind: Literal["white", "black"]
    x0: float
    x1: float
    mid: float


class Geometry(CamelModel):
    """Everything the overlay derives: the keys and their lanes."""

    keys: list[PianoKey]
    lanes: list[KeyLane]
    #: The lane margin this geometry was built with, in white key widths.
    margin: float


# ----------------------------------------------------- what it detected -----


class DetectedRun(CamelModel):
    """One rectangle the detector found, on one key, in one picture."""

    midi: int
    #: The last rectangle tip — the highest row of the run, where the note stops.
    y_top: int = Field(..., alias="yTop")
    #: The rectangle tip — the lowest row, the side that reaches the piano first.
    y_bottom: int = Field(..., alias="yBottom")
    #: The whole width of the rectangle, measured across the lane borders.
    x0: float
    x1: float
    mid: float
    width_keys: float = Field(..., alias="widthKeys")
    #: Cut by the upper line rather than tipped there (V-16), so it is sounding.
    clipped: bool
    #: False when the tip sits inside the halo guard band, where it is
    #: extrapolated rather than read (V-08). A flag, never a deletion (V-30).
    tip_trusted: bool = Field(..., alias="tipTrusted")
    #: Still coming into view at the roll top, so its last tip is not real yet.
    entering: bool
    #: What the frame window rule made of it: onset, sustain or released (V-18).
    verdict: Literal["onset", "sustain", "released"] = "released"
    #: What the momentum rule made of it when there was a neighbouring frame to
    #: ask: fell, static, or unknown because there was no neighbour (V-33).
    momentum: Literal["fell", "static", "unknown"] = "unknown"


class RejectedRun(CamelModel):
    """One shape a lane found and a gate threw out, with the gate that did it.

    A shape whose width or whose midpoint does not match a key is **reported**
    rather than rounded onto one (Task 4.1.2), because that is a detection
    problem wearing the mask of a timing problem. Nothing is inferred from a
    rejection; it is there so a person can look at what the reading dropped.
    """

    midi: int
    y_top: int = Field(..., alias="yTop")
    y_bottom: int = Field(..., alias="yBottom")
    x0: float
    x1: float
    mid: float
    width_keys: float = Field(..., alias="widthKeys")
    #: Which gate: too narrow, too wide, nearer another key, no bright column.
    reason: str


class Detection(CamelModel):
    """What the detector says about one picture, under one offset line."""

    slug: str | None = None
    #: The offset line, in pixels above the upper line. One window of time.
    offset_px: float = Field(..., alias="offsetPx")
    onsets: list[int]
    sustains: list[int]
    runs: list[DetectedRun]
    #: Runs the momentum rule refused, kept here so a refusal can be looked at.
    refused: list[DetectedRun] = Field(default_factory=list)
    #: Milliseconds the detector took, so a change that helps can be paid for.
    elapsed_ms: float = Field(0.0, alias="elapsedMs")


# ------------------------------------------------------- the example set ----


class Annotation(CamelModel):
    """One reading of one example, by hand, with the offset line in one place.

    The triple (example, offset line position, the keys marked) is the entry, so
    the same example read with the offset line in three places is three entries —
    which is what tests whether the detector follows the window and not a fixed
    guess (V-25, Task 2.2.2).
    """

    model_config = ConfigDict(populate_by_name=True)

    #: Distance from the upper line to the offset line, in pixels of the picture.
    offset_px: float = Field(..., alias="offsetPx", gt=0)
    onsets: list[int] = Field(default_factory=list)
    sustains: list[int] = Field(default_factory=list)
    #: Keys the picture cannot answer for. They come out of the score on both
    #: sides rather than being guessed — Phase 1 found one on `shut-up-and-dance`.
    skip: list[int] = Field(default_factory=list)
    note: str = ""

    @model_validator(mode="after")
    def _sorted_and_disjoint(self) -> "Annotation":
        self.onsets = sorted(set(self.onsets))
        self.sustains = sorted(set(self.sustains) - set(self.onsets))
        self.skip = sorted(set(self.skip))
        return self


class FrameExample(CamelModel):
    """One example screenshot: its picture, its calibration, its annotations."""

    slug: str
    #: Working-resolution size of the picture the app serves and reads.
    image_width: int = Field(..., alias="imageWidth")
    image_height: int = Field(..., alias="imageHeight")
    calibration: Calibration | None = None
    annotations: list[Annotation] = Field(default_factory=list)
    #: Set on an example with no roll to read. It is left out of the score board
    #: rather than counted as a failure — `superestrella` is a crop of a keyboard.
    no_roll: bool = Field(False, alias="noRoll")
    note: str = ""


class ExampleSummary(CamelModel):
    """One row of the example list, without loading the picture."""

    slug: str
    has_calibration: bool = Field(..., alias="hasCalibration")
    annotation_count: int = Field(..., alias="annotationCount")
    no_roll: bool = Field(..., alias="noRoll")


class Disagreement(CamelModel):
    """One key the detector and the hand reading do not agree about."""

    midi: int
    name_en: str = Field(..., alias="nameEn")
    #: What the hand reading says, then what the detector says.
    truth: Literal["onset", "sustain", "released"]
    detected: Literal["onset", "sustain", "released"]


class ScoreLine(CamelModel):
    """The score of one example at one offset line position."""

    slug: str
    offset_px: float = Field(..., alias="offsetPx")
    onsets_found: int = Field(..., alias="onsetsFound")
    onsets_invented: int = Field(..., alias="onsetsInvented")
    onsets_missed: int = Field(..., alias="onsetsMissed")
    sustains_found: int = Field(..., alias="sustainsFound")
    sustains_invented: int = Field(..., alias="sustainsInvented")
    sustains_missed: int = Field(..., alias="sustainsMissed")
    disagreements: list[Disagreement] = Field(default_factory=list)
    #: Why this line could not be scored, when it could not.
    error: str | None = None


class ScoreBoard(CamelModel):
    """Every scored example, and the total that says whether a change helped."""

    lines: list[ScoreLine]
    total: ScoreLine
    #: Examples that were not scored, and why — no calibration, no annotation, or
    #: no roll. An honest failure list is a result; a rounded up number is not.
    skipped: dict[str, str] = Field(default_factory=dict)


# ------------------------------------------------------------ one video -----
#
# A video lives inside the audio folder of the piece it belongs to (V-03), and
# the video file is the source while the sampled frames are a cache (V-01).
# `sampleMs` below is how often we look at the video. It is **never** `frameMs`,
# which is the column length the sheet is read at (V-04): two different numbers
# with two different owners, never derived from each other.


class VideoMetadata(CamelModel):
    """`video/metadata_video.json` — what the downloaded file is, and how it was
    sampled.

    Everything here is measured from the file itself with ffprobe, except
    :attr:`sample_ms` and :attr:`frame_count`, which the sampling step writes.
    """

    #: The piece this video belongs to. One URL gives one piece (V-03).
    audio_uuid: str = Field(..., alias="audioUuid")
    title: str = ""
    source_url: str | None = Field(None, alias="sourceUrl")

    #: The size of the downloaded file, before the working resolution is applied.
    width: int = Field(0, ge=0)
    height: int = Field(0, ge=0)
    duration_seconds: float = Field(0.0, alias="durationSeconds", ge=0)
    #: Frames per second of the source. Not the sampling granularity.
    fps: float = Field(0.0, ge=0)
    #: Bytes on disk, so the disk cost of keeping the video can be stated.
    size_bytes: int = Field(0, alias="sizeBytes", ge=0)

    #: How often we look at the video, in milliseconds. Zero before sampling.
    sample_ms: float = Field(0.0, alias="sampleMs", ge=0)
    #: How many sampled frames are on disk.
    frame_count: int = Field(0, alias="frameCount", ge=0)
    #: Width and height of one sampled frame — the working resolution.
    frame_width: int = Field(0, alias="frameWidth", ge=0)
    frame_height: int = Field(0, alias="frameHeight", ge=0)
    #: Bytes the sampled frames take, which is the number V-01 rests on.
    frames_bytes: int = Field(0, alias="framesBytes", ge=0)


class ScrollSpeed(CamelModel):
    """How fast the rectangles fall, measured never assumed (V-06, V-45).

    One estimate per pair of consecutive sampled frames: the mean fall of every
    rectangle edge followed from one frame into the next. The series is stored
    and the mean over every followed edge is the answer. A pair with too few
    rectangles in it cannot answer and is reported rather than averaged in.
    """

    #: The answer: how far the roll falls in one sampled frame, in picture pixels.
    px_per_frame: float = Field(..., alias="pxPerFrame", ge=0)
    #: The same thing in the unit a person reads.
    px_per_second: float = Field(..., alias="pxPerSecond", ge=0)
    #: The quartiles and the tails of the usable pairs, in pixels per frame.
    q1: float = 0.0
    q3: float = 0.0
    p5: float = 0.0
    p95: float = 0.0
    #: How many pairs held enough followed edges to answer, out of how many there are.
    usable_pairs: int = Field(0, alias="usablePairs", ge=0)
    total_pairs: int = Field(0, alias="totalPairs", ge=0)
    #: How many pairs held rectangles that did not move at all. Those are
    #: pauses, and counting them says how much of the video stood still rather
    #: than saying the speed is unstable (V-06).
    still_pairs: int = Field(0, alias="stillPairs", ge=0)
    #: False when the spread says the speed is not stable. A video whose speed is
    #: not stable is reported as such and is not transcribed silently (V-06).
    stable: bool = True
    #: Why it is not stable, in words, when it is not. Empty when it is.
    reason: str = ""
    #: The whole series, one entry per pair, so the spread can be looked at.
    series: list[float] = Field(default_factory=list)


class VideoMeasurement(CamelModel):
    """Everything the motion of the roll says about one video.

    The scroll speed (V-06) and the two edges of the roll (V-28) come from the
    same fact — the roll scrolls and nothing else does — so they are measured
    together and answered together. The roll top and the guard band are written
    into the calibration, because that is where the detector reads them from.
    """

    scroll_speed: ScrollSpeed = Field(..., alias="scrollSpeed")
    #: Nothing above this row is music (V-28).
    roll_top: float = Field(0.0, alias="rollTop", ge=0)
    #: Rows above the upper line where the strike light makes the picture
    #: unreadable (V-08, V-24), measured rather than defaulted.
    guard_band: float = Field(0.0, alias="guardBand", ge=0)
    #: The offset line this video has, which is not a free parameter: it is the
    #: measured scroll speed times the sampling granularity, and nothing else
    #: (V-25).
    offset_px: float = Field(0.0, alias="offsetPx", ge=0)


class VideoSummary(CamelModel):
    """`GET /video/{uuid}` — what we have about one video, in one answer."""

    metadata: VideoMetadata
    calibration: Calibration | None = None
    measurement: VideoMeasurement | None = None
    #: True once `frames.jsonl` exists.
    detected: bool = False
    #: How many sampled frames `frames.jsonl` holds.
    detected_frames: int = Field(0, alias="detectedFrames", ge=0)
    #: How many notes the stitched roll read (V-32). Zero before it has run.
    note_count: int = Field(0, alias="noteCount", ge=0)
    #: True once this piece has an `events.json` — from this video or from the
    #: model. It is the same file either way (V-02).
    has_piece: bool = Field(False, alias="hasPiece")


class FrameLine(CamelModel):
    """One line of `frames.jsonl`: what the detector saw in one sampled frame.

    The simplified notation the prompt asks for, and the readable record of what
    the detector saw. Released is the default and is never written down (V-19),
    so a key that appears in neither list is released.
    """

    #: The time of this sampled frame, in seconds from the start of the video.
    t: float
    onsets: list[int] = Field(default_factory=list)
    sustains: list[int] = Field(default_factory=list)


class DetectionReport(CamelModel):
    """What one run of the detector over a whole video did, in numbers.

    Written beside `frames.jsonl` so a change to a threshold can be compared
    against the run before it without re-reading the video (V-20).
    """

    frame_count: int = Field(0, alias="frameCount", ge=0)
    #: Rectangles found, before and after the momentum rule refused any (V-33).
    runs_found: int = Field(0, alias="runsFound", ge=0)
    runs_refused: int = Field(0, alias="runsRefused", ge=0)
    onsets: int = 0
    sustains: int = 0
    #: Onsets per second over the whole video — the sanity number of V-25.
    onsets_per_second: float = Field(0.0, alias="onsetsPerSecond", ge=0)
    #: Frame to frame agreement (V-31): the share of runs that reappear one
    #: travel lower in the next sampled frame. The score when there is no ground
    #: truth, and it needs no labelling.
    agreement: float = Field(0.0, ge=0)
    #: Wall clock seconds the whole run took, and over how many worker processes.
    elapsed_seconds: float = Field(0.0, alias="elapsedSeconds", ge=0)
    workers: int = 1


# -------------------------------------------------- the piece, from a video --
#
# Phase 4. The stitched roll (V-32) turns the whole video into one tall picture
# whose vertical axis is time, a note is one shape in it, and its bottom and top
# rows convert straight to seconds (V-05). What comes out is `events.json` and
# nothing else (V-02): the hand split, the matrix, the peaks, the ladder and the
# sheet are untouched and do not know where the notes came from.


class VideoNote(CamelModel):
    """One note read off the stitched roll, before it becomes an event.

    It carries where it was read as well as when it sounds, because a note that
    looks wrong on the sheet has to be findable in the picture it came from.
    """

    midi: int
    #: Seconds from the start of the video. The onset is the shape's lowest row
    #: and the release its highest, both turned into seconds with the measured
    #: scroll speed (V-05).
    start: float
    end: float
    #: The rows of the stitched roll this shape spans, lowest row last.
    row_top: int = Field(..., alias="rowTop")
    row_bottom: int = Field(..., alias="rowBottom")
    #: Width of the shape in local white key widths, the number the width gate
    #: judged it by.
    width_keys: float = Field(..., alias="widthKeys")
    #: How far the shape's midpoint sits from the midpoint of the key it was
    #: given, in median white key widths. V-14's margin, per note.
    key_distance: float = Field(0.0, alias="keyDistance")
    #: The shape reaches the bottom edge of the stitched roll: this note was
    #: already sounding when the video started, so its onset is not in the
    #: picture. The same fact `clipped` records about a run the upper line cut.
    starts_before: bool = Field(False, alias="startsBefore")
    #: The shape reaches the top edge: the note is still falling when the video
    #: ends, so its release is not in the picture.
    ends_after: bool = Field(False, alias="endsAfter")


class NoteReport(CamelModel):
    """What one reading of the stitched roll did, in numbers (V-20).

    Written beside the notes so a change to a threshold can be compared against
    the reading before it without stitching the video again.
    """

    #: How tall and how wide the stitched roll was, and what it cost in memory.
    rows: int = 0
    width: int = 0
    megabytes: float = 0.0
    #: The strip: where it was cut from a frame and how tall it was.
    strip_top: int = Field(0, alias="stripTop")
    strip_height: int = Field(0, alias="stripHeight")
    head_rows: int = Field(0, alias="headRows")
    frame_count: int = Field(0, alias="frameCount", ge=0)

    notes: int = 0
    #: Shapes a gate threw out, by the gate that did it. Reported, never rounded
    #: onto a key (Task 4.1.2).
    rejected: dict[str, int] = Field(default_factory=dict)
    notes_starting_before: int = Field(0, alias="notesStartingBefore", ge=0)
    notes_ending_after: int = Field(0, alias="notesEndingAfter", ge=0)
    #: Notes whose onset falls past the end of the video: the tail of the roll
    #: that never reached the piano. They are dropped and counted.
    notes_past_the_end: int = Field(0, alias="notesPastTheEnd", ge=0)

    #: The shape of what was read, so the reading can be judged without a score.
    median_width_keys: float = Field(0.0, alias="medianWidthKeys")
    median_length_ms: float = Field(0.0, alias="medianLengthMs")
    #: The worst distance from a key midpoint, in median white key widths. V-14
    #: has a measured margin of 0.33; anything near that is a warning.
    worst_key_distance: float = Field(0.0, alias="worstKeyDistance")
    notes_per_second: float = Field(0.0, alias="notesPerSecond")

    #: What the same picture answers when a note is one connected shape rather
    #: than one run in one key's lane — the letter of V-32, kept as the
    #: comparison a rule needs to earn its place (V-20).
    connected_shapes: int = Field(0, alias="connectedShapes", ge=0)

    #: Keys whose lane is foreground more than six tenths of the time. The plate
    #: is the median of what stands still and cannot tell a drone held for most
    #: of the piece from the roll behind it (V-44), so such a lane is named
    #: rather than trusted.
    busy_keys: list[int] = Field(default_factory=list, alias="busyKeys")

    elapsed_seconds: float = Field(0.0, alias="elapsedSeconds", ge=0)


class NoteCorrection(CamelModel):
    """One note the person reading took off, or put on, before the piece is written.

    A reading made by a person cannot be reproduced, so corrections are kept
    beside the video like the calibration and never rebuilt (V-12). A removal
    names the note it removes by pitch and onset; an addition carries the whole
    note, because there is nothing on the picture to name.
    """

    midi: int
    start: float
    #: Only an addition has an end. A removal leaves it out.
    end: float | None = None


class NoteCorrections(CamelModel):
    """Everything the person changed about one video's reading."""

    removed: list[NoteCorrection] = Field(default_factory=list)
    added: list[NoteCorrection] = Field(default_factory=list)


class VideoNotes(CamelModel):
    """`video/notes.json` — what the stitched roll read, and what to write.

    It is not the piece. The piece is `events.json`, written through the writer
    that already exists (V-02); this is what `POST /video/{uuid}/events` will
    write, shown first so it can be corrected (Task 4.3.1).
    """

    audio_uuid: str = Field(..., alias="audioUuid")
    notes: list[VideoNote] = Field(default_factory=list)
    report: NoteReport = Field(default_factory=NoteReport)
    #: Seconds of the video, which is what `durationSeconds` of the piece becomes.
    duration_seconds: float = Field(0.0, alias="durationSeconds", ge=0)
    #: Shapes the gates threw out, so a missing note can be looked at rather than
    #: guessed at. Capped, because a picture this tall can reject thousands.
    rejected: list[RejectedRun] = Field(default_factory=list)
