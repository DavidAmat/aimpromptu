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
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { PageContainer, SectionCard } from "../../ui";
import PeakPlot from "../../components/time/PeakPlot";
import ScorePlayer, {
  type ScorePlayerControls,
} from "../../components/time/ScorePlayer";
import TimeScoreView from "../../components/time/TimeScoreView";
import ToolboxDialog from "../../components/common/ToolboxDialog";
import {
  FIGURE_LABELS,
  timeScoreApi,
  type FigureName,
  type HandChoice,
  type LadderPreview,
  type Peak,
  type PeaksResponse,
  KEY_LABELS,
  KEY_SIGNATURES,
  type KeySignatureName,
  type SavedRhythm,
  type TimeScorePayload,
} from "../../api";
import { ApiError } from "../../api";
import {
  applyKeySignatureRange,
  applyOttava,
  clearKeySignatureRange,
  clearOttavaRange,
  keySignatureAtFrame,
  ottavaAtFrame,
  type FingerNumber,
  type KeyChangeAnnotation,
  type KeySignature,
  type OttavaAnnotation,
  type OttavaKind,
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
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

const NAMEABLE_FIGURES: FigureName[] = [
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
];

/** Thumb to little finger. There is no 0 and no 6. */
const FINGERS: FingerNumber[] = [1, 2, 3, 4, 5];

/** Stands for "a saved reading already answered this", which outranks any suggestion. */
const SAVED_OTTAVAS = "\u0000saved";

/** What a stretch of columns can carry. One pill each, and only that one's controls on screen. */
const FRAME_TABS = [
  { id: "key" as const, label: "Key" },
  { id: "octave" as const, label: "Octave" },
];

type FrameTab = (typeof FRAME_TABS)[number]["id"];

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

/** Everything a single note may be drawn as. Wider than the list used to name a gap. */
const ALL_FIGURES: FigureName[] = [
  "redonda",
  "blanca",
  "dottedBlanca",
  "negra",
  "dottedNegra",
  "corchea",
  "semicorchea",
];

interface Stretch {
  /** The frame the stretch starts at. Everything before it keeps the previous name. */
  startFrame: number;
  /** What a gap is called from here on, in milliseconds. */
  anchorMs: number;
}

/** A clicked note arrives as `hand:frame:row`; an override belongs to the whole chord at that frame. */
function figureKeyOf(noteKey: string): string {
  const [hand, frame] = noteKey.split(":");
  return `${hand}:${frame}`;
}

/** How wide the floating toolbox is, and how far it stands off what it is about. */
const TOOLBOX_WIDTH = 360;
const TOOLBOX_GAP = 16;

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

function besideOnScreen(
  box: DOMRect | null,
): { x: number; y: number } | undefined {
  if (!box) return undefined;
  const toTheRight = box.right + TOOLBOX_GAP;
  const x =
    toTheRight + TOOLBOX_WIDTH + TOOLBOX_GAP <= window.innerWidth
      ? toTheRight
      : Math.max(TOOLBOX_GAP, box.left - TOOLBOX_GAP - TOOLBOX_WIDTH);
  const y = Math.max(TOOLBOX_GAP, Math.min(box.top, window.innerHeight - 260));
  return { x: Math.round(x), y: Math.round(y) };
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
   * Figures set by hand on one note, keyed `hand:startFrame`.
   *
   * Kept here and drawn on top rather than saved, because an override is only a glyph: nothing
   * moves and no other note changes. Writing the sheet again keeps them.
   */
  const [overrides, setOverrides] = useState<Record<string, FigureName>>({});
  const [selectedNote, setSelectedNote] = useState<string | null>(null);
  /**
   * The signature the whole piece is written in, and what the notes themselves suggest.
   *
   * A transcription has no key. The recording says which keys were pressed and nothing about how
   * they should be spelled, so until someone chooses, everything is written in C and every black
   * key prints its own accidental. Choosing moves those accidentals into the clef.
   */
  const [keySignature, setKeySignature] = useState<KeySignatureName>("C");
  const [keyHint, setKeyHint] = useState<{
    best: KeySignatureName;
    saved: number;
  } | null>(null);
  /**
   * Where the piece leaves the main signature, and what it changes to.
   *
   * Kept as transitions rather than as ranges, which is how the drawing package stores them: at any
   * column exactly one signature is sounding, so two edits cannot disagree. Giving a passage its own
   * key writes two, one at each end.
   */
  const [keyChanges, setKeyChanges] = useState<KeyChangeAnnotation[]>([]);
  /**
   * Where each hand is written an octave or two from where it sounds.
   *
   * Seeded from what the register asks for the first time a piece is drawn, and the reader's from
   * then on: a bracket they cleared must stay cleared, which is why these are held here rather than
   * worked out on each render. Saved with the rhythm for the same reason.
   */
  const [ottavas, setOttavas] = useState<OttavaAnnotation[]>([]);
  /** The piece whose brackets have already been decided, so a redraw never re-adds a cleared one. */
  const decidedOttavasFor = useRef<string | null>(null);
  /** Notes picked on the sheet: click one, then hold Command and click more. */
  const [selectedNotes, setSelectedNotes] = useState<readonly string[]>([]);
  const [framesToolbox, setFramesToolbox] = useState(false);
  /** Which pill is open in the frame toolbox. */
  const [frameTab, setFrameTab] = useState<FrameTab>("key");
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
  /**
   * Notes the reader has asked to start a new beam.
   *
   * Kept beside the overrides and for the same reason: it changes how the page is grouped and
   * nothing about the music. A long arpeggio beams as one slope because no rule can see where the
   * phrase restarts — only the person reading can, so they say.
   */
  const [beamBreaks, setBeamBreaks] = useState<ReadonlySet<string>>(new Set());
  /**
   * Notes the reader took off the page, as `startFrame:row`.
   *
   * A transcriber inventing a note out of a pedal blur is the commonest thing wrong with a page, and
   * the honest fix is to stop drawing it, not to say it was never played. The recording is evidence
   * and stays as it is; this is a set of keys beside it. Bringing one back restores it exactly.
   */
  const [hiddenNotes, setHiddenNotes] = useState<ReadonlySet<NoteRef>>(
    new Set(),
  );
  /**
   * Notes the reader sent to the other staff, as `startFrame:row` to the staff they belong on.
   *
   * The hand split is worked out by an algorithm that cannot see the player's hands, and where it is
   * wrong a pianist can see it at a glance. Correcting it is a statement about how the piece is
   * played, so it belongs here rather than in the matrix the split was computed from.
   */
  const [handOverrides, setHandOverrides] = useState<
    ReadonlyMap<NoteRef, PrintedHand>
  >(new Map());
  /** Which finger plays each note, keyed `hand:startFrame:row` by the staff it is drawn on. */
  const [fingers, setFingers] = useState<Record<string, FingerNumber>>({});
  /** Numbers pressed for the selection now open, so a chord can be given several at once. */
  const [fingerDraft, setFingerDraft] = useState<{
    forSelection: string;
    picked: FingerNumber[];
  } | null>(null);
  /** A move the far staff had no room for, said once, in words. */
  const [moveRefused, setMoveRefused] = useState<string | null>(null);
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
  /**
   * Where the piece changes speed, as frames, and what a gap is called after each of them.
   *
   * A boundary is drawn by hand. Nothing detects them: a wrong hand-drawn one spoils one stretch,
   * while a wrong automatic one scatters speed changes through the piece and makes the sheet
   * unreadable. Frames are absolute wall clock, so a boundary never moves a note.
   */
  const [stretches, setStretches] = useState<Stretch[]>([]);
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
   * Everything read for one (piece, hand, resolution), kept together under the key it belongs to.
   *
   * One object rather than five, because they always change together: asking about the other hand
   * invalidates the piles, the chosen pile, the preview and the sheet at once. Comparing the key
   * during render is how the reset happens, which keeps it out of the effect.
   */
  const key = `${audioUuid ?? ""}|${hand}|${frameMs}`;
  const [view, setView] = useState<View>(() => emptyView(key));
  const [untranscribed, setUntranscribed] = useState(false);
  if (view.key !== key) setView(emptyView(key));

  const { peaks, selected, preview, score, error } = view;

  const renderOverrides = useMemo(
    () => ({ hidden: hiddenNotes, hands: handOverrides }),
    [hiddenNotes, handOverrides],
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
      const staff = handOverrides.get(ref) ?? note.hand;
      const key = `${staff}:${note.startFrame}`;
      const rows = found.get(key);
      if (rows) rows.push(note.row);
      else found.set(key, [note.row]);
    }
    return found;
  }, [score, hiddenNotes, handOverrides]);

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
    octave: range
      ? ottavaAtFrame(ottavas, "left", range.fromColumn) !== undefined ||
        ottavaAtFrame(ottavas, "right", range.fromColumn) !== undefined
      : false,
  };

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

  // Read back what this piece was last read as, once per piece.
  //
  // Restoring the anchor is not enough on its own: the pile it names has to be the one the plot
  // shows, or the number under the name would say one thing and the highlighted bar another. So the
  // nearest pile is selected too, and if none is near, the saved reading is kept and the plot simply
  // has nothing highlighted, which is honest about the two disagreeing.
  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    timeScoreApi
      .rhythm(audioUuid, controller.signal)
      .then((found) => {
        if (!found) return;
        setSaved(found);
        setHand(found.hand);
        setFigure(found.anchorFigure);
        setStretches(
          found.speedChanges.map((change) => ({
            startFrame: change.startFrame,
            anchorMs: change.anchorMs,
          })),
        );
        setOverrides(
          Object.fromEntries(
            found.overrides.map((one) => [
              `${one.hand}:${one.startFrame}`,
              one.figure,
            ]),
          ),
        );
        setBeamBreaks(
          new Set(
            found.beamBreaks.map((one) => `${one.hand}:${one.startFrame}`),
          ),
        );
        setHiddenNotes(
          new Set(
            (found.hiddenNotes ?? []).map(
              (one) => `${one.startFrame}:${one.row}`,
            ),
          ),
        );
        setHandOverrides(
          new Map(
            (found.handOverrides ?? []).map((one) => [
              `${one.startFrame}:${one.row}`,
              one.hand as PrintedHand,
            ]),
          ),
        );
        setFingers(
          Object.fromEntries(
            (found.fingers ?? []).map((one) => [
              `${one.hand}:${one.startFrame}:${one.row}`,
              one.finger as FingerNumber,
            ]),
          ),
        );
        if (found.keySignature) setKeySignature(found.keySignature);
        setKeyChanges(
          (found.keyChanges ?? []).map((change) => ({
            fromColumn: change.fromColumn,
            keySignature: change.keySignature as KeySignature,
          })),
        );
        // A reading saved before brackets existed has nothing to say about them, so it is left to
        // the suggestion. One saved since does, including when what it says is "none".
        if (found.ottavas) {
          decidedOttavasFor.current = null;
          setOttavas(
            found.ottavas.map((span) => ({
              kind: span.kind as OttavaKind,
              hand:
                span.hand === "left" ? ("left" as const) : ("right" as const),
              fromColumn: span.fromColumn,
              toColumn: span.toColumn,
            })),
          );
          decidedOttavasFor.current = SAVED_OTTAVAS;
        }
      })
      .catch(() => {
        // A reading that cannot be read is not worth stopping the screen for: the plot still works
        // and the reader can name the gap again.
      });
    return () => controller.abort();
  }, [audioUuid]);

  /**
   * Both of these have to keep the same identity between renders.
   *
   * The sheet is rebuilt whenever anything it draws from changes, and a handler written inline is a
   * different function every time, so the sheet would be rebuilt on every click and would lose the
   * selection it had just made.
   */
  const pickRange = useCallback(
    (picked: { fromColumn: number; toColumn: number }) => {
      setRange(picked);
      setFramesToolbox(true);
      setFramesAt(besideOnScreen(pressedAt.current));
    },
    [],
  );

  /**
   * Take the brackets the register asks for — once, and only if nobody has said otherwise.
   *
   * The suggestion is recomputed on every redraw, so without the guard a bracket the reader had
   * just cleared would come straight back on the next keystroke. That is the D38 fault in a
   * different place: the answer is not to stop suggesting, it is to stop overwriting.
   */
  const takeSuggestedOttavas = useCallback(
    (spans: OttavaAnnotation[]) => {
      if (
        decidedOttavasFor.current === key ||
        decidedOttavasFor.current === SAVED_OTTAVAS
      )
        return;
      decidedOttavasFor.current = key;
      setOttavas(spans);
    },
    [key],
  );

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
  const live = useMemo(() => {
    if (!score || chords.size === 0) {
      return { ottavas, beamBreaks, overrides, fingers };
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
      overrides: Object.fromEntries(
        Object.entries(overrides).filter(([groupKey]) => chords.has(groupKey)),
      ),
      fingers: Object.fromEntries(
        Object.entries(fingers).filter(([noteKey]) =>
          chords.has(groupKeyOf(noteKey)),
        ),
      ),
    };
  }, [score, chords, ottavas, beamBreaks, overrides, fingers]);

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
    (marker: { fromColumn: number; toColumn: number }) => {
      setRange({ fromColumn: marker.fromColumn, toColumn: marker.toColumn });
      setFramesToolbox(true);
      setFramesAt(besideOnScreen(pressedAt.current));
    },
    [],
  );

  const pickNotes = useCallback((keys: readonly string[]) => {
    setSelectedNotes(keys);
    setNotesToolbox(keys.length > 0);
    // Measured from the noteheads rather than from the click, so a rubber band that took in half
    // the line opens its panel clear of the whole band instead of on top of it.
    if (keys.length > 0) {
      setNotesAt(
        besideOnScreen(
          screenBoxOf(".grid-note-target.is-selected") ?? pressedAt.current,
        ),
      );
    }
  }, []);

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
    setClearedAt((at) => at + 1);
  }, []);

  const closeNotes = useCallback(() => {
    setNotesToolbox(false);
    setSelectedNotes([]);
    setSelectedNote(null);
    setClearedAt((at) => at + 1);
  }, []);

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
    [],
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

  /** Take the picked notes off the page. The recording keeps them; the drawing stops asking. */
  const hideSelected = useCallback(() => {
    const refs = selectedNotes.map(noteRefOf);
    setHiddenNotes((current) => new Set([...current, ...refs]));
    setFingers((current) => {
      const next = { ...current };
      for (const noteKey of selectedNotes) delete next[noteKey];
      return next;
    });
    closeNotes();
  }, [selectedNotes, closeNotes]);

  /** Send the picked notes to the other staff. */
  const moveSelected = useCallback(
    (to: PrintedHand) => {
      setMoveRefused(null);
      setHandOverrides((current) => {
        const next = new Map(current);
        for (const noteKey of selectedNotes) next.set(noteRefOf(noteKey), to);
        return next;
      });
      // The numbers travel with the notes, or a fingering would be left over an empty staff.
      setFingers((current) => {
        const next = { ...current };
        for (const noteKey of selectedNotes) {
          const finger = next[noteKey];
          if (finger === undefined) continue;
          delete next[noteKey];
          next[`${to}:${frameOf(noteKey)}:${rowOf(noteKey)}`] = finger;
        }
        return next;
      });

      // A figure and a beam break belong to a whole chord, so they travel only when the whole chord
      // does. Half a chord moving leaves them where they are and the prune above decides their
      // fate: they still name the notes that stayed, or they name nothing and go. Carrying them on
      // a partial move would be a guess about which half the reader meant them for.
      const whole = new Set(selectedChords.whole);
      const moved = (groupKey: string): string =>
        `${to}:${groupKey.split(":")[1]}`;
      if (whole.size > 0) {
        setOverrides((current) => {
          const next = { ...current };
          for (const groupKey of whole) {
            const figure = next[groupKey];
            if (figure === undefined) continue;
            delete next[groupKey];
            next[moved(groupKey)] = figure;
          }
          return next;
        });
        setBeamBreaks((current) => {
          const next = new Set(current);
          for (const groupKey of whole) {
            if (!next.delete(groupKey)) continue;
            next.add(moved(groupKey));
          }
          return next;
        });
      }
      closeNotes();
    },
    [selectedNotes, selectedChords, closeNotes],
  );

  const toggleBeamBreak = useCallback(() => {
    const targets = selectedChords.whole;
    if (targets.length === 0 || selectedChords.partial.length > 0) return;
    setBeamBreaks((current) => {
      const next = new Set(current);
      const breaking = !targets.every((key) => next.has(key));
      for (const key of targets) {
        if (breaking) next.add(key);
        else next.delete(key);
      }
      return next;
    });
  }, [selectedChords]);

  const sayRefused = useCallback((refused: readonly NoteRef[]) => {
    setMoveRefused(
      refused.length === 0
        ? null
        : `${refused.length} note${refused.length === 1 ? "" : "s"} stayed where they were: the other staff already plays that key at that moment, and one key cannot be struck twice in the same frame.`,
    );
  }, []);

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

  const save = useCallback(async () => {
    if (!audioUuid || !selected) return;
    setSaving(true);
    setSavedNote(null);
    const body: SavedRhythm = {
      hand,
      frameMs,
      keySignature,
      keyChanges: keyChanges.map((change) => ({
        fromColumn: change.fromColumn,
        keySignature: change.keySignature,
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
      ottavas: live.ottavas.map((span) => ({
        kind: span.kind,
        hand: span.hand,
        fromColumn: span.fromColumn,
        toColumn: span.toColumn,
      })),
      hiddenNotes: [...hiddenNotes].map((ref) => {
        const [frame, row] = ref.split(":");
        return { startFrame: Number(frame), row: Number(row) };
      }),
      handOverrides: [...handOverrides].map(([ref, staff]) => {
        const [frame, row] = ref.split(":");
        return { startFrame: Number(frame), row: Number(row), hand: staff };
      }),
      fingers: Object.entries(live.fingers).map(([noteKey, finger]) => ({
        hand: handOf(noteKey),
        startFrame: frameOf(noteKey),
        row: rowOf(noteKey),
        finger,
      })),
    };
    try {
      const stored = await timeScoreApi.saveRhythm(audioUuid, body);
      setSaved(stored);
      setSavedNote("Saved with the piece. It will be here next time.");
    } catch (caught) {
      setSavedNote(readable(caught, "Could not save this rhythm."));
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
    stretches,
    live,
    hiddenNotes,
    handOverrides,
  ]);

  const apply = useCallback(async () => {
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
          boundaries: stretches.map((stretch) => stretch.startFrame),
          boundaryMs: [
            selected.medianMs,
            ...stretches.map((stretch) => stretch.anchorMs),
          ],
        }),
      ]);
      setView((current) =>
        current.key === key
          ? { ...current, preview: nextPreview, score: nextScore, error: null }
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
  }, [audioUuid, selected, figure, hand, frameMs, key, stretches]);

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
          {preview ? (
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {preview.headerLabel}
            </Typography>
          ) : null}
        </Stack>

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
              controls={player}
              onScrollToCursor={scrollToCursor}
            />
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
                keySignature={keySignature}
                keyChanges={keyChanges}
                ottavas={live.ottavas}
                onOttavaSuggestion={takeSuggestedOttavas}
                onKeySuggestion={setKeyHint}
                onSelectNote={setSelectedNote}
                onSelectNotes={pickNotes}
                onSelectRange={pickRange}
                onSelectMarkedRange={pickMarkedRange}
                renderOverrides={renderOverrides}
                fingers={live.fingers}
                onMovesRefused={sayRefused}
                selectedRange={range}
                clearSelectionsAt={clearedAt}
                playheadSeconds={playheadSeconds}
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
              {hiddenNotes.size === 0 && handOverrides.size === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Click a notehead to open the note toolbox. Hold Command
                  (Control on Windows) and click more to build a set: a finger
                  number, a beam break, a move to the other staff or a deletion
                  then applies to the whole set at once.
                </Typography>
              ) : (
                <>
                  <Typography variant="body2" color="text.secondary">
                    {hiddenNotes.size > 0
                      ? `${hiddenNotes.size} note${hiddenNotes.size === 1 ? "" : "s"} off the page`
                      : null}
                    {hiddenNotes.size > 0 && handOverrides.size > 0
                      ? " \u00b7 "
                      : null}
                    {handOverrides.size > 0
                      ? `${handOverrides.size} note${
                          handOverrides.size === 1 ? "" : "s"
                        } moved to the other staff`
                      : null}
                    . The recording still has every one of them.
                  </Typography>
                  {hiddenNotes.size > 0 ? (
                    <Button
                      size="small"
                      onClick={() => setHiddenNotes(new Set())}
                    >
                      Bring them all back
                    </Button>
                  ) : null}
                  {handOverrides.size > 0 ? (
                    <Button
                      size="small"
                      onClick={() => setHandOverrides(new Map())}
                    >
                      Undo every move
                    </Button>
                  ) : null}
                </>
              )}
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
      >
        <Stack spacing={1.5}>
          {/*
            One pill per thing this stretch can carry, and only that thing's controls below it.

            The panel used to show every control at once with a paragraph explaining each — which
            made the common case, changing one setting, a page of reading. A pill wears the accent
            colour when this stretch already carries that setting, so what has been edited here is
            visible before anything is opened.
          */}
          <Stack direction="row" spacing={1}>
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
          </Stack>

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
              {(["left", "right"] as const).map((side) => {
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
                    <Typography variant="body2" sx={{ minWidth: 34 }}>
                      {side === "left" ? "L" : "R"}
                    </Typography>
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
                          // Touching a chip is the reader deciding, and a decision outlasts every
                          // redraw: from here on the suggestion never writes over this piece.
                          decidedOttavasFor.current = SAVED_OTTAVAS;
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
                    <IconButton
                      size="small"
                      color="error"
                      title="Remove the bracket on this hand"
                      disabled={!range || !active}
                      onClick={() => {
                        if (!range) return;
                        decidedOttavasFor.current = SAVED_OTTAVAS;
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

          <Divider />
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => void save()}
              disabled={!selected || saving}
              startIcon={saving ? <CircularProgress size={14} /> : undefined}
            >
              Save with the piece
            </Button>
            {savedNote ? (
              <Typography variant="caption" color="text.secondary">
                {savedNote}
              </Typography>
            ) : null}
          </Stack>
        </Stack>
      </ToolboxDialog>

      <ToolboxDialog
        open={notesToolbox && selectedNotes.length > 0}
        title={
          selectedNotes.length === 1 ? "Note" : `${selectedNotes.length} notes`
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
      >
        <Stack spacing={1.5}>
          <Typography variant="body2" color="text.secondary">
            {selectedNotes.length === 1
              ? "Hold Command (Control on Windows) and click more noteheads to build a set."
              : oneChord
                ? "One chord. Numbers pressed here are read low to high against the noteheads low to high."
                : "Everything below applies to the whole set at once."}
          </Typography>

          <Divider textAlign="left">
            <Typography variant="caption" color="text.secondary">
              Fingering
            </Typography>
          </Divider>
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: "center", flexWrap: "wrap" }}
          >
            <ButtonGroup size="small">
              {FINGERS.map((finger) => (
                <Button
                  key={finger}
                  variant={
                    pickedFingers.includes(finger) ? "contained" : "outlined"
                  }
                  onClick={() => pressFinger(finger)}
                  data-finger={finger}
                >
                  {finger}
                </Button>
              ))}
            </ButtonGroup>
            <Button
              size="small"
              disabled={
                !selectedNotes.some((noteKey) => fingers[noteKey] !== undefined)
              }
              onClick={() => {
                setFingerDraft({ forSelection: selectionKey, picked: [] });
                applyFingers([], selectedNotes, oneChord);
              }}
            >
              Clear
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {oneChord
              ? `Press one number to give it to all ${oneChord.length} noteheads, or press ${oneChord.length} of them to give each note its own \u2014 they print stacked over the chord, lowest at the bottom.`
              : "One number, on every note picked. Several at once only mean something on a single chord, where they can be read against the noteheads in order."}
          </Typography>

          <Divider textAlign="left">
            <Typography variant="caption" color="text.secondary">
              Hand
            </Typography>
          </Divider>
          <Typography variant="caption" color="text.secondary">
            The split is worked out by an algorithm that cannot see your hands.
            Where it is wrong, say so — the matrix is not touched and the note
            can come back at any time.
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              disabled={selectedNotes.every(
                (noteKey) => handOf(noteKey) === "right",
              )}
              onClick={() => moveSelected("right")}
            >
              Play with the right hand
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={selectedNotes.every(
                (noteKey) => handOf(noteKey) === "left",
              )}
              onClick={() => moveSelected("left")}
            >
              Play with the left hand
            </Button>
          </Stack>

          <Divider textAlign="left">
            <Typography variant="caption" color="text.secondary">
              Beam
            </Typography>
          </Divider>
          <Button
            size="small"
            variant="outlined"
            disabled={
              selectedChords.partial.length > 0 ||
              selectedChords.whole.length === 0
            }
            onClick={toggleBeamBreak}
          >
            {selectedChords.whole.length > 0 &&
            selectedChords.whole.every((key) => beamBreaks.has(key))
              ? "Join the beam again"
              : "Start a new beam here"}
          </Button>
          <Typography variant="caption" color="text.secondary">
            {selectedChords.partial.length > 0
              ? `A beam holds a whole chord, so it can only be cut in front of all of it. Pick the rest of the notes at ${selectedChords.partial
                  .map((key) => `f${key.split(":")[1]}`)
                  .join(", ")} as well.`
              : "The beam is cut in front of these notes, and a new group runs on from them."}
          </Typography>

          {selectedNotes.length === 1 && selectedNote ? (
            <>
              <Divider textAlign="left">
                <Typography variant="caption" color="text.secondary">
                  Figure
                </Typography>
              </Divider>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <TextField
                  select
                  size="small"
                  label="Draw this note as"
                  value={overrides[figureKeyOf(selectedNote)] ?? ""}
                  onChange={(event) =>
                    setOverrides((current) => ({
                      ...current,
                      [figureKeyOf(selectedNote)]: event.target
                        .value as FigureName,
                    }))
                  }
                  sx={{ minWidth: 200 }}
                >
                  {ALL_FIGURES.map((name) => (
                    <MenuItem key={name} value={name}>
                      {FIGURE_LABELS[name]}
                    </MenuItem>
                  ))}
                </TextField>
                {overrides[figureKeyOf(selectedNote)] ? (
                  <Button
                    size="small"
                    onClick={() =>
                      setOverrides((current) => {
                        const next = { ...current };
                        delete next[figureKeyOf(selectedNote)];
                        return next;
                      })
                    }
                  >
                    Undo
                  </Button>
                ) : null}
              </Stack>
            </>
          ) : null}

          <Divider />
          <Button
            size="small"
            color="error"
            variant="outlined"
            onClick={hideSelected}
          >
            Take{" "}
            {selectedNotes.length === 1
              ? "this note"
              : `these ${selectedNotes.length} notes`}{" "}
            off the page
          </Button>
          <Typography variant="caption" color="text.secondary">
            The recording keeps them. Only the drawing stops asking for them,
            and the undo is under the sheet.
          </Typography>
        </Stack>
      </ToolboxDialog>
    </PageContainer>
  );
}

export default RhythmPage;
