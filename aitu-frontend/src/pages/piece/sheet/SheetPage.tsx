/**
 * The Sheet step of a project: the piano sheet, its floating bar and its toolboxes.
 *
 * The page is the sheet (plan section 11.2): the title lines, a scrub bar, the music, and a
 * floating bar with play, undo, redo, the sheet toolbox, Record, Print and Save. The figure ladder
 * is chosen by the backend when nobody has named it (the highest pile of gaps is a negra, D-09 as
 * changed by implementation 02), and the key signature with the fewest accidentals and the octave
 * brackets of high passages are applied when the sheet is first written (plan section 11.3). Each
 * default is an ordinary edit after that.
 *
 * It is step 5 (**Sheet**) of the flow page (implementation 08, Story 8.2). When the notes or the
 * hands changed after the reading was saved, it opens with a banner and waits for **Write the
 * sheet** instead of drawing the old reading by itself.
 *
 * Implementation 02, Phase 2 split the old `RhythmPage.tsx` into this folder: the edits model
 * (`sheetEdits.ts`), the note toolbox, the range toolbox, the sheet toolbox, the two keyboards and
 * the floating bar each have their own module, and this page keeps the state they share, the
 * requests and the effects.
 */

import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ConfirmDialog, EmptyState, IconAction, PillButton, Toolbox } from "../../../ui";
import type { StepState } from "../../../api";
import { noteName } from "../../../music/noteNames";
import ScorePlayer, {
  type ScorePlayerControls,
} from "../../../components/time/ScorePlayer";
import TimeScoreView, { MIN_ZOOM } from "../../../components/time/TimeScoreView";
import ScorePdfDialog from "../../../components/time/ScorePdfDialog";
import ComposePassagePanel from "../../../components/editing/ComposePassagePanel";
import CheckIcon from "@mui/icons-material/Check";
import {
  timeScoreApi,
  type DefaultReading,
  type FigureName,
  type HandChoice,
  type KeySignatureName,
  type SavedRhythm,
  type TimeScorePayload,
  type TrillSuggestion,
} from "../../../api";
import {
  clefAtFrame,
  ottavaAtFrame,
  resizeOttava,
  suggestClefRanges,
  type ClefChangeAnnotation,
  type ClefRange,
  type GridNotationRenderer,
  type KeySignature,
  type LyricPlaceChange,
  type OttavaAnnotation,
  type OttavaResizeChange,
} from "@aimpromptu/grid-notation";
import {
  figureSteps,
  shiftFigure,
  transposeKey,
  transposeKeyChanges,
  transposeRowMarks,
} from "../../../music/transpose";
import {
  frameOf,
  groupKeyOf,
  handOf,
  rowOf,
  type NoteRef,
  type PrintedHand,
} from "../../../music/renderOverrides";
import { useEditHistory } from "../../../hooks/useEditHistory";
import { useWorkingArtifact } from "../../../state/useWorkingArtifact";
import {
  BEAMABLE_FIGURES,
  DEFAULT_CLEF,
  formatSeconds,
  HAND_COLOUR,
  HELD_COLOUR,
  MARKER_TABS,
  NO_HANDS,
  notTranscribed,
  readable,
  type FrameTab,
  type RangeHand,
  type SoundingNote,
} from "./sheetConstants";
import {
  EDIT_LABELS,
  editsFromSaved,
  hiddenNotesOut,
  NO_EDITS,
  sameSheet,
  savedRhythmOf,
  type SheetEdits,
  type Stretch,
} from "./sheetEdits";
import {
  besideOnScreen,
  clearOfRange,
  firstLineBoxOf,
  pressedBox,
  screenBoxOf,
} from "./toolboxPlacement";
import { useNoteActions, type FingerDraft } from "./useNoteActions";
import { useRangeActions, type FrameRange } from "./useRangeActions";
import { NoteToolbox } from "./NoteToolbox";
import { RangeToolbox } from "./RangeToolbox";
import { DecorationToolbox, PianoToolbox } from "./PianoToolboxes";
import { SheetFloatingBar } from "./SheetFloatingBar";
import { SheetToolbox, type SheetTab } from "./SheetToolbox";
import { TransposeDialog, type PreviewSheet } from "./TransposeDialog";
import { landingOf, movePiece, piecesIn, placePiece } from "./lyricsPieces";
import { POOL_DRAG_TYPE } from "./LyricsTab";

/**
 * Everything read for one (piece, hand, resolution), kept together under the key it belongs to:
 * the figure ladder the sheet is written from, the sheet itself, and why it could not be drawn.
 */
interface View {
  key: string;
  reading: DefaultReading | null;
  score: TimeScorePayload | null;
  error: string | null;
}

function emptyView(key: string): View {
  return { key, reading: null, score: null, error: null };
}

/**
 * What the flow page tells the piano sheet when it is the Sheet tab.
 *
 * `state` and `reason` are the backend's answer for the Sheet step (`GET /pieces/{uuid}/status`).
 * `onChanged` is called after a write that can change that answer: a saved reading makes the step
 * ready, **Remove all** makes it missing.
 */
export interface SheetStep {
  audioUuid: string;
  label?: string | undefined;
  state: StepState;
  reason: string | null;
  onChanged: () => void;
  /**
   * A version of the library, opened to look at (Phase 6): the sheet draws and plays and prints;
   * nothing on it opens a toolbox, and there is no Save. It changes through **Edit**.
   */
  readOnly?: boolean;
}

/** In place of a handler on a sheet that only shows. */
const ignore = () => undefined;

/**
 * The octave brackets a hand can take where it reads its own clef.
 *
 * A passage takes a clef change or a bracket, never both (the drawing package refuses the pair):
 * a left-hand run the clef rule wrote in the treble clef is already where it sounds. A bracket
 * that starts on the hand's own clef and runs into a clef change is cut where the clef changes.
 */
function clearOfClefChanges(
  spans: readonly OttavaAnnotation[],
  clefChanges: readonly ClefChangeAnnotation[],
): OttavaAnnotation[] {
  return spans.flatMap((span) => {
    if (clefAtFrame(span.fromColumn, span.hand, clefChanges) !== DEFAULT_CLEF[span.hand]) return [];
    const next = clefChanges.find(
      (change) =>
        change.hand === span.hand &&
        change.fromColumn > span.fromColumn &&
        change.fromColumn < span.toColumn,
    );
    return [next ? { ...span, toColumn: next.fromColumn } : span];
  });
}

/** A transposition waiting in its preview dialog for **Transpose** or **Cancel**. */
type TransposePreview =
  | {
      kind: "notes";
      semitones: number;
      facts: string[];
      sheet: PreviewSheet | null;
      error: string | null;
    }
  | {
      kind: "figures";
      to: FigureName;
      anchorFigure: FigureName;
      overrides: Record<string, FigureName>;
      beamBreaks: ReadonlySet<string>;
      beamJoins: ReadonlySet<string>;
      facts: string[];
      sheet: PreviewSheet | null;
      error: string | null;
    };

