/**
 * The Sheet step with the new sheet (implementation 03, Phase 5): the sheet the backend draws without compases,
 * to see and to hear. It is what `SheetPage` shows first on the Sheet step, a version of My library and in Play
 * mode; the old vexflow-v2 sheet stays one press away for editing until Phase 8 (`onOldSheet`).
 *
 * - **At once**: the sheet as it is now: the AI's (Sonnet 5.5 today), or the algorithm's on a part it has not
 *   enhanced. A sheet the AI enhanced carries the green badge **Enhanced with AI** for good, whatever changes later
 *   (the user's rule of 2026-10-25): a new run is then **Enhance it again with AI**, at the user's own risk of the
 *   same result. The page says "AI", not the model's name: the model may change.
 * - **The AI in the background** (plan section 3.6): a new transcription is sent by itself; any other part offers
 *   **Enhance with AI** (on a version of My library, the button opens the copy that edits it, as **Edit** does,
 *   and starts there). The segment at the AI looks pale, a segment that comes back appears column by column, and
 *   no text says any of it. The old sheet cannot be opened while the AI writes: the segments still waiting cannot
 *   be edited.
 * - **To hear**: the recording plays with a cursor, the notes it reaches lit, and a click on the sheet moves the
 *   recording there.
 * - **To edit** (Phase 6): notes are picked on the sheet (a click, ⌘ or Shift to add, a box dragged across the
 *   staves) and the note toolbox opens beside them; its **Hand** writes the hand into the notes, and the sheet comes
 *   back drawn again. **Undo** and **Redo** (the floating bar, ⌘Z and ⇧⌘Z) walk the part's steps, which the backend
 *   keeps (`part_sheet.edits`): they survive a reload. Nothing can be changed while the AI writes the sheet.
 * - **The tools** (Phase 7): the note toolbox has every row of the old one that the new sheet keeps (figures,
 *   fingers, hand, beams, the grace note switch, ornaments, taking notes off the page: Delete); a stretch marked in
 *   the strip above the staves opens the range toolbox (**Both / Right / Left**, Key, Clef, Octave). Either selection
 *   hands over to the other from its title bar, and either one can be sent to the AI with the user's own words
 *   (**Enhance with AI**: the stretch gets the pale veil while the AI writes it, then appears column by column).
 * - **The sheet toolbox** (Phase 8): Title, Key, Transpose (notes and figures, with their preview), Lyrics (the
 *   words pasted and the pool, whose pieces are dragged onto the sheet) and View (zoom, space between lines). A
 *   click on a lyrics piece on the sheet picks it and opens the lyrics toolbox beside it (Phase 8A++, the user's
 *   request: its words, font, size, bold and italic); the block is moved and resized on the sheet itself, and the
 *   bar of its frames in the strip says when it sounds. **Print to PDF**; and in
 *   the `⋯` the keyboard panel (the keys sounding under the cursor; a click takes a note off or adds one). The note
 *   toolbox has a keyboard of its own for the picked column (the user's request): a key adds a note to the chord (the
 *   note added is then the one picked) or takes one off, and ⌘ and a click on a lit key picks that note or lets it go,
 *   so **Hand** moves only the notes picked.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesomeOutlined";
import EditNoteIcon from "@mui/icons-material/EditNoteOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PianoIcon from "@mui/icons-material/PianoOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PrintIcon from "@mui/icons-material/PrintOutlined";
import RedoIcon from "@mui/icons-material/RedoOutlined";
import TuneIcon from "@mui/icons-material/TuneOutlined";
import UndoIcon from "@mui/icons-material/UndoOutlined";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import {
  sheetApi,
  type FramesSheet,
  type LyricLine,
  type ReadingEdit,
  type SheetNote,
  type SheetPreview,
  type StretchRequest,
} from "../../../../api";
import ScorePlayer, { type ScorePlayerControls } from "../../../../components/time/ScorePlayer";
import { useElementSize } from "../../../../hooks/useElementSize";
import { noteName } from "../../../../music/noteNames";
import { intervalWords } from "../../../../music/transpose";
import { ConfirmDialog, FloatingBar, IconAction, Pill, PillButton, RowMenu, semantic } from "../../../../ui";
import { piecesIn } from "../lyricsPieces";
import { PianoToolbox } from "../PianoToolboxes";
import { HAND_COLOUR, HELD_COLOUR, type SoundingNote } from "../sheetConstants";
import type { SheetStep } from "../SheetPage";
import { besideOnScreen, clearOfRange, firstLineBoxOf, screenBoxOf } from "../toolboxPlacement";
import { EnhanceStretchDialog } from "./EnhanceStretchDialog";
import { FramesLyricsToolbox } from "./FramesLyricsToolbox";
import { FramesNoteToolbox } from "./FramesNoteToolbox";
import { FramesRangeToolbox, type RangeHand } from "./FramesRangeToolbox";
import { FramesSheetView, type MarkedRange, type PickHow } from "./FramesSheetView";
import { FramesPdfDialog } from "./FramesPdfDialog";
import { FramesPreviewDialog } from "./FramesPreviewDialog";
import { FramesSheetToolbox, MAX_ZOOM, MIN_ZOOM, type FramesSheetTab } from "./FramesSheetToolbox";
import { placeAt, steadyColumns } from "./geometry";
import { frameOf, handForKey, midiOf, oneColumn } from "./readingTools";
import { ENHANCE_WITH_AI } from "./navigation";
import { useFramesLyrics } from "./useFramesLyrics";
import { useFramesSheet } from "./useFramesSheet";

/** The size the sheet is drawn at: about the old sheet's (8 px a staff space at the Sheet step's width). */
const PX_PER_SPACE = 8.5;
/** The SVG adds this much margin to the staff width, in staff spaces. */
const MARGINS = 8;
/** The width asked for moves in steps of this many staff spaces, so a small resize draws nothing again. */
const WIDTH_STEP = 4;
/** The zoom of the page is kept in this browser (it is how the page is looked at, not part of the sheet). */
const ZOOM_KEY = "aitu.framesSheet.zoom";
/** The lyrics toolbox keeps this many pixels clear on each side of the blocks it opens for. */
const BLOCK_ROOM = 120;

