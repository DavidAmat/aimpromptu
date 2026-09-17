/**
 * Rhythm — read the playing, name one pile, see the sheet.
 *
 * Everything the wall-clock model asks of a person happens on this one screen, in the order it
 * makes sense: look at where the notes keep landing, say what one of those piles is, and read the
 * result. Naming a different pile changes the names on the page and nothing else, so trying two is
 * cheap and nothing is lost by getting it wrong the first time.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import LinkIcon from "@mui/icons-material/LinkOutlined";
import PianoIcon from "@mui/icons-material/PianoOutlined";
import BackspaceIcon from "@mui/icons-material/BackspaceOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RedoIcon from "@mui/icons-material/RedoOutlined";
import SaveIcon from "@mui/icons-material/SaveOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import UndoIcon from "@mui/icons-material/UndoOutlined";
import VisibilityIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffOutlined";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { PageContainer, SectionCard } from "../../ui";
import { noteName, spanishNoteName } from "../../music/noteNames";
import PeakPlot from "../../components/time/PeakPlot";
import ScorePlayer, {
  type ScorePlayerControls,
} from "../../components/time/ScorePlayer";
import TimeScoreView, {
  DEFAULT_LINE_SPACING,
  DEFAULT_NOTE_SPACING,
  MAX_LINE_SPACING,
  MAX_NOTE_SPACING,
  MAX_ZOOM,
  MIN_LINE_SPACING,
  MIN_NOTE_SPACING,
  MIN_ZOOM,
} from "../../components/time/TimeScoreView";
import FigureGlyph from "../../components/time/FigureGlyph";
import { FIGURE_SHORT, PLAIN_FIGURES } from "../../music/figures";
import FloatingBar from "../../components/common/FloatingBar";
import ScorePdfDialog from "../../components/time/ScorePdfDialog";
import ToolboxDialog from "../../components/common/ToolboxDialog";
import { Piano } from "../../piano/Piano";
import ComposePassagePanel from "../../components/editing/ComposePassagePanel";
import RangeRerecordPanel from "../../components/editing/RangeRerecordPanel";
import {
  FIGURE_LABELS,
  timeScoreApi,
  type FigureName,
  type GraceNote,
  type HandChoice,
  type LadderPreview,
  type Peak,
  type PeaksResponse,
  KEY_LABELS,
  KEY_SIGNATURES,
  type CueRange,
  type KeySignatureName,
  type LyricLine,
  type SavedRhythm,
  type TimeScorePayload,
  type Trill,
  type TrillSuggestion,
} from "../../api";
import { ApiError } from "../../api";
import {
  applyClefRange,
  applyKeySignatureRange,
  applyOttava,
  clearClefRange,
  clearKeySignatureRange,
  clearOttavaRange,
  clefAtFrame,
  keySignatureAtFrame,
  LYRIC_FONT_SIZE,
  MAX_EVEN_SPACING_SCALE,
  MAX_LYRIC_FONT_SIZE,
  MIN_EVEN_SPACING_SCALE,
  MIN_LYRIC_FONT_SIZE,
  ottavaAtFrame,
  pitchToStaffPosition,
  resizeOttava,
  type Clef,
  type ClefChangeAnnotation,
  type EvenSpacingAnnotation,
  type FingerNumber,
  type GridNotationRenderer,
  type KeyChangeAnnotation,
  type KeySignature,
  type LyricLayoutChange,
  type OttavaAnnotation,
  type OttavaKind,
  type OttavaResizeChange,
  type SpacingAnnotation,
  type StaffGapOverride,
} from "@aimpromptu/grid-notation";
import {
  frameOf,
  groupKeyOf,
  handOf,
  noteRefOf,
  rowOf,
  type NoteRef,
  type PrintedHand,
} from "../../music/renderOverrides";
import { palette, semantic } from "../../ui";
import { useEditHistory } from "../../hooks/useEditHistory";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

const NAMEABLE_FIGURES: FigureName[] = [
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
];

/** No note is moved by hand any more: a corrected hand is written onto the recording. */
const NO_HANDS: ReadonlyMap<NoteRef, PrintedHand> = new Map();

/**
 * Which hand a colour on the keyboard stands for.
 *
 * The page draws two staves and the keyboard draws one row of keys, so without a colour per hand a
 * reader looking at a chord on it cannot tell which hand is holding which note — which is most of
 * what they opened the panel to find out. Blue is the right hand everywhere in this app already;
 * orange is the left here, rather than the green the roll uses, because green beside blue at this
 * size is two shades of the same thing.
 */
const HAND_COLOUR: Record<PrintedHand, string> = {
  right: semantic.rightHand.onset,
  left: palette.dark.Orange,
};

/**
 * The same two, paler, for a key **still sounding** from a note struck in an earlier column.
 *
 * Without the second shade the panel says something it does not mean. At f103 of Superestrella the
 * right hand strikes B6 and is still holding the B5 it struck at f97, so two Si light up while the
 * sheet draws one notehead at that column — and a reader comparing the two reasonably concludes the
 * keyboard is wrong. It is not: both keys really are down. What it could not say is *which* of them
 * begins here.
 *
 * It matters more than it used to, because a key is now something you click. Clicking the pale B5
 * takes off a note that starts three columns back, and the reader has to be able to see that before
 * they press rather than after.
 *
 * The pale blue is the one the roll already uses for a held note, so a reader who has seen one has
 * seen both.
 */
const HELD_COLOUR: Record<PrintedHand, string> = {
  right: semantic.rightHand.sustain,
  left: palette.light.Orange,
};

/**
 * The four things a lit key can mean, in the order they are read.
 *
 * Each hand twice: struck in the column under the cursor, and still sounding from a note struck
 * earlier — whose notehead is back where it began rather than under the cursor. Naming both is what
 * answers "why are two Si lit when the page draws one", and it answers it beside the colours
 * instead of in a paragraph under the keyboard.
 */
const KEY_LEGEND: { colour: string; label: string }[] = [
  { colour: HAND_COLOUR.right, label: "Right hand (RH) onset" },
  { colour: HELD_COLOUR.right, label: "RH sustain" },
  { colour: HAND_COLOUR.left, label: "Left hand (LH) onset" },
  { colour: HELD_COLOUR.left, label: "LH sustain" },
];

/** What a decoration note is drawn in on the keyboard, and what the note it leans on is drawn in. */
const DECORATION_COLOUR = palette.dark.Pink;
const PRINCIPAL_COLOUR = palette.dark.Lavender;

/**
 * The figures that print with flags, and so can share a beam.
 *
 * A negra and anything longer has no beam to share, which is why **Beam all** stands down on them
 * rather than drawing something that is not a beam. The dotted pair is out for the same reason a
 * dotted figure is not a rung of the ladder: neither of the two this page offers carries a flag.
 */
const BEAMABLE_FIGURES = new Set<FigureName>([
  "corchea",
  "semicorchea",
  "fusa",
  "semifusa",
]);

/** How much one press of the plus or the minus moves an even run, as a fraction of its own width. */
const EVEN_SPACING_STEP = 0.15;

/** Thumb to little finger. There is no 0 and no 6. */
const FINGERS: FingerNumber[] = [1, 2, 3, 4, 5];

/**
 * What a stretch of columns can carry. One pill each, and only that one's controls on screen.
 *
 * Two of them left. **Trill** and **Small** are statements about notes, not about columns — "these
 * notes are a shake", "these notes are decoration" — so they moved to the note toolbox, where the
 * notes they are about are already picked and the panel does not have to ask which hand.
 */
const FRAME_TABS = [
  { id: "key" as const, label: "Key" },
  { id: "clef" as const, label: "Clef" },
  { id: "octave" as const, label: "Octave" },
  { id: "lyrics" as const, label: "Lyrics" },
  { id: "spacing" as const, label: "Spacing" },
  { id: "rerecord" as const, label: "Re-record" },
];

type FrameTab = (typeof FRAME_TABS)[number]["id"];

/**
 * Which pill a marked stretch opens when the reader clicks one of its corners, or its bracket.
 *
 * The drawing package names its kinds after the notation; the panel names its pills after what a
 * reader is about to change. `Re-record` and `Spacing` are not in the list because neither draws a
 * corner: nothing about them is a stretch of markup you can lose the edges of.
 */
const MARKER_TABS: Readonly<Record<string, FrameTab | undefined>> = {
  ottava: "octave",
  clef: "clef",
  key: "key",
  lyric: "lyrics",
};

/**
 * Which staff a marked stretch is about: one hand, or the piece.
 *
 * The first thing the frames toolbox asks, because it changes what every pill below it means and
 * what the highlight on the page covers. A clef and an octave bracket belong to one hand; a key
 * signature is drawn on both clefs and a line of words is sung over the piece, so those ignore it.
 */
type RangeHand = PrintedHand | "both";

/** Which clef each hand reads when nobody has said otherwise. The page's starting point. */
const DEFAULT_CLEF: Record<PrintedHand, Clef> = { right: "treble", left: "bass" };

/** The two clefs this page prints, and what each is called. */
const CLEF_CHOICES: { clef: Clef; label: string; hint: string }[] = [
  { clef: "treble", label: "Treble", hint: "the G clef — where the right hand normally reads" },
  { clef: "bass", label: "Bass", hint: "the F clef — where the left hand normally reads" },
];

/** The four brackets, and what each does to a passage, in the order a reader meets them. */
const OTTAVA_CHOICES: { kind: OttavaKind; label: string; hint: string }[] = [
  { kind: "8va", label: "8va", hint: "written an octave lower than it sounds" },
  {
    kind: "15ma",
    label: "15ma",
    hint: "written two octaves lower than it sounds",
  },
  {
    kind: "8vb",
    label: "8vb",
    hint: "written an octave higher than it sounds",
  },
  {
    kind: "15mb",
    label: "15mb",
    hint: "written two octaves higher than it sounds",
  },
];