export function SheetPage({ step }: { step?: SheetStep } = {}) {
  const readOnly = step?.readOnly ?? false;
  const { artifact } = useWorkingArtifact();
  const audioUuid = step ? step.audioUuid : artifact.audioUuid;
  const pieceLabel = step ? step.label : artifact.label;
  const frameMs = artifact.frameMs;
  /**
   * The notes or the hands changed after the reading was saved (plan section 8.3). The reading is
   * still loaded, but it is not drawn by itself: the reader presses **Write the sheet** and then
   * **Save**, and only that save makes the step ready again.
   */
  const stale = step?.state === "stale";

  /**
   * Which hand's gaps the figure ladder is measured from. Right until a saved reading says
   * otherwise; the backend falls back to both hands when this one has no peak.
   */
  const [hand, setHand] = useState<HandChoice>("right");
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
    anchorFigure,
    title,
    subtitle,
    artist,
    keySignature,
    keyChanges,
    clefChanges,
    ottavas,
    trills,
    lyrics,
    lyricsPool,
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
  const set = edits.set;
  const {
    ottavas: setOttavas,
    trills: setTrills,
    lyrics: setLyrics,
    fingers: setFingers,
    overrides: setOverrides,
    beamBreaks: setBeamBreaks,
    hiddenNotes: setHiddenNotes,
    staffGaps: setStaffGaps,
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
  /**
   * Whether the key signature of this sheet has been decided: by a saved reading, by the reader,
   * or by the default taken on the first write (plan section 11.3).
   */
  const keyDecided = useRef(false);
  /** Whether the clefs of this sheet have been decided: by a saved reading, or by the first write. */
  const clefsDecided = useRef(false);
  /**
   * The first write has just replaced the key, so the octave brackets that same build proposed
   * were measured in the old key. The next build proposes them again in the new one.
   */
  const keyMoving = useRef(false);
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
  /** Numbers pressed for the selection now open, so a chord can be given several at once. */
  const [fingerDraft, setFingerDraft] = useState<FingerDraft | null>(null);
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
  const [saving, setSaving] = useState(false);
  /**
   * The edits as they were last saved or loaded, by identity.
   *
   * Every edit makes a new value and undo puts the old one back, so comparing identities is
   * exactly "is the page what was saved". `null` while nothing is saved: every sheet then has
   * changes to keep, including the defaults of its first write.
   */
  const [cleanEdits, setCleanEdits] = useState<SheetEdits | null>(null);
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
  /** **Remove all** asks first: it throws away every decision about the piece, on disk too. */
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [clearing, setClearing] = useState(false);
  /** What the bar has just done, said on the button that did it, then gone. */
  const [flash, setFlash] = useState<"saved" | null>(null);
  /** The sheet toolbox, and which of its tabs is open. */
  const [sheetToolbox, setSheetToolbox] = useState(false);
  const [sheetTab, setSheetTab] = useState<SheetTab>("title");
  /** The Record toolbox: play a passage and put it into the piece. */
  const [recordOpen, setRecordOpen] = useState(false);
  /** The Trills toolbox: what **Find trills** found, each one a press away from being written. */
  const [trillsOpen, setTrillsOpen] = useState(false);
  /** A transposition in its preview dialog, the preview being written, and the write. */
  const [transposePreview, setTransposePreview] = useState<TransposePreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [transposing, setTransposing] = useState(false);
  /** The lyrics pieces picked in the Lyrics tab, by their first frame. */
  const [pickedLyrics, setPickedLyrics] = useState<readonly number[]>([]);
  /**
   * The words of the song saved with the part (**Save lyrics**, `project.json`), the lyrics field
   * as it is being edited (`null` until it is touched: it shows the saved words), and the save.
   * Not an edit of the sheet: no undo, and the sheet's own Save does not carry it.
   */
  const [songLyrics, setSongLyrics] = useState<{
    forPart: string;
    text: string | null;
    /** The pool as saved: what **Save lyrics** compares the pool on the page with. */
    pool: readonly string[];
  } | null>(null);
  const [lyricsDraft, setLyricsDraft] = useState<{ forPart: string; text: string } | null>(null);
  const [savingLyrics, setSavingLyrics] = useState(false);

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
  /**
   * Whether the saved reading of this piece has been asked for and answered (found or not). The
   * first sheet waits for it: drawing before it would write the defaults over the reader's own
   * key and brackets.
   */
  const [rhythmCheckedFor, setRhythmCheckedFor] = useState<string | null>(null);
  const rhythmChecked = rhythmCheckedFor === editsKey;
  if (editsFor !== editsKey) {
    setEditsFor(editsKey);
    resetEdits(NO_EDITS);
  }

  const { reading, score, error } = view;
  /** The length of the highest pile of gaps, which every figure is named from. */
  const anchorMs = reading?.anchorMs ?? null;

  /**
   * How long the piece is, and whether there is anything in it.
   *
   * Read from the envelope rather than from a separate request: the sheet already carries the
   * column count and the column length, and an empty piece is drawn as one empty column, so "no
   * notes" is the honest test rather than "no columns".
   */
  const pieceSeconds = score
    ? (score.envelope.frameCount * score.envelope.frameMs) / 1000
    : (reading?.endSeconds ?? 0);
  const pieceIsEmpty = reading !== null && reading.attackCount === 0;
  /** Unsaved: nothing saved yet, or the page is not what was saved, or the saved one is stale. */
  // The lyrics pool aside: it has its own save, **Save lyrics**.
  const unsaved = cleanEdits === null || !sameSheet(edits.state, cleanEdits) || stale;

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

  /**
   * The defaults of the first write (plan section 11.3): the key signature with the fewest
   * accidentals, then the octave brackets of the high passages, measured in that key.
   *
   * The sheet reports both on every build. The first report of a sheet nobody has decided about is
   * taken whole, as the baseline rather than as a step: the reader did not do it, and a Command-Z
   * on a page nobody has touched must do nothing. After that each is an ordinary edit, and the
   * same answers stay one press away in the sheet toolbox.
   */
  const takeKeyHint = useCallback(
    (hint: { best: KeySignatureName; saved: number } | null) => {
      setKeyHint(hint);
      keyMoving.current = false;
      if (keyDecided.current) return;
      keyDecided.current = true;
      if (!hint) return;
      keyMoving.current = true;
      resetEdits((current) => ({ ...current, keySignature: hint.best }));
    },
    [resetEdits],
  );
  const takeOttavaHint = useCallback(
    (spans: OttavaAnnotation[]) => {
      setOttavaHint(spans);
      if (keyMoving.current || ottavasDecided.current || spans.length === 0) return;
      ottavasDecided.current = true;
      // After the clefs of the same build, so a run the clef rule wrote in the treble clef does
      // not take a bracket as well.
      resetEdits((current) => ({
        ...current,
        ottavas: clearOfClefChanges(spans, current.clefChanges),
      }));
    },
    [resetEdits],
  );
  /**
   * The clef rule of a first write (plan section 11.7): the left hand's high runs of four figures
   * or more in the treble clef. Taken as the baseline once, measured in the key just chosen, like
   * the brackets; after that the Clef tab of the range toolbox offers it again per stretch.
   */
  const takeClefHint = useCallback(
    (changes: ClefChangeAnnotation[]) => {
      if (keyMoving.current || clefsDecided.current) return;
      clefsDecided.current = true;
      if (changes.length === 0) return;
      resetEdits((current) => ({ ...current, clefChanges: changes }));
    },
    [resetEdits],
  );

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

  /**
   * The figure ladder the sheet is written from: the highest pile of gaps of `hand`, which the
   * backend calls a negra (D-09 as changed by implementation 02). The reader's own name for it,
   * when there is one, is `anchorFigure` of the edits; only the pile comes from here.
   */
  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    timeScoreApi
      .defaultReading(audioUuid, { hand, frameMs }, controller.signal)
      .then((found) => {
        setUntranscribed(false);
        setView((current) =>
          current.key === key ? { ...current, reading: found } : current,
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
  // The reading arrives as the baseline and not as a step. It is where the reader left off rather
  // than something they have just done, and a Command-Z that emptied the page on arrival would be
  // the worst possible first impression of an undo.
  useEffect(() => {
    if (!audioUuid) return;
    // Whether anybody has decided about the key and the brackets is a fact about this piece, so a
    // different piece has not been asked yet and may take the page's own defaults.
    ottavasDecided.current = false;
    keyDecided.current = false;
    clefsDecided.current = false;
    const controller = new AbortController();
    // The saved lyrics and pool come with the reading, in one answer, so neither overwrites the
    // other's pool. The pool saved by **Save lyrics** wins; one saved by an older sheet is the
    // fallback. A failure to read the lyrics leaves them empty.
    Promise.all([
      timeScoreApi.rhythm(audioUuid, controller.signal),
      timeScoreApi.lyrics(audioUuid, controller.signal).catch(() => null),
    ])
      .then(([found, song]) => {
        const pool = song?.pool ?? found?.lyricsPool ?? [];
        if (found) {
          setHand(found.hand);
          // A saved reading decided its key. A reading that carries a list of brackets — even an
          // empty one — decided those too; one saved before brackets existed did not.
          keyDecided.current = true;
          clefsDecided.current = true;
          ottavasDecided.current = Array.isArray(found.ottavas);
          const next = { ...editsFromSaved(found), lyricsPool: pool };
          resetEdits(next);
          setCleanEdits(next);
        } else if (pool.length > 0) {
          resetEdits((current) => ({ ...current, lyricsPool: pool }));
        }
        setSongLyrics({ forPart: audioUuid, text: song?.text ?? null, pool });
        setRhythmCheckedFor(editsKey);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        // A reading that cannot be read is not worth stopping the screen for: the sheet is written
        // from the defaults instead.
        setRhythmCheckedFor(editsKey);
      });
    return () => controller.abort();
  }, [audioUuid, editsKey, resetEdits]);

  const savedLyricsText =
    songLyrics && songLyrics.forPart === audioUuid ? songLyrics.text : null;
  const savedPool = songLyrics && songLyrics.forPart === audioUuid ? songLyrics.pool : [];
  /** The pool on the page is not the one saved: **Save lyrics** is offered for it too. */
  const poolUnsaved =
    lyricsPool.length !== savedPool.length || lyricsPool.some((text, at) => text !== savedPool[at]);
  const lyricsFieldText =
    lyricsDraft && lyricsDraft.forPart === audioUuid ? lyricsDraft.text : (savedLyricsText ?? "");
  const saveSongLyrics = useCallback(
    async (text: string) => {
      if (!audioUuid) return;
      setSavingLyrics(true);
      try {
        const saved = await timeScoreApi.saveLyrics(audioUuid, text, lyricsPool);
        setSongLyrics({ forPart: audioUuid, text: saved.text, pool: saved.pool ?? [] });
        setLyricsDraft({ forPart: audioUuid, text: saved.text ?? "" });
      } catch (caught) {
        setMoveRefused(readable(caught, "Could not save the lyrics."));
      } finally {
        setSavingLyrics(false);
      }
    },
    [audioUuid, lyricsPool],
  );

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
      // In the Lyrics tab a stretch picks the lyrics pieces over it: the box a reader drags over
      // several pieces at once.
      if (lyricsModeNow.current) {
        setPickedLyrics(piecesIn(lyricsNow.current, picked));
        setClearedAt((at) => at + 1);
        return;
      }
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
   * `live`, kept as the same objects while its content is the same, for the sheet.
   *
   * The sheet is drawn again from scratch whenever one of these is a new object, and `live` gives
   * six new ones whenever anything it reads changes, even when nothing in them did. A hand move
   * did exactly that: the fingerings were handed back as an equal copy, and the whole sheet was
   * drawn once more with the old notes before the new sheet arrived (implementation 08, Phase 8).
   */
  const liveContent = useMemo(
    () =>
      JSON.stringify([
        live.ottavas,
        [...live.beamBreaks],
        [...live.beamJoins],
        live.overrides,
        live.evenSpacings,
        live.fingers,
      ]),
    [live],
  );
  // eslint-disable-next-line react-hooks/exhaustive-deps -- the same content keeps the same objects
  const drawnMarks = useMemo(() => live, [liveContent]);

  /**
   * Whether the Lyrics tab is open: then a click on a piece picks it, and a stretch marked above the
   * staves picks the pieces over it instead of opening the range toolbox.
   *
   * Held in refs as well, so the handlers the sheet keeps stay the same functions: a new handler
   * would rebuild every note of the sheet.
   */
  const lyricsMode = sheetToolbox && sheetTab === "lyrics";
  const lyricsModeNow = useRef(lyricsMode);
  const lyricsNow = useRef(lyrics);
  useEffect(() => {
    lyricsModeNow.current = lyricsMode;
    lyricsNow.current = lyrics;
  }, [lyricsMode, lyrics]);

  /** A press on the sheet but not on a lyrics piece, or Escape: every piece is plain text again. */
  const clearPickedLyrics = useCallback(() => setPickedLyrics([]), []);

  /** A lyrics piece was clicked: the Lyrics tab opens on it, picked (Command-click adds it). */
  const pickLyric = useCallback((fromColumn: number, additive: boolean) => {
    setSheetToolbox(true);
    setSheetTab("lyrics");
    setPickedLyrics((current) =>
      additive
        ? current.includes(fromColumn)
          ? current.filter((one) => one !== fromColumn)
          : [...current, fromColumn]
        : [fromColumn],
    );
  }, []);

  /**
   * A lyrics piece was dragged on the sheet and let go: it snaps to the frames under its edges.
   * Refused, with the reason, where it would cover another piece.
   */
  const placeLyric = useCallback(
    (change: LyricPlaceChange) => {
      const outcome = movePiece(lyricsNow.current, change);
      if ("refused" in outcome) {
        setMoveRefused(outcome.refused);
        return;
      }
      setLyrics(outcome.ok);
      setPickedLyrics((current) =>
        current.map((one) => (one === change.fromColumn ? change.nextFromColumn : one)),
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
      // A lyrics piece is a piece of the Lyrics tab, not a stretch of the range toolbox.
      if (marker.kind === "lyric") {
        pickLyric(marker.fromColumn, false);
        return;
      }
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
    [pickLyric],
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

  const notes = useNoteActions({
    score,
    selectedNotes,
    chords,
    state: edits.state,
    set: edits.set,
    fingerDraft,
    setFingerDraft,
    closeNotes,
  });
  const { selectedChords, onlyNote, graceHere, hideSelected } = notes;

  const rangeActions = useRangeActions({
    range,
    rangeHand,
    chords,
    state: edits.state,
    set: edits.set,
    passageDraft,
  });
  const { notesUnderRange } = rangeActions;

  /**
   * A re-record was accepted. It writes over a window of the recording, and may splice the audio
   * itself. Nothing brings that back, so the marks inside the window are dropped and the history is
   * started again here rather than left holding steps that point into a passage that is not there
   * any more. The panel says so before Accept is pressed.
   */
  const acceptRerecord = (accepted: FrameRange) => {
    const from = accepted.fromColumn;
    const to = accepted.toColumn;
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
  };

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
      if (lyricsMode && pickedLyrics.length > 0) {
        event.preventDefault();
        setLyrics((current) => current.filter((line) => !pickedLyrics.includes(line.fromColumn)));
        setPickedLyrics([]);
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
  }, [
    selectedNotes,
    hideSelected,
    range,
    rangeHand,
    ottavas,
    setOttavaHidden,
    lyricsMode,
    pickedLyrics,
    setLyrics,
  ]);

  // Escape drops whatever is picked, which is what it does everywhere else.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      closeFrames();
      closeNotes();
      // A picked lyrics piece goes back to plain text.
      setPickedLyrics([]);
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
    if (!audioUuid || anchorMs === null) return;
    setSaving(true);
    setSaveProblem(null);
    const keptEdits = edits.state;
    const body: SavedRhythm = savedRhythmOf({
      // The hand the ladder was measured from, which may be both when the asked hand had no peak.
      hand: reading?.hand ?? hand,
      frameMs,
      anchorMs,
      edits: keptEdits,
      live,
    });
    let kept = false;
    try {
      await timeScoreApi.saveRhythm(audioUuid, body);
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
      setCleanEdits(keptEdits);
      setFlash("saved");
      step?.onChanged();
    } catch (caught) {
      const why = readable(caught, "Could not save this sheet.");
      if (kept) setCleanEdits(keptEdits);
      setSaveProblem(
        kept
          ? `Saved, but the notes you took off the page are still in the recording. ${why}`
          : `Not saved. ${why}`,
      );
      setFlash(null);
    } finally {
      setSaving(false);
    }
  }, [audioUuid, anchorMs, reading, hand, frameMs, edits.state, live, step]);

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
      hiddenNotes: hiddenNotesOut(hiddenNotes),
      // On the request for the same reason: the held note a trill prints as takes its length from
      // the gap to the next onset after the run, which is measured where the figures are named.
      trills: [...trills],
      // On the request because an ornament is found on the printed figures and taking it off
      // renames the note before it, which only the side that names figures can do.
      dropDecorative,
    }),
    [hiddenNotes, trills, dropDecorative],
  );
  /**
   * Everything the sheet request is built from, as one string: the page edits above, the figure
   * ladder and the speed changes. When it moves the sheet is asked for again by itself; there is
   * no **Write the sheet** to press, except on a stale sheet.
   */
  const editSignature = useMemo(
    () => JSON.stringify({ pageEdits, anchorFigure, anchorMs, stretches }),
    [pageEdits, anchorFigure, anchorMs, stretches],
  );
  /** The edits the sheet on screen was built from, so it is only asked for again when they move. */
  const sheetBuiltFor = useRef<string | null>(null);

  // What the bar has just done, said on the button that did it, then gone. Long enough to read
  // while looking somewhere else on the page, short enough not to be mistaken for the resting state.
  useEffect(() => {
    if (!flash) return;
    const timer = window.setTimeout(() => setFlash(null), 2600);
    return () => window.clearTimeout(timer);
  }, [flash]);

  /**
   * Ask for the sheet again.
   *
   * What it is drawn from can be passed in rather than read off the state, for the one caller that
   * has just replaced it (**Remove all**): React has not re-rendered yet when it calls, so the
   * closure here still holds the edits it threw away and would draw the sheet it was asked to
   * forget.
   */
  const apply = useCallback(
    async (fresh?: {
      stretches: Stretch[];
      anchorFigure: SheetEdits["anchorFigure"];
      pageEdits: typeof pageEdits;
    }) => {
      const drawn = fresh?.stretches ?? stretches;
      const figure = fresh?.anchorFigure ?? anchorFigure;
      const marks = fresh?.pageEdits ?? pageEdits;
      if (!audioUuid || anchorMs === null) return;
      setBusy(true);
      try {
        const nextScore = await timeScoreApi.score(audioUuid, {
          anchorFigure: figure,
          anchorMs,
          frameMs,
          boundaries: drawn.map((stretch) => stretch.startFrame),
          boundaryMs: [anchorMs, ...drawn.map((stretch) => stretch.anchorMs)],
          ...marks,
        });
        sheetBuiltFor.current = fresh
          ? JSON.stringify({ pageEdits: marks, anchorFigure: figure, anchorMs, stretches: drawn })
          : editSignature;
        setView((current) =>
          current.key === key ? { ...current, score: nextScore, error: null } : current,
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
    [audioUuid, anchorMs, anchorFigure, frameMs, key, stretches, pageEdits, editSignature],
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
   * The sheet as the preview dialog draws it: everything the page draws, with the changes of the
   * transposition on top. Built from the marks that still have a note under them.
   */
  const previewSheetOf = useCallback(
    (previewScore: TimeScorePayload, changes: Partial<PreviewSheet>): PreviewSheet => ({
      score: previewScore,
      overrides: drawnMarks.overrides,
      beamBreaks: drawnMarks.beamBreaks,
      beamJoins: drawnMarks.beamJoins,
      keySignature,
      keyChanges,
      clefChanges,
      ottavas: drawnMarks.ottavas,
      fingers: drawnMarks.fingers,
      trills,
      lyrics,
      cueRanges,
      graceNotes,
      spacings,
      evenSpacings: drawnMarks.evenSpacings,
      lineSpacing,
      noteSpacing,
      staffGaps,
      annotationScale,
      renderOverrides,
      ...changes,
    }),
    [
      drawnMarks,
      keySignature,
      keyChanges,
      clefChanges,
      trills,
      lyrics,
      cueRanges,
      graceNotes,
      spacings,
      lineSpacing,
      noteSpacing,
      staffGaps,
      annotationScale,
      renderOverrides,
    ],
  );

  /** What moves with the notes when every key moves by `semitones` (plan section 11.4). */
  const notesMarksMoved = useCallback(
    (semitones: number) => ({
      keySignature: transposeKey(keySignature, semitones),
      keyChanges: transposeKeyChanges(keyChanges, semitones),
      ...transposeRowMarks({ fingers, hiddenNotes, trills, graceNotes }, semitones),
    }),
    [keySignature, keyChanges, fingers, hiddenNotes, trills, graceNotes],
  );

  /**
   * **Preview** of a notes transposition: the backend counts what would move and what would leave
   * the keyboard, and draws the sheet with the notes moved, writing nothing.
   */
  const previewNotes = useCallback(
    async (semitones: number) => {
      if (!audioUuid || anchorMs === null) return;
      const moved = notesMarksMoved(semitones);
      // The sheet says what changes. A line is added only where it changes the decision: notes the
      // keyboard cannot hold (below).
      setTransposePreview({ kind: "notes", semitones, facts: [], sheet: null, error: null });
      setPreviewing(true);
      try {
        const [counts, previewScore] = await Promise.all([
          timeScoreApi.transpose(audioUuid, { semitones, preview: true }),
          timeScoreApi.score(audioUuid, {
            anchorFigure,
            anchorMs,
            frameMs,
            boundaries: stretches.map((stretch) => stretch.startFrame),
            boundaryMs: [anchorMs, ...stretches.map((stretch) => stretch.anchorMs)],
            hiddenNotes: hiddenNotesOut(moved.hiddenNotes),
            trills: moved.trills,
            dropDecorative,
            transpose: semitones,
          }),
        ]);
        const counted = [
          ...(counts.outside > 0
            ? [
                `${counts.outside} note${counts.outside === 1 ? "" : "s"} would leave the keyboard and ${
                  counts.outside === 1 ? "is" : "are"
                } taken off the page.`,
              ]
            : []),
        ];
        setTransposePreview((current) =>
          current?.kind === "notes" && current.semitones === semitones
            ? {
                ...current,
                facts: [...current.facts, ...counted],
                sheet: previewSheetOf(previewScore, {
                  keySignature: moved.keySignature,
                  keyChanges: moved.keyChanges,
                  fingers: Object.fromEntries(
                    Object.entries(moved.fingers).filter(([key]) => {
                      const [hand, frame] = key.split(":");
                      return previewScore.notes.some(
                        (note) => note.hand === hand && note.startFrame === Number(frame),
                      );
                    }),
                  ) as typeof drawnMarks.fingers,
                  trills: moved.trills,
                  graceNotes: moved.graceNotes,
                  renderOverrides: { hidden: moved.hiddenNotes, hands: NO_HANDS },
                }),
              }
            : current,
        );
      } catch (caught) {
        setTransposePreview((current) =>
          current ? { ...current, error: readable(caught, "Could not write the preview.") } : current,
        );
      } finally {
        setPreviewing(false);
      }
    },
    [
      audioUuid,
      anchorMs,
      anchorFigure,
      frameMs,
      stretches,
      dropDecorative,
      notesMarksMoved,
      previewSheetOf,
      drawnMarks,
    ],
  );

  /**
   * **Preview** of a figures transposition: every figure moved the same number of steps (the
   * figure shift of D-18). A figure set by hand moves with them; one that has no figure to become,
   * and a beam mark on notes that can no longer be beamed (a negra or longer), is removed, and
   * the dialog says how many. Undo brings them back exactly: they are page edits.
   */
  const previewFigures = useCallback(
    async (from: FigureName, to: FigureName) => {
      if (!audioUuid || anchorMs === null) return;
      const steps = figureSteps(from, to);
      const nextAnchor = shiftFigure(anchorFigure, steps);
      if (!nextAnchor) return;
      const nextOverrides: Record<string, FigureName> = {};
      let overridesRemoved = 0;
      for (const [key, figure] of Object.entries(overrides)) {
        const moved = shiftFigure(figure, steps);
        if (moved) nextOverrides[key] = moved;
        else overridesRemoved += 1;
      }
      setTransposePreview({
        kind: "figures",
        to,
        anchorFigure: nextAnchor,
        overrides: nextOverrides,
        beamBreaks,
        beamJoins,
        facts: [],
        sheet: null,
        error: null,
      });
      setPreviewing(true);
      try {
        const previewScore = await timeScoreApi.score(audioUuid, {
          anchorFigure: nextAnchor,
          anchorMs,
          frameMs,
          boundaries: stretches.map((stretch) => stretch.startFrame),
          boundaryMs: [anchorMs, ...stretches.map((stretch) => stretch.anchorMs)],
          ...pageEdits,
        });
        // What each chord prints as after the change: its figure set by hand, or the new name.
        const printed = new Map<string, FigureName>();
        for (const note of previewScore.notes) {
          const key = `${note.hand}:${note.startFrame}`;
          if (!printed.has(key)) printed.set(key, nextOverrides[key] ?? note.figure);
        }
        const beamable = (key: string) => {
          const figure = printed.get(key);
          return figure === undefined || BEAMABLE_FIGURES.has(figure);
        };
        const keptBreaks = new Set([...beamBreaks].filter(beamable));
        const keptJoins = new Set([...beamJoins].filter(beamable));
        const beamsRemoved = beamBreaks.size - keptBreaks.size + (beamJoins.size - keptJoins.size);
        const removed = [
          ...(beamsRemoved > 0
            ? [`${beamsRemoved} beam mark${beamsRemoved === 1 ? "" : "s"}`]
            : []),
          ...(overridesRemoved > 0
            ? [`${overridesRemoved} figure${overridesRemoved === 1 ? "" : "s"} set by hand`]
            : []),
        ];
        setTransposePreview((current) =>
          current?.kind === "figures" && current.to === to
            ? {
                ...current,
                beamBreaks: keptBreaks,
                beamJoins: keptJoins,
                facts: [
                  ...current.facts,
                  ...(removed.length > 0
                    ? [`Removed, because they no longer fit: ${removed.join(", ")}.`]
                    : []),
                ],
                sheet: previewSheetOf(previewScore, {
                  overrides: nextOverrides,
                  beamBreaks: keptBreaks,
                  beamJoins: keptJoins,
                }),
              }
            : current,
        );
      } catch (caught) {
        setTransposePreview((current) =>
          current ? { ...current, error: readable(caught, "Could not write the preview.") } : current,
        );
      } finally {
        setPreviewing(false);
      }
    },
    [
      audioUuid,
      anchorMs,
      anchorFigure,
      frameMs,
      stretches,
      pageEdits,
      overrides,
      beamBreaks,
      beamJoins,
      previewSheetOf,
    ],
  );

  /**
   * **Transpose** in the dialog. One step of the history either way.
   *
   * Notes: written onto the recording first, then the key and the marks addressed by a key move
   * with them, in the same step; the step carries the call that moves every note back (with the
   * notes that stayed and the notes taken off, so the undo is exact) and the call that moves them
   * again. Figures: a page edit, the main figure, the figures set by hand, the beam marks and the
   * **From** of the next time.
   */
  const confirmTranspose = useCallback(async () => {
    const chosen = transposePreview;
    if (!chosen || !audioUuid) return;
    if (chosen.kind === "figures") {
      stageEdit("Transpose figures");
      set.anchorFigure(chosen.anchorFigure);
      set.figuresFrom(chosen.to);
      set.overrides(chosen.overrides);
      set.beamBreaks(chosen.beamBreaks);
      set.beamJoins(chosen.beamJoins);
      setTransposePreview(null);
      return;
    }
    const { semitones } = chosen;
    setTransposing(true);
    try {
      const done = await timeScoreApi.transpose(audioUuid, { semitones });
      const back = { semitones: -semitones, hold: done.held, restore: done.takenOff };
      const moved = notesMarksMoved(semitones);
      stageEdit("Transpose notes", {
        undo: async () => {
          await timeScoreApi.transpose(audioUuid, back);
          await applyRef.current();
        },
        redo: async () => {
          await timeScoreApi.transpose(audioUuid, { semitones });
          await applyRef.current();
        },
      });
      set.keySignature(moved.keySignature);
      set.keyChanges(moved.keyChanges);
      set.fingers(moved.fingers as typeof fingers);
      set.hiddenNotes(moved.hiddenNotes);
      set.trills(moved.trills);
      set.graceNotes(moved.graceNotes);
      setTransposePreview(null);
      await apply();
    } catch (caught) {
      setTransposePreview((current) =>
        current ? { ...current, error: readable(caught, "Could not transpose the notes.") } : current,
      );
    } finally {
      setTransposing(false);
    }
  }, [transposePreview, audioUuid, stageEdit, set, notesMarksMoved, apply]);

  /**
   * **Key for this passage** (plan section 11.6): the key that prints the fewest accidentals over
   * the marked stretch, measured by the drawing itself, when it is not the one in force there.
   */
  const passageKeyHint = useMemo<KeySignatureName | null>(() => {
    if (!range || !sheetRenderer) return null;
    const found = sheetRenderer.suggestKeyFor(range.fromColumn, range.toColumn);
    const inForce = sheetRenderer.keySignatureAt(range.fromColumn);
    return found?.best && found.best !== inForce && (found.savedAgainstActive ?? 0) > 0
      ? (found.best as KeySignatureName)
      : null;
  }, [range, sheetRenderer]);

  /** The clef rule (plan section 11.7) over the marked stretch, for the Clef tab to offer again. */
  const clefRunsHere = useMemo<ClefRange[]>(() => {
    const music = sheetRenderer?.getMusic();
    if (!range || !music) return [];
    return suggestClefRanges(music, { keySignature: keySignature as KeySignature })
      .map((run) => ({
        ...run,
        fromFrame: Math.max(run.fromFrame, range.fromColumn),
        toFrame: Math.min(run.toFrame, range.toColumn),
      }))
      .filter(
        (run) =>
          run.toFrame > run.fromFrame &&
          run.fromFrame > 0 &&
          clefAtFrame(run.fromFrame, "left", clefChanges) !== "treble",
      );
  }, [range, sheetRenderer, keySignature, clefChanges]);

  /**
   * A lyrics piece dropped from the pool onto the sheet: it starts on the frame under the pointer
   * (the column that holds it, as a click above the staves reads it), in one step. It stays in the
   * pool, ticked. Refused where another piece already covers that frame.
   */
  const dropFromPool = useCallback(
    (index: number, clientX: number, clientY: number) => {
      sheetRenderer?.showLyricGuide(undefined);
      const text = lyricsPool[index];
      const at = sheetRenderer?.frameAtClientPoint(clientX, clientY);
      if (text === undefined || !at || !score) return;
      const outcome = placePiece(lyrics, text, at.frame, frameMs, score.envelope.frameCount);
      if ("refused" in outcome) {
        setMoveRefused(outcome.refused);
        return;
      }
      set.lyrics(outcome.ok);
      setPickedLyrics([at.frame]);
    },
    [lyricsPool, sheetRenderer, score, lyrics, frameMs, set],
  );

  /**
   * The piece of the pool being dragged, and the frame its guide was last drawn for. While it is
   * over the sheet, the sheet shades every placed piece's frames and the frames it would cover:
   * green where it may land, red where another piece is.
   */
  const poolDrag = useRef<{ index: number; frame: number | null } | null>(null);
  const onPoolDrag = useCallback(
    (index: number | null) => {
      poolDrag.current = index === null ? null : { index, frame: null };
      if (index === null) sheetRenderer?.showLyricGuide(undefined);
    },
    [sheetRenderer],
  );
  const guidePoolDrag = useCallback(
    (clientX: number, clientY: number) => {
      const dragging = poolDrag.current;
      const text = dragging ? lyricsPool[dragging.index] : undefined;
      if (!dragging || text === undefined || !sheetRenderer || !score) return;
      const at = sheetRenderer.frameAtClientPoint(clientX, clientY);
      if (!at || at.frame === dragging.frame) return;
      dragging.frame = at.frame;
      const landing = landingOf(lyrics, text, at.frame, frameMs, score.envelope.frameCount);
      sheetRenderer.showLyricGuide({ fromColumn: landing.fromColumn, toColumn: landing.toColumn });
    },
    [lyricsPool, sheetRenderer, score, lyrics, frameMs],
  );

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
    const takenOff = hiddenNotesOut(hiddenNotes);
    setClearing(true);
    setConfirmRemove(false);
    // Every decision at once, back to the piece as the recording alone describes it. The sheet is
    // then written for the first time again, so it takes the defaults of a first write: the key
    // with the fewest accidentals and the brackets of the high passages (plan section 11.3).
    keyDecided.current = false;
    ottavasDecided.current = false;
    clefsDecided.current = false;
    // The pool is the song's words, saved apart from the sheet: Remove all leaves it.
    resetEdits((current) => ({ ...NO_EDITS, lyricsPool: current.lyricsPool }));
    setCleanEdits(null);
    setTrillSuggestions(null);
    setPickedLyrics([]);
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
      step?.onChanged();
    } catch (caught) {
      // The screen is already clear, so this is only about what a reload would bring back.
      setSaveProblem(readable(caught, "Could not forget the saved sheet."));
    } finally {
      setClearing(false);
    }
    await apply({
      stretches: NO_EDITS.stretches,
      anchorFigure: NO_EDITS.anchorFigure,
      pageEdits: { hiddenNotes: [], trills: [], dropDecorative: NO_EDITS.dropDecorative },
    });
  }, [audioUuid, apply, frameMs, hiddenNotes, resetEdits, step]);

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
      // Not urgent: re-rendering this page to close the panel takes tens of milliseconds, and
      // while it runs the answer of the hand request below cannot be read, so the new sheet would
      // be asked for only after it. As a transition React pauses that render for the answer.
      startTransition(() => {
        setMoveRefused(null);
        setMovingHand(true);
        closeNotes();
      });
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
      return Math.max(1, Math.round((anchorMs ?? frameMs) / frameMs));
    },
    [score, anchorMs, frameMs],
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
   * Draw the sheet on arrival, from the saved reading or from the defaults.
   *
   * Coming back used to mean pressing **Write the sheet** to see what you already decided, and a
   * new piece waited for a peak to be named on a plot. Neither waits now (plan section 11.1). Once
   * per piece, and only while nothing has been drawn yet.
   */
  const restored = useRef<string | null>(null);
  useEffect(() => {
    // A stale reading waits for the reader: the banner asks for **Write the sheet** first. Every
    // other sheet is drawn as soon as the saved reading has been asked for (so the defaults of a
    // first write never land on a reader's own key) and the figure ladder is known.
    if (!audioUuid || !rhythmChecked || anchorMs === null || score || busy || stale) return;
    if (restored.current === key) return;
    restored.current = key;
    void apply();
  }, [audioUuid, rhythmChecked, anchorMs, score, busy, stale, key, apply]);

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
    if (!audioUuid || anchorMs === null || !score) return;
    if (sheetBuiltFor.current === editSignature) return;
    const waiting = window.setTimeout(() => void apply(), 400);
    return () => window.clearTimeout(waiting);
  }, [editSignature, audioUuid, anchorMs, score, apply]);

  if (!audioUuid) {
    return <EmptyState message="Open a project to see its sheet." />;
  }

  const sheetTitle = title ?? pieceLabel ?? "Untitled";
  const underTitle = [subtitle, artist].filter(Boolean).join(" · ");
  const recordAt = range?.fromColumn;

  return (
    <Box data-sheet-page>
      {/*
        A stale reading is loaded but not drawn until the reader presses Write the sheet; once
        drawn, Save makes it the sheet of the piece again. The one warning of this page, because it
        changes what the reader should do next.
      */}
      {stale ? (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          data-sheet-banner="stale"
          action={
            score ? undefined : (
              <PillButton kind="primary" size="small" busy={busy} disabled={anchorMs === null} onClick={() => void apply()}>
                Write the sheet
              </PillButton>
            )
          }
        >
          {score
            ? readOnly
              ? "Drawn from the current notes and hands."
              : "Drawn from the current notes and hands. Save to keep it."
            : "The notes or the hands changed since this sheet was saved."}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity={untranscribed ? "warning" : "error"} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {pieceIsEmpty ? (
        <EmptyState
          message="Nothing to write yet."
          action={
            readOnly ? undefined : (
              <PillButton kind="primary" onClick={() => setRecordOpen(true)}>
                Record a passage
              </PillButton>
            )
          }
        />
      ) : null}

      {score ? (
        <Stack spacing={1.5}>
          {/* The title lines of the sheet, as they print. Changed in the Title tab. */}
          <Box sx={{ px: 1 }}>
            <Typography
              component="h2"
              sx={{ fontSize: 20, fontWeight: 600, lineHeight: 1.3 }}
              noWrap
              title={sheetTitle}
              data-sheet-title
            >
              {sheetTitle}
            </Typography>
            {underTitle ? (
              <Typography variant="body2" color="text.secondary" noWrap title={underTitle}>
                {underTitle}
              </Typography>
            ) : null}
          </Box>
          <ScorePlayer
            compact
            audioUuid={audioUuid}
            scoreSeconds={(score.envelope.frameCount * score.envelope.frameMs) / 1000}
            onTime={setPlayheadSeconds}
            controlsRef={player}
            onScrollToCursor={scrollToCursor}
            onPlaying={setPlaying}
          />
          <SheetFloatingBar
            readOnly={readOnly}
            playing={playing}
            onTogglePlay={() => player.current?.toggle()}
            undo={{
              can: edits.canUndo,
              label: edits.undoLabel,
              busy: edits.busy,
              run: () => void edits.undo(),
            }}
            redo={{
              can: edits.canRedo,
              label: edits.redoLabel,
              busy: edits.busy,
              run: () => void edits.redo(),
            }}
            toolboxOpen={sheetToolbox}
            onToolbox={() => setSheetToolbox((open) => !open)}
            onRecord={() => setRecordOpen(true)}
            canPrint={Boolean(sheetRenderer)}
            onPrint={() => setPdfOpen(true)}
            canSave={anchorMs !== null}
            unsaved={unsaved}
            saving={saving}
            flash={flash}
            onSave={() => void save()}
            pianoOpen={pianoOpen}
            onPiano={() => setPianoOpen((open) => !open)}
            onFindTrills={() => {
              setTrillsOpen(true);
              void findTrills();
            }}
            hiddenCount={hiddenNotes.size}
            onBringBack={() => setHiddenNotes(new Set())}
            clearing={clearing}
            onRemoveAll={() => setConfirmRemove(true)}
            saveProblem={saveProblem}
            onCloseProblem={() => setSaveProblem(null)}
            refused={moveRefused ?? (edits.failure ? readable(edits.failure, "That edit could not be taken back.") : null)}
            onCloseRefused={() => {
              setMoveRefused(null);
              edits.clearFailure();
            }}
          />
          {/*
            Capture, so the press is recorded before the sheet's own handlers run and open a
            toolbox from it.
          */}
          <Box
            onPointerDownCapture={(event) => {
              pressedAt.current = pressedBox(event);
            }}
            // A lyrics piece dragged from the pool lands on the frame under the pointer.
            onDragOver={(event) => {
              if (!readOnly && event.dataTransfer.types.includes(POOL_DRAG_TYPE)) {
                event.preventDefault();
                event.dataTransfer.dropEffect = "copy";
                guidePoolDrag(event.clientX, event.clientY);
              }
            }}
            onDrop={(event) => {
              const index = event.dataTransfer.getData(POOL_DRAG_TYPE);
              if (readOnly || index === "") return;
              event.preventDefault();
              dropFromPool(Number(index), event.clientX, event.clientY);
            }}
            data-sheet-drop
          >
            <TimeScoreView
              score={score}
              overrides={drawnMarks.overrides}
              beamBreaks={drawnMarks.beamBreaks}
              beamJoins={drawnMarks.beamJoins}
              keySignature={keySignature}
              keyChanges={keyChanges}
              clefChanges={clefChanges}
              ottavas={drawnMarks.ottavas}
              onKeySuggestion={takeKeyHint}
              onClefSuggestion={readOnly ? undefined : takeClefHint}
              onOttavaSuggestion={takeOttavaHint}
              showFrameLabels={frameLabelsOn}
              spacings={spacings}
              evenSpacings={drawnMarks.evenSpacings}
              lineSpacing={lineSpacing}
              noteSpacing={noteSpacing}
              staffGaps={staffGaps}
              onStaffGapsChange={readOnly ? ignore : setStaffGaps}
              onSelectNotes={readOnly ? ignore : pickNotes}
              onSelectRange={readOnly ? ignore : pickRange}
              onSelectMarkedRange={readOnly ? ignore : pickMarkedRange}
              onOttavaResize={readOnly ? ignore : stretchOttava}
              renderOverrides={renderOverrides}
              fingers={drawnMarks.fingers}
              trills={trills}
              lyrics={lyrics}
              onLyricPlace={readOnly ? undefined : placeLyric}
              onLyricSelect={readOnly ? undefined : pickLyric}
              selectedLyrics={lyricsMode ? pickedLyrics : undefined}
              onLyricsClear={readOnly ? undefined : clearPickedLyrics}
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
        </Stack>
      ) : !error && !pieceIsEmpty && !(stale && rhythmChecked && anchorMs !== null) ? (
        // Reserve the place of the sheet while it is written, so nothing jumps when it arrives.
        <Box sx={{ display: "grid", placeItems: "center", minHeight: 320 }} data-sheet-loading>
          <CircularProgress size={22} />
        </Box>
      ) : null}

      <SheetToolbox
        open={sheetToolbox && score !== null}
        onClose={() => setSheetToolbox(false)}
        tab={sheetTab}
        onTab={setSheetTab}
        state={edits.state}
        set={edits.set}
        pieceLabel={pieceLabel}
        keyHint={keyHint}
        ottavaHint={ottavaHint}
        onTakeOttavaHint={() => {
          ottavasDecided.current = true;
          setOttavas(clearOfClefChanges(ottavaHint, clefChanges));
        }}
        frameLabelsOn={frameLabelsOn}
        setFrameLabelsOn={setFrameLabelsOn}
        sheetZoom={sheetZoom}
        setSheetZoom={setSheetZoom}
        transposing={previewing}
        onPreviewNotes={(semitones) => void previewNotes(semitones)}
        onPreviewFigures={(from, to) => void previewFigures(from, to)}
        pickedLyrics={pickedLyrics}
        setPickedLyrics={setPickedLyrics}
        onRefused={setMoveRefused}
        lyricsField={{
          onPoolDrag,
          pasted: lyricsFieldText,
          setPasted: (text) => setLyricsDraft({ forPart: audioUuid, text }),
          savedText: savedLyricsText,
          poolUnsaved,
          saving: savingLyrics,
          onSave: (text) => void saveSongLyrics(text),
        }}
      />

      <TransposeDialog
        open={transposePreview !== null}
        title={transposePreview?.kind === "figures" ? "Transpose the figures" : "Transpose the notes"}
        facts={transposePreview?.facts ?? []}
        sheet={transposePreview?.sheet ?? null}
        loading={previewing}
        error={transposePreview?.error ?? null}
        confirming={transposing}
        onConfirm={() => void confirmTranspose()}
        onCancel={() => setTransposePreview(null)}
      />

      {/*
        Record: play a passage and put it into the piece, at the start of the marked stretch or at
        the end. Paste joins it in Phase 8 and Record in Sheet replaces it in Phase 9.
      */}
      <Toolbox
        open={recordOpen}
        title="Record a passage"
        subtitle={
          recordAt === undefined
            ? "Added at the end"
            : `Added at ${formatSeconds((recordAt * frameMs) / 1000)}`
        }
        initialPosition={{ x: 24, y: 120 }}
        onClose={() => setRecordOpen(false)}
        width={420}
      >
        <Stack spacing={1.5}>
          <Alert severity="warning" variant="outlined">
            Placing a passage writes it onto the recording. Undo cannot take it back.
          </Alert>
          <ComposePassagePanel
            audioUuid={audioUuid}
            frameMs={frameMs}
            durationSeconds={pieceSeconds}
            atColumn={recordAt}
            anchorFigure={anchorFigure}
            anchorMs={anchorMs ?? undefined}
            speedChanges={stretches.map((stretch) => ({
              startFrame: stretch.startFrame,
              anchorMs: stretch.anchorMs,
            }))}
            clickIntervalMs={anchorMs ?? undefined}
            onPlaced={() => {
              setRecordOpen(false);
              setComposed((token) => token + 1);
            }}
          />
        </Stack>
      </Toolbox>

      {/* What Find trills found: two notes taking turns three times or more, one row each. */}
      <Toolbox
        open={trillsOpen}
        title="Trills"
        initialPosition={{ x: 24, y: 120 }}
        onClose={() => setTrillsOpen(false)}
      >
        {findingTrills || trillSuggestions === null ? (
          <CircularProgress size={18} />
        ) : unmarkedTrills.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {trillSuggestions.length === 0
              ? "No trills found."
              : "Every trill found is already written."}
          </Typography>
        ) : (
          <Stack spacing={0.5} data-trill-suggestions={unmarkedTrills.length}>
            {unmarkedTrills.map((one) => (
              <Stack
                key={`${one.hand}:${one.startFrame}`}
                direction="row"
                spacing={1}
                sx={{ alignItems: "center" }}
              >
                <Typography variant="body2" sx={{ flex: 1 }}>
                  {one.noteName}–{one.otherNoteName} · {one.hand === "left" ? "left" : "right"} hand ·{" "}
                  {formatSeconds(one.startSeconds)}
                </Typography>
                <IconAction
                  title="Write as a trill"
                  icon={<CheckIcon fontSize="small" />}
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
              </Stack>
            ))}
          </Stack>
        )}
        {trills.length > 0 ? (
          <Box sx={{ mt: 1.5 }}>
            <PillButton kind="quiet" size="small" onClick={() => setTrills([])}>
              Print every trill as its notes ({trills.length})
            </PillButton>
          </Box>
        ) : null}
      </Toolbox>

      <PianoToolbox
        open={pianoOpen}
        onClose={() => setPianoOpen(false)}
        playheadFrame={playheadFrame}
        frameMs={frameMs}
        addHand={addHand}
        setAddHand={setAddHand}
        addingNote={addingNote}
        soundingColours={soundingColours}
        soundingNow={soundingNow}
        onKeyPress={pressKeyboardKey}
        noteNameAt={noteNameAt}
      />

      <DecorationToolbox
        open={decorationFor !== null && onlyNote !== null}
        onlyNote={onlyNote}
        onClose={() => setDecorationFor(null)}
        graceHere={graceHere}
        clearGrace={notes.clearGrace}
        putGrace={notes.putGrace}
        noteNameAt={noteNameAt}
      />
      <RangeToolbox
        open={framesToolbox}
        range={range}
        setRange={setRange}
        frameMs={frameMs}
        framesAt={framesAt}
        onClose={closeFrames}
        onSelectNotes={selectNotesUnderRange}
        canSelectNotes={Boolean(sheetRenderer)}
        rangeHand={rangeHand}
        setRangeHand={setRangeHand}
        frameTab={frameTab}
        setFrameTab={setFrameTab}
        rangeActions={rangeActions}
        setPassageDraft={setPassageDraft}
        passageKeyHint={passageKeyHint}
        clefRunsHere={clefRunsHere}
        score={score}
        state={edits.state}
        set={edits.set}
        setOttavaHidden={setOttavaHidden}
        audioUuid={audioUuid}
        anchorMs={anchorMs}
        onRerecordAccepted={acceptRerecord}
      />

      <NoteToolbox
        open={notesToolbox}
        selectedNotes={selectedNotes}
        notesAt={notesAt}
        frameMs={frameMs}
        onClose={closeNotes}
        onSelectFrames={selectRangeOfNotes}
        notes={notes}
        fingers={fingers}
        setFingerDraft={setFingerDraft}
        movingHand={movingHand}
        onMoveHand={moveSelected}
        noteNameAt={noteNameAt}
        onOpenDecoration={setDecorationFor}
      />

      <ConfirmDialog
        open={confirmRemove}
        title="Remove all your changes to this sheet?"
        message="The key, the figures, every mark and the notes taken off go back to the first sheet. The saved sheet is deleted. Undo cannot take this back."
        confirmLabel="Remove all"
        danger
        busy={clearing}
        onConfirm={() => void wipe()}
        onCancel={() => setConfirmRemove(false)}
      />

      <ScorePdfDialog
        open={pdfOpen}
        onClose={() => setPdfOpen(false)}
        renderer={sheetRenderer}
        pieceName={sheetTitle}
      />
    </Box>
  );
}

export default SheetPage;