function rememberedZoom(): number {
  try {
    const value = Number(window.localStorage.getItem(ZOOM_KEY));
    return value >= MIN_ZOOM && value <= MAX_ZOOM ? value : 1;
  } catch {
    return 1;
  }
}

/** A transposition waiting in its preview for **Transpose** or **Cancel**. */
interface Previewing {
  kind: "notes" | "figures";
  /** Semitones (notes) or steps (figures: positive is shorter). */
  value: number;
  title: string;
  facts: string[];
  preview: SheetPreview | null;
  error: string | null;
}

export function FramesSheetPage({ step, onOldSheet }: { step: SheetStep; onOldSheet: () => void }) {
  const audioUuid = step.audioUuid;
  const playView = step.play ?? null;
  const playMode = playView !== null;
  const readOnly = (step.readOnly ?? false) || playMode;
  const navigate = useNavigate();
  const location = useLocation();

  const [sizeRef, size] = useElementSize<HTMLDivElement>();
  const [zoom, setZoomNow] = useState(rememberedZoom);
  const setZoom = useCallback((next: number) => {
    setZoomNow(next);
    try {
      window.localStorage.setItem(ZOOM_KEY, String(next));
    } catch {
      // A browser that keeps nothing: the zoom lasts for this page.
    }
  }, []);
  const width = useMemo(() => {
    if (size.width <= 0) return null;
    const spaces = size.width / (PX_PER_SPACE * zoom) - MARGINS;
    return Math.min(320, Math.max(60, Math.round(spaces / WIDTH_STEP) * WIDTH_STEP));
  }, [size.width, zoom]);

  const { sheet, error, run, starting, edit, editing, editError, enhanceStretch, notice } = useFramesSheet(audioUuid, width, {
    autoStart: !readOnly,
    onChanged: step.onChanged,
  });

  // The title lines of the sheet toolbox (Phase 8; the old sheet's Title tab was never used: none to carry over).
  const titles = sheet?.titles ?? {};
  const title = titles.title || step.label || "Untitled";
  const underTitle = [titles.subtitle, titles.artist].filter(Boolean).join(" · ");

  // ------------------------------------------------------------------ the recording

  const ownPlayer = useRef<ScorePlayerControls | null>(null);
  // Play mode plays this sheet from its own button and keys: the player fills its handle directly.
  const player = playView?.playerRef ?? ownPlayer;
  const [seconds, setSeconds] = useState<number | null>(0);
  const [playing, setPlaying] = useState(false);
  const [openedAtRevision] = useState(step.audioRevision);
  const onPlayTime = playView?.onTime;
  const reportTime = useCallback(
    (now: number | null) => {
      setSeconds(now);
      onPlayTime?.(now);
    },
    [onPlayTime],
  );
  const onPlayPlaying = playView?.onPlaying;
  const reportPlaying = useCallback(
    (now: boolean) => {
      setPlaying(now);
      onPlayPlaying?.(now);
    },
    [onPlayPlaying],
  );
  const onPlaySeek = playView?.onSeek;
  const seek = (to: number) => {
    player.current?.seek(to);
    onPlaySeek?.();
  };
  // A stretch of a playlist starts where it was chosen.
  const fromMs = playView?.fromMs ?? null;
  const [startedAt, setStartedAt] = useState<string | null>(null);
  useEffect(() => {
    if (!sheet || fromMs === null || startedAt === `${audioUuid}:${fromMs}`) return;
    const wait = window.setTimeout(() => {
      player.current?.seek(fromMs / 1000);
      setStartedAt(`${audioUuid}:${fromMs}`);
    }, 120);
    return () => window.clearTimeout(wait);
  }, [sheet, fromMs, startedAt, audioUuid, player]);

  // ------------------------------------------------------------------ the AI

  const running = sheet?.llm.state === "running" || starting;
  const enhanced = sheet?.llm.enhanced === true;
  const runs = sheet?.llm.runs ?? 0;
  const viaEdit = sheet?.llm.viaEdit === true && step.enhanceInCopy !== undefined;
  const offerAi = !playMode && !running && (sheet?.llm.canRun === true || viaEdit);
  const enhanceLabel = enhanced ? "Enhance it again with AI" : "Enhance with AI";
  const [asking, setAsking] = useState(false);
  const enhance = () => {
    setAsking(false);
    if (sheet?.llm.canRun) void run();
    else step.enhanceInCopy?.();
  };
  // The edit copy opened by **Enhance with AI** on a version of My library: the AI starts here.
  const askedInCopy = (location.state as typeof ENHANCE_WITH_AI | null)?.enhanceWithAi === true;
  useEffect(() => {
    if (!askedInCopy || !sheet) return;
    navigate(location.pathname, { replace: true, state: null });
    if (sheet.llm.canRun) void run();
  }, [askedInCopy, sheet, navigate, location.pathname, run]);

  // ------------------------------------------------------------------ editing (Phase 6)

  const canEdit = !readOnly && sheet !== null;
  const locked = !sheet || sheet.editable ? null : running ? "The AI is enhancing this sheet" : "This sheet cannot be changed here";
  const notes = useMemo(() => new Map<string, SheetNote>((sheet?.notes ?? []).map((note) => [note.ref, note])), [sheet?.notes]);
  const [pick, setPick] = useState<{ uuid: string; refs: string[] }>({ uuid: audioUuid, refs: [] });
  // The notes picked that the sheet still holds (an edit may drop a note: two of one key and column in one hand).
  const picked = useMemo(
    () => (pick.uuid === audioUuid ? pick.refs.filter((ref) => notes.has(ref)) : []),
    [pick, audioUuid, notes],
  );
  const pickedSet = useMemo(() => new Set(picked), [picked]);
  // The toolbox opens beside the notes, measured when a pick starts (it is dragged after that).
  const [toolboxAt, setToolboxAt] = useState<{ x: number; y: number } | undefined>(undefined);
  // The stretch marked in the strip above the staves (Phase 7): one selection at a time, notes or a stretch.
  const [mark, setMark] = useState<{ uuid: string; range: MarkedRange } | null>(null);
  const range = mark && mark.uuid === audioUuid ? mark.range : null;
  const [rangeHand, setRangeHand] = useState<RangeHand>("both");
  const [rangeAt, setRangeAt] = useState<{ x: number; y: number } | undefined>(undefined);
  // The range toolbox opens to the left of where the stretch starts (the old sheet's place), measured once the band
  // is drawn (two frames later).
  // What the stretch's handler reads of the Lyrics tab, declared below (the handler is made once per stretch).
  const lyricsModeRef = useRef(false);
  const lyricsPickRef = useRef<(starts: number[]) => void>(() => undefined);
  const lyricsLinesRef = useRef<readonly LyricLine[]>([]);
  const placeRange = useCallback(() => {
    window.requestAnimationFrame(() =>
      window.requestAnimationFrame(() => setRangeAt(clearOfRange(firstLineBoxOf("[data-frames-sheet] [data-range-band]")))),
    );
  }, []);
  const onRange = useCallback(
    (next: MarkedRange) => {
      if (lyricsModeRef.current) {
        // In the Lyrics tab a stretch picks every lyrics piece over it, as on the old sheet.
        lyricsPickRef.current(piecesIn(lyricsLinesRef.current, { fromColumn: next.start, toColumn: next.end }));
        return;
      }
      if (!range) placeRange();
      setMark({ uuid: audioUuid, range: next });
      setPick({ uuid: audioUuid, refs: [] });
      lyricsPickRef.current([]);
    },
    [audioUuid, range, placeRange],
  );

  const onPick = useCallback(
    (refs: string[], how: PickHow) => {
      if (picked.length === 0 && refs.length > 0) {
        setToolboxAt(besideOnScreen(screenBoxOf(refs.map((ref) => `[data-frames-sheet] [data-note~="${ref}"]`).join(","))));
      }
      if (refs.length > 0) {
        setMark(null);
        lyricsPickRef.current([]);
      }
      setPick((current) => {
        const now = current.uuid === audioUuid ? current.refs : [];
        if (how === "only") return { uuid: audioUuid, refs: [...new Set(refs)] };
        // ⌘ or Shift on notes already picked takes them away, as in the old sheet.
        const all = refs.every((ref) => now.includes(ref));
        return { uuid: audioUuid, refs: all ? now.filter((ref) => !refs.includes(ref)) : [...new Set([...now, ...refs])] };
      });
    },
    [audioUuid, picked.length],
  );
  const unpick = useCallback(() => setPick({ uuid: audioUuid, refs: [] }), [audioUuid]);
  const unmark = useCallback(() => setMark(null), []);

  const moveHand = (hand: SheetNote["hand"]) => {
    if (width === null || picked.length === 0) return;
    void edit(() => sheetApi.moveHands(audioUuid, picked, hand, width));
  };
  const apply = useCallback(
    async (change: ReadingEdit) => {
      if (width === null) return false;
      return (await edit(() => sheetApi.read(audioUuid, change, width))) !== null;
    },
    [width, edit, audioUuid],
  );
  /** Something asked of the lyrics could not be done: said once, in words, at the foot of the window. */
  const [refused, setRefused] = useState<string | null>(null);
  const editNotes = (change: Omit<ReadingEdit, "notes">) => {
    if (picked.length > 0) void apply({ ...change, notes: picked });
  };
  const editRange = (change: Omit<ReadingEdit, "start" | "end">) => {
    if (range) void apply({ staff: rangeHand, ...change, start: range.start, end: range.end });
  };

  // ------------------------------------------------------------------ the sheet toolbox (Phase 8)

  const [toolboxOpen, setToolboxOpen] = useState(false);
  const [toolboxTab, setToolboxTab] = useState<FramesSheetTab>("title");
  const lyrics = useFramesLyrics(audioUuid, sheet, apply, setRefused);
  // The lyrics toolbox opens beside the piece clicked (Phase 8A++); one selection at a time: notes, a stretch or lyrics.
  const [lyricsAt, setLyricsAt] = useState<{ x: number; y: number } | undefined>(undefined);
  /** Beside the blocks with room around them: a block is moved and widened there, and its handles must stay free. */
  const besideBlocks = (starts: readonly number[]) => {
    const box = screenBoxOf(starts.map((start) => `[data-frames-sheet] [data-lyric][data-start="${start}"]`).join(","));
    return besideOnScreen(box && new DOMRect(box.left - BLOCK_ROOM, box.top, box.width + 2 * BLOCK_ROOM, box.height));
  };
  const lyricsMode = toolboxOpen && toolboxTab === "lyrics";
  const pickedLyrics = useMemo(() => new Set(lyrics.picked), [lyrics.picked]);
  useEffect(() => {
    lyricsModeRef.current = lyricsMode;
    lyricsPickRef.current = (starts) => {
      if (starts.length > 0 && lyrics.picked.length === 0) {
        setLyricsAt(besideBlocks(starts));
      }
      if (starts.length > 0 || lyrics.picked.length > 0) lyrics.setPicked(starts);
    };
    lyricsLinesRef.current = lyrics.lines;
  }, [lyricsMode, lyrics]);
  const pickLyric = useCallback(
    (start: number, add: boolean) => {
      if (lyrics.picked.length === 0) {
        setLyricsAt(besideBlocks([start]));
      }
      setPick({ uuid: audioUuid, refs: [] });
      setMark(null);
      lyrics.setPicked((now) => (add ? (now.includes(start) ? now.filter((one) => one !== start) : [...now, start]) : [start]));
    },
    [lyrics, audioUuid, setLyricsAt],
  );
  const unpickLyrics = useCallback(() => lyrics.setPicked([]), [lyrics]);

  // Transpose, with its preview: nothing is written until **Transpose**.
  const [previewing, setPreviewing] = useState<Previewing | null>(null);
  const [confirming, setConfirming] = useState(false);
  const previewNotes = (semitones: number) => {
    if (width === null) return;
    setPreviewing({ kind: "notes", value: semitones, title: `Transpose the notes: ${intervalWords(semitones).toLowerCase()}`, facts: [], preview: null, error: null });
    sheetApi
      .transpose(audioUuid, semitones, width, true)
      .then((found) =>
        setPreviewing((now) =>
          now && now.kind === "notes" && now.value === semitones
            ? {
                ...now,
                preview: found,
                facts: found.outside
                  ? [`${found.outside} note${found.outside === 1 ? "" : "s"} would leave the keyboard: taken off the page.`]
                  : [],
              }
            : now,
        ),
      )
      .catch((caught: unknown) =>
        setPreviewing((now) => (now ? { ...now, error: caught instanceof Error ? caught.message : "The preview could not be drawn." } : now)),
      );
  };
  const previewFigures = (steps: number) => {
    if (width === null || steps === 0) return;
    const k = Math.abs(steps);
    setPreviewing({
      kind: "figures",
      value: steps,
      title: `Transpose the figures: every figure ${k} step${k === 1 ? "" : "s"} ${steps > 0 ? "shorter" : "longer"}`,
      facts: ["No note moves: the figures are named again."],
      preview: null,
      error: null,
    });
    sheetApi
      .previewRead(audioUuid, { action: "figures", value: steps }, width)
      .then((found) => setPreviewing((now) => (now && now.kind === "figures" && now.value === steps ? { ...now, preview: found } : now)))
      .catch((caught: unknown) =>
        setPreviewing((now) => (now ? { ...now, error: caught instanceof Error ? caught.message : "The preview could not be drawn." } : now)),
      );
  };
  const confirmPreview = async () => {
    if (!previewing || width === null) return;
    setConfirming(true);
    const done =
      previewing.kind === "notes"
        ? (await edit(() => sheetApi.transpose(audioUuid, previewing.value, width))) !== null
        : await apply({ action: "figures", value: previewing.value });
    setConfirming(false);
    if (done) setPreviewing(null);
  };

  // The keyboard panel: the keys sounding under the cursor; a click takes one off, or adds one to a hand.
  const [pianoOpen, setPianoOpen] = useState(false);
  const [addHand, setAddHand] = useState<SheetNote["hand"]>("right");
  const steady = useMemo(() => steadyColumns(sheet?.columns ?? []), [sheet?.columns]);
  const cursorAt = sheet && seconds !== null ? placeAt(steady, sheet.systems, seconds * 1000) : null;
  const cursorFrame = cursorAt && cursorAt.column >= 0 ? (steady[cursorAt.column]?.frame ?? null) : null;
  const sounding = useMemo(() => {
    if (!sheet || cursorFrame === null) return [] as (SoundingNote & { ref: string; end: number })[];
    return sheet.notes
      .filter((note) => {
        const frame = frameOf(note.ref);
        return frame === cursorFrame || (frame < cursorFrame && (note.end ?? frame) > cursorFrame);
      })
      .map((note) => ({
        row: Number(note.ref.split(":")[1]) - 21,
        hand: note.hand,
        onsetFrame: frameOf(note.ref),
        ref: note.ref,
        end: note.end ?? frameOf(note.ref) + 1,
      }));
  }, [sheet, cursorFrame]);
  const soundingColours = useMemo(() => {
    const out: Record<number, string> = {};
    for (const note of sounding) out[note.row] = note.onsetFrame === cursorFrame ? HAND_COLOUR[note.hand] : HELD_COLOUR[note.hand];
    return out;
  }, [sounding, cursorFrame]);
  const pressKey = (row: number) => {
    if (width === null || cursorFrame === null) return;
    const lit = sounding.find((note) => note.row === row);
    if (lit) {
      void edit(() => sheetApi.remove(audioUuid, [lit.ref], width));
      return;
    }
    // The length that hand is already holding there, as on the old sheet.
    const held = sounding.find((note) => note.hand === addHand);
    void edit(() =>
      sheetApi.addNote(
        audioUuid,
        { frame: cursorFrame, midi: row + 21, hand: addHand, ...(held ? { lengthMs: (held.end - held.onsetFrame) * 40 } : {}) },
        width,
      ),
    );
  };

  // The keyboard of the note toolbox (the user's requests of 2026-10-26): the picked column's chord, key by key.
  /**
   * After a key: the notes still picked (the one added alone, so **Hand** applies to it at once), found again a frame
   * or two away when the column moved (its first note was taken off); when none of them is left, the notes of those
   * hands still in the column.
   */
  const repick = (answer: FramesSheet, column: number, refs: readonly string[], hands: ReadonlySet<SheetNote["hand"]>) => {
    const there = new Set(answer.notes.map((note) => note.ref));
    for (const near of [0, -1, 1, -2, 2]) {
      const found = refs.map((ref) => `${column + near}:${midiOf(ref)}`).filter((ref) => there.has(ref));
      if (found.length > 0) return setPick({ uuid: audioUuid, refs: found });
    }
    for (const near of [0, -1, 1, -2, 2]) {
      const found = answer.notes.filter((note) => frameOf(note.ref) === column + near && hands.has(note.hand));
      if (found.length > 0) return setPick({ uuid: audioUuid, refs: found.map((note) => note.ref) });
    }
    setPick({ uuid: audioUuid, refs: [] });
  };
  const pressChordKey = (midi: number, add: boolean) => {
    const pickedNotes = picked.map((ref) => notes.get(ref)).filter((note): note is SheetNote => note !== undefined);
    const column = oneColumn(pickedNotes);
    if (width === null || !sheet || column === null) return;
    const here = sheet.notes.filter((note) => frameOf(note.ref) === column);
    const hands = new Set(pickedNotes.map((note) => note.hand));
    const lit = here.find((note) => midiOf(note.ref) === midi);
    if (lit && add) {
      // ⌘ and a click picks that note or lets it go: the keyboard picks within its chord, as ⌘ on the sheet does.
      // The last note picked stays (the toolbox would close).
      const kept = picked.includes(lit.ref) ? picked.filter((ref) => ref !== lit.ref) : [...picked, lit.ref];
      if (kept.length > 0) setPick({ uuid: audioUuid, refs: kept });
      return;
    }
    if (lit) {
      void edit(() => sheetApi.remove(audioUuid, [lit.ref], width)).then((answer) => {
        if (answer) repick(answer, column, picked.filter((ref) => ref !== lit.ref), hands);
      });
      return;
    }
    // In the picked hand, as long as that hand's chord here.
    const hand = handForKey(midi, pickedNotes, here);
    const ends = here.filter((note) => note.hand === hand && note.end != null).map((note) => note.end!);
    const lengthMs = ends.length > 0 ? (Math.max(...ends) - column) * 40 : undefined;
    void edit(() => sheetApi.addNote(audioUuid, { frame: column, midi, hand, ...(lengthMs ? { lengthMs } : {}) }, width)).then(
      (answer) => {
        if (answer) repick(answer, column, [`${column}:${midi}`], new Set([hand]));
      },
    );
  };

  const [pdfOpen, setPdfOpen] = useState(false);
  const removePicked = useCallback(() => {
    if (width === null || picked.length === 0) return;
    void edit(() => sheetApi.remove(audioUuid, picked, width)).then((done) => {
      if (done) setPick({ uuid: audioUuid, refs: [] });
    });
  }, [width, picked, edit, audioUuid]);

  /** The frames the picked notes cover: from the first one to the column after the last one. */
  const framesOfPicked = (): MarkedRange | null => {
    if (!sheet || picked.length === 0) return null;
    const frames = picked.map(frameOf);
    const start = Math.min(...frames);
    const last = Math.max(...frames);
    const next = sheet.columns.find((column) => column.frame > last);
    return { start, end: next ? next.frame : last + 1 };
  };
  const pickedHands = new Set(picked.map((ref) => notes.get(ref)?.hand).filter(Boolean));
  const selectFrames = () => {
    const next = framesOfPicked();
    if (!next) return;
    setRangeHand(pickedHands.size === 1 ? ([...pickedHands][0] as RangeHand) : "both");
    setPick({ uuid: audioUuid, refs: [] });
    placeRange();
    setMark({ uuid: audioUuid, range: next });
  };
  const selectNotes = () => {
    if (!range || !sheet) return;
    const refs = sheet.notes
      .filter((note) => {
        const frame = frameOf(note.ref);
        return frame >= range.start && frame < range.end && (rangeHand === "both" || note.hand === rangeHand);
      })
      .map((note) => note.ref);
    setMark(null);
    setToolboxAt(besideOnScreen(screenBoxOf(refs.map((ref) => `[data-frames-sheet] [data-note~="${ref}"]`).join(","))));
    setPick({ uuid: audioUuid, refs });
  };

  // **Enhance with AI** of one stretch, with the user's words (plan task 7.5).
  const aiHere = sheet?.llm.canRun === true;
  const [asked, setAsked] = useState<{ stretch: Omit<StretchRequest, "instruction">; what: string } | null>(null);
  const askNotes = () => {
    const stretch = framesOfPicked();
    if (!stretch) return;
    const what = picked.length === 1 ? "this note" : `these ${picked.length} notes`;
    setAsked({ stretch: { ...stretch, staff: "both", notes: picked }, what });
  };
  const askRange = () => {
    if (!range) return;
    const what = rangeHand === "both" ? "this stretch" : `this stretch of the ${rangeHand} hand`;
    setAsked({ stretch: { ...range, staff: rangeHand }, what });
  };
  const sendStretch = (instruction: string) => {
    if (!asked) return;
    const stretch = asked.stretch;
    setAsked(null);
    unpick();
    unmark();
    void enhanceStretch({ ...stretch, instruction });
  };
  const history = sheet?.history ?? { undo: null, redo: null };
  const walk = useCallback(
    (to: "undo" | "redo") => {
      if (width === null || !sheet?.editable || !(to === "undo" ? sheet.history.undo : sheet.history.redo)) return;
      void edit(() => sheetApi.walk(audioUuid, to, width));
    },
    [width, sheet, edit, audioUuid],
  );

  // ⌘Z, ⇧⌘Z (and Control-Z, Control-Y), and Escape to drop the pick. A text field keeps its own keys.
  useEffect(() => {
    if (!canEdit) return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
      if (event.key === "Escape") {
        unpick();
        unmark();
        unpickLyrics();
        return;
      }
      if ((event.key === "Delete" || event.key === "Backspace") && !(event.metaKey || event.ctrlKey)) {
        if (lyrics.picked.length > 0 && sheet?.editable && !editing) {
          event.preventDefault();
          lyrics.removePicked();
          return;
        }
        if (picked.length > 0 && sheet?.editable && !editing) {
          event.preventDefault();
          removePicked();
        }
        return;
      }
      if (!(event.metaKey || event.ctrlKey)) return;
      const pressed = event.key.toLowerCase();
      const wants = pressed === "z" ? (event.shiftKey ? "redo" : "undo") : pressed === "y" ? "redo" : null;
      if (!wants) return;
      event.preventDefault();
      walk(wants);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canEdit, walk, unpick, unmark, unpickLyrics, picked.length, sheet?.editable, editing, removePicked, lyrics]);

  // A blank sheet (From scratch): the old page has its empty state, with Record a passage and Paste.
  const empty = sheet !== null && sheet.columns.length === 0;
  useEffect(() => {
    if (empty && !playMode) onOldSheet();
  }, [empty, playMode, onOldSheet]);

  const scoreSeconds = sheet && sheet.columns.length > 0 ? sheet.columns[sheet.columns.length - 1].ms / 1000 + 1 : 1;

  return (
    <Box data-sheet-page data-sheet-engine="frames">
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      {editError ? (
        <Alert severity="warning" sx={{ mb: 2 }} data-edit-error>
          {editError}
        </Alert>
      ) : null}
      {notice ? (
        <Alert severity="info" sx={{ mb: 2 }} data-sheet-notice>
          {notice}
        </Alert>
      ) : null}
      <Stack spacing={1.5}>
        {playMode ? null : (
          <Box sx={{ px: 1 }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", minWidth: 0 }}>
              <Typography component="h2" sx={{ fontSize: 20, fontWeight: 600, lineHeight: 1.3, minWidth: 0 }} noWrap title={title} data-sheet-title>
                {title}
              </Typography>
              {enhanced ? (
                <Box data-enhanced-badge sx={{ flexShrink: 0 }}>
                  <Pill
                    label="Enhanced with AI"
                    selected
                    color={semantic.status.success}
                    title={runs > 1 ? `The AI enhanced this sheet ${runs} times` : "The AI enhanced this sheet"}
                  />
                </Box>
              ) : null}
            </Stack>
            {underTitle ? (
              <Typography variant="body2" color="text.secondary" noWrap title={underTitle}>
                {underTitle}
              </Typography>
            ) : null}
          </Box>
        )}
        {sheet ? (
          <ScorePlayer
            compact
            audioUuid={audioUuid}
            version={`${openedAtRevision ?? 0}`}
            scoreSeconds={scoreSeconds}
            onTime={reportTime}
            controlsRef={player}
            onPlaying={reportPlaying}
            keys={!playMode}
            headless={playMode}
            stopAt={playView?.toMs != null ? playView.toMs / 1000 : null}
            onEnded={playView?.onEnded}
            preload={playView?.preload ?? "auto"}
          />
        ) : null}
        <Box ref={sizeRef}>
          {sheet ? (
            <FramesSheetView
              sheet={sheet}
              playheadSeconds={seconds}
              follow={playing}
              centre={playMode}
              onSeek={seek}
              selected={canEdit ? pickedSet : undefined}
              onPick={canEdit ? onPick : undefined}
              range={canEdit ? range : null}
              rangeScope={rangeHand}
              onRange={canEdit ? onRange : undefined}
              playing={playing}
              {...(canEdit && sheet.editable
                ? {
                    lyrics: {
                      picked: pickedLyrics,
                      onPick: pickLyric,
                      onUnpick: unpickLyrics,
                      onPlace: (start: number, place: { at: number; dx: number; dy: number }) =>
                        lyrics.shape([start], place, "Move a lyrics block"),
                      onWidth: (start: number, wide: number) => lyrics.shape([start], { width: wide }, "Width of a lyrics block"),
                      onScale: (start: number, size: number, wide: number | null) =>
                        lyrics.shape([start], { size, ...(wide === null ? {} : { width: wide }) }, "Size of a lyrics block"),
                      onFrames: lyrics.setFrames,
                      landing: lyrics.landing,
                      onDropPool: lyrics.dropPool,
                    },
                  }
                : {})}
            />
          ) : !error ? (
            <Box sx={{ display: "grid", placeItems: "center", minHeight: 320 }} data-sheet-loading>
              <CircularProgress size={22} />
            </Box>
          ) : null}
        </Box>
      </Stack>

      {playMode || !sheet ? null : (
        <FloatingBar open label="sheet buttons">
          <IconAction
            title={playing ? "Pause" : "Play"}
            shortcut="Space"
            icon={playing ? <PauseIcon /> : <PlayArrowIcon />}
            onClick={() => player.current?.toggle()}
            placement="top"
          />
          <IconAction title="Print to PDF" icon={<PrintIcon />} onClick={() => setPdfOpen(true)} placement="top" data-testid="sheet-print" />
          {readOnly ? null : (
            <>
              <IconAction
                title={history.undo ? `Undo: ${history.undo}` : "Undo"}
                shortcut="⌘Z"
                icon={<UndoIcon />}
                onClick={() => walk("undo")}
                disabled={!history.undo || editing || locked !== null}
                disabledTitle={locked ?? "Nothing to undo"}
                placement="top"
                data-testid="sheet-undo"
              />
              <IconAction
                title={history.redo ? `Redo: ${history.redo}` : "Redo"}
                shortcut="⇧⌘Z"
                icon={<RedoIcon />}
                onClick={() => walk("redo")}
                disabled={!history.redo || editing || locked !== null}
                disabledTitle={locked ?? "Nothing to redo"}
                placement="top"
                data-testid="sheet-redo"
              />
              <Divider orientation="vertical" flexItem />
              <IconAction
                title="Sheet toolbox"
                icon={<TuneIcon />}
                onClick={() => setToolboxOpen((open) => !open)}
                active={toolboxOpen}
                placement="top"
                data-testid="sheet-toolbox"
              />
              <RowMenu
                title="More sheet actions"
                items={[
                  {
                    label: pianoOpen ? "Hide the keyboard" : "Show the keyboard",
                    icon: <PianoIcon fontSize="small" />,
                    onClick: () => setPianoOpen((open) => !open),
                  },
                ]}
              />
            </>
          )}
          {offerAi ? (
            <PillButton
              kind="secondary"
              size="small"
              startIcon={<AutoAwesomeIcon fontSize="small" />}
              onClick={() => setAsking(true)}
              data-testid="enhance-with-ai"
            >
              {enhanceLabel}
            </PillButton>
          ) : null}
          <Divider orientation="vertical" flexItem />
          <IconAction
            title={readOnly ? "Open the old sheet (print, copy a stretch)" : "Edit in the old sheet"}
            icon={<EditNoteIcon />}
            onClick={onOldSheet}
            disabled={running}
            disabledTitle="The AI is enhancing this sheet"
            placement="top"
            data-testid="old-sheet"
          />
        </FloatingBar>
      )}

      {canEdit ? (
        <FramesNoteToolbox
          picked={picked}
          notes={notes}
          at={toolboxAt}
          onClose={unpick}
          onMoveHand={moveHand}
          onEdit={editNotes}
          onRemove={removePicked}
          onChordKey={pressChordKey}
          onSelectFrames={selectFrames}
          onEnhance={aiHere ? askNotes : null}
          busy={editing}
          locked={locked}
        />
      ) : null}
      {canEdit && sheet ? (
        <FramesLyricsToolbox
          lines={lyrics.lines}
          pool={lyrics.pool}
          picked={lyrics.picked}
          at={lyricsAt}
          sizeOf={lyrics.sizeOf}
          onClose={unpickLyrics}
          setLines={lyrics.setLines}
          setPool={lyrics.setPool}
          setPicked={lyrics.setPicked}
          onShape={(change, label) => void lyrics.shape(lyrics.picked, change, label)}
          onRefused={setRefused}
          busy={editing}
          locked={locked}
        />
      ) : null}
      {canEdit && sheet && range ? (
        <FramesRangeToolbox
          audioUuid={audioUuid}
          range={range}
          reading={sheet.reading}
          notes={sheet.notes}
          at={rangeAt}
          rangeHand={rangeHand}
          setRangeHand={setRangeHand}
          onClose={unmark}
          onEdit={editRange}
          onSelectNotes={selectNotes}
          onEnhance={aiHere ? askRange : null}
          busy={editing}
          locked={locked}
        />
      ) : null}
      {canEdit && sheet ? (
        <FramesSheetToolbox
          open={toolboxOpen}
          onClose={() => setToolboxOpen(false)}
          tab={toolboxTab}
          onTab={setToolboxTab}
          audioUuid={audioUuid}
          sheet={sheet}
          pieceLabel={step.label}
          onEdit={(change) => void apply(change)}
          busy={editing}
          locked={locked}
          transposing={previewing !== null && previewing.preview === null && previewing.error === null}
          onPreviewNotes={previewNotes}
          onPreviewFigures={previewFigures}
          zoom={zoom}
          setZoom={setZoom}
          lyrics={{
            lines: lyrics.lines,
            pool: lyrics.pool,
            picked: lyrics.picked,
            setLines: lyrics.setLines,
            setPool: lyrics.setPool,
            setPicked: lyrics.setPicked,
            onRefused: setRefused,
            onPoolDrag: lyrics.onPoolDrag,
            pasted: lyrics.pasted,
            setPasted: lyrics.setPasted,
            savedText: lyrics.savedText,
            poolUnsaved: lyrics.poolUnsaved,
            saving: lyrics.saving,
            onSave: (text) => void lyrics.save(text),
          }}
        />
      ) : null}
      {canEdit ? (
        <PianoToolbox
          open={pianoOpen}
          onClose={() => setPianoOpen(false)}
          playheadFrame={cursorFrame}
          frameMs={40}
          addHand={addHand}
          setAddHand={setAddHand}
          addingNote={editing}
          soundingColours={soundingColours}
          soundingNow={sounding}
          onKeyPress={pressKey}
          noteNameAt={(row) => noteName(row + 21)}
        />
      ) : null}
      <FramesPreviewDialog
        open={previewing !== null}
        title={previewing?.title ?? ""}
        facts={previewing?.facts ?? []}
        preview={previewing?.preview ?? null}
        error={previewing?.error ?? null}
        confirming={confirming}
        onConfirm={() => void confirmPreview()}
        onCancel={() => setPreviewing(null)}
      />
      {sheet && !playMode ? (
        <FramesPdfDialog
          open={pdfOpen}
          onClose={() => setPdfOpen(false)}
          audioUuid={audioUuid}
          pieceName={title}
          subtitle={underTitle}
        />
      ) : null}
      <Snackbar
        open={refused !== null}
        autoHideDuration={4000}
        onClose={() => setRefused(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        message={refused}
        data-testid="sheet-refused"
      />
      <EnhanceStretchDialog
        open={asked !== null}
        what={asked?.what ?? "this stretch"}
        onConfirm={sendStretch}
        onCancel={() => setAsked(null)}
      />

      <ConfirmDialog
        open={asking}
        title={enhanced ? "Enhance this sheet again with AI?" : "Enhance this sheet with AI?"}
        message={
          !sheet?.llm.canRun
            ? "This opens a copy in Projects, as Edit does, and the AI enhances it there in a few minutes (about $1 of the monthly credits). Save it to your library when it is done."
            : enhanced
              ? "The AI already enhanced this sheet. A new run may give much the same result, and it uses about $1 of the monthly credits. If it does not finish, the sheet you have now stays."
              : "The AI writes the hands and the reading of the sheet, part by part, in a few minutes. It uses about $1 of the monthly credits. The hands you have now are kept in the history."
        }
        confirmLabel={enhanceLabel}
        onConfirm={enhance}
        onCancel={() => setAsking(false)}
      />
    </Box>
  );
}

export default FramesSheetPage;