/** `mm:ss.cc`, so a column range can be read as a moment in the recording. */
function formatSeconds(seconds: number): string {
  const total = Math.max(0, Math.round(seconds * 100));
  const minutes = Math.floor(total / 6000);
  const rest = Math.floor((total % 6000) / 100);
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}.${String(
    total % 100,
  ).padStart(2, "0")}`;
}

/**
 * The rungs a figure shift walks: the plain figures, each twice the one below it (D-18).
 *
 * The dotted pair is not here. A dot is an exception the vocabulary allows on two figures so a held
 * note can be written; it is not a rung, and stepping onto it would re-scale the ladder by 1.5
 * rather than doubling it. This mirrors `SHIFT_LADDER` in `matrix/ladder.py`, which is the same
 * list on the other side.
 */
const SHIFT_LADDER: FigureName[] = [
  "semifusa",
  "fusa",
  "semicorchea",
  "corchea",
  "negra",
  "blanca",
  "redonda",
];

/** The figure `steps` rungs away, or `null` when that runs off the end of the vocabulary. */
function shifted(figure: FigureName, steps: number): FigureName | null {
  const at = SHIFT_LADDER.indexOf(figure);
  if (at < 0) return null;
  return SHIFT_LADDER[at + steps] ?? null;
}

/** One note the keyboard panel can point at: what it is, who holds it, and where it began. */
interface SoundingNote {
  row: number;
  hand: PrintedHand;
  /** The column the note was struck in, which is how every mark on this page addresses one. */
  onsetFrame: number;
}

interface Stretch {
  /** The frame the stretch starts at. Everything before it keeps the previous name. */
  startFrame: number;
  /** What a gap is called from here on, in milliseconds. */
  anchorMs: number;
}

/**
 * Everything a reader decides about this sheet, in one value.
 *
 * One object rather than sixteen pieces of state, because undo is going back to the set of
 * decisions that was here a moment ago, and a set is only a thing you can go back to if it is one
 * thing. This is also exactly what `rhythm.json` stores, which is not a coincidence: the file is
 * the list of things nobody can derive, and so is this.
 *
 * What is *not* in here: which notes are picked, which stretch is marked, where a toolbox sits,
 * what is half-typed in a field, and which pile of gaps was named. None of those is a decision
 * about the sheet, and a Command-Z that took the reader's selection away would be a nuisance.
 */
interface SheetEdits {
  /** The signature the whole piece is written in. C until somebody chooses. */
  keySignature: KeySignatureName;
  /**
   * Where the piece leaves that signature, and what it changes to.
   *
   * Transitions rather than ranges, which is how the drawing package stores them: at any column
   * exactly one signature is sounding, so two edits cannot disagree. Giving a passage its own key
   * writes two, one at each end.
   */
  keyChanges: KeyChangeAnnotation[];
  /**
   * Where each hand leaves the clef it normally reads, and what it changes to.
   *
   * Transitions rather than ranges, which is how the drawing package stores them and for the same
   * reason the key changes are: at any column each hand prints exactly one clef, so two edits
   * cannot disagree. Giving a passage its own clef writes two, one at each end.
   *
   * It is the honest answer to a hand that spends a page far outside its own staff, and a better
   * one than an octave bracket where the passage is long: under a bracket the notes are written an
   * octave from where they sound, on the other clef they are written exactly where they sound.
   */
  clefChanges: ClefChangeAnnotation[];
  /**
   * Where each hand is written an octave or two from where it sounds. **Entirely the reader's.**
   *
   * Nothing proposes these any more. The screen used to seed itself from what the register asked
   * for, which existed because the hand split left passages stranded on the wrong staff under a
   * pile of ledger lines and a bracket was the cheapest way to make them readable. P8.6 charged
   * the split for those ledger lines instead, so an automatic bracket is now mostly a bracket over
   * music that did not need one. A single high note still reads better under `8va`, and that is
   * one click on the Octave pill.
   */
  ottavas: OttavaAnnotation[];
  /**
   * Stretches printed as one held note with `tr` over them.
   *
   * The alternations stay in the recording and playback still sounds every one of them; what the
   * mark changes is which noteheads are drawn. They travel with the sheet request rather than
   * being applied here, because the printed length of the held note is the gap to the next onset
   * after the run, and only the backend measures that.
   */
  trills: readonly Trill[];
  /** Lines of words under the staff, over a stretch of columns. */
  lyrics: readonly LyricLine[];
  /** Stretches printed smaller than the rest of the page. */
  cueRanges: readonly CueRange[];
  /** Stretches the reader set wider or narrower than the page would set them. */
  spacings: SpacingAnnotation[];
  /**
   * Runs of one hand's notes the reader asked to have set an equal distance apart.
   *
   * The page measures every column from what is drawn in it, and both staves share the column — so
   * a run of even corcheas in the right hand comes out unevenly spaced wherever the left hand needs
   * room at one of those moments. Nothing is wrong with the page when that happens; the space
   * really is being used. It still reads as a mistake in the playing, because a beam of equal notes
   * that is not equally spaced is what an uneven performance looks like.
   *
   * So this is the reader choosing: make the run even, and let the width be whatever that costs.
   * `scale` is a multiple of the tightest even spacing the run allows — never less than one,
   * because a gap cannot close below the ink in its columns.
   */
  evenSpacings: EvenSpacingAnnotation[];
  /** Which finger plays each note, keyed `hand:startFrame:row`. */
  fingers: Record<string, FingerNumber>;
  /**
   * Figures set by hand on one chord, keyed `hand:startFrame`.
   *
   * Drawn on top rather than sent back for a rebuild, because an override is only a glyph: nothing
   * moves and no other note changes. Writing the sheet again keeps them.
   */
  overrides: Record<string, FigureName>;
  /**
   * Notes the reader has asked to start a new beam, keyed `hand:startFrame`.
   *
   * Beside the overrides and for the same reason: it changes how the page is grouped and nothing
   * about the music. A long arpeggio beams as one slope because no rule can see where the phrase
   * restarts — only the person reading can, so they say.
   */
  beamBreaks: ReadonlySet<string>;
  /**
   * Notes the reader asked to keep inside the beam they are in, keyed `hand:startFrame`.
   *
   * The other half of a beam break, and it has to be stored for the same reason: the page cuts a
   * beam where a run turns over at its lowest note, which is right for an arpeggio and wrong for a
   * scale that happens to dip. "These are one gesture" is a reading of the music, exactly as "the
   * phrase restarts here" is, and no rule has it.
   */
  beamJoins: ReadonlySet<string>;
  /**
   * Notes the reader took off the page, as `startFrame:row`.
   *
   * A transcriber inventing a note out of a pedal blur is the commonest thing wrong with a page,
   * and the honest fix is to stop drawing it, not to say it was never played. The recording is
   * evidence and stays as it is; this is a set of keys beside it. Bringing one back restores it
   * exactly.
   */
  hiddenNotes: ReadonlySet<NoteRef>;
  /**
   * Small notes leaning on a note of the music.
   *
   * Never inferred, and never played: a grace note is a reading of how a note should be
   * approached, and nothing in a recording distinguishes one from a very short note that was
   * really struck.
   */
  graceNotes: readonly GraceNote[];
  /** Whether the ornaments are left off the page. */
  dropDecorative: boolean;
  /** How large the marks over and under the staff are drawn, as a multiple of normal. */
  annotationScale: number;
  /**
   * How much white space there is between the staves of one line and the staves of the next, in
   * pixels. Nought puts one set of pentagrams directly under the one above.
   */
  lineSpacing: number;
  /**
   * Extra pixels between one note and the next, everywhere on the page.
   *
   * The twin of the space between lines, one axis over. The page measures each column from what is
   * drawn in it, which is right and can still be tighter than a person wants to play from — so this
   * is the reader's own answer, charged to the columns that carry a note and to no others. The
   * silences keep the width the wall clock gives them, because that is the one thing this page
   * already says well.
   */
  noteSpacing: number;
  /**
   * Lines spread wider or narrower than the rest, one at a time, keyed by a column inside each.
   *
   * The handle between the two staves of a line. It is per line rather than per page because the
   * reason for wanting it is per line: one wide chord, or one passage reaching down, needs room
   * that every other line on the score would only waste.
   *
   * Keyed by a column and not by a place down the page, because the page re-wraps to the window
   * and "the third line" is different music after it. A column never moves, which is what every
   * other mark here is addressed by.
   */
  staffGaps: readonly StaffGapOverride[];
  /**
   * Where the piece changes speed, and what a gap is called after each of them.
   *
   * A boundary is drawn by hand. Nothing detects them: a wrong hand-drawn one spoils one stretch,
   * while a wrong automatic one scatters speed changes through the piece and makes the sheet
   * unreadable. Frames are absolute wall clock, so a boundary never moves a note.
   */
  stretches: Stretch[];
}


/**
 * What each edit is called, on the two buttons and in their tooltips.
 *
 * A button that only says "Undo" asks a reader to remember what they last did, and on a page with
 * sixteen kinds of edit they often do not. One name per field, and a step that touches several
 * fields at once is named by the first of them — or explicitly, where that would read wrong.
 */
const EDIT_LABELS: Readonly<Record<keyof SheetEdits, string>> = {
  keySignature: "Key signature",
  keyChanges: "Key of a stretch",
  clefChanges: "Clef of a stretch",
  ottavas: "Octave bracket",
  trills: "Trill",
  lyrics: "Words",
  cueRanges: "Small stretch",
  spacings: "Spacing",
  evenSpacings: "Even spacing",
  fingers: "Fingering",
  overrides: "Figure",
  beamBreaks: "Beam",
  beamJoins: "Beam",
  hiddenNotes: "Notes off the page",
  graceNotes: "Grace note",
  dropDecorative: "Decorative notes",
  annotationScale: "Mark size",
  lineSpacing: "Space between lines",
  noteSpacing: "Space between notes",
  staffGaps: "Line spread",
  stretches: "Speed change",
};

/** A piece nobody has read yet. Also what **Remove all** goes back to. */
const NO_EDITS: SheetEdits = {
  keySignature: "C",
  keyChanges: [],
  clefChanges: [],
  ottavas: [],
  trills: [],
  lyrics: [],
  cueRanges: [],
  spacings: [],
  evenSpacings: [],
  fingers: {},
  overrides: {},
  beamBreaks: new Set<string>(),
  beamJoins: new Set<string>(),
  hiddenNotes: new Set<NoteRef>(),
  graceNotes: [],
  dropDecorative: false,
  annotationScale: 1,
  lineSpacing: DEFAULT_LINE_SPACING,
  noteSpacing: DEFAULT_NOTE_SPACING,
  staffGaps: [],
  stretches: [],
};

/** How wide the floating toolbox is, and how far it stands off what it is about. */
const TOOLBOX_WIDTH = 360;
const TOOLBOX_GAP = 16;
/** Enough of a panel to be worth opening. It is what the bottom of the window is measured against. */
const TOOLBOX_MIN_HEIGHT = 260;

/**
 * The box on screen that a set of drawn elements takes up, or `null` when none are drawn.
 *
 * Read from the page rather than worked out from frame numbers, because a frame's x depends on the
 * system it wrapped onto, how much is happening in it and where the reader has scrolled — three
 * things the page already knows and this file would only be guessing at.
 */
function screenBoxOf(selector: string): DOMRect | null {
  const nodes = document.querySelectorAll(selector);
  if (nodes.length === 0) return null;
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;
  for (const node of nodes) {
    const box = node.getBoundingClientRect();
    if (box.width === 0 && box.height === 0) continue;
    left = Math.min(left, box.left);
    top = Math.min(top, box.top);
    right = Math.max(right, box.right);
    bottom = Math.max(bottom, box.bottom);
  }
  if (!Number.isFinite(left)) return null;
  return new DOMRect(left, top, right - left, bottom - top);
}

/**
 * The box the marked stretch takes up **on the line it starts on**.
 *
 * The highlight is painted one rectangle per group, and a stretch that wraps paints them on several
 * lines — so taking all of them would union a box the height of the page and leave nowhere clear to
 * open. The reader is looking at where the stretch begins, so that is the fragment the panel is
 * kept clear of. Every rectangle on one line shares a top, which is what they are grouped by.
 */
function firstLineBoxOf(selector: string): DOMRect | null {
  const nodes = [...document.querySelectorAll(selector)]
    .map((node) => node.getBoundingClientRect())
    .filter((box) => box.width > 0 || box.height > 0);
  const first = nodes[0];
  if (!first) return null;
  const onThatLine = nodes.filter((box) => Math.abs(box.top - first.top) < 2);
  const left = Math.min(...onThatLine.map((box) => box.left));
  const right = Math.max(...onThatLine.map((box) => box.right));
  const top = Math.min(...onThatLine.map((box) => box.top));
  const bottom = Math.max(...onThatLine.map((box) => box.bottom));
  return new DOMRect(left, top, right - left, bottom - top);
}

/**
 * Where to open a toolbox so it sits beside what it is about instead of on top of it.
 *
 * To the right when there is room, otherwise to the left; a panel that covered the notes it edits
 * would have to be dragged away before it could be used, every time. Vertically it starts level
 * with the selection and is pulled back onto the screen if that would run off the bottom.
 */
/**
 * The box a press was on: the whole frame group or notehead if it landed on one, else the point.
 *
 * A toolbox that must not cover what it is about has to know how big that thing is, and the only
 * moment the answer is on the page is the press itself — a frame group's highlight is not painted
 * until a render later.
 */
function pressedBox(event: {
  target: EventTarget | null;
  clientX: number;
  clientY: number;
}): DOMRect {
  const on = (event.target as Element | null)?.closest?.(
    ".grid-frame-range, .grid-frame-cell, [data-note-target]",
  );
  const box = on?.getBoundingClientRect();
  if (box && (box.width > 0 || box.height > 0)) return box;
  return new DOMRect(event.clientX - 8, event.clientY - 8, 16, 16);
}

/**
 * Where to open the frames toolbox so a range that grows never ends up underneath it.
 *
 * `besideOnScreen` below puts a panel to the right of what it is about, which is right for a set of
 * noteheads: a selection of notes is the size it is. A marked stretch is not. It starts where the
 * reader clicked and they then drag its right-hand handle out to where they actually want it — so a
 * panel to the right is a panel the range grows underneath, and the reader has to drag the panel
 * away before they can finish the gesture they were in the middle of.
 *
 * To the **left** of where the range starts, then, because that is the one side it does not grow
 * towards. When there is no room there — a stretch near the left margin, or a narrow window — it
 * goes **below the staves** instead, left-aligned with the start of the range, which is clear of it
 * in the other axis.
 */
function clearOfRange(box: DOMRect | null): { x: number; y: number } | undefined {
  if (!box) return undefined;
  // To the left first, because that is the one side a stretch does not grow towards.
  if (box.left >= TOOLBOX_WIDTH + TOOLBOX_GAP * 2) {
    return onScreen(box.left - TOOLBOX_GAP - TOOLBOX_WIDTH, box.top);
  }
  // Then the right. It is the side the stretch grows into, so it is the second choice — but a
  // panel beside the stretch is still better than one on top of it.
  if (window.innerWidth - box.right >= TOOLBOX_WIDTH + TOOLBOX_GAP * 2) {
    return onScreen(box.right + TOOLBOX_GAP, box.top);
  }
  // Neither side has room: a wide stretch, a narrow window, or a magnified page. Below it, held on
  // screen — and at a large enough zoom the stretch covers the window and there is no clear ground
  // left to open on, which is the reader's cue to zoom out or drag the panel where they want it.
  return onScreen(box.left, box.bottom + TOOLBOX_GAP);
}

function besideOnScreen(
  box: DOMRect | null,
): { x: number; y: number } | undefined {
  if (!box) return undefined;
  const toTheRight = box.right + TOOLBOX_GAP;
  const x =
    toTheRight + TOOLBOX_WIDTH + TOOLBOX_GAP <= window.innerWidth
      ? toTheRight
      : box.left - TOOLBOX_GAP - TOOLBOX_WIDTH;
  return onScreen(x, box.top);
}

/**
 * A panel's top-left corner, held inside the window wherever it was asked for.
 *
 * Both placements above measure something drawn on the sheet, and the sheet can be **magnified**:
 * at 3× a stretch that was 200 pixels wide is 600, and a selection wider or taller than the window
 * is ordinary rather than exotic. Without this the panel was asked to open past the edge of the
 * screen and the browser simply drew it there, so it read as the panel having been lost.
 */
function onScreen(x: number, y: number): { x: number; y: number } {
  const lastX = Math.max(TOOLBOX_GAP, window.innerWidth - TOOLBOX_WIDTH - TOOLBOX_GAP);
  const lastY = Math.max(TOOLBOX_GAP, window.innerHeight - TOOLBOX_MIN_HEIGHT);
  return {
    x: Math.round(Math.min(Math.max(TOOLBOX_GAP, x), lastX)),
    y: Math.round(Math.min(Math.max(TOOLBOX_GAP, y), lastY)),
  };
}

interface View {
  key: string;
  peaks: PeaksResponse | null;
  selected: Peak | null;
  preview: LadderPreview | null;
  score: TimeScorePayload | null;
  error: string | null;
}

function emptyView(key: string): View {
  return {
    key,
    peaks: null,
    selected: null,
    preview: null,
    score: null,
    error: null,
  };
}

/**
 * The backend's own sentence, without the status code in front of it.
 *
 * `ApiError.message` reads "409 — This piece was transcribed before…", which is
 * a number a reader has no use for. The `detail` behind it is written to be shown
 * as it stands, so that is what appears.
 */
function readable(caught: unknown, fallback: string): string {
  if (caught instanceof ApiError) return caught.detail;
  return caught instanceof Error ? caught.message : fallback;
}

/** A piece with no recorded notes yet: not a failure, just nothing to read. */
function notTranscribed(caught: unknown): boolean {
  return caught instanceof ApiError && caught.status === 409;
}

export function RhythmPage() {
  const { artifact } = useWorkingArtifact();
  const audioUuid = artifact.audioUuid;
  const frameMs = artifact.frameMs;

  const [hand, setHand] = useState<HandChoice>("right");
  const [figure, setFigure] = useState<FigureName>("negra");
  const [busy, setBusy] = useState(false);

  /**
   * Every edit a reader makes on this sheet, and the way back through all of them.
   *
   * The sixteen values below used to be sixteen pieces of state, each with its own private way out
   * — an Undo button in one toolbox, a chip that cleared itself in another, a "Bring them all
   * back" under the sheet, and for a fingering, nothing at all. One history replaces the lot:
   * Command-Z takes the last edit back whatever kind it was, and every setter below is written
   * exactly the way a `useState` setter is, so nothing else on this page had to change.
   *
   * The labels are what the two buttons say they are about, so a reader knows what is about to go
   * before they press.
   */
  const edits = useEditHistory<SheetEdits>(NO_EDITS, EDIT_LABELS);
  const {
    keySignature,
    keyChanges,
    clefChanges,
    ottavas,
    trills,
    lyrics,
    cueRanges,
    spacings,
    evenSpacings,
    fingers,
    overrides,
    beamBreaks,
    beamJoins,
    hiddenNotes,
    graceNotes,
    dropDecorative,
    annotationScale,
    lineSpacing,
    noteSpacing,
    staffGaps,
    stretches,
  } = edits.state;
  const {
    keySignature: setKeySignature,
    keyChanges: setKeyChanges,
    clefChanges: setClefChanges,
    ottavas: setOttavas,
    trills: setTrills,
    lyrics: setLyrics,
    cueRanges: setCueRanges,
    spacings: setSpacings,
    evenSpacings: setEvenSpacings,
    fingers: setFingers,
    overrides: setOverrides,
    beamBreaks: setBeamBreaks,
    beamJoins: setBeamJoins,
    hiddenNotes: setHiddenNotes,
    graceNotes: setGraceNotes,
    dropDecorative: setDropDecorative,
    annotationScale: setAnnotationScale,
    lineSpacing: setLineSpacing,
    noteSpacing: setNoteSpacing,
    staffGaps: setStaffGaps,
    stretches: setStretches,
  } = edits.set;
  const resetEdits = edits.reset;
  const stageEdit = edits.stage;
  /**
   * The live renderer behind the sheet, and whether the print panel is open.
   *
   * Printing needs the renderer itself rather than the payload: the widths it measured and every
   * choice the reader has made since are what make the printed page the same music as the screen.
   */
  const [sheetRenderer, setSheetRenderer] =
    useState<GridNotationRenderer | null>(null);
  const [pdfOpen, setPdfOpen] = useState(false);

  const [keyHint, setKeyHint] = useState<{
    best: KeySignatureName;
    saved: number;
  } | null>(null);
  /**
   * The octave brackets the notes ask for, reported by the sheet on every build. Taken as they
   * are the first time a piece is drawn that nobody has decided about brackets on, and on request
   * after that: a passage of three or more chords far outside its staff reads as one bracket, and
   * the reader keeps, moves or clears what was proposed with the Octave pill.
   */
  const [ottavaHint, setOttavaHint] = useState<OttavaAnnotation[]>([]);
  const ottavasDecided = useRef(false);
  /** The keyboard panel: what is sounding under the playhead, coloured on a piano. */
  const [pianoOpen, setPianoOpen] = useState(false);
  /**
   * Whether the column numbers are printed over the guides. **Off until asked for.**
   *
   * A column number is an address, not notation. It is what every mark on this page is keyed by and
   * it is how a reader says where something is, so it has to be one click away — but it is also
   * fifty-two of the sixty pixels above every staff, spent on numbers that mean nothing musically,
   * on a page whose whole job is to be read as music. Off is the better resting state.
   *
   * Not an edit, so it is not in `SheetEdits`: it is how the page is being looked at rather than
   * something decided about the piece, the same as the keyboard panel beside it.
   */
  const [frameLabelsOn, setFrameLabelsOn] = useState(false);
  /**
   * How large the sheet is drawn, as a multiple of its natural size. Command and the wheel moves it.
   *
   * Not an edit, so it is not in `SheetEdits`: it is how the page is being looked at rather than
   * something decided about the piece, the same as the column numbers above. It is also not a
   * change to the music — the drawing is magnified, so no column is measured again and the page
   * does not wrap somewhere else — which is why nothing about it is saved.
   */
  const [sheetZoom, setSheetZoom] = useState(MIN_ZOOM);
  /** Notes picked on the sheet: click one, then hold Command and click more. */
  const [selectedNotes, setSelectedNotes] = useState<readonly string[]>([]);
  const [framesToolbox, setFramesToolbox] = useState(false);
  /**
   * Raised each time a stretch is marked, so the panel can be placed against the highlight the page
   * paints rather than against the click that started it. See the effect beside `pickRange`.
   */
  const [framesOpenedAt, setFramesOpenedAt] = useState(0);
  /** Which pill is open in the frame toolbox. */
  const [frameTab, setFrameTab] = useState<FrameTab>("key");
  /**
   * Which staff the marked stretch is about.
   *
   * Not an edit, so it is not in `SheetEdits`: it is part of the selection, like the columns
   * themselves, and a Command-Z that put the hand pills back where they were would be a nuisance.
   * It survives one selection to the next on purpose — a reader narrowing a clef to the left hand
   * is usually about to do it again a page later — and is let go when the toolbox closes.
   */
  const [rangeHand, setRangeHand] = useState<RangeHand>("both");
  /**
   * The note the decoration keyboard is open for, or `null`.
   *
   * Held as the note key rather than as a boolean, so the panel cannot end up open over a note that
   * is no longer picked.
   */
  const [decorationFor, setDecorationFor] = useState<string | null>(null);
  /** Which hand a note added from the keyboard panel is given to. */
  const [addHand, setAddHand] = useState<PrintedHand>("right");
  /** A note is on its way onto the recording, and the sheet is being drawn again from it. */
  const [addingNote, setAddingNote] = useState(false);
  const [notesToolbox, setNotesToolbox] = useState(false);
  /** Raised to drop every selection on the sheet: Escape, or closing a toolbox. */
  const [clearedAt, setClearedAt] = useState(0);
  /**
   * What the frames toolbox will write when Apply is pressed, and which selection it was chosen for.
   *
   * Carried with the range it belongs to rather than reset by an effect: picking a different stretch
   * of columns should offer whatever is sounding there, not whatever was chosen for the last one.
   */
  const [passageDraft, setPassageDraft] = useState<{
    forRange: string;
    value: KeySignatureName;
  } | null>(null);
  /** What the backend found the last time it was asked, and whether it is looking now. */
  const [trillSuggestions, setTrillSuggestions] = useState<
    readonly TrillSuggestion[] | null
  >(null);
  const [findingTrills, setFindingTrills] = useState(false);
  /** What is being typed for the stretch now open, so the field survives a redraw. */
  const [lyricDraft, setLyricDraft] = useState<{
    forRange: string;
    text: string;
  } | null>(null);
  /** Numbers pressed for the selection now open, so a chord can be given several at once. */
  const [fingerDraft, setFingerDraft] = useState<{
    forSelection: string;
    picked: FingerNumber[];
  } | null>(null);
  /** A move that could not be made, said once, in words. */
  const [moveRefused, setMoveRefused] = useState<string | null>(null);
  /** A hand change is on its way to the recording, and the sheet is being drawn again from it. */
  const [movingHand, setMovingHand] = useState(false);
  /**
   * Where each toolbox opened, measured from what it is about.
   *
   * Set when the selection is made and then left alone: the panel is draggable, and moving the
   * thing it points at should not snatch it back out of the reader's hand.
   */
  const [framesAt, setFramesAt] = useState<
    { x: number; y: number } | undefined
  >(undefined);
  const [notesAt, setNotesAt] = useState<{ x: number; y: number } | undefined>(
    undefined,
  );
  /**
   * Where the last press on the sheet landed.
   *
   * The frames toolbox opens from a callback that runs before its highlight is painted, so there
   * is nothing on the page to measure yet. The click itself is the next best anchor, and it is
   * where the reader is looking in any case.
   */
  const pressedAt = useRef<DOMRect | null>(null);
  const [range, setRange] = useState<{
    fromColumn: number;
    toColumn: number;
  } | null>(null);
  // Where the recording is, in seconds, while it plays. `null` when nothing is playing, which is
  // what hides the line on the staves.
  // Starts at zero rather than nothing, so the line is on the page — and so grabbable — before the
  // recording has ever been played. `null` only after the player itself has gone.
  const [playheadSeconds, setPlayheadSeconds] = useState<number | null>(0);
  /** The transport, so dragging the cursor on the staves can move the recording. */
  const player = useRef<ScorePlayerControls | null>(null);
  const [scrollCursorAt, setScrollCursorAt] = useState(0);
  const [newAnchorMs, setNewAnchorMs] = useState(320);
  /**
   * The reading saved with the piece, and whether this screen still matches it.
   *
   * `null` means nobody has read this piece yet, which is the blank state the plot is for.
   */
  const [saved, setSaved] = useState<SavedRhythm | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState<string | null>(null);
  /**
   * Why the last save did not happen, in the backend's own words.
   *
   * Held apart from `savedNote` because the two are read in different places and one of them is an
   * emergency. The note is a line under the Save at the foot of the page; a failure has to reach a
   * reader wherever they are, because the Save they pressed is on the bar that follows them down
   * the sheet — and until now a refused save said nothing at all up there. A reading that a reader
   * believes is saved and is not is the worst thing this page can do.
   */
  const [saveProblem, setSaveProblem] = useState<string | null>(null);
  /** Whether the recording is sounding, so the floating bar can draw the button it will act as. */
  const [playing, setPlaying] = useState(false);
  /**
   * Whether the wipe has been armed, and what the bar has just done.
   *
   * The wipe throws away everything anyone decided about the piece, which is far too much to lose
   * to a misclick on a bar that follows the reader down the page — so it takes two presses, and it
   * forgets the first if the second does not come. `flash` is the other half of the same problem:
   * the bar is the only thing on screen at that moment, so it has to say what happened itself.
   */
  const [armed, setArmed] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [flash, setFlash] = useState<"saved" | "removed" | null>(null);

  /**
   * Everything read for one (piece, hand, resolution), kept together under the key it belongs to.
   *
   * One object rather than five, because they always change together: asking about the other hand
   * invalidates the piles, the chosen pile, the preview and the sheet at once. Comparing the key
   * during render is how the reset happens, which keeps it out of the effect.
   */
  /**
   * Raised whenever a passage is put into the piece (Epic 13). It is in the view key because
   * placing one changes the music: the piles, the chosen pile, the sheet and the saved reading are
   * all about playing that has just changed, so all of them are read again rather than patched.
   */
  const [composed, setComposed] = useState(0);
  /**
   * Which piece the reader has unfolded the passage stage on, or `null` while nobody has said.
   *
   * Held as the key rather than as a boolean so that loading a different piece forgets the answer:
   * unfolding it on one piece is not a statement about the next.
   */
  const [composeChoice, setComposeChoice] = useState<string | null>(null);
  const key = `${audioUuid ?? ""}|${hand}|${frameMs}|${composed}`;
  const [view, setView] = useState<View>(() => emptyView(key));
  const [untranscribed, setUntranscribed] = useState(false);
  if (view.key !== key) setView(emptyView(key));

  /**
   * A different piece, or a passage placed into this one: start the edits and the history again.
   *
   * Not on a change of hand, which only changes which hand's gaps the plot is read from and leaves
   * every decision about the sheet standing. Placing a passage is in here because it moves every
   * mark after the insertion point, so a step from before it would put a bracket back over notes
   * that are somewhere else now.
   *
   * Compared during render, the same way the view above is, so there is no render in between
   * showing one piece's edits over another piece's notes.
   */
  const editsKey = `${audioUuid ?? ""}|${composed}`;
  const [editsFor, setEditsFor] = useState(editsKey);
  if (editsFor !== editsKey) {
    setEditsFor(editsKey);
    resetEdits(NO_EDITS);
  }

  const { peaks, selected, preview, score, error } = view;

  /**
   * How long the piece is, and whether there is anything in it.
   *
   * Read from the envelope rather than from a separate request: the sheet already carries the
   * column count and the column length, and an empty piece is drawn as one empty column, so "no
   * notes" is the honest test rather than "no columns".
   */
  const pieceSeconds = score
    ? (score.envelope.frameCount * score.envelope.frameMs) / 1000
    : (peaks?.endSeconds ?? 0);
  const pieceIsEmpty = (peaks?.attackCount ?? 0) === 0;
  /**
   * A piece with nothing in it has nothing else to offer, so the passage stage is open on arrival.
   * On a piece that already has music the plot is what the reader came for, so it is folded away
   * until they ask. Derived rather than stored, so there is no state to keep in step.
   */
  const composeOpen =
    composeChoice === key || (composeChoice === null && Boolean(peaks) && pieceIsEmpty);

  const renderOverrides = useMemo(
    () => ({ hidden: hiddenNotes, hands: NO_HANDS }),
    [hiddenNotes],
  );

  /**
   * Every notehead still on the page, gathered into the chord it is drawn as part of.
   *
   * Keyed by the staff the note ends up on rather than the one the split gave it, because after a
   * move the chord a note beams with is the one on its new staff.
   */
  const chords = useMemo(() => {
    const found = new Map<string, number[]>();
    for (const note of score?.notes ?? []) {
      const ref: NoteRef = `${note.startFrame}:${note.row}`;
      if (hiddenNotes.has(ref)) continue;
      const staff = note.hand;
      const key = `${staff}:${note.startFrame}`;
      const rows = found.get(key);
      if (rows) rows.push(note.row);
      else found.set(key, [note.row]);
    }
    return found;
  }, [score, hiddenNotes]);

  /** The selection, gathered the same way, so the two can be compared chord by chord. */
  const selectedChords = useMemo(() => {
    const byGroup = new Map<string, Set<number>>();
    for (const noteKey of selectedNotes) {
      const key = groupKeyOf(noteKey);
      const rows = byGroup.get(key);
      if (rows) rows.add(rowOf(noteKey));
      else byGroup.set(key, new Set([rowOf(noteKey)]));
    }
    const whole: string[] = [];
    const partial: string[] = [];
    for (const [key, rows] of byGroup) {
      const all = chords.get(key) ?? [];
      if (all.length > 0 && all.every((row) => rows.has(row))) whole.push(key);
      else partial.push(key);
    }
    return { whole, partial };
  }, [selectedNotes, chords]);

  /** The whole selection is one chord, which is when several finger numbers make sense at once. */
  const oneChord = useMemo(() => {
    if (selectedNotes.length < 2) return null;
    const groups = new Set(selectedNotes.map(groupKeyOf));
    if (groups.size !== 1) return null;
    return [...selectedNotes].sort((left, right) => rowOf(left) - rowOf(right));
  }, [selectedNotes]);

  /**
   * The chords the selection touches, what they are all drawn as, and how to say otherwise.
   *
   * A figure belongs to a chord and never to one notehead — notes struck together are written as
   * one thing — so picking any note of a chord names the whole of it, which is what the single-note
   * panel always did. What a band adds is doing it to every chord at once: a passage written as a
   * mix of corcheas, semicorcheas and tresillos becomes one figure without a column moving. That is
   * safe here in a way it would not be on a bar-counted page, because a column is a slice of wall
   * clock and a figure is a label on a note rather than its length (D-18).
   *
   * `selectedPrintedFigure` below is empty when the chords picked disagree, so the row of pills
   * offers a name instead of claiming one of them is already the answer.
   */
  const selectedGroups = useMemo(
    () => [...new Set(selectedNotes.map(groupKeyOf))],
    [selectedNotes],
  );

  /**
   * What each chord on the page is actually drawn as: the reader's name where there is one, and the
   * score's otherwise.
   *
   * `namedGroups` below answers a narrower question — which chords the reader has renamed — and
   * that is the right question for the undo. It is the wrong one for a row of figure pills, which
   * has to show what is on the page whether anybody named it or not.
   */
  const printedFigures = useMemo(() => {
    const byGroup = new Map<string, FigureName>();
    for (const note of score?.notes ?? []) {
      const groupKey = `${note.hand}:${note.startFrame}`;
      if (!byGroup.has(groupKey)) byGroup.set(groupKey, note.figure);
    }
    for (const [groupKey, name] of Object.entries(overrides)) {
      byGroup.set(groupKey, name);
    }
    return byGroup;
  }, [score, overrides]);

  /** The one figure every picked chord prints as, or empty when they disagree. */
  const selectedPrintedFigure = useMemo<FigureName | "">(() => {
    const drawn = selectedGroups.map((groupKey) => printedFigures.get(groupKey));
    const first = drawn[0];
    if (!first) return "";
    return drawn.every((one) => one === first) ? first : "";
  }, [selectedGroups, printedFigures]);

  /**
   * Whether these notes could share one beam at all.
   *
   * Three conditions, and every one of them is a thing that cannot be drawn rather than a rule of
   * taste: a beam holds whole chords, it needs at least two of them, and every one has to print a
   * figure that carries flags — a negra has no beam to share. The button is disabled rather than
   * hidden so the tooltip can say which of the three is missing.
   */
  const beamable = useMemo(() => {
    if (selectedChords.partial.length > 0 || selectedChords.whole.length < 2) return false;
    return selectedChords.whole.every((groupKey) => {
      const name = printedFigures.get(groupKey);
      return name !== undefined && BEAMABLE_FIGURES.has(name);
    });
  }, [selectedChords, printedFigures]);

  const joinedHere =
    selectedChords.whole.length > 0 &&
    selectedChords.whole.every((groupKey) => beamJoins.has(groupKey));
  const brokenHere =
    selectedChords.whole.length > 0 &&
    selectedChords.whole.every((groupKey) => beamBreaks.has(groupKey));

  /**
   * The run of columns the picked notes cover, on the one hand they are all on.
   *
   * `null` when the selection spans both hands or holds fewer than two onsets — neither of which is
   * a run that can be set evenly. A run needs two notes to have a distance between them.
   */
  const selectedRun = useMemo(() => {
    if (selectedNotes.length === 0) return null;
    const sides = new Set(selectedNotes.map(handOf));
    if (sides.size !== 1) return null;
    const columns = [...new Set(selectedNotes.map(frameOf))].sort((a, z) => a - z);
    if (columns.length < 2) return null;
    return {
      hand: [...sides][0]!,
      fromColumn: columns[0]!,
      toColumn: columns[columns.length - 1]! + 1,
    };
  }, [selectedNotes]);

  /** The even spacing already on this run, if the reader has asked for one. */
  const evenHere = useMemo(() => {
    if (!selectedRun) return null;
    return (
      evenSpacings.find(
        (run) =>
          run.hand === selectedRun.hand &&
          run.fromColumn === selectedRun.fromColumn &&
          run.toColumn === selectedRun.toColumn,
      ) ?? null
    );
  }, [selectedRun, evenSpacings]);

  /**
   * Set the picked run an equal distance apart, or put it back the way the page measured it.
   *
   * The scale starts at one, which is the **tightest even spacing the run allows** — every gap
   * opened out to the widest gap it already had. Nothing is ever closed up, because a gap is the
   * sum of its columns' own widths and a column cannot be narrower than the ink in it.
   */
  const toggleEvenSpacing = useCallback(() => {
    if (!selectedRun) return;
    setEvenSpacings((current) => {
      const kept = current.filter(
        (run) =>
          !(
            run.hand === selectedRun.hand &&
            run.fromColumn === selectedRun.fromColumn &&
            run.toColumn === selectedRun.toColumn
          ),
      );
      return kept.length < current.length ? kept : [...kept, { ...selectedRun, scale: 1 }];
    });
  }, [selectedRun, setEvenSpacings]);

  /**
   * Open the picked run further, or close it up.
   *
   * Only reachable once the run has been made even, which is why the two buttons are disabled until
   * then: there is nothing for them to be a multiple of until a run has one distance rather than
   * several.
   *
   * **It closes below one.** One is the widest gap the run already had, and that gap is usually
   * wide because of the *other* hand — a four-note chord with accidentals under one of these
   * notes — so evening a run to it makes the whole run as wide as its worst moment. A reader
   * looking at their own hand's notes with room to spare is right about that, and a control that
   * refuses them over a collision they can see has not happened is second-guessing what is in front
   * of them. Below one the glyphs may touch. That is visible, it is reversible, and it is theirs.
   */
  const nudgeEvenSpacing = useCallback(
    (by: number) => {
      if (!selectedRun) return;
      setEvenSpacings((current) =>
        current.map((run) =>
          run.hand === selectedRun.hand &&
          run.fromColumn === selectedRun.fromColumn &&
          run.toColumn === selectedRun.toColumn
            ? {
                ...run,
                scale:
                  Math.round(
                    Math.min(
                      MAX_EVEN_SPACING_SCALE,
                      Math.max(MIN_EVEN_SPACING_SCALE, run.scale + by),
                    ) * 100,
                  ) / 100,
              }
            : run,
        ),
      );
    },
    [selectedRun, setEvenSpacings],
  );

  /** Whether the picked notes are already inside a stretch printed small. */
  const cueHere = useMemo(() => {
    if (selectedNotes.length === 0) return false;
    const sides = new Set(selectedNotes.map(handOf));
    const side = sides.size === 1 ? [...sides][0]! : "single";
    const columns = selectedNotes.map(frameOf);
    const fromColumn = Math.min(...columns);
    const toColumn = Math.max(...columns) + 1;
    return cueRanges.some(
      (cue) => cue.hand === side && cue.fromColumn <= fromColumn && cue.toColumn >= toColumn,
    );
  }, [selectedNotes, cueRanges]);

  /**
   * Whether these notes could be one shake.
   *
   * One hand, and three onsets or more. That is the whole test, and it is deliberately looser than
   * the rule behind **Find trills**: an ornament the automatic rule was too strict for is exactly
   * the case a reader has to be able to overrule, and they are looking at the notes.
   */
  const trillable = useMemo(() => {
    if (selectedNotes.length < 3) return false;
    if (new Set(selectedNotes.map(handOf)).size !== 1) return false;
    return new Set(selectedNotes.map(frameOf)).size >= 3;
  }, [selectedNotes]);

  /** The chords in the selection that carry a name already, which is what the undo is about. */
  const namedGroups = useMemo(
    () => selectedGroups.filter((groupKey) => overrides[groupKey] !== undefined),
    [selectedGroups, overrides],
  );

  const drawSelectionAs = useCallback(
    (name: FigureName) => {
      setOverrides((current) => {
        const next = { ...current };
        for (const groupKey of selectedGroups) next[groupKey] = name;
        return next;
      });
    },
    [selectedGroups, setOverrides],
  );

  /** Back to whatever the score called them. */
  const unnameSelection = useCallback(() => {
    setOverrides((current) => {
      const next = { ...current };
      for (const groupKey of selectedGroups) delete next[groupKey];
      return next;
    });
  }, [selectedGroups, setOverrides]);

  const selectionKey = selectedNotes.join("|");
  // Numbers only belong to the selection they were pressed for. Carried with that selection rather
  // than cleared by an effect, so picking a different chord offers a clean row of chips without a
  // render in between showing the last chord's answer.
  const pickedFingers = useMemo<FingerNumber[]>(
    () =>
      fingerDraft?.forSelection === selectionKey ? fingerDraft.picked : [],
    [fingerDraft, selectionKey],
  );

  // Which stretch the toolbox is about, and what it will write. The signature offered is whatever
  // is already sounding at the start of the stretch, until the reader picks another.
  const rangeKey = range ? `${range.fromColumn}:${range.toColumn}` : "";

  /**
   * Which settings this stretch already carries, so its pill can say so before it is opened.
   *
   * Read from the stored edits rather than kept in state: a marker that could disagree with the
   * thing it marks is worse than no marker.
   */
  /**
   * The first sheet of a piece nobody has decided about brackets on takes the proposal whole.
   *
   * It replaces the baseline rather than becoming a step, because the reader did not do it. A
   * Command-Z on a page nobody has touched yet must do nothing, not take back something the page
   * did to itself before anyone arrived.
   */
  useEffect(() => {
    if (ottavasDecided.current || ottavaHint.length === 0) return;
    ottavasDecided.current = true;
    resetEdits((current) => ({ ...current, ottavas: ottavaHint }));
  }, [ottavaHint, resetEdits]);

  /** The scale the selected stretch is set at: the stretch that covers its first column, or 1. */
  const spacingHere = range
    ? (spacings.find(
        (stretch) =>
          stretch.fromColumn <= range.fromColumn && stretch.toColumn > range.fromColumn,
      )?.scale ?? 1)
    : 1;
  /**
   * Set the marked stretch to take `scale` times the room the page measured for it.
   *
   * A handle rather than the two step buttons it replaces. Those moved by a fixed factor each
   * press, so finding the spot a crowded run actually reads at meant pressing *Wider* five times
   * and *Narrower* twice while watching the page jump — and the number the reader was after is a
   * look, not an arithmetic sequence. The sheet redraws as the handle moves, so the spot is found
   * by seeing it.
   *
   * A scale of exactly one is stored as nothing, so a stretch put back where it started leaves no
   * mark on the page and none in the file.
   */
  const setRangeSpacing = (scale: number) => {
    if (!range) return;
    const next = Math.round(Math.min(4, Math.max(0.25, scale)) * 100) / 100;
    setSpacings((current) => [
      ...current.filter(
        (stretch) =>
          !(stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn),
      ),
      ...(next === 1
        ? []
        : [{ fromColumn: range.fromColumn, toColumn: range.toColumn, scale: next }]),
    ]);
  };
  const clearSpacingRange = () => {
    if (!range) return;
    setSpacings((current) =>
      current.filter(
        (stretch) =>
          !(stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn),
      ),
    );
  };

  /**
   * The staves the frame pills act on: the one the reader narrowed to, or both.
   *
   * A clef and an octave bracket belong to one hand, so narrowing is the whole point of the pills.
   * A key signature is drawn on both clefs whatever is chosen, and a line of words is sung over the
   * piece — those two read the scope and ignore it, which the panel says.
   */
  const handsInScope: PrintedHand[] =
    rangeHand === "both" ? ["right", "left"] : [rangeHand];

  const editedHere: Record<FrameTab, boolean> = {
    key: range
      ? keySignatureAtFrame(
          range.fromColumn,
          keySignature as KeySignature,
          keyChanges,
        ) !== keySignature ||
        keyChanges.some(
          (change) =>
            change.fromColumn > range.fromColumn &&
            change.fromColumn < range.toColumn,
        )
      : false,
    clef: range
      ? handsInScope.some(
          (side) => clefAtFrame(range.fromColumn, side, clefChanges) !== DEFAULT_CLEF[side],
        ) ||
        clefChanges.some(
          (change) =>
            change.fromColumn > range.fromColumn && change.fromColumn < range.toColumn,
        )
      : false,
    octave: range
      ? handsInScope.some(
          (side) => ottavaAtFrame(ottavas, side, range.fromColumn) !== undefined,
        )
      : false,
    lyrics: range
      ? lyrics.some(
          (line) =>
            line.fromColumn < range.toColumn && line.toColumn > range.fromColumn,
        )
      : false,
    spacing: range
      ? spacings.some(
          (stretch) =>
            stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn,
        )
      : false,
    rerecord: false,
  };


  /**
   * What the lyric tab needs to know about the stretch now open.
   *
   * Read from the marks themselves rather than kept in state: a panel that could disagree with
   * what is on the page is worse than a panel that has to look it up.
   */
  const lyricHere = range
    ? (lyrics.find(
        (line) =>
          line.fromColumn < range.toColumn && line.toColumn > range.fromColumn,
      ) ?? null)
    : null;
  const lyricText =
    lyricDraft?.forRange === rangeKey ? lyricDraft.text : (lyricHere?.text ?? "");

  /** Row 0 is MIDI 21, the bottom A of an 88-key piano. */
  const noteNameAt = useCallback((row: number) => noteName(row + 21), []);

  /** The suggestions that are not already written as a trill. */
  const unmarkedTrills = useMemo(
    () =>
      (trillSuggestions ?? []).filter(
        (one) =>
          !trills.some(
            (mark) =>
              mark.hand === one.hand &&
              mark.startFrame < one.endFrame &&
              mark.endFrame > one.startFrame,
          ),
      ),
    [trillSuggestions, trills],
  );


  /**
   * The one note picked, or `null` when none or several are.
   *
   * A grace note leans on exactly one note. Offering it for a chord would have to answer which
   * notehead it hangs off, and the honest answer is that the reader has to say.
   */
  const onlyNote = selectedNotes.length === 1 ? selectedNotes[0]! : null;
  const graceHere = onlyNote
    ? (graceNotes.find(
        (one) =>
          one.hand === handOf(onlyNote) &&
          one.startFrame === frameOf(onlyNote) &&
          one.targetRow === rowOf(onlyNote),
      ) ?? null)
    : null;

  /**
   * Put a decoration note of a given pitch in front of the note it leans on, replacing any already
   * there.
   *
   * The pitch is picked on a keyboard rather than off a list of intervals. The list was six
   * buttons — a tone below, a third above — which covers most decorations and refuses the rest, and
   * it asked a reader to do arithmetic on a page where they can already see the note they want. The
   * keyboard shows the note being decorated in one colour and the decoration in another, so the
   * question is answered by pointing at it.
   *
   * Every one of them leans on its note. Crushed and leaned-on is a distinction a reader can make
   * in their playing and rarely wants to argue about in print, and offering the choice cost two
   * buttons and a paragraph explaining them.
   */
  const putGrace = useCallback(
    (noteKey: string, row: number) => {
      if (row < 0 || row > 87 || row === rowOf(noteKey)) return;
      const grace: GraceNote = {
        hand: handOf(noteKey),
        startFrame: frameOf(noteKey),
        targetRow: rowOf(noteKey),
        row,
        kind: "appoggiatura",
      };
      setGraceNotes((current) => [
        ...current.filter(
          (one) =>
            !(
              one.hand === grace.hand &&
              one.startFrame === grace.startFrame &&
              one.targetRow === grace.targetRow
            ),
        ),
        grace,
      ]);
    },
    [setGraceNotes],
  );

  /** Take the decoration off the note it leans on. */
  const clearGrace = useCallback(() => {
    if (!graceHere) return;
    setGraceNotes((current) => current.filter((one) => one !== graceHere));
  }, [graceHere, setGraceNotes]);

  /** Ask the backend where two notes are trading places. Nothing is written by asking. */
  const findTrills = useCallback(async () => {
    if (!audioUuid) return;
    setFindingTrills(true);
    try {
      const found = await timeScoreApi.trills(audioUuid, { frameMs });
      setTrillSuggestions(found.suggestions);
    } catch {
      // Nothing on the page depends on the answer, so a failure leaves the sheet as it is.
      setTrillSuggestions([]);
    } finally {
      setFindingTrills(false);
    }
  }, [audioUuid, frameMs]);

  const passageKey: KeySignatureName =
    passageDraft?.forRange === rangeKey
      ? passageDraft.value
      : (keySignatureAtFrame(
          range?.fromColumn ?? 0,
          keySignature as KeySignature,
          keyChanges,
        ) as KeySignatureName);

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    timeScoreApi
      .peaks(audioUuid, { hand, frameMs }, controller.signal)
      .then((found) => {
        setUntranscribed(false);
        // The pile holding most of the playing is the one a reader looks at first, so it starts
        // chosen. Nothing is committed by that: the sheet only appears once a name is given.
        const biggest =
          [...found.peaks].sort((a, b) => b.share - a.share)[0] ?? null;
        setView((current) =>
          current.key === key
            ? { ...current, peaks: found, selected: biggest }
            : current,
        );
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        // Stop waiting. Leaving the spinner turning says "nearly there" to a
        // reader whose piece is never going to load.
        setUntranscribed(notTranscribed(caught));
        setView((current) =>
          current.key === key
            ? {
                ...current,
                error: readable(caught, "Could not read the rhythm."),
              }
            : current,
        );
      });
    return () => controller.abort();
  }, [audioUuid, hand, frameMs, key]);

  // Read back what this piece was last read as, once per piece — and again after a passage is
  // placed, because an insertion moves every mark after it and the columns held here are stale.
  //
  // Restoring the anchor is not enough on its own: the pile it names has to be the one the plot
  // shows, or the number under the name would say one thing and the highlighted bar another. So the
  // nearest pile is selected too, and if none is near, the saved reading is kept and the plot simply
  // has nothing highlighted, which is honest about the two disagreeing.
  //
  // The reading arrives as the baseline and not as a step. It is where the reader left off rather
  // than something they have just done, and a Command-Z that emptied the page on arrival would be
  // the worst possible first impression of an undo.
  useEffect(() => {
    if (!audioUuid) return;
    // Whether anybody has decided about brackets is a fact about this piece, so a different piece
    // has not been asked yet and may take the page's own proposal.
    ottavasDecided.current = false;
    const controller = new AbortController();
    timeScoreApi
      .rhythm(audioUuid, controller.signal)
      .then((found) => {
        if (!found) return;
        setSaved(found);
        setHand(found.hand);
        setFigure(found.anchorFigure);
        // A reading that carries a list of brackets — even an empty one — was decided; one saved
        // before brackets existed was not, and the page may take its own proposal.
        ottavasDecided.current = Array.isArray(found.ottavas);
        resetEdits({
          keySignature: found.keySignature ?? "C",
          keyChanges: (found.keyChanges ?? []).map((change) => ({
            fromColumn: change.fromColumn,
            keySignature: change.keySignature as KeySignature,
          })),
          clefChanges: (found.clefChanges ?? []).map((change) => ({
            fromColumn: change.fromColumn,
            hand: change.hand === "left" ? ("left" as const) : ("right" as const),
            clef: change.clef as Clef,
          })),
          // Whatever the reader put there, and nothing when they put nothing. A reading saved
          // before brackets existed simply has none, which is now the same answer as any other
          // piece nobody has bracketed.
          ottavas: (found.ottavas ?? []).map((span) => ({
            kind: span.kind as OttavaKind,
            hand: span.hand === "left" ? ("left" as const) : ("right" as const),
            fromColumn: span.fromColumn,
            toColumn: span.toColumn,
            // Absent on a reading saved before a bracket could be hidden, which reads as drawn —
            // the same answer that reading was saved with.
            hidden: span.hidden ?? false,
          })),
          trills: found.trills ?? [],
          lyrics: found.lyrics ?? [],
          cueRanges: found.cueRanges ?? [],
          spacings: found.spacings ?? [],
          evenSpacings: (found.evenSpacings ?? []).map((run) => ({
            hand: run.hand === "left" ? ("left" as const) : ("right" as const),
            fromColumn: run.fromColumn,
            toColumn: run.toColumn,
            scale: run.scale,
          })),
          fingers: Object.fromEntries(
            (found.fingers ?? []).map((one) => [
              `${one.hand}:${one.startFrame}:${one.row}`,
              one.finger as FingerNumber,
            ]),
          ),
          overrides: Object.fromEntries(
            found.overrides.map((one) => [
              `${one.hand}:${one.startFrame}`,
              one.figure,
            ]),
          ),
          beamBreaks: new Set(
            found.beamBreaks.map((one) => `${one.hand}:${one.startFrame}`),
          ),
          beamJoins: new Set(
            (found.beamJoins ?? []).map((one) => `${one.hand}:${one.startFrame}`),
          ),
          hiddenNotes: new Set(
            (found.hiddenNotes ?? []).map(
              (one) => `${one.startFrame}:${one.row}`,
            ),
          ),
          graceNotes: found.graceNotes ?? [],
          dropDecorative: found.dropDecorative ?? false,
          annotationScale: found.annotationScale ?? 1,
          lineSpacing: found.lineSpacing ?? DEFAULT_LINE_SPACING,
          noteSpacing: found.noteSpacing ?? DEFAULT_NOTE_SPACING,
          staffGaps: found.staffGaps ?? [],
          stretches: found.speedChanges.map((change) => ({
            startFrame: change.startFrame,
            anchorMs: change.anchorMs,
          })),
        });
      })
      .catch(() => {
        // A reading that cannot be read is not worth stopping the screen for: the plot still works
        // and the reader can name the gap again.
      });
    return () => controller.abort();
  }, [audioUuid, composed, resetEdits]);

  /**
   * Both of these have to keep the same identity between renders.
   *
   * The sheet is rebuilt whenever anything it draws from changes, and a handler written inline is a
   * different function every time, so the sheet would be rebuilt on every click and would lose the
   * selection it had just made.
   */
  const pickRange = useCallback(
    (
      picked: { fromColumn: number; toColumn: number },
      options?: { adjusting?: boolean },
    ) => {
      setRange(picked);
      setFramesToolbox(true);
      // Only when the stretch is a new one.
      //
      // Dragging an end of a stretch that is already marked reports through here too, and placing
      // the panel again on every step of that drag put it next to the *handle* — which is the end
      // being dragged, so the panel walked along underneath the stretch it was supposed to be clear
      // of. Where a panel sits is the reader's, from the moment it opens: it moves when they drag
      // it and at no other time.
      if (options?.adjusting) return;
      // The click, for now. The highlight it is supposed to be clear of is not painted until a
      // render later, so this is an opening guess and the effect below settles it.
      setFramesAt(clearOfRange(pressedAt.current));
      setFramesOpenedAt((at) => at + 1);
    },
    [],
  );

  /**
   * Put the frames toolbox clear of the highlight the page actually painted.
   *
   * The click is the only thing on screen at the moment a stretch is marked, so that is what the
   * placement above can measure — and a click is sixteen pixels while the stretch it starts is
   * whatever the reader drags it out to. That was survivable until the sheet could be **magnified**:
   * at 3× the band is three times the size and the panel, placed beside a point, lands inside it.
   *
   * So it is placed again here, against the band itself. On the next animation frame rather than in
   * the effect body: the band is drawn by the sheet's own effect and the only moment its box is a
   * real answer is after the page has painted, which is what `requestAnimationFrame` waits for.
   */
  useEffect(() => {
    if (framesOpenedAt === 0) return;
    const frame = requestAnimationFrame(() => {
      const band = firstLineBoxOf(".grid-frame-range-fill");
      if (band) setFramesAt(clearOfRange(band));
    });
    return () => cancelAnimationFrame(frame);
  }, [framesOpenedAt]);

  /**
   * Every page edit that still has a note under it. What gets drawn, and what gets saved.
   *
   * An override is a statement *about* something drawn. Move the notes it was about to the other
   * staff, or take them off the page, and there is nothing left for it to be about — but the edit
   * is still in the state, and a range one keeps drawing. That is the `8vb` David found stretched
   * across an empty treble staff after its chords went to the left hand: a bracket saying "this
   * sounds an octave down" over nothing at all.
   *
   * So an override has to touch at least one note to count, checked against what the page actually
   * draws. Filtered here rather than deleted from the state, because the state is what the reader
   * said and the notes can come back: undo the move and the bracket is over its chords again,
   * exactly the way undoing a deletion restores the note. Nothing dead is drawn, and nothing dead
   * is written to the file, which is the whole of what "delete it" has to mean.
   *
   * Empty until the sheet exists, and then everything would look orphaned — so before that, and
   * only before that, the reader's own list is passed through untouched.
   */
  /**
   * What is sounding in each column, which hand is holding it, and where that note began.
   *
   * The onset matters as much as the pitch: the keyboard panel is a way of *editing* a chord now,
   * and a note is addressed by the column it started in — not by the column the reader happens to
   * be looking at halfway through it. The run each held cell belongs to is worked out the same way
   * the drawing works it out, breaking at a new attack and at a gap in the columns.
   *
   * Notes the reader has taken off the page are left out, so the keyboard and the sheet agree.
   */
  const soundingByFrame = useMemo(() => {
    const byFrame = new Map<number, SoundingNote[]>();
    if (!score || !pianoOpen) return byFrame;
    for (const [side, matrix] of [
      ["right", score.envelope.rMatrix],
      ["left", score.envelope.lMatrix],
    ] as const) {
      const byRow = new Map<number, { col: number; onset: boolean }[]>();
      matrix.rows.forEach((row, index) => {
        const cell = { col: matrix.cols[index]!, onset: matrix.onset[index] === row };
        const cells = byRow.get(row);
        if (cells) cells.push(cell);
        else byRow.set(row, [cell]);
      });
      for (const [row, cells] of byRow) {
        cells.sort((left, right) => left.col - right.col);
        let onsetFrame: number | null = null;
        let previous: number | null = null;
        for (const cell of cells) {
          const broken = previous !== null && cell.col !== previous + 1;
          if (cell.onset || onsetFrame === null || broken) onsetFrame = cell.col;
          previous = cell.col;
          if (hiddenNotes.has(`${onsetFrame}:${row}`)) continue;
          const here = byFrame.get(cell.col);
          const note: SoundingNote = { row, hand: side, onsetFrame };
          if (here) here.push(note);
          else byFrame.set(cell.col, [note]);
        }
      }
    }
    return byFrame;
  }, [score, pianoOpen, hiddenNotes]);

  /**
   * Which column the playhead is in, as a whole number.
   *
   * The nudge is not superstition. A column turned into seconds and back is a division and a
   * multiplication in binary floating point, and on about one column in a hundred the answer comes
   * out a hair *under* the whole number — so a cursor put exactly on a note landed in the column
   * before it, and the keyboard panel drew the wrong chord. A millionth of a column is far below
   * anything that can be seen and far above the error.
   */
  const playheadFrame = useMemo(() => {
    if (!score || playheadSeconds === null) return null;
    return Math.floor((playheadSeconds * 1000) / score.envelope.frameMs + 1e-6);
  }, [score, playheadSeconds]);

  const soundingNow = useMemo<readonly SoundingNote[]>(
    () => (playheadFrame === null ? [] : (soundingByFrame.get(playheadFrame) ?? [])),
    [playheadFrame, soundingByFrame],
  );

  /**
   * One colour per hand, and a paler one for a key held from an earlier column.
   *
   * Two things a reader needs at once: who is playing this note, and whether it begins here. Full
   * colour is struck in this column and has a notehead on the page under the cursor; pale is still
   * ringing from a note that began further back, and its notehead is where it began.
   */
  const soundingColours = useMemo(() => {
    const colours: Record<number, string> = {};
    for (const note of soundingNow) {
      colours[note.row] =
        note.onsetFrame === playheadFrame
          ? HAND_COLOUR[note.hand]
          : HELD_COLOUR[note.hand];
    }
    return colours;
  }, [soundingNow, playheadFrame]);

  const live = useMemo(() => {
    if (!score || chords.size === 0) {
      return { ottavas, beamBreaks, beamJoins, overrides, fingers, evenSpacings };
    }
    const occupied: Record<PrintedHand, number[]> = { right: [], left: [] };
    for (const groupKey of chords.keys()) {
      const [staff, frame] = groupKey.split(":");
      occupied[staff === "left" ? "left" : "right"].push(Number(frame));
    }
    const anyNoteUnder = (
      staff: PrintedHand,
      fromColumn: number,
      toColumn: number,
    ): boolean =>
      occupied[staff].some((frame) => frame >= fromColumn && frame < toColumn);

    return {
      ottavas: ottavas.filter((span) =>
        anyNoteUnder(
          span.hand === "left" ? "left" : "right",
          span.fromColumn,
          span.toColumn,
        ),
      ),
      beamBreaks: new Set(
        [...beamBreaks].filter((groupKey) => chords.has(groupKey)),
      ),
      beamJoins: new Set(
        [...beamJoins].filter((groupKey) => chords.has(groupKey)),
      ),
      overrides: Object.fromEntries(
        Object.entries(overrides).filter(([groupKey]) => chords.has(groupKey)),
      ),
      evenSpacings: evenSpacings.filter((run) =>
        anyNoteUnder(run.hand, run.fromColumn, run.toColumn),
      ),
      fingers: Object.fromEntries(
        Object.entries(fingers).filter(([noteKey]) =>
          chords.has(groupKeyOf(noteKey)),
        ),
      ),
    };
  }, [score, chords, ottavas, beamBreaks, beamJoins, overrides, fingers, evenSpacings]);

  /**
   * A lyric's block was dragged somewhere, or its right edge pulled in. Keep where it was put.
   *
   * The columns it is stored against never change, so the words stay with their music through a
   * re-wrap and this is only how far from it the reader moved them. Reported once when the pointer
   * is let go, which is what makes it one step of Command-Z rather than one per pixel.
   */
  const placeLyric = useCallback(
    (change: LyricLayoutChange) => {
      setLyrics((current) =>
        current.map((line) =>
          line.fromColumn === change.fromColumn && line.toColumn === change.toColumn
            ? {
                ...line,
                offsetX: change.offsetX,
                offsetY: change.offsetY,
                width: change.width,
              }
            : line,
        ),
      );
    },
    [setLyrics],
  );

  /** Bring the cursor on screen — space, a click on the bar, a jump the reader did not make. */
  const scrollToCursor = useCallback(
    () => setScrollCursorAt((at) => at + 1),
    [],
  );

  /** The cursor was dragged. The transport owns the recording, so it does the moving. */
  const scrub = useCallback(
    (seconds: number) => player.current?.seek(seconds),
    [],
  );

  /**
   * A corner mark was clicked: select the stretch it belongs to and open the toolbox on it.
   *
   * This is the point of drawing the corners. A stretch that carries an edit is visible without
   * being selected, so a reader who wants to undo one goes straight to it instead of remembering
   * which columns they used.
   */
  const pickMarkedRange = useCallback(
    (marker: { kind: string; hand: string; fromColumn: number; toColumn: number }) => {
      setRange({ fromColumn: marker.fromColumn, toColumn: marker.toColumn });
      // The stretch arrives with its own answers to the two questions the panel asks first: which
      // staff it is about, and which kind of markup it carries. Filling both in is the difference
      // between "here is the stretch" and "here is the thing you clicked" — a reader who clicks an
      // octave bracket is asking about that bracket, not about the columns under it.
      if (marker.hand === "right" || marker.hand === "left") setRangeHand(marker.hand);
      const tab = MARKER_TABS[marker.kind];
      if (tab) setFrameTab(tab);
      setFramesToolbox(true);
      setFramesAt(clearOfRange(pressedAt.current));
      setFramesOpenedAt((at) => at + 1);
    },
    [],
  );

  /**
   * A reader pulled one end of an octave bracket on the sheet and let go.
   *
   * The bracket being dragged wins over whatever it now reaches: enlarging an `8va` over a `15ma`
   * leaves the `8va` and no trace of the `15ma`. Two brackets over one note would have to be added
   * together, which is never what anyone meant, and refusing the drag instead would leave the
   * reader dragging against a wall with nothing on the page to say why.
   *
   * One step in the history, so Command-Z puts the bracket back the length it was.
   */
  const stretchOttava = useCallback(
    (change: OttavaResizeChange) => {
      const frameCount = score?.envelope.frameCount;
      if (frameCount === undefined) return;
      setOttavas((current) =>
        resizeOttava(
          current,
          { hand: change.hand, fromColumn: change.fromColumn, toColumn: change.toColumn },
          { fromColumn: change.nextFromColumn, toColumn: change.nextToColumn },
          frameCount,
        ),
      );
    },
    [score, setOttavas],
  );

  /**
   * Take the bracket off the page without taking the reading off the piece.
   *
   * A player who already knows a passage is played an octave up does not need a dashed line over
   * every bar of it saying so, and above the right hand is the most crowded strip on the page. But
   * the notes under a bracket are written an octave from where they sound: un-shifting them would
   * be a different edit, and a reader asking for less ink would get a wall of ledger lines. So the
   * transposition stays and only the bracket goes.
   *
   * **Not a way of removing one.** The trash button in the Octave pill is the only way out, which
   * is why a hidden bracket keeps its corner marks — they are the way back to it.
   *
   * The bracket covering the **first column** of the stretch, which is the one the pill's chips are
   * already describing. Every bracket the stretch overlaps would be more generous and would make
   * the panel lie: the row says `8va` about one bracket, and the eye beside it would have acted on
   * two.
   */
  const setOttavaHidden = useCallback(
    (hands: readonly PrintedHand[], atColumn: number, hidden: boolean) => {
      setOttavas((current) =>
        current.map((span) =>
          hands.includes(span.hand) && span.fromColumn <= atColumn && span.toColumn > atColumn
            ? { ...span, hidden }
            : span,
        ),
      );
    },
    [setOttavas],
  );

  /**
   * Picking noteheads also takes the recording to where they are.
   *
   * Every note is a moment as well as a pitch, and the keyboard panel only ever draws one moment —
   * the one under the cursor. Without this, clicking a chord on the staves opened a panel about it
   * while the keyboard went on showing whatever the cursor happened to be standing on, which is
   * usually a different chord and sometimes nothing at all.
   *
   * The **first** column of the selection, when a band takes in several: a range has to resolve to
   * one moment and its start is the one the reader dragged from.
   *
   * The page is deliberately **not** scrolled. The reader is looking at the notes they just
   * clicked; bringing the cursor on screen would only take that place away. This is the same choice
   * the double-click seek makes, for the same reason.
   */
  const pickNotes = useCallback(
    (keys: readonly string[]) => {
      setSelectedNotes(keys);
      setNotesToolbox(keys.length > 0);
      if (keys.length === 0) return;
      // Measured from the noteheads rather than from the click, so a rubber band that took in half
      // the line opens its panel clear of the whole band instead of on top of it.
      setNotesAt(
        besideOnScreen(
          screenBoxOf(".grid-note-target.is-selected") ?? pressedAt.current,
        ),
      );
      player.current?.seek((Math.min(...keys.map(frameOf)) * frameMs) / 1000);
    },
    [frameMs],
  );

  /**
   * Which note is picked, said in solfège: `Do 4`, `Do-# 3`, `Re-b 5`.
   *
   * Only when exactly one is picked. A chord is three notes at one moment and naming all of them in
   * a panel title would be a list rather than an answer; the keyboard under **Show piano** is where
   * a chord is read.
   *
   * **Spelled the way the sheet spells it**, through the same `pitchToStaffPosition` the noteheads
   * come from, against the signature sounding at that column — so a black key printed as `Re-b`
   * under five flats is called `Re-b` here and not `Do-#`. Working the name out from the row on its
   * own would have been a second opinion about the same note.
   *
   * The hand is the staff the note is drawn on and has nothing to do with the name; it is passed
   * because the spelling takes it, and it only moves the staff step, which this throws away. An
   * octave bracket does not move it either: `letter` and `octave` are the note as it **sounds**.
   */
  const pickedNoteName =
    selectedNotes.length === 1 && selectedNotes[0]
      ? spanishNoteName(
          pitchToStaffPosition(
            rowOf(selectedNotes[0]),
            handOf(selectedNotes[0]),
            keySignatureAtFrame(
              frameOf(selectedNotes[0]),
              keySignature as KeySignature,
              keyChanges,
            ),
          ),
        )
      : null;

  /**
   * Closing a toolbox lets the selection go with it.
   *
   * A dashed outline left on the page after its panel has gone says something is still picked when
   * nothing is, and the next click would then extend that invisible selection instead of starting a
   * new one.
   */
  const closeFrames = useCallback(() => {
    setFramesToolbox(false);
    setRange(null);
    setPassageDraft(null);
    // The hand scope is part of the selection, so it goes when the selection does. It survives one
    // stretch to the next while the panel stays open, which is what a reader narrowing a clef to
    // the left hand for a whole page wants.
    setRangeHand("both");
    setClearedAt((at) => at + 1);
  }, []);

  const closeNotes = useCallback(() => {
    setNotesToolbox(false);
    setSelectedNotes([]);
    // The decoration keyboard is about one picked note, so it cannot outlive the picking.
    setDecorationFor(null);
    setClearedAt((at) => at + 1);
  }, []);

  /**
   * The noteheads a marked stretch covers, on the staves the hand pills name.
   *
   * By the column a note **begins** in, which is the column it is addressed by everywhere else on
   * this page — a note struck before the stretch and still sounding through it is not in it, the
   * same way it is not in the stretch's beam and does not take its figure from it. `toColumn` is
   * exclusive, as it is in every range this page holds.
   */
  const notesUnderRange = useMemo<readonly string[]>(() => {
    if (!range) return [];
    const hands: PrintedHand[] = rangeHand === "both" ? ["right", "left"] : [rangeHand];
    const keys: string[] = [];
    for (const [groupKey, rows] of chords) {
      const [staffName, frameText] = groupKey.split(":");
      const staff: PrintedHand = staffName === "left" ? "left" : "right";
      const frame = Number(frameText);
      if (!hands.includes(staff)) continue;
      if (frame < range.fromColumn || frame >= range.toColumn) continue;
      for (const row of rows) keys.push(`${staff}:${frame}:${row}`);
    }
    return keys.sort((left, right) =>
      frameOf(left) === frameOf(right)
        ? rowOf(left) - rowOf(right)
        : frameOf(left) - frameOf(right),
    );
  }, [range, rangeHand, chords]);

  /**
   * The two selections are one selection, said two ways, and either button hands it to the other.
   *
   * A reader who has picked three noteheads and now wants a clef change over them was marking the
   * same music twice: once by clicking the notes, and then again on the ruler, by eye, trying to
   * find the columns they were already pointing at. Both directions are exact, because both read
   * the same addresses — a note carries the column it begins in, and a stretch of columns carries
   * every note that begins inside it.
   *
   * **Neither of them raises `clearedAt`.** That is the page's "drop everything picked", and it
   * clears the stretch *and* the noteheads — which is precisely one half too much here, and would
   * wipe the selection this has just handed over. Each side is closed by hand instead.
   *
   * The selection itself is made through the renderer rather than by writing state: the renderer
   * owns which noteheads are picked, and `setSelection` reports straight back through the same
   * `onSelectionChange` a click does, so the panel opens, is placed and takes the cursor to the
   * notes exactly as if the reader had clicked them.
   */
  const selectNotesUnderRange = useCallback(() => {
    if (!range || notesUnderRange.length === 0) return;
    setFramesToolbox(false);
    setPassageDraft(null);
    // The hand scope goes with the stretch: the noteheads now say which staff this is about, and a
    // scope left behind would narrow the *next* stretch the reader marks.
    setRangeHand("both");
    setRange(null);
    sheetRenderer?.setSelection(notesUnderRange);
  }, [range, notesUnderRange, sheetRenderer]);

  /**
   * The other way: the stretch from the leftmost picked note to the rightmost.
   *
   * Whichever staff they are on. A selection spanning both hands names the columns it spans and the
   * scope stays **Both**; one that is all in one hand arrives with that hand's pills already
   * pressed, because a reader who picked only left-hand notes is about to do something to the left
   * hand.
   *
   * The end is the last picked column **plus one**, because a range is half-open here: a stretch
   * ending at the column its last note begins in would not contain that note.
   */
  const selectRangeOfNotes = useCallback(() => {
    if (selectedNotes.length === 0) return;
    const columns = selectedNotes.map(frameOf);
    const hands = new Set(selectedNotes.map(handOf));
    // Measured before the selection goes, because it is the noteheads that say where the frames
    // panel should open and they are about to stop being marked.
    const box = screenBoxOf(".grid-note-target.is-selected") ?? pressedAt.current;
    sheetRenderer?.clearSelection();
    setNotesToolbox(false);
    setSelectedNotes([]);
    setDecorationFor(null);
    setRangeHand(hands.size === 1 ? [...hands][0]! : "both");
    setRange({
      fromColumn: Math.min(...columns),
      toColumn: Math.max(...columns) + 1,
    });
    setFramesToolbox(true);
    setFramesAt(clearOfRange(box));
    setFramesOpenedAt((at) => at + 1);
  }, [selectedNotes, sheetRenderer]);

  /**
   * Put the numbers that are pressed onto the notes that are picked.
   *
   * One number goes on every note in the selection, which is what a run of the same finger is. Two
   * or more only mean anything on a single chord: there the numbers are read low to high against the
   * noteheads low to high, which is the order a hand takes them in and the order they print in. A
   * selection spanning several onsets keeps to one number, because pairing across chords would be
   * guessing which note in one chord answers which in the next.
   */
  const applyFingers = useCallback(
    (
      picked: FingerNumber[],
      notes: readonly string[],
      chord: readonly string[] | null,
    ) => {
      setFingers((current) => {
        const next = { ...current };
        for (const noteKey of notes) delete next[noteKey];
        if (picked.length === 0) return next;
        if (chord && picked.length > 1) {
          const ordered = [...picked].sort((left, right) => left - right);
          chord.forEach((noteKey, index) => {
            const finger = ordered[index];
            if (finger !== undefined) next[noteKey] = finger;
          });
          return next;
        }
        const one = picked[picked.length - 1]!;
        for (const noteKey of notes) next[noteKey] = one;
        return next;
      });
    },
    [setFingers],
  );

  const pressFinger = useCallback(
    (finger: FingerNumber) => {
      const single = oneChord === null;
      const already = pickedFingers.includes(finger);
      const picked: FingerNumber[] = single
        ? already
          ? []
          : [finger]
        : already
          ? pickedFingers.filter((one) => one !== finger)
          : [...pickedFingers, finger];
      setFingerDraft({ forSelection: selectionKey, picked });
      applyFingers(picked, selectedNotes, oneChord);
    },
    [applyFingers, oneChord, pickedFingers, selectedNotes, selectionKey],
  );

  /**
   * Take the picked notes off the page.
   *
   * Marked here and nothing more. **Save** is what takes them out of the piano matrix the piece is
   * drawn from, which is also what makes the roll and the falling view agree with this page; until
   * then it is only the drawing that has stopped asking for them. `wipe` puts them back.
   */
  const hideSelected = useCallback(() => {
    const refs = selectedNotes.map(noteRefOf);
    setHiddenNotes((current) => new Set([...current, ...refs]));
    setFingers((current) => {
      const next = { ...current };
      for (const noteKey of selectedNotes) delete next[noteKey];
      return next;
    });
    closeNotes();
  }, [selectedNotes, closeNotes, setFingers, setHiddenNotes]);

  /**
   * Cut the beam in front of the picked chords, or join it again.
   *
   * A beam holds a whole chord, so it can only be cut in front of all of it — half a chord starting
   * a new group is not a thing that can be drawn. Cutting also drops any *join* on the same chords:
   * the two are opposite answers to one question, and holding both would mean the reader had said
   * two contradictory things about the same note.
   */
  const toggleBeamBreak = useCallback(() => {
    const targets = selectedChords.whole;
    if (targets.length === 0 || selectedChords.partial.length > 0) return;
    const breaking = !targets.every((key) => beamBreaks.has(key));
    setBeamBreaks((current) => {
      const next = new Set(current);
      for (const key of targets) {
        if (breaking) next.add(key);
        else next.delete(key);
      }
      return next;
    });
    if (breaking) {
      setBeamJoins((current) => {
        const next = new Set(current);
        for (const key of targets) next.delete(key);
        return next;
      });
    }
  }, [selectedChords, beamBreaks, setBeamBreaks, setBeamJoins]);

  /**
   * Beam the picked notes as one group, whatever the page's own rule makes of them.
   *
   * The rule cuts a run where it turns over at its lowest note, which is right for an arpeggio and
   * wrong for a scale that happens to dip a step. Only the reader can tell those apart, and this is
   * where they say so: every chord in the selection is marked as not starting a group, and any
   * break the reader had put inside the selection is taken off, because it says the opposite.
   *
   * It only reaches a run the page could beam at all — everything in it has to be a corchea or
   * shorter, since a negra has no beam to share. `beamable` below is what decides that.
   */
  const joinBeams = useCallback(() => {
    const targets = selectedChords.whole;
    if (targets.length === 0) return;
    setBeamJoins((current) => new Set([...current, ...targets]));
    setBeamBreaks((current) => {
      const next = new Set(current);
      for (const key of targets) next.delete(key);
      return next;
    });
  }, [selectedChords, setBeamBreaks, setBeamJoins]);

  /**
   * Write the picked notes as one held note with `tr` over it.
   *
   * It used to be a pill on the frames toolbox, which had to ask which hand and then guess which
   * note of that hand the shake stood on. A selection answers both: the hand is the hand the notes
   * are on, the run is from the first column to the last, and the note that stays is the lowest —
   * because `tr` means "alternate with the note above".
   */
  const markTrillOnSelection = useCallback(() => {
    if (selectedNotes.length === 0) return;
    const side = handOf(selectedNotes[0]!);
    if (!selectedNotes.every((noteKey) => handOf(noteKey) === side)) return;
    const columns = selectedNotes.map(frameOf);
    const rows = selectedNotes.map(rowOf);
    setTrills((current) => [
      ...current,
      {
        hand: side,
        startFrame: Math.min(...columns),
        endFrame: Math.max(...columns) + 1,
        row: Math.min(...rows),
      },
    ]);
    closeNotes();
  }, [selectedNotes, setTrills, closeNotes]);

  /**
   * Print the picked notes smaller than the rest of the page, or full size again.
   *
   * Also moved off the frames toolbox, and for the same reason: "these notes are decoration" is a
   * statement about notes. The stretch it writes is the columns the selection covers, on the staff
   * the selection is on — which is what the panel used to make the reader say twice.
   */
  const toggleCueOnSelection = useCallback(() => {
    if (selectedNotes.length === 0) return;
    const sides = new Set(selectedNotes.map(handOf));
    const side = sides.size === 1 ? [...sides][0]! : "single";
    const columns = selectedNotes.map(frameOf);
    const fromColumn = Math.min(...columns);
    const toColumn = Math.max(...columns) + 1;
    setCueRanges((current) => {
      const covering = current.filter(
        (cue) =>
          cue.hand === side && cue.fromColumn <= fromColumn && cue.toColumn >= toColumn,
      );
      if (covering.length > 0) {
        return current.filter((cue) => !covering.includes(cue));
      }
      return [
        ...current.filter(
          (cue) =>
            !(cue.hand === side && cue.fromColumn < toColumn && cue.toColumn > fromColumn),
        ),
        { hand: side, fromColumn, toColumn },
      ];
    });
  }, [selectedNotes, setCueRanges]);

  const sayRefused = useCallback((refused: readonly NoteRef[]) => {
    setMoveRefused(
      refused.length === 0
        ? null
        : `${refused.length} note${refused.length === 1 ? "" : "s"} stayed where they were: the other staff already plays that key at that moment, and one key cannot be struck twice in the same frame.`,
    );
  }, []);

  /**
   * Delete takes the picked notes off the page, exactly as the trash button does.
   *
   * The same call, so it is the same one step in the history and Command-Z brings them back
   * whichever way they went — a shortcut that did its own thing would be a second way to delete a
   * note and a second thing to keep in step with the undo.
   *
   * **Both keys.** On a Mac the key most people call Delete sends `Backspace`; `Delete` is the
   * forward one, which the full keyboards have. Refusing one of them would be right about the names
   * and wrong about the hands.
   *
   * It stands down while the focus is in a field, because there Backspace already means something
   * and deleting four noteheads while somebody edits a lyric would be unforgivable.
   *
   * **With no note picked and a stretch marked, it hides that stretch's octave bracket instead.**
   * Notes first, because that is what the key has always meant here and a note is the smaller, more
   * frequent thing; and only then the bracket, because a marked stretch with nothing picked inside
   * it is a reader pointing at the stretch itself. Hiding is not removing — the notes stay written
   * where the bracket puts them and the trash button in the Octave pill is still the only way out.
   */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      const on = event.target as Element | null;
      if (on?.closest?.("input, textarea, select, [contenteditable='true']")) return;
      if (selectedNotes.length > 0) {
        // Backspace is the browser's "go back" on a page with nothing focused, which would take the
        // reader off the sheet and lose every edit they had not saved.
        event.preventDefault();
        hideSelected();
        return;
      }
      if (!range) return;
      const hands: PrintedHand[] = rangeHand === "both" ? ["right", "left"] : [rangeHand];
      // Only the ones that are actually drawn. With every bracket here already hidden, Delete has
      // nothing to do, and swallowing the key would leave the reader pressing it at nothing.
      const bracketed = hands.filter((side) => {
        const span = ottavaAtFrame(ottavas, side, range.fromColumn);
        return span !== undefined && !span.hidden;
      });
      if (bracketed.length === 0) return;
      event.preventDefault();
      setOttavaHidden(bracketed, range.fromColumn, true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedNotes, hideSelected, range, rangeHand, ottavas, setOttavaHidden]);

  // Escape drops whatever is picked, which is what it does everywhere else.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      closeFrames();
      closeNotes();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeFrames, closeNotes]);

  /**
   * Command-Z takes the last edit back, Shift-Command-Z puts it back.
   *
   * Control-Z on Windows, and Control-Y as well, because that is the other redo half the world
   * has. The browser has its own undo for text, so this stands down while the focus is in a field:
   * pressing Command-Z in the **Words** box takes back what you typed, which is what it should do.
   *
   * `preventDefault` matters here. Without it the browser runs its own undo on top of this one, on
   * whatever field it last saw.
   */
  const { undo, redo } = edits;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey) return;
      const pressed = event.key.toLowerCase();
      const wants =
        pressed === "z" ? (event.shiftKey ? "redo" : "undo") : pressed === "y" ? "redo" : null;
      if (!wants) return;
      const on = event.target as Element | null;
      if (on?.closest?.("input, textarea, select, [contenteditable='true']")) return;
      event.preventDefault();
      void (wants === "undo" ? undo() : redo());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo]);

  const save = useCallback(async () => {
    if (!audioUuid || !selected) return;
    setSaving(true);
    setSavedNote(null);
    setSaveProblem(null);
    const body: SavedRhythm = {
      hand,
      frameMs,
      keySignature,
      keyChanges: keyChanges.map((change) => ({
        fromColumn: change.fromColumn,
        keySignature: change.keySignature,
      })),
      clefChanges: clefChanges.map((change) => ({
        hand: change.hand,
        fromColumn: change.fromColumn,
        clef: change.clef,
      })),
      anchorFigure: figure,
      anchorMs: selected.medianMs,
      speedChanges: stretches.map((stretch) => ({
        startFrame: stretch.startFrame,
        anchorMs: stretch.anchorMs,
      })),
      overrides: Object.entries(live.overrides).map(([key, name]) => {
        const [side, frame] = key.split(":");
        // The row is not part of the key: an override belongs to a chord, not to one notehead, so
        // every note struck together takes it. Row 0 stands for "the group at this column".
        return {
          hand: side ?? "right",
          row: 0,
          startFrame: Number(frame),
          figure: name,
        };
      }),
      beamBreaks: [...live.beamBreaks].map((key) => {
        const [side, frame] = key.split(":");
        return { hand: side ?? "right", startFrame: Number(frame) };
      }),
      beamJoins: [...live.beamJoins].map((key) => {
        const [side, frame] = key.split(":");
        return { hand: side ?? "right", startFrame: Number(frame) };
      }),
      ottavas: live.ottavas.map((span) => ({
        kind: span.kind,
        hand: span.hand,
        fromColumn: span.fromColumn,
        toColumn: span.toColumn,
        // Whether the reader took the bracket off the page. The notes are written an octave from
        // where they sound either way, so a reading that lost this would come back with a wall of
        // dashed lines the reader had already decided against.
        hidden: span.hidden ?? false,
      })),
      spacings: spacings.map((stretch) => ({
        fromColumn: stretch.fromColumn,
        toColumn: stretch.toColumn,
        scale: stretch.scale,
      })),
      evenSpacings: live.evenSpacings.map((run) => ({
        hand: run.hand,
        fromColumn: run.fromColumn,
        toColumn: run.toColumn,
        scale: run.scale,
      })),
      dropDecorative,
      hiddenNotes: [...hiddenNotes].map((ref) => {
        const [frame, row] = ref.split(":");
        return { startFrame: Number(frame), row: Number(row) };
      }),
      fingers: Object.entries(live.fingers).map(([noteKey, finger]) => ({
        hand: handOf(noteKey),
        startFrame: frameOf(noteKey),
        row: rowOf(noteKey),
        finger,
      })),
      trills: [...trills],
      lyrics: [...lyrics],
      cueRanges: [...cueRanges],
      graceNotes: [...graceNotes],
      annotationScale,
      lineSpacing,
      noteSpacing,
      staffGaps: staffGaps.map((one) => ({ fromColumn: one.fromColumn, gap: one.gap })),
    };
    let kept = false;
    try {
      const stored = await timeScoreApi.saveRhythm(audioUuid, body);
      // From here on the reading is on disk. What follows writes to the recording, and a failure
      // there must not be reported as "your reading was lost", because it was not.
      kept = true;
      // A note taken off the page is a note the transcriber invented, so keeping
      // the reading also takes it out of the piano matrix the piece is drawn
      // from. Until this call it was an overlay: the sheet stopped drawing it,
      // but the roll and the falling view still showed it and the recording still
      // had it. The drawing does not change here — the figures were already named
      // with these notes excluded — but everything else now agrees with the page.
      //
      // They stay in the saved reading as well. A reading from before this existed
      // still lists notes that are still in the recording, and dropping the field
      // would silently un-hide them.
      if (body.hiddenNotes && body.hiddenNotes.length > 0) {
        await timeScoreApi.setRemoved(audioUuid, frameMs, body.hiddenNotes, true);
      }
      setSaved(stored);
      setSavedNote("Saved with the piece. It will be here next time.");
      setFlash("saved");
    } catch (caught) {
      const why = readable(caught, "Could not save this rhythm.");
      setSavedNote(
        kept
          ? `The reading was saved. Taking the hidden notes off the recording failed: ${why}`
          : why,
      );
      setSaveProblem(
        kept
          ? `Saved, but the notes you took off the page are still in the recording. ${why}`
          : `Not saved. ${why}`,
      );
      setFlash(null);
    } finally {
      setSaving(false);
    }
  }, [
    audioUuid,
    selected,
    hand,
    frameMs,
    figure,
    keySignature,
    keyChanges,
    clefChanges,
    stretches,
    live,
    hiddenNotes,
    trills,
    lyrics,
    cueRanges,
    graceNotes,
    annotationScale,
    lineSpacing,
    noteSpacing,
    staffGaps,
    dropDecorative,
    spacings,
  ]);

  /**
   * The page edits, in the shape the sheet request takes, and a signature for them.
   *
   * They travel with the request because the printed length of a note is the gap to the next onset
   * **in the same hand**: send a note across and its old neighbour runs on to a later onset, its new
   * neighbour is cut short, and the note itself takes its length from where it landed. Applying the
   * move only here would leave all three named wrong — on Mr Blue, twenty-five sampled single-note
   * moves each renamed at least one other note. Hiding a note does the same to whatever preceded it,
   * which is the point of hiding one the transcriber invented.
   */
  const pageEdits = useMemo(
    () => ({
      hiddenNotes: [...hiddenNotes].map((ref) => {
        const [frame, row] = ref.split(":");
        return { startFrame: Number(frame), row: Number(row) };
      }),
      // On the request for the same reason: the held note a trill prints as takes its length from
      // the gap to the next onset after the run, which is measured where the figures are named.
      trills: [...trills],
      // On the request because an ornament is found on the printed figures and taking it off
      // renames the note before it, which only the side that names figures can do.
      dropDecorative,
    }),
    [hiddenNotes, trills, dropDecorative],
  );
  const editSignature = useMemo(() => JSON.stringify(pageEdits), [pageEdits]);
  /** The edits the sheet on screen was built from, so it is only asked for again when they move. */
  const sheetBuiltFor = useRef<string | null>(null);

  // What the bar has just done, said on the button that did it, then gone. Long enough to read
  // while looking somewhere else on the page, short enough not to be mistaken for the resting state.
  useEffect(() => {
    if (!flash) return;
    const timer = window.setTimeout(() => setFlash(null), 2600);
    return () => window.clearTimeout(timer);
  }, [flash]);

  // An armed wipe that nobody confirms disarms itself, so a bar left alone is never one press away
  // from throwing the reading out.
  useEffect(() => {
    if (!armed) return;
    const timer = window.setTimeout(() => setArmed(false), 5000);
    return () => window.clearTimeout(timer);
  }, [armed]);

  /**
   * Ask for the sheet again.
   *
   * The speed changes can be passed in rather than read off the state, for the one caller that has
   * just replaced them: React has not re-rendered yet when it calls, so the closure here still
   * holds the changes it threw away and would draw the sheet it was asked to undo.
   */
  const apply = useCallback(
    async (withStretches?: Stretch[]) => {
      const drawn = withStretches ?? stretches;
      if (!audioUuid || !selected) return;
      setBusy(true);
      try {
        const [nextPreview, nextScore] = await Promise.all([
          timeScoreApi.ladderPreview(audioUuid, {
            anchorFigure: figure,
            anchorMs: selected.medianMs,
            hand,
            frameMs,
          }),
          timeScoreApi.score(audioUuid, {
            anchorFigure: figure,
            anchorMs: selected.medianMs,
            frameMs,
            boundaries: drawn.map((stretch) => stretch.startFrame),
            boundaryMs: [
              selected.medianMs,
              ...drawn.map((stretch) => stretch.anchorMs),
            ],
            ...pageEdits,
          }),
        ]);
        sheetBuiltFor.current = editSignature;
        setView((current) =>
          current.key === key
            ? {
                ...current,
                preview: nextPreview,
                score: nextScore,
                error: null,
              }
            : current,
        );
      } catch (caught) {
        const message = readable(caught, "Could not build the sheet.");
        setView((current) =>
          current.key === key ? { ...current, error: message } : current,
        );
      } finally {
        setBusy(false);
      }
    },
    [
      audioUuid,
      selected,
      figure,
      hand,
      frameMs,
      key,
      stretches,
      pageEdits,
      editSignature,
    ],
  );

  /**
   * The latest `apply`, reachable from a closure that was made several edits ago.
   *
   * A step that carries a backend call has to draw the sheet again after it has taken that call
   * back, and the closure holding it was made when the edit happened. The `apply` it captured then
   * still holds the ladder and the speed changes of that moment, so calling it would redraw the
   * piece as it was rather than as it is.
   */
  const applyRef = useRef(apply);
  useEffect(() => {
    applyRef.current = apply;
  }, [apply]);

  /**
   * Throw away every decision made about this piece, on screen and on disk.
   *
   * Everything cleared here is something a person chose and nothing the recording knows: the key
   * and where it changes, where the piece changes speed, the notes renamed by hand, the beams cut,
   * the octave brackets, the notes taken off the page and every fingering. What is left is the piece as the recording alone describes it, still drawn from the
   * gap that was named — starting over on the reading is a different thing and is done above.
   *
   * The saved reading goes with it. Clearing only the screen would look identical and be undone by
   * the next visit, which is the worst kind of button: one that appears to work.
   *
   * The notes taken off the page need the same care for a different reason. Saving now takes them
   * out of the piano matrix, so clearing the *list* of them would leave the notes themselves gone
   * with nothing left on screen that remembers them — the same failure one layer down. They are put
   * back on the recording here, before the list is dropped.
   *
   * The brackets need saying twice. They are seeded from what the register suggests the first time
   * a piece is drawn, so clearing them without also recording that somebody has now decided would
   * put every one of them straight back on the next redraw (D38).
   *
   * **Command-Z does not reach this.** It is the one control that also deletes the file and puts
   * notes back on the recording, and an undo that restored the screen would say the file had come
   * back too, which it has not. So it starts the history again rather than adding a step to it, and
   * the button says as much. It is already armed behind two presses for the same reason.
   */
  const wipe = useCallback(async () => {
    if (!audioUuid) return;
    // Read before anything is cleared: this is the only record of which notes to
    // put back, and the state below is about to drop it.
    const takenOff = [...hiddenNotes].map((ref) => {
      const [frame, row] = ref.split(":");
      return { startFrame: Number(frame), row: Number(row) };
    });
    setClearing(true);
    setArmed(false);
    setSavedNote(null);
    // Every decision at once, back to the piece as the recording alone describes it. Somebody has
    // now decided about brackets, so the proposal does not come straight back on the next redraw.
    ottavasDecided.current = true;
    resetEdits(NO_EDITS);
    setTrillSuggestions(null);
    setLyricDraft(null);
    setSelectedNotes([]);
    setPassageDraft(null);
    setFingerDraft(null);
    setMoveRefused(null);
    setRange(null);
    setClearedAt((at) => at + 1);
    try {
      if (takenOff.length > 0) {
        await timeScoreApi.setRemoved(audioUuid, frameMs, takenOff, false);
      }
      await timeScoreApi.forgetRhythm(audioUuid);
      setSaved(null);
      setFlash("removed");
    } catch (caught) {
      // The screen is already clear, so this is only about what a reload would bring back.
      setSavedNote(readable(caught, "Could not forget the saved reading."));
    } finally {
      setClearing(false);
    }
    // Drawn again with no speed changes, and passed them explicitly: the state above has not
    // reached this closure yet.
    await apply([]);
  }, [audioUuid, apply, frameMs, hiddenNotes, resetEdits]);

  /**
   * Say which hand plays the picked notes, on the recording.
   *
   * Not a page edit. The printed length of a note is the gap to the next onset **in the same hand**,
   * so a note that changes hands renames its old neighbour, its new neighbour and itself — measured
   * on this piece, twenty-five sampled single-note moves each renamed at least one other note. A
   * bracket or a beam over it may stop making sense too. Everything on the page is derived from the
   * split, so the correction goes upstream of all of it: written onto the note event, the matrix
   * built with it, and the sheet asked for again. Nothing about it is kept beside the drawing.
   *
   * The fingerings follow, because they are about the noteheads and the noteheads have moved. A
   * figure or a beam break that is left naming nothing is dropped by `live`.
   */
  const moveSelected = useCallback(
    async (to: PrintedHand) => {
      if (!audioUuid || selectedNotes.length === 0) return;
      const picked = [...selectedNotes];
      // The hand each note is drawn on now, read before anything moves. This is the whole of what
      // taking the move back needs: the route that writes a hand takes one per note, so writing
      // these back is the exact opposite of writing the new one.
      const wasPlayedBy = picked.map((noteKey) => ({
        startFrame: frameOf(noteKey),
        row: rowOf(noteKey),
        hand: handOf(noteKey),
      }));
      const nowPlayedBy = picked.map((noteKey) => ({
        startFrame: frameOf(noteKey),
        row: rowOf(noteKey),
        hand: to,
      }));
      setMoveRefused(null);
      setMovingHand(true);
      closeNotes();
      try {
        const result = await timeScoreApi.setHands(audioUuid, {
          frameMs,
          notes: nowPlayedBy,
        });
        // Named before the fingerings and the figures are moved, so the step is called what the
        // reader did rather than what it happened to touch first, and so it carries the two calls
        // that take the move off the recording and put it back.
        stageEdit("Hand", {
          undo: async () => {
            await timeScoreApi.setHands(audioUuid, {
              frameMs,
              notes: wasPlayedBy,
            });
            await applyRef.current();
          },
          redo: async () => {
            await timeScoreApi.setHands(audioUuid, {
              frameMs,
              notes: nowPlayedBy,
            });
            await applyRef.current();
          },
        });
        if (result.unmatched > 0) {
          setMoveRefused(
            `${result.unmatched} note${result.unmatched === 1 ? "" : "s"} could not be placed: ` +
              "nothing recorded matches that key at that moment.",
          );
        }
        setFingers((current) => {
          const next = { ...current };
          for (const noteKey of picked) {
            const finger = next[noteKey];
            if (finger === undefined) continue;
            delete next[noteKey];
            next[`${to}:${frameOf(noteKey)}:${rowOf(noteKey)}`] = finger;
          }
          return next;
        });
        // A figure and a beam break belong to a whole chord, so they travel only when the whole
        // chord does. Half a chord moving leaves them where they are and `live` decides: they still
        // name the notes that stayed, or they name nothing and go.
        const whole = new Set(selectedChords.whole);
        const movedKey = (groupKey: string): string =>
          `${to}:${groupKey.split(":")[1]}`;
        if (whole.size > 0) {
          setOverrides((current) => {
            const next = { ...current };
            for (const groupKey of whole) {
              const figure = next[groupKey];
              if (figure === undefined) continue;
              delete next[groupKey];
              next[movedKey(groupKey)] = figure;
            }
            return next;
          });
          setBeamBreaks((current) => {
            const next = new Set(current);
            for (const groupKey of whole) {
              if (!next.delete(groupKey)) continue;
              next.add(movedKey(groupKey));
            }
            return next;
          });
        }
        await apply();
      } catch (caught) {
        setMoveRefused(
          readable(caught, "Could not change the hand of those notes."),
        );
      } finally {
        setMovingHand(false);
      }
    },
    [
      audioUuid,
      frameMs,
      selectedNotes,
      selectedChords,
      closeNotes,
      apply,
      stageEdit,
      setBeamBreaks,
      setFingers,
      setOverrides,
    ],
  );
  /**
   * How many columns a note added by hand is held for.
   *
   * The same as whatever that hand is already holding at that moment, which is the answer a reader
   * expects: adding a note to a chord makes it part of that chord, and a chord is written as one
   * figure. Where the hand is holding several lengths at once — a held bass under a moving inner
   * voice — the longest wins, because the note is far more likely to be joining the chord than
   * cutting across it. Where it is holding nothing, the named gap is used: it is the one length on
   * this page anybody has actually chosen.
   *
   * It is only a starting point in any case. The note can be drawn as anything from the figure
   * pills the moment it is on the page.
   */
  const lengthForAddedNote = useCallback(
    (side: PrintedHand, frame: number): number => {
      const held = (score?.notes ?? []).filter(
        (note) =>
          note.hand === side &&
          note.startFrame <= frame &&
          note.startFrame + Math.max(1, note.printedFrames) > frame,
      );
      if (held.length > 0) {
        return Math.max(1, Math.max(...held.map((note) => note.printedFrames)));
      }
      return Math.max(1, Math.round((selected?.medianMs ?? frameMs) / frameMs));
    },
    [score, selected, frameMs],
  );

  /**
   * Put a note into the recording from the keyboard panel.
   *
   * Not a page edit, and for exactly the reason a hand change is not one: the printed length of a
   * note is the gap to the next onset **in the same hand**, so a note appearing out of nowhere
   * renames its neighbour. Drawing it beside the score would also leave the roll, the falling view
   * and playback all disagreeing with the page. So it goes onto the recorded notes, the matrix is
   * built with it, and the sheet is asked for again.
   *
   * Taking it back marks it removed rather than deleting it, which is what every other way off this
   * page does and is exact: the note is gone from the matrix, the gaps and the sheet.
   */
  const addNoteAt = useCallback(
    async (row: number) => {
      if (!audioUuid || playheadFrame === null) return;
      const frame = playheadFrame;
      const side = addHand;
      setAddingNote(true);
      try {
        const result = await timeScoreApi.addNotes(audioUuid, {
          frameMs,
          notes: [
            {
              startFrame: frame,
              row,
              hand: side,
              lengthFrames: lengthForAddedNote(side, frame),
            },
          ],
        });
        if (result.added === 0) {
          setMoveRefused(
            "That key is already struck in that column, so nothing was added. One key cannot be " +
              "played twice in the same frame.",
          );
          return;
        }
        stageEdit("Note added", {
          undo: async () => {
            await timeScoreApi.setRemoved(
              audioUuid,
              frameMs,
              [{ startFrame: frame, row }],
              true,
            );
            await applyRef.current();
          },
          redo: async () => {
            await timeScoreApi.setRemoved(
              audioUuid,
              frameMs,
              [{ startFrame: frame, row }],
              false,
            );
            await applyRef.current();
          },
        });
        await apply();
      } catch (caught) {
        setMoveRefused(readable(caught, "Could not add that note."));
      } finally {
        setAddingNote(false);
      }
    },
    [audioUuid, playheadFrame, addHand, frameMs, lengthForAddedNote, stageEdit, apply],
  );

  /**
   * A key on the panel was clicked: take that note off the page, or put a new one there.
   *
   * One gesture, two meanings, and which one it is is never ambiguous — a key that is already lit
   * is a note the reader can see, and clicking it means that one. A key that is dark holds nothing
   * at this moment, so clicking it can only mean "there should be a note here".
   */
  const pressKeyboardKey = useCallback(
    (row: number) => {
      const sounding = soundingNow.find((note) => note.row === row);
      if (!sounding) {
        void addNoteAt(row);
        return;
      }
      const ref: NoteRef = `${sounding.onsetFrame}:${row}`;
      setHiddenNotes((current) => new Set([...current, ref]));
      setFingers((current) => {
        const next = { ...current };
        delete next[`${sounding.hand}:${sounding.onsetFrame}:${row}`];
        return next;
      });
    },
    [soundingNow, addNoteAt, setHiddenNotes, setFingers],
  );

  /**
   * Draw the sheet the piece was last saved as, without asking for it again.
   *
   * Everything on this page except the reading is worked out from the recording on every visit, so
   * coming back used to mean pressing **Write the sheet** to see what you already decided. The
   * reading is on disk; the page can act on it. Once per piece, and only while nothing has been
   * drawn yet, so it never fights a reader who has already pressed the button.
   */
  const restored = useRef<string | null>(null);
  useEffect(() => {
    if (!audioUuid || !saved || !selected || score || busy) return;
    if (restored.current === key) return;
    restored.current = key;
    void apply();
  }, [audioUuid, saved, selected, score, busy, key, apply]);

  /**
   * Ask for the sheet again when a note has changed hands or left the page.
   *
   * Only the figures are wrong until it comes back: the notes are already in the right place, drawn
   * from the same edits folded into a copy of the matrix in the browser. So this is deliberately
   * unhurried — a short wait first, so dragging a band over forty-eight notes and sending them
   * across is one request rather than forty-eight, and no spinner, because nothing on screen is
   * waiting on it.
   */
  useEffect(() => {
    if (!audioUuid || !selected || !score) return;
    if (sheetBuiltFor.current === editSignature) return;
    const waiting = window.setTimeout(() => void apply(), 400);
    return () => window.clearTimeout(waiting);
  }, [editSignature, audioUuid, selected, score, apply]);

  if (!audioUuid) {
    return (
      <PageContainer
        title="Rhythm"
        subtitle="Read how the piece was played, name one gap, and the sheet follows."
        wide
      >
        <Alert severity="info">
          Load and transcribe an audio on the <strong>Upload / Input</strong>{" "}
          tab first. The rhythm is read from the notes that transcription
          records.
        </Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="Rhythm"
      subtitle="Every bar below is a gap that keeps repeating between one note and the next. Click the one you recognise, say what it is, and the sheet is written from it. Choosing a different one renames the notes and moves nothing."
      wide
    >
      {error ? (
        <Alert severity={untranscribed ? "warning" : "error"} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {/*
        Composing (Epic 13). Open by itself on a piece that has nothing in it yet, because on such a
        piece it is the only thing there is to do; folded away on a piece that already has music,
        because adding to one is the rarer intent and the plot below is what a reader came for.
      */}
      <SectionCard
        title="Add a passage"
        description={
          pieceIsEmpty
            ? "This piece is empty. Play its first passage and put it in."
            : "Play a new passage and put it at the end, or open the piece at a moment and put it there."
        }
      >
        {composeOpen ? (
          <Stack spacing={1.5}>
            <Alert severity="warning" variant="outlined">
              A passage put into the piece is written onto the recording, and
              every mark after it moves along with the notes.{" "}
              <strong>Command-Z cannot take it back</strong>, and placing one
              forgets every edit you could have taken back until now.
            </Alert>
            <ComposePassagePanel
              audioUuid={audioUuid}
              frameMs={frameMs}
              durationSeconds={pieceSeconds}
              atColumn={range?.fromColumn}
              anchorFigure={figure}
              anchorMs={selected?.medianMs}
              speedChanges={stretches.map((stretch) => ({
                startFrame: stretch.startFrame,
                anchorMs: stretch.anchorMs,
              }))}
              clickIntervalMs={selected?.medianMs}
                onPlaced={() => setComposed((token) => token + 1)}
            />
          </Stack>
        ) : (
          <Button variant="outlined" size="small" onClick={() => setComposeChoice(key)}>
            Play a passage
          </Button>
        )}
      </SectionCard>

      <SectionCard
        title="How this piece was played"
        description="Measured from the recording itself, one hand at a time, before anything was rounded."
      >
        <Stack spacing={2}>
          <Stack
            direction="row"
            spacing={2}
            sx={{ alignItems: "center", flexWrap: "wrap" }}
          >
            <TextField
              label="Hand"
              select
              size="small"
              value={hand}
              onChange={(event) => setHand(event.target.value as HandChoice)}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="right">Right hand</MenuItem>
              <MenuItem value="left">Left hand</MenuItem>
              <MenuItem value="both">Both hands</MenuItem>
            </TextField>
            {peaks ? (
              <Typography variant="body2" color="text.secondary">
                {peaks.gapCount} gaps between {peaks.attackCount} notes, over{" "}
                {peaks.endSeconds.toFixed(1)} seconds.
              </Typography>
            ) : error ? null : (
              <CircularProgress size={18} />
            )}
          </Stack>

          {peaks?.warning ? (
            <Alert severity="info" sx={{ mb: 1 }}>
              {peaks.warning}
            </Alert>
          ) : null}

          {peaks ? (
            <PeakPlot
              peaks={peaks.peaks}
              labelled={preview?.labelled}
              selectedMs={selected?.centreMs ?? null}
              onSelect={(peak) =>
                setView((current) => ({ ...current, selected: peak }))
              }
            />
          ) : null}
        </Stack>
      </SectionCard>

      <SectionCard
        title="Name it"
        description="One name fixes every other figure, because they are all proportions of each other."
      >
        <Stack
          direction="row"
          spacing={2}
          sx={{ alignItems: "center", flexWrap: "wrap" }}
        >
          <Typography variant="body1">
            The{" "}
            <strong>{selected ? Math.round(selected.centreMs) : "—"} ms</strong>{" "}
            gap is one
          </Typography>
          <TextField
            select
            size="small"
            value={figure}
            onChange={(event) => setFigure(event.target.value as FigureName)}
            sx={{ minWidth: 240 }}
            disabled={!selected}
          >
            {NAMEABLE_FIGURES.map((name) => (
              <MenuItem key={name} value={name}>
                {FIGURE_LABELS[name]}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="contained"
            onClick={() => void apply()}
            disabled={!selected || busy}
            startIcon={busy ? <CircularProgress size={16} /> : undefined}
          >
            Write the sheet
          </Button>
          {/*
            The way back, beside the way forward.

            Every edit on this sheet is one press of Command-Z away, and these two are the same
            thing for a reader who does not know that. Each says what it is about — *Undo: Octave
            bracket* — because a button that only says "Undo" asks a reader to remember what they
            last did, and on a page with sixteen kinds of edit they often do not.
          */}
          <ButtonGroup size="small" variant="outlined">
            <Tooltip
              title={
                edits.canUndo
                  ? `Undo: ${edits.undoLabel} (⌘Z)`
                  : "Nothing to take back yet"
              }
            >
              <span>
                <Button
                  onClick={() => void edits.undo()}
                  disabled={!edits.canUndo || edits.busy}
                  startIcon={
                    edits.busy ? <CircularProgress size={14} /> : <UndoIcon />
                  }
                  aria-label="Undo the last edit"
                >
                  Undo
                </Button>
              </span>
            </Tooltip>
            <Tooltip
              title={
                edits.canRedo
                  ? `Redo: ${edits.redoLabel} (⇧⌘Z)`
                  : "Nothing to put back"
              }
            >
              <span>
                <Button
                  onClick={() => void edits.redo()}
                  disabled={!edits.canRedo || edits.busy}
                  startIcon={<RedoIcon />}
                  aria-label="Redo the last edit taken back"
                >
                  Redo
                </Button>
              </span>
            </Tooltip>
          </ButtonGroup>
          {preview ? (
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {preview.headerLabel}
            </Typography>
          ) : null}
        </Stack>

        {edits.failure ? (
          <Alert severity="warning" sx={{ mt: 2 }} onClose={edits.clearFailure}>
            {readable(
              edits.failure,
              "That edit could not be taken back. Nothing on the page has changed.",
            )}
          </Alert>
        ) : null}

        {/*
          A figure shift. The same playing, written in longer or shorter figures: `negra = 337`
          becomes `blanca = 337`, and every note is renamed with it. Nothing moves, because a column
          is wall clock and the name of a note has no say in where it sits (D-18).

          It is the answer to a page of semicorcheas that should read as corcheas. The names were
          never wrong in any measurable way, they are just harder to read than they need to be, and
          this is one button rather than a re-transcription.
        */}
        {score ? (
          <Stack
            direction="row"
            spacing={1.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, mt: 2 }}
          >
            <Typography variant="body2">
              Too many short notes, or too few?
            </Typography>
            <Button
              size="small"
              variant="outlined"
              disabled={busy || shifted(figure, 1) === null}
              onClick={() => {
                const next = shifted(figure, 1);
                if (next) setFigure(next);
              }}
            >
              Write it one step longer
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={busy || shifted(figure, -1) === null}
              onClick={() => {
                const next = shifted(figure, -1);
                if (next) setFigure(next);
              }}
            >
              Write it one step shorter
            </Button>
            <Typography variant="caption" color="text.secondary">
              Renames every note. Nothing moves, and the recording is untouched.
              Press <strong>Write the sheet</strong> to see it.
            </Typography>
          </Stack>
        ) : null}
      </SectionCard>

      {score ? (
        <SectionCard
          title="Does the piece change speed?"
          description="Drag across the numbers above the staves to mark where it changes, then say what a gap is worth after that point. Everything before keeps the name it had."
        >
          <Stack spacing={1.5}>
            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              {range ? (
                <>
                  <Typography variant="body2">
                    From column <strong>{range.fromColumn}</strong>, a gap is
                  </Typography>
                  <TextField
                    size="small"
                    type="number"
                    value={newAnchorMs}
                    onChange={(event) =>
                      setNewAnchorMs(Number(event.target.value))
                    }
                    sx={{ width: 120 }}
                    slotProps={{ htmlInput: { min: 20, step: 5 } }}
                  />
                  <Typography variant="body2">ms</Typography>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setStretches((current) =>
                        [
                          ...current.filter(
                            (one) => one.startFrame !== range.fromColumn,
                          ),
                          {
                            startFrame: range.fromColumn,
                            anchorMs: newAnchorMs,
                          },
                        ].sort((a, b) => a.startFrame - b.startFrame),
                      );
                      setRange(null);
                    }}
                  >
                    Add the change
                  </Button>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Nothing selected. Drag over the column numbers above the
                  staves to choose where a change starts.
                </Typography>
              )}
            </Stack>

            {stretches.length ? (
              <Stack
                direction="row"
                spacing={1}
                sx={{ flexWrap: "wrap", rowGap: 1 }}
              >
                {score.passages.map((passage, index) => (
                  <Typography
                    key={passage.id}
                    variant="caption"
                    color="text.secondary"
                  >
                    <strong>
                      {index === 0
                        ? "From the start"
                        : `From column ${passage.startFrame}`}
                    </strong>
                    : {passage.headerLabel}
                  </Typography>
                ))}
                <Button size="small" onClick={() => setStretches([])}>
                  Remove all changes
                </Button>
              </Stack>
            ) : null}

            <Typography variant="caption" color="text.secondary">
              After adding or removing a change, press{" "}
              <strong>Write the sheet</strong> again.
            </Typography>
          </Stack>
        </SectionCard>
      ) : null}

      <SectionCard
        title="The sheet"
        description={
          score
            ? `${score.notes.length} notes, ${score.envelope.frameMs} ms per column.`
            : "Name a gap above and it appears here."
        }
      >
        {score ? (
          <Stack spacing={1.5}>
            <ScorePlayer
              audioUuid={audioUuid}
              scoreSeconds={
                (score.envelope.frameCount * score.envelope.frameMs) / 1000
              }
              onTime={setPlayheadSeconds}
              controlsRef={player}
              onScrollToCursor={scrollToCursor}
              onPlaying={setPlaying}
            />
            {/*
              The two decisions that are made here and paid for pages further down.

              Everything below this point is one long sheet, and both of these buttons used to sit
              at the end of it: keeping what you just did meant scrolling past every stave to find
              **Save**, and then scrolling back to where you were reading. The bar follows instead.
              It is draggable because it necessarily sits over the notes, and it can be put away
              because sometimes the notes underneath are the ones being read.
            */}
            {/*
              A refused save, where the reader is.

              It stays until it is closed rather than fading: this is the one message on the page
              that a reader must not miss, and a save is pressed and then looked away from. The
              backend's own words, so a bound it refused names the field it refused.
            */}
            <Snackbar
              open={saveProblem !== null}
              anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
              onClose={() => setSaveProblem(null)}
              sx={{ zIndex: 1250 }}
            >
              <Alert
                severity="error"
                variant="filled"
                onClose={() => setSaveProblem(null)}
                sx={{ maxWidth: 560 }}
              >
                {saveProblem}
              </Alert>
            </Snackbar>
            <FloatingBar open label="sheet buttons">
              <Tooltip
                title={playing ? "Pause the recording" : "Play the recording"}
              >
                <IconButton
                  size="small"
                  color="primary"
                  aria-label={playing ? "Pause" : "Play"}
                  onClick={() => {
                    setArmed(false);
                    player.current?.toggle();
                  }}
                >
                  {playing ? <PauseIcon /> : <PlayArrowIcon />}
                </IconButton>
              </Tooltip>
              <Divider orientation="vertical" flexItem />
              {/*
                A greyed Save used to say nothing about why. It is disabled until a pile of gaps is
                named, because the name is half of what a reading *is* — and a reader looking at a
                drawn sheet has no way of guessing that the plot above it is what the button is
                waiting for. A failed save is the other half: it turns red and says so, because the
                only Save there is lives up here on the bar.
              */}
              <Tooltip
                title={
                  !selected
                    ? "Name a pile of gaps on the plot above first: that is what a reading is saved as"
                    : saveProblem
                      ? saveProblem
                      : "Keep this reading with the piece"
                }
              >
                <span>
                  <Button
                    size="small"
                    variant="contained"
                    color={
                      flash === "saved"
                        ? "success"
                        : saveProblem
                          ? "error"
                          : "primary"
                    }
                    disabled={!selected || saving || clearing}
                    // Pressing anything else on the bar is an answer to "sure?", and the answer is no.
                    onClick={() => {
                      setArmed(false);
                      void save();
                    }}
                    startIcon={
                      saving ? <CircularProgress size={14} /> : <SaveIcon />
                    }
                  >
                    {flash === "saved"
                      ? "Saved"
                      : saveProblem
                        ? "Save failed"
                        : "Save"}
                  </Button>
                </span>
              </Tooltip>
              <Tooltip title="Throws away every decision about this piece, on screen and on disk, and puts back the notes taken off the recording. Command-Z cannot take it back.">
              <Button
                size="small"
                color={flash === "removed" ? "success" : "error"}
                variant={armed ? "contained" : "outlined"}
                disabled={saving || clearing}
                onClick={() => {
                  if (armed) void wipe();
                  else setArmed(true);
                }}
                startIcon={
                  clearing ? (
                    <CircularProgress size={14} />
                  ) : (
                    <DeleteSweepIcon />
                  )
                }
              >
                {flash === "removed"
                  ? "Removed"
                  : armed
                    ? "Sure? Remove all"
                    : "Remove all"}
              </Button>
              </Tooltip>
              <Divider orientation="vertical" flexItem />
              {/*
                The way off the screen. A window is whatever width it happens to be; paper is 210
                millimetres, so the music has to be laid out again before it can be printed, and
                the panel is where that is looked at before it is committed to a file.
              */}
              <Tooltip title="Lay the sheet out on paper and download it">
                <span>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={!sheetRenderer}
                    onClick={() => {
                      setArmed(false);
                      setPdfOpen(true);
                    }}
                    startIcon={<PictureAsPdfIcon />}
                  >
                    PDF
                  </Button>
                </span>
              </Tooltip>
            </FloatingBar>
            {/*
              The key signature belongs beside the sheet rather than beside the plot, because it is
              read off the sheet: you change it and look at how many sharps and flats disappear.
            */}
            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <TextField
                select
                size="small"
                label="Key signature"
                value={keySignature}
                onChange={(event) =>
                  setKeySignature(event.target.value as KeySignatureName)
                }
                sx={{ minWidth: 200 }}
                helperText="Written on both clefs. It changes spelling only: no note moves."
              >
                {KEY_SIGNATURES.map((name) => (
                  <MenuItem key={name} value={name}>
                    {KEY_LABELS[name]}
                  </MenuItem>
                ))}
              </TextField>
              {/*
                How far apart the lines of the piece are drawn.

                A line here is one pair of pentagrams under a curly bracket, and a long piece wraps
                onto many of them. One fixed gap cannot be right for every piece: most sheets are
                mostly white space at it, and on a sheet with high notes a low note of the left hand
                and a high note of the next line's right hand reach towards each other through it
                until the two runs of ledger lines meet. So the reader sets it, and it is saved with
                the piece — it belongs to this piece the same way the mark size does.

                Beside the key signature because that is where a reader is already standing when
                they look at how the page reads, and because both change the page and neither moves
                a note or touches the recording.
              */}
              <Box sx={{ minWidth: 190 }}>
                <Typography variant="caption" color="text.secondary">
                  Space between lines — {Math.round(lineSpacing)} px
                </Typography>
                <Slider
                  size="small"
                  min={MIN_LINE_SPACING}
                  max={MAX_LINE_SPACING}
                  step={4}
                  marks={[{ value: DEFAULT_LINE_SPACING }]}
                  value={lineSpacing}
                  onChange={(_, value) => setLineSpacing(value as number)}
                  valueLabelDisplay="auto"
                  aria-label="Space between the staves of one line and the next"
                />
                <Typography variant="caption" color="text.secondary">
                  The white between one pair of staves and the next. At nought
                  they sit directly under each other.
                </Typography>
              </Box>
              {/*
                How far apart the notes stand, which is the same question one axis over.

                Each column is as wide as what is drawn in it, so a page of even corcheas comes out
                as tight as the noteheads allow — right for reading a texture, and tighter than a
                player wants when the next thing to happen is a blanca. This opens every note up by
                the same amount and leaves the silences alone: a column where nothing starts is
                already exactly as wide as the time it holds, and widening it would say time had
                passed that did not. A stretch that needs more than the page does is still the
                Spacing pill's job.
              */}
              <Box sx={{ minWidth: 190 }}>
                <Typography variant="caption" color="text.secondary">
                  Space between notes — {Math.round(noteSpacing)} px
                </Typography>
                <Slider
                  size="small"
                  min={MIN_NOTE_SPACING}
                  max={MAX_NOTE_SPACING}
                  step={2}
                  marks={[{ value: DEFAULT_NOTE_SPACING }]}
                  value={noteSpacing}
                  onChange={(_, value) => setNoteSpacing(value as number)}
                  valueLabelDisplay="auto"
                  aria-label="Extra space between one note and the next"
                />
                <Typography variant="caption" color="text.secondary">
                  Added to every note, and to no silence. Nothing is renamed and
                  the recording is untouched.
                </Typography>
              </Box>
              {keyHint ? (
                <Button
                  size="small"
                  onClick={() => setKeySignature(keyHint.best)}
                >
                  Try {KEY_LABELS[keyHint.best]}
                  {keyHint.saved > 0
                    ? ` (${keyHint.saved} fewer accidentals)`
                    : ""}
                </Button>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No other signature would print fewer accidentals than this
                  one.
                </Typography>
              )}
              <Chip
                size="small"
                label={`Group high notes under 8va${
                  ottavaHint.length ? ` (${ottavaHint.length})` : ""
                }`}
                title="One bracket over every run of three or more chords written three ledger lines or more outside its staff, in either hand. Replaces the brackets on the page; the Octave pill of a stretch edits them."
                variant="outlined"
                disabled={!score || ottavaHint.length === 0}
                onClick={() => {
                  ottavasDecided.current = true;
                  setOttavas(ottavaHint);
                }}
              />
              <Chip
                size="small"
                label="Show frame numbers"
                title="The column numbers over the guides — f0, f100. They are how a mark on this page is addressed; the dashed lines and the stretches you can select stay either way."
                color={frameLabelsOn ? "secondary" : "default"}
                variant={frameLabelsOn ? "filled" : "outlined"}
                onClick={() => setFrameLabelsOn((current) => !current)}
              />
              <Chip
                size="small"
                label={
                  sheetZoom === MIN_ZOOM
                    ? "Zoom: Command and scroll"
                    : `Zoom ${Math.round(sheetZoom * 100)}% — back to normal`
                }
                title={`Hold Command (Control on Windows) and scroll over the sheet to draw it larger, up to ${
                  MAX_ZOOM * 100
                }%. It magnifies the page and changes nothing about the music: no column is measured again and the lines wrap exactly where they did.`}
                color={sheetZoom === MIN_ZOOM ? "default" : "secondary"}
                variant={sheetZoom === MIN_ZOOM ? "outlined" : "filled"}
                onClick={() => setSheetZoom(MIN_ZOOM)}
              />
              <Chip
                size="small"
                label="Remove decorative notes"
                title="A sixteenth or shorter right before an eighth or longer is an ornament. Off the page, and the note before it runs on; nothing is written in its place."
                color={dropDecorative ? "secondary" : "default"}
                variant={dropDecorative ? "filled" : "outlined"}
                onClick={() => setDropDecorative((current) => !current)}
              />
              {dropDecorative && score?.decorativeDropped ? (
                <Typography variant="caption" color="text.secondary">
                  {score.decorativeDropped} left off
                </Typography>
              ) : null}
              <Chip
                size="small"
                label={pianoOpen ? "Hide piano" : "Show piano"}
                title="A keyboard with the keys sounding under the playhead coloured in."
                color={pianoOpen ? "secondary" : "default"}
                variant={pianoOpen ? "filled" : "outlined"}
                onClick={() => setPianoOpen((current) => !current)}
              />
            </Stack>
            {/*
              Capture, so the press is recorded before the sheet's own handlers run and open a
              toolbox from it.
            */}
            <Box
              onPointerDownCapture={(event) => {
                pressedAt.current = pressedBox(event);
              }}
            >
              <TimeScoreView
                score={score}
                overrides={live.overrides}
                beamBreaks={live.beamBreaks}
                beamJoins={live.beamJoins}
                keySignature={keySignature}
                keyChanges={keyChanges}
                clefChanges={clefChanges}
                ottavas={live.ottavas}
                onKeySuggestion={setKeyHint}
                onOttavaSuggestion={setOttavaHint}
                showFrameLabels={frameLabelsOn}
                spacings={spacings}
                evenSpacings={live.evenSpacings}
                lineSpacing={lineSpacing}
                noteSpacing={noteSpacing}
                staffGaps={staffGaps}
                onStaffGapsChange={setStaffGaps}
                onSelectNotes={pickNotes}
                onSelectRange={pickRange}
                onSelectMarkedRange={pickMarkedRange}
                onOttavaResize={stretchOttava}
                renderOverrides={renderOverrides}
                fingers={live.fingers}
                trills={trills}
                lyrics={lyrics}
                onLyricLayoutChange={placeLyric}
                zoom={sheetZoom}
                onZoomChange={setSheetZoom}
                cueRanges={cueRanges}
                graceNotes={graceNotes}
                annotationScale={annotationScale}
                onMovesRefused={sayRefused}
                onRendererChange={setSheetRenderer}
                // The hand travels with the stretch so the highlight covers the staff the pills
                // are about, and only that one.
                selectedRange={
                  range && rangeHand !== "both" ? { ...range, hand: rangeHand } : range
                }
                clearSelectionsAt={clearedAt}
                playheadSeconds={playheadSeconds}
                followPlayhead={playing}
                onScrub={scrub}
                scrollCursorAt={scrollCursorAt}
              />
            </Box>
            {moveRefused ? (
              <Alert severity="warning" onClose={() => setMoveRefused(null)}>
                {moveRefused}
              </Alert>
            ) : null}
            {/*
              Everything above is a decision, and until now every one of them went when the tab did.
              The columns, the figures and the beams are all worked out again from the recording on
              each visit, so they cost nothing to lose; which pile is the beat, where the piece
              changes speed, which note you renamed and where you broke a beam are not in the
              recording at all, and re-deciding them is the actual work.
            */}
            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <Button
                variant="outlined"
                onClick={() => void save()}
                disabled={!selected || saving}
                startIcon={saving ? <CircularProgress size={16} /> : undefined}
              >
                Save this rhythm with the piece
              </Button>
              {savedNote ? (
                <Typography variant="body2" color="text.secondary">
                  {savedNote}
                </Typography>
              ) : saved ? (
                <Typography variant="body2" color="text.secondary">
                  Last saved as {FIGURE_LABELS[saved.anchorFigure]} ={" "}
                  {saved.anchorMs.toFixed(0)} ms
                  {saved.keySignature
                    ? `, in ${KEY_LABELS[saved.keySignature]}`
                    : ""}
                  .
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Nothing saved yet, so this reading goes when you leave the
                  tab.
                </Typography>
              )}
            </Stack>

            {/*
              What the page is no longer showing, and the way back. A note taken off the page cannot
              be clicked to bring it back, so the only honest place for the undo is here, where it is
              visible whether or not anything is selected.
            */}
            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              {hiddenNotes.size === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Click a notehead to open the note toolbox. Hold Command
                  (Control on Windows) and click more to build a set: a finger
                  number, a beam break, a move to the other staff or a deletion
                  then applies to the whole set at once.
                </Typography>
              ) : (
                <>
                  <Typography variant="body2" color="text.secondary">
                    {hiddenNotes.size} note{hiddenNotes.size === 1 ? "" : "s"}{" "}
                    off the page. The recording still has every one of them.
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => setHiddenNotes(new Set())}
                  >
                    Bring them all back
                  </Button>
                </>
              )}
            </Stack>

            {/*
              The marks that are not attached to one notehead: the shakes, the words and the size
              they are all drawn at. Kept here rather than in the frames toolbox because none of
              them needs a stretch selected to be worth seeing — finding the trills in a piece is
              the first thing a reader does, before they have marked anything.
            */}
            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <Button
                size="small"
                variant="outlined"
                onClick={() => void findTrills()}
                disabled={findingTrills}
                startIcon={
                  findingTrills ? <CircularProgress size={14} /> : undefined
                }
              >
                Find trills
              </Button>
              {trillSuggestions === null ? (
                <Typography variant="body2" color="text.secondary">
                  Two notes taking turns at least three times over are written as
                  one held note with <em>tr</em> over it.
                </Typography>
              ) : unmarkedTrills.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {trillSuggestions.length === 0
                    ? "Nothing in this piece looks like a shake."
                    : "Every shake found is already written as a trill."}
                </Typography>
              ) : (
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ alignItems: "center", flexWrap: "wrap" }}
                >
                  {unmarkedTrills.map((one) => (
                    <Chip
                      key={`${one.hand}:${one.startFrame}`}
                      size="small"
                      variant="outlined"
                      label={`${one.noteName}–${one.otherNoteName} · ${one.noteCount} notes · ${formatSeconds(one.startSeconds)}`}
                      title={`${one.hand === "left" ? "Left" : "Right"} hand, about ${one.medianGapMs.toFixed(0)} ms apart. Click to write it as one held note with tr over it.`}
                      onClick={() =>
                        setTrills((current) => [
                          ...current,
                          {
                            hand: one.hand,
                            startFrame: one.startFrame,
                            endFrame: one.endFrame,
                            row: one.row,
                          },
                        ])
                      }
                    />
                  ))}
                </Stack>
              )}
              {trills.length > 0 ? (
                <Button size="small" onClick={() => setTrills([])}>
                  Print all the alternations again
                </Button>
              ) : null}
            </Stack>

            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <Typography variant="body2" color="text.secondary">
                Mark size
              </Typography>
              <ButtonGroup size="small" variant="outlined">
                <Button
                  onClick={() =>
                    setAnnotationScale((value) =>
                      Math.max(0.5, Math.round((value - 0.1) * 10) / 10),
                    )
                  }
                  disabled={annotationScale <= 0.5}
                >
                  Smaller
                </Button>
                <Button
                  onClick={() =>
                    setAnnotationScale((value) =>
                      Math.min(2, Math.round((value + 0.1) * 10) / 10),
                    )
                  }
                  disabled={annotationScale >= 2}
                >
                  Larger
                </Button>
              </ButtonGroup>
              <Typography variant="body2" color="text.secondary">
                {Math.round(annotationScale * 100)}% — the fingering, the words
                and the <em>tr</em> marks. No note moves.
              </Typography>
              {lyrics.length > 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {lyrics.length} line{lyrics.length === 1 ? "" : "s"} of words
                  under the staff.
                </Typography>
              ) : null}
            </Stack>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nothing written yet.
          </Typography>
        )}
      </SectionCard>

      {/*
        Two toolboxes, because a column and a notehead answer different questions. A column belongs
        to the piece and both hands are in it; a notehead is one note in one hand. Keeping them
        apart is what stopped `8vb` being offered to the right hand only pointing upward.
      */}
      <ToolboxDialog
        open={pianoOpen}
        title="Piano"
        subtitle={
          playheadFrame === null
            ? "The keys sounding under the playhead"
            : `f${playheadFrame} \u00b7 click a lit key to take it off the page, a dark one to add it`
        }
        initialPosition={{ x: 24, y: Math.max(80, window.innerHeight - 300) }}
        onClose={() => setPianoOpen(false)}
        width={760}
      >
        <Stack spacing={1}>
          {/*
            The keyboard as a way of editing a chord, which is the shortest route there is to
            "this chord has a note in it that was never played" and to "this chord is missing one".
            On the staves those are a notehead among five others; here they are a key that is lit
            when it should be dark, or dark when it should be lit.
          */}
          <Stack
            direction="row"
            spacing={1.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
          >
            <Typography variant="caption" color="text.secondary">
              Add note
            </Typography>
            <ButtonGroup size="small">
              {(["right", "left"] as const).map((side) => (
                <Button
                  key={side}
                  variant={addHand === side ? "contained" : "outlined"}
                  onClick={() => setAddHand(side)}
                  sx={{ minWidth: 34 }}
                  title={`A key you click that is not already sounding is added to the ${side} hand`}
                >
                  {side === "right" ? "R" : "L"}
                </Button>
              ))}
            </ButtonGroup>
            {/*
              The legend, and the only explanation the panel needs.

              Four colours and four names. It replaces a paragraph under the keyboard that said the
              same thing in prose — and a reader looking at a lit key wants to look *across* at a
              swatch of the same colour, not down at a sentence about it. `onset` and `sustain` are
              the words the roll and the matrix already use for struck and still-sounding, so this
              is one vocabulary rather than a second one invented for this panel.
            */}
            {KEY_LEGEND.map((entry) => (
              <Stack
                key={entry.label}
                direction="row"
                spacing={0.5}
                sx={{ alignItems: "center" }}
              >
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: 0.5,
                    bgcolor: entry.colour,
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {entry.label}
                </Typography>
              </Stack>
            ))}
            {addingNote ? <CircularProgress size={14} /> : null}
          </Stack>
          <Piano
            width="100%"
            height="auto"
            keyColours={soundingColours}
            onKeyPress={pressKeyboardKey}
            keyTitle={(row) => {
              const sounding = soundingNow.find((note) => note.row === row);
              if (!sounding) {
                return `${noteNameAt(row)} \u2014 click to add it to the ${
                  addHand === "left" ? "left" : "right"
                } hand here.`;
              }
              const hand = sounding.hand === "left" ? "left" : "right";
              // A held key is about a notehead somewhere else on the page, and the tooltip is the
              // only place that can say so before the reader presses it.
              return sounding.onsetFrame === playheadFrame
                ? `${noteNameAt(row)} \u2014 ${hand} hand, struck here. Click to take it off the page.`
                : `${noteNameAt(row)} \u2014 ${hand} hand, still sounding from f${sounding.onsetFrame}. Click to take that note off the page.`;
            }}
            ariaLabel="Keys sounding under the playhead"
          />
        </Stack>
      </ToolboxDialog>

      {/*
        The decoration keyboard.

        The same drawing doing the opposite job: instead of reporting what is sounding, it asks what
        should sound just before the picked note. The note it leans on is coloured so the answer can
        be read off as an interval without anybody naming one.
      */}
      <ToolboxDialog
        open={decorationFor !== null && onlyNote !== null}
        title="Piano Edit"
        subtitle={
          onlyNote
            ? `The decoration played just before ${noteNameAt(rowOf(onlyNote))}`
            : undefined
        }
        initialPosition={{ x: 24, y: Math.max(80, window.innerHeight - 300) }}
        onClose={() => setDecorationFor(null)}
        width={760}
      >
        {onlyNote ? (
          <Stack spacing={1}>
            <Stack
              direction="row"
              spacing={1.5}
              sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
            >
              <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: 0.5,
                    bgcolor: PRINCIPAL_COLOUR,
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {noteNameAt(rowOf(onlyNote))} — the note it leans on
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: 0.5,
                    bgcolor: DECORATION_COLOUR,
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {graceHere
                    ? `${noteNameAt(graceHere.row)} — the decoration`
                    : "Click a key to choose the decoration"}
                </Typography>
              </Stack>
              {graceHere ? (
                <Button size="small" color="error" onClick={clearGrace}>
                  Take it off
                </Button>
              ) : null}
            </Stack>
            <Piano
              width="100%"
              height="auto"
              keyColours={{
                [rowOf(onlyNote)]: PRINCIPAL_COLOUR,
                ...(graceHere ? { [graceHere.row]: DECORATION_COLOUR } : {}),
              }}
              onKeyPress={(row) => putGrace(onlyNote, row)}
              keyTitle={(row) => `${noteNameAt(row)} as the decoration`}
              ariaLabel="Choose the decoration note"
            />
          </Stack>
        ) : null}
      </ToolboxDialog>
      <ToolboxDialog
        open={framesToolbox && range !== null}
        title="Frames"
        subtitle={
          range
            ? `f${range.fromColumn} – f${range.toColumn - 1} · ${formatSeconds(
                (range.fromColumn * frameMs) / 1000,
              )} → ${formatSeconds((range.toColumn * frameMs) / 1000)}`
            : undefined
        }
        initialPosition={framesAt ?? { x: 24, y: 140 }}
        onClose={closeFrames}
        headerAction={
          /*
            The same music, picked the other way round. It is disabled rather than hidden when the
            stretch holds no notes on the staves in scope, so the tooltip can say which of the two
            it is — an empty stretch, or a hand that is silent through it.
          */
          <Tooltip
            title={
              notesUnderRange.length === 0
                ? "No notes begin inside this stretch on the staff it is about"
                : `Pick the ${notesUnderRange.length} note${
                    notesUnderRange.length === 1 ? "" : "s"
                  } that begin inside this stretch and open the note toolbox on them`
            }
          >
            <span>
              <Button
                size="small"
                color="inherit"
                disabled={notesUnderRange.length === 0 || !sheetRenderer}
                startIcon={<SwapHorizIcon fontSize="small" />}
                onClick={selectNotesUnderRange}
                sx={{ textTransform: "none", whiteSpace: "nowrap" }}
              >
                Select notes
              </Button>
            </span>
          </Tooltip>
        }
      >
        <Stack spacing={1.5}>
          {/*
            Which staff this stretch is about, asked first because it changes what everything under
            it means and what the highlight on the page covers.

            A clef and an octave bracket belong to one hand; a key signature is drawn on both clefs
            and a line of words is sung over the piece, so those two read this and ignore it. The
            labels are one letter because the reader is aiming at them, not reading them.
          */}
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: "center" }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 42 }}>
              Applies to
            </Typography>
            <ButtonGroup size="small">
              {([
                ["both", "Both"],
                ["right", "R"],
                ["left", "L"],
              ] as const).map(([side, label]) => (
                <Button
                  key={side}
                  variant={rangeHand === side ? "contained" : "outlined"}
                  onClick={() => setRangeHand(side)}
                  sx={{ minWidth: 34, px: 1 }}
                  title={
                    side === "both"
                      ? "The whole system: the highlight covers both staves"
                      : `Only the ${side} hand: the highlight covers that staff alone`
                  }
                >
                  {label}
                </Button>
              ))}
            </ButtonGroup>
          </Stack>

          {/*
            One pill per thing this stretch can carry, and only that thing's controls below it.

            Laid out as a grid rather than a row: there are six of them, and a row of six on a panel
            this wide put half of them off the edge. A pill wears the accent colour when this stretch
            already carries that setting, so what has been edited here is visible before anything is
            opened.
          */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 0.75,
            }}
          >
            {FRAME_TABS.map((tab) => (
              <Chip
                key={tab.id}
                size="small"
                label={tab.label}
                onClick={() => setFrameTab(tab.id)}
                // Two signals that must not collide: colour says *this stretch already carries
                // one*, fill says *this is the pill you are looking at*. Folding them into one
                // would hide the first behind the second the moment a marked pill was opened.
                color={editedHere[tab.id] ? "secondary" : "default"}
                variant={frameTab === tab.id ? "filled" : "outlined"}
                sx={{ fontWeight: frameTab === tab.id ? 600 : 400 }}
              />
            ))}
          </Box>

          {frameTab === "key" ? (
            <Stack spacing={1.5}>
              <TextField
                select
                size="small"
                label="Key"
                value={passageKey}
                onChange={(event) =>
                  setPassageDraft({
                    forRange: rangeKey,
                    value: event.target.value as KeySignatureName,
                  })
                }
                fullWidth
              >
                {KEY_SIGNATURES.map((name) => (
                  <MenuItem key={name} value={name}>
                    {KEY_LABELS[name]}
                  </MenuItem>
                ))}
              </TextField>
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  size="small"
                  disabled={!range || !score}
                  onClick={() => {
                    if (!range || !score) return;
                    setKeyChanges(
                      applyKeySignatureRange(
                        keyChanges,
                        {
                          fromFrame: range.fromColumn,
                          toFrame: range.toColumn,
                          keySignature: passageKey as KeySignature,
                        },
                        keySignature as KeySignature,
                        score.envelope.frameCount,
                      ),
                    );
                  }}
                >
                  Apply
                </Button>
                <Button
                  size="small"
                  color="error"
                  disabled={!range || !score || !editedHere.key}
                  startIcon={<DeleteOutlineIcon />}
                  onClick={() => {
                    if (!range || !score) return;
                    setKeyChanges(
                      clearKeySignatureRange(
                        keyChanges,
                        {
                          fromFrame: range.fromColumn,
                          toFrame: range.toColumn,
                        },
                        keySignature as KeySignature,
                        score.envelope.frameCount,
                      ),
                    );
                  }}
                >
                  Remove
                </Button>
              </Stack>
            </Stack>
          ) : null}

          {frameTab === "octave" ? (
            <Stack spacing={1}>
              {/*
                One row per staff in scope. Narrowing to a hand above leaves one row here, which is
                the panel's answer to being asked the same question twice: the reader has already
                said which hand, and a second L/R inside the pill was the thing they were saying it
                to.
              */}
              {handsInScope.map((side) => {
                const active = range
                  ? ottavaAtFrame(ottavas, side, range.fromColumn)
                  : undefined;
                return (
                  <Stack
                    key={side}
                    direction="row"
                    spacing={0.75}
                    sx={{ alignItems: "center" }}
                  >
                    {handsInScope.length > 1 ? (
                      <Typography variant="body2" sx={{ minWidth: 34 }}>
                        {side === "left" ? "L" : "R"}
                      </Typography>
                    ) : null}
                    {OTTAVA_CHOICES.map((choice) => (
                      <Chip
                        key={choice.kind}
                        size="small"
                        label={choice.label}
                        title={choice.hint}
                        disabled={!range || !score}
                        color={
                          active?.kind === choice.kind ? "secondary" : "default"
                        }
                        variant={
                          active?.kind === choice.kind ? "filled" : "outlined"
                        }
                        onClick={() => {
                          if (!range || !score) return;
                          // Pressing the bracket already on clears it, so one chip is both the way
                          // in and the way out and there is no separate "none".
                          setOttavas(
                            active?.kind === choice.kind
                              ? clearOttavaRange(ottavas, side, {
                                  fromColumn: range.fromColumn,
                                  toColumn: range.toColumn,
                                })
                              : applyOttava(
                                  ottavas,
                                  {
                                    kind: choice.kind,
                                    hand: side,
                                    fromColumn: range.fromColumn,
                                    toColumn: range.toColumn,
                                  },
                                  score.envelope.frameCount,
                                ),
                          );
                        }}
                      />
                    ))}
                    {/*
                      Take the bracket off the page without taking the reading off the piece.

                      A player who already knows a passage is played an octave up does not need a
                      dashed line over every bar of it saying so, and above the right hand is the
                      most crowded strip on the page. The notes stay written exactly where the
                      bracket puts them — that is the whole difference between this and the trash
                      beside it — so a hidden bracket is still there, and its corner marks are how
                      a reader gets back to it. Delete does the same thing from the keyboard.
                    */}
                    <IconButton
                      size="small"
                      title={
                        active?.hidden
                          ? "Draw the bracket again. The notes do not move either way."
                          : "Hide the bracket and keep the reading — or press Delete. The notes stay written where it puts them."
                      }
                      disabled={!range || !active}
                      onClick={() => {
                        if (!range || !active) return;
                        setOttavaHidden([side], range.fromColumn, !active.hidden);
                      }}
                    >
                      {active?.hidden ? (
                        <VisibilityOffIcon fontSize="small" />
                      ) : (
                        <VisibilityIcon fontSize="small" />
                      )}
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      title="Remove the bracket on this hand. The notes go back to where they sound, in ledger lines if that is where they are."
                      disabled={!range || !active}
                      onClick={() => {
                        if (!range) return;
                        setOttavas(
                          clearOttavaRange(ottavas, side, {
                            fromColumn: range.fromColumn,
                            toColumn: range.toColumn,
                          }),
                        );
                      }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                );
              })}
            </Stack>
          ) : null}

          {/*
            Which clef each hand in scope prints over this stretch.

            The answer to a hand that spends a passage far outside its own staff, and a better one
            than an octave bracket where the passage is long: under a bracket the notes are written
            an octave from where they sound and the reader has to hold that in mind, while on the
            other clef they are written exactly where they sound. Nothing moves and nothing is
            renamed — a clef decides which lines the noteheads are drawn on and nothing else.
          */}
          {frameTab === "clef" ? (
            <Stack spacing={1}>
              {handsInScope.map((side) => {
                const active = range
                  ? clefAtFrame(range.fromColumn, side, clefChanges)
                  : DEFAULT_CLEF[side];
                return (
                  <Stack
                    key={side}
                    direction="row"
                    spacing={0.75}
                    sx={{ alignItems: "center" }}
                  >
                    {handsInScope.length > 1 ? (
                      <Typography variant="body2" sx={{ minWidth: 34 }}>
                        {side === "left" ? "L" : "R"}
                      </Typography>
                    ) : null}
                    {CLEF_CHOICES.map((choice) => (
                      <Chip
                        key={choice.clef}
                        size="small"
                        label={choice.label}
                        title={choice.hint}
                        disabled={!range || !score}
                        color={active === choice.clef ? "secondary" : "default"}
                        variant={active === choice.clef ? "filled" : "outlined"}
                        onClick={() => {
                          if (!range || !score) return;
                          // Asking for the clef the hand already reads is asking for nothing, so
                          // the stretch goes back to the hand's own rather than storing a
                          // transition that changes nothing.
                          setClefChanges(
                            choice.clef === DEFAULT_CLEF[side]
                              ? clearClefRange(
                                  clefChanges,
                                  {
                                    hand: side,
                                    fromFrame: range.fromColumn,
                                    toFrame: range.toColumn,
                                  },
                                  score.envelope.frameCount,
                                )
                              : applyClefRange(
                                  clefChanges,
                                  {
                                    hand: side,
                                    fromFrame: range.fromColumn,
                                    toFrame: range.toColumn,
                                    clef: choice.clef,
                                  },
                                  score.envelope.frameCount,
                                ),
                          );
                        }}
                      />
                    ))}
                    <IconButton
                      size="small"
                      color="error"
                      title="Back to the clef this hand normally reads"
                      disabled={!range || !score || active === DEFAULT_CLEF[side]}
                      onClick={() => {
                        if (!range || !score) return;
                        setClefChanges(
                          clearClefRange(
                            clefChanges,
                            {
                              hand: side,
                              fromFrame: range.fromColumn,
                              toFrame: range.toColumn,
                            },
                            score.envelope.frameCount,
                          ),
                        );
                      }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                );
              })}
            </Stack>
          ) : null}

          {frameTab === "spacing" && range ? (
            <Stack spacing={1}>
              <Typography variant="caption" color="text.secondary">
                How much room this stretch takes, against what the page measured
                for it. Only the columns inside it move, and the sheet redraws as
                the handle moves so the right spot can be found by looking at it.
              </Typography>
              <Slider
                size="small"
                min={25}
                max={400}
                step={5}
                marks={[{ value: 100 }]}
                value={Math.round(spacingHere * 100)}
                onChange={(_, value) => setRangeSpacing((value as number) / 100)}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) => `${value}%`}
                disabled={!score}
                aria-label="How much room this stretch takes"
              />
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <Typography variant="body2" sx={{ minWidth: 54 }}>
                  {Math.round(spacingHere * 100)}%
                </Typography>
                <IconButton
                  size="small"
                  color="error"
                  title="Back to the page's own spacing"
                  disabled={spacingHere === 1}
                  onClick={clearSpacingRange}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Stack>
              {/*
                Said out loud because the pills above promise otherwise. A column is one slice of
                wall clock and both staves share it — that is the whole of what makes the two hands
                line up (D-22) — so there is no such thing as widening a column for one hand. The
                clef and the octave bracket honour the hand pills; this one cannot.
              */}
              <Typography variant="caption" color="text.secondary">
                Both staves, whichever hand is chosen above: a column is one slice
                of the clock and the two hands share it.
              </Typography>
            </Stack>
          ) : null}

          {frameTab === "lyrics" && range ? (
            <Stack spacing={1.5}>
              <TextField
                size="small"
                label="Lyrics"
                multiline
                maxRows={3}
                value={lyricText}
                placeholder="The line sung over this stretch"
                onChange={(event) =>
                  setLyricDraft({ forRange: rangeKey, text: event.target.value })
                }
                helperText="Drawn above the right hand, over the marked stretch. Drag the block to move it, drag its right edge to fold the words into more lines. It never moves a note."
              />
              {lyricHere ? (
                <>
                  {/*
                    Per lyric and not per page, because the reason for changing it is per lyric:
                    one line is three words over eight seconds and the next a whole sentence over
                    one.
                  */}
                  <Stack spacing={0.5}>
                    <Typography variant="caption" color="text.secondary">
                      Text size — {Math.round(lyricHere.fontSize ?? LYRIC_FONT_SIZE)} px
                    </Typography>
                    <Slider
                      size="small"
                      value={lyricHere.fontSize ?? LYRIC_FONT_SIZE}
                      min={MIN_LYRIC_FONT_SIZE}
                      max={MAX_LYRIC_FONT_SIZE}
                      step={1}
                      valueLabelDisplay="auto"
                      onChange={(_event, value) =>
                        setLyrics((current) =>
                          current.map((line) =>
                            line === lyricHere
                              ? { ...line, fontSize: value as number }
                              : line,
                          ),
                        )
                      }
                    />
                  </Stack>
                  {lyricHere.offsetX !== undefined ||
                  lyricHere.offsetY !== undefined ||
                  lyricHere.width !== undefined ? (
                    <Button
                      size="small"
                      onClick={() =>
                        setLyrics((current) =>
                          // Built back up rather than picked apart, because "no answer" here is
                          // the field being absent and not a number meaning nothing.
                          current.map((line) =>
                            line === lyricHere
                              ? {
                                  fromColumn: line.fromColumn,
                                  toColumn: line.toColumn,
                                  text: line.text,
                                  ...(line.fontSize === undefined
                                    ? {}
                                    : { fontSize: line.fontSize }),
                                }
                              : line,
                          ),
                        )
                      }
                    >
                      Put the block back over its stretch
                    </Button>
                  ) : null}
                </>
              ) : null}
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  variant="contained"
                  disabled={lyricText.trim().length === 0}
                  onClick={() => {
                    const text = lyricText.trim();
                    setLyrics((current) => [
                      ...current.filter(
                        (line) =>
                          line.fromColumn >= range.toColumn ||
                          line.toColumn <= range.fromColumn,
                      ),
                      {
                        fromColumn: range.fromColumn,
                        toColumn: range.toColumn,
                        text,
                      },
                    ]);
                    setLyricDraft(null);
                  }}
                >
                  Write it here
                </Button>
                {lyricHere ? (
                  <Button
                    size="small"
                    onClick={() => {
                      setLyrics((current) =>
                        current.filter((line) => line !== lyricHere),
                      );
                      setLyricDraft(null);
                    }}
                  >
                    Take it off
                  </Button>
                ) : null}
              </Stack>
            </Stack>
          ) : null}

          {frameTab === "rerecord" && range && audioUuid ? (
            <Stack spacing={1.5}>
              <Alert severity="warning" variant="outlined">
                Playing this stretch again writes over the recording.{" "}
                <strong>Command-Z cannot take it back</strong>, and accepting it
                also forgets every edit you could have taken back until now.
              </Alert>
              <RangeRerecordPanel
                audioUuid={audioUuid}
                frameMs={frameMs}
                fromColumn={range.fromColumn}
                toColumn={range.toColumn}
                anchorFigure={figure}
                anchorMs={selected?.medianMs}
                speedChanges={stretches.map((stretch) => ({
                  startFrame: stretch.startFrame,
                  anchorMs: stretch.anchorMs,
                }))}
                clickIntervalMs={((): number => {
                  let ms = selected?.medianMs ?? 480;
                  for (const stretch of stretches) {
                    if (stretch.startFrame <= range.fromColumn) ms = stretch.anchorMs;
                  }
                  return ms;
                })()}
                onRangeChange={(start, end) => {
                  const fromColumn = Math.max(0, Math.round((start * 1000) / frameMs));
                  const toColumn = Math.max(
                    fromColumn + 1,
                    Math.round((end * 1000) / frameMs),
                  );
                  setRange({ fromColumn, toColumn });
                }}
                onAccepted={() => {
                  // A re-record writes over a window of the recording, and may splice the audio
                  // itself. Nothing brings that back, so the marks inside the window are dropped and
                  // the history is started again here rather than left holding steps that point into
                  // a passage that is not there any more. The panel says so before Accept is pressed.
                  const from = range.fromColumn;
                  const to = range.toColumn;
                  const inside = (frame: number) => frame >= from && frame < to;
                  setOverrides((current) => {
                    const next = { ...current };
                    for (const key of Object.keys(next)) {
                      if (inside(Number(key.split(":")[1]))) delete next[key];
                    }
                    return next;
                  });
                  setBeamBreaks(
                    (current) =>
                      new Set(
                        [...current].filter(
                          (key) => !inside(Number(key.split(":")[1])),
                        ),
                      ),
                  );
                  setHiddenNotes(
                    (current) =>
                      new Set(
                        [...current].filter(
                          (ref) => !inside(Number(ref.split(":")[0])),
                        ),
                      ),
                  );
                  setFingers((current) => {
                    const next = { ...current };
                    for (const key of Object.keys(next)) {
                      if (inside(Number(key.split(":")[1]))) delete next[key];
                    }
                    return next;
                  });
                  setOttavas((current) =>
                    current.filter(
                      (span) =>
                        span.fromColumn < from || span.fromColumn >= to,
                    ),
                  );
                  resetEdits((current) => current);
                  void apply();
                }}
              />
            </Stack>
          ) : null}

          {/*
            No **Save with the piece** here any more.

            Every panel on this page edits the same one reading, and a save button inside one of
            them read as saving that panel's own part of it. The bar that follows the reader down
            the sheet carries the only Save there is, beside Remove all, which is where a reader
            looking for either of them goes.
          */}
        </Stack>
      </ToolboxDialog>

      <ToolboxDialog
        open={notesToolbox && selectedNotes.length > 0}
        title={
          // Which note it is, rather than the word "Note" — a reader who has just clicked a
          // notehead already knows it is a note, and what they cannot read off a stack of ledger
          // lines at a glance is which one.
          selectedNotes.length === 1
            ? (pickedNoteName ?? "Note")
            : `${selectedNotes.length} notes`
        }
        subtitle={
          // The columns, each said once. A chord is three notes at one moment, and printing that
          // moment three times reads as three moments.
          selectedNotes.length > 0
            ? (() => {
                const columns = [...new Set(selectedNotes.map(frameOf))].sort(
                  (a, z) => a - z,
                );
                return (
                  columns
                    .slice(0, 4)
                    .map((column) => `f${column}`)
                    .join(", ") + (columns.length > 4 ? ", \u2026" : "")
                );
              })()
            : undefined
        }
        initialPosition={notesAt ?? { x: 420, y: 140 }}
        onClose={closeNotes}
        headerAction={
          /*
            From the notes to the columns they stand in, so the stretch is exactly the music that is
            picked rather than an aim at the ruler.
          */
          <Tooltip title="Mark the stretch from the first picked note to the last, and open the frames toolbox on it">
            <span>
              <Button
                size="small"
                color="inherit"
                startIcon={<SwapHorizIcon fontSize="small" />}
                onClick={selectRangeOfNotes}
                sx={{ textTransform: "none", whiteSpace: "nowrap" }}
              >
                Select frames
              </Button>
            </span>
          </Tooltip>
        }
      >
        <Stack spacing={1.25}>
          {/*
            Everything a reader can decide about a note, as controls rather than as prose.

            This panel used to explain each of its sections in a paragraph — what an acciaccatura
            was, how fingering numbers were read against a chord, what happened to a note taken off
            the page. All of it was true and none of it was being read: a reader who has already
            picked three noteheads wants a row of things to press. What is left is the shapes, the
            numbers and two letters, with the sentences moved into the tooltips where they are
            reachable and out of the way.
          */}

          {/*
            The figures, as the shapes they print as.

            A pill is filled when every picked chord is drawn as that figure already; pressing one
            names all of them, which is how a passage written as a mix of corcheas, semicorcheas and
            tresillos becomes one figure. Nothing moves — not a column, not a timing (D-18) — and a
            tresillo renamed here loses its 3, because it is now written as what it says it is.
          */}
          <Stack
            direction="row"
            spacing={0.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
          >
            {PLAIN_FIGURES.map((name) => {
              const chosen = selectedPrintedFigure === name;
              return (
                <IconButton
                  key={name}
                  size="small"
                  onClick={() => drawSelectionAs(name)}
                  title={`Draw ${
                    selectedGroups.length === 1
                      ? "this chord"
                      : `all ${selectedGroups.length} chords`
                  } as a ${FIGURE_SHORT[name].toLowerCase()}`}
                  aria-label={`Draw as a ${FIGURE_SHORT[name]}`}
                  aria-pressed={chosen}
                  sx={{
                    borderRadius: 1,
                    border: 1,
                    borderColor: chosen ? "secondary.main" : "divider",
                    bgcolor: chosen ? "secondary.main" : "transparent",
                    color: chosen ? "secondary.contrastText" : "text.primary",
                    px: 0.5,
                    py: 0.25,
                  }}
                >
                  <FigureGlyph figure={name} size={24} />
                </IconButton>
              );
            })}
            <Tooltip title="Back to whatever the score called them">
              <span>
                <IconButton
                  size="small"
                  disabled={namedGroups.length === 0}
                  onClick={unnameSelection}
                  aria-label="Back to the score's own figures"
                >
                  <BackspaceIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>

          <Divider />

          {/* Which finger plays them. One number on all of them, or one each on a single chord. */}
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
              Finger
            </Typography>
            <ButtonGroup size="small">
              {FINGERS.map((finger) => (
                <Button
                  key={finger}
                  variant={
                    pickedFingers.includes(finger) ? "contained" : "outlined"
                  }
                  onClick={() => pressFinger(finger)}
                  data-finger={finger}
                  title={
                    oneChord
                      ? `Press one number for the whole chord, or ${oneChord.length} of them to give each notehead its own`
                      : "One number, on every note picked"
                  }
                >
                  {finger}
                </Button>
              ))}
            </ButtonGroup>
            <Tooltip title="Take the numbers off">
              <span>
                <IconButton
                  size="small"
                  disabled={
                    !selectedNotes.some((noteKey) => fingers[noteKey] !== undefined)
                  }
                  onClick={() => {
                    setFingerDraft({ forSelection: selectionKey, picked: [] });
                    applyFingers([], selectedNotes, oneChord);
                  }}
                  aria-label="Clear the fingering"
                >
                  <BackspaceIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>

          {/*
            Which hand plays them.

            Written onto the recording rather than onto the drawing, because the printed length of a
            note is the gap to the next onset in the same hand — so a note that changes hands renames
            its old neighbour, its new neighbour and itself. The button is two letters; the tooltip
            is where that sentence lives now.
          */}
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
              Hand
            </Typography>
            <ButtonGroup size="small">
              {(["right", "left"] as const).map((side) => {
                const on = selectedNotes.every(
                  (noteKey) => handOf(noteKey) === side,
                );
                return (
                  <Button
                    key={side}
                    variant={on ? "contained" : "outlined"}
                    disabled={movingHand || on}
                    onClick={() => void moveSelected(side)}
                    sx={{ minWidth: 34 }}
                    title={`Play with the ${side} hand \u2014 written onto the recording, so the figures around it are named again`}
                  >
                    {side === "right" ? "R" : "L"}
                  </Button>
                );
              })}
            </ButtonGroup>
            {movingHand ? <CircularProgress size={14} /> : null}
          </Stack>

          {/* How they are grouped, and how far apart they stand. Five things, so it may wrap. */}
          <Stack
            direction="row"
            spacing={0.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
              Beam
            </Typography>
            <Tooltip
              title={
                beamable
                  ? "Beam all of these as one group, whatever the page would do with them"
                  : "Pick two or more whole chords, all of them a corchea or shorter: a negra has no beam to share"
              }
            >
              <span>
                <IconButton
                  size="small"
                  color={joinedHere ? "secondary" : "default"}
                  disabled={!beamable}
                  onClick={joinBeams}
                  aria-label="Beam these notes as one group"
                >
                  <LinkIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip
              title={
                selectedChords.partial.length > 0
                  ? `A beam holds a whole chord, so it can only be cut in front of all of it. Pick the rest of the notes at ${selectedChords.partial
                      .map((key) => `f${key.split(":")[1]}`)
                      .join(", ")} as well.`
                  : brokenHere
                    ? "Join the beam again"
                    : "Cut the beam in front of these, so a new group runs on from them"
              }
            >
              <span>
                <IconButton
                  size="small"
                  color={brokenHere ? "secondary" : "default"}
                  disabled={
                    selectedChords.partial.length > 0 ||
                    selectedChords.whole.length === 0
                  }
                  onClick={toggleBeamBreak}
                  aria-label="Start a new beam here"
                >
                  <ContentCutIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
            {/*
              Set the run an equal distance apart, then open it or close it.

              A column belongs to the whole system, so a run of even corcheas in one hand is drawn
              unevenly wherever the other hand needs room at one of those moments. The page is not
              wrong when that happens — the space really is being used — but a beam of equal notes
              that is not equally spaced reads as an uneven performance, which is a worse lie than
              the width. This is the reader choosing evenness and paying for it in width, and the
              other hand moves with it.

              The plus and the minus stand down until the run is even, because until then there is
              no one distance for them to be a multiple of. And the minus stops at even rather than
              going below it: every gap is the sum of the widths its columns asked for, so closing
              one further would print one note over another. The minimums are the page's and only
              the maximum is the reader's.
            */}
            <Tooltip
              title={
                selectedRun === null
                  ? "Pick two or more notes of one hand to set them an equal distance apart"
                  : evenHere
                    ? "Back to the spacing the page measured"
                    : "Set these an equal distance apart, whatever the other hand needs at those moments"
              }
            >
              <span>
                <IconButton
                  size="small"
                  color={evenHere ? "secondary" : "default"}
                  disabled={selectedRun === null}
                  onClick={toggleEvenSpacing}
                  aria-label="Set these notes an equal distance apart"
                  aria-pressed={Boolean(evenHere)}
                >
                  <DragHandleIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip
              title={
                !evenHere
                  ? "Set them even first"
                  : evenHere.scale >= MAX_EVEN_SPACING_SCALE
                    ? "As open as this run goes"
                    : "More room between them"
              }
            >
              <span>
                <IconButton
                  size="small"
                  disabled={!evenHere || evenHere.scale >= MAX_EVEN_SPACING_SCALE}
                  onClick={() => nudgeEvenSpacing(EVEN_SPACING_STEP)}
                  aria-label="More room between these notes"
                >
                  <AddIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip
              title={
                !evenHere
                  ? "Set them even first"
                  : evenHere.scale <= MIN_EVEN_SPACING_SCALE
                    ? "As close as this run goes"
                    : "Less room between them"
              }
            >
              <span>
                <IconButton
                  size="small"
                  disabled={!evenHere || evenHere.scale <= MIN_EVEN_SPACING_SCALE}
                  onClick={() => nudgeEvenSpacing(-EVEN_SPACING_STEP)}
                  aria-label="Less room between these notes"
                >
                  <RemoveIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            {evenHere && evenHere.scale !== 1 ? (
              <Typography variant="caption" color="text.secondary">
                {Math.round(evenHere.scale * 100)}%
              </Typography>
            ) : null}
          </Stack>

          <Divider />

          {/* The three marks that hang off a note rather than off a column. */}
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.75 }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
              Marks
            </Typography>
            <Chip
              size="small"
              icon={<PianoIcon />}
              label={
                graceHere ? `Decoration ${noteNameAt(graceHere.row)}` : "Decoration"
              }
              color={graceHere ? "secondary" : "default"}
              variant={graceHere ? "filled" : "outlined"}
              disabled={onlyNote === null}
              title={
                onlyNote === null
                  ? "Pick one notehead to lean a small note on it"
                  : "A small note played just before this one. Pick its pitch on the keyboard."
              }
              onClick={() => setDecorationFor(onlyNote)}
              {...(graceHere ? { onDelete: clearGrace } : {})}
            />
            <Chip
              size="small"
              label="Small"
              color={cueHere ? "secondary" : "default"}
              variant={cueHere ? "filled" : "outlined"}
              title="Print these smaller than the rest of the page, so a florid run reads as decoration and takes less width"
              onClick={toggleCueOnSelection}
            />
            <Chip
              size="small"
              label="Trill"
              variant="outlined"
              disabled={!trillable}
              title={
                trillable
                  ? "Write these as one held note with tr and a wavy line over it. Every alternation stays in the recording and still plays."
                  : "Pick three or more onsets in one hand \u2014 the notes taking turns"
              }
              onClick={markTrillOnSelection}
            />
          </Stack>

          <Divider />

          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Tooltip title="Take them off the page — or press Delete. Command-Z brings them back, the recording keeps every one of them, and Remove all puts them back.">
              <IconButton
                size="small"
                color="error"
                onClick={hideSelected}
                aria-label={`Take ${
                  selectedNotes.length === 1
                    ? "this note"
                    : `these ${selectedNotes.length} notes`
                } off the page`}
              >
                <DeleteOutlineIcon />
              </IconButton>
            </Tooltip>
            <Typography variant="caption" color="text.secondary">
              {selectedNotes.length === 1
                ? "Hold Command and click more noteheads to build a set."
                : oneChord
                  ? `One chord of ${oneChord.length}.`
                  : `${selectedGroups.length} chords.`}
            </Typography>
          </Stack>
        </Stack>
      </ToolboxDialog>

      <ScorePdfDialog
        open={pdfOpen}
        onClose={() => setPdfOpen(false)}
        renderer={sheetRenderer}
        {...(artifact.label ? { pieceName: artifact.label } : {})}
      />
    </PageContainer>
  );
}

export default RhythmPage;
