/**
 * Steps 3 and 4, **Notes** and **Hands**: one editor of the piano roll visualization (implementation
 * 08, plan sections 7.1, 9.5 and 9.6; restyled by implementation 02, plan section 10.2: icon actions
 * with tooltips, the primary action on the top row, the hand tools in the floating toolbox). The Notes step is the live transcription and the edits of the rectangles;
 * the Hands step is the same view coloured by hand, with **Predict hands** and the hand tools.
 *
 * **While the piece is transcribed**, the rectangles appear as the engine writes them: the page
 * follows the progress stream of the running job (`status.steps.notes.details.jobId`), the view
 * follows the part already transcribed, and the bar below says how far it is and how long it
 * took. No audio plays. A page opened or reloaded during the transcription receives everything
 * sent so far and continues from there.
 *
 * **When it ends**, the page reads the saved notes once and puts them in place of the streamed
 * ones: the same notes with the same ids, moved by the lag correction measured at the end. Then
 * the audio of the piece can be played under them. The notes are in the time of the piece, and so
 * is the audio file the page plays (once cuts are saved, the backend serves the edited audio), so
 * the moment the playhead touches a rectangle is the moment the note sounds.
 *
 * **The editor.** Every gesture of the canvas (`PianoRollCanvas`) becomes one step of the undo
 * history, as a set of changes on top of the saved notes (`notes/noteEdits.ts`). Nothing is written
 * before **Save**, which sends the changes as operations with the revision they were made on; a
 * change made elsewhere in the meantime is refused, not overwritten.
 *
 * **Hands.** On the Notes step the rectangles are coloured by hand as soon as the piece has hands,
 * and **Hand colours** turns that off. On the Hands step, **Predict hands** saves what is unsaved,
 * runs the hand split as a job with its progress bar, and lays the answer over the notes as
 * unsaved changes; **To right hand** and **To left hand** (R, L) move the selected rectangles, the
 * filter shows one hand alone, and the notes the split could not place are red until they are given
 * a hand or deleted. **Save** sends the hands as `hand` operations, like any other edit.
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Snackbar from "@mui/material/Snackbar";
import Stack from "@mui/material/Stack";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import BackHandIcon from "@mui/icons-material/BackHandOutlined";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import MyLocationIcon from "@mui/icons-material/MyLocation";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RedoIcon from "@mui/icons-material/Redo";
import ReplayIcon from "@mui/icons-material/Replay";
import SaveIcon from "@mui/icons-material/Save";
import UndoIcon from "@mui/icons-material/Undo";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import { useNavigate } from "react-router-dom";
import { ApiError, audioApi, matrixApi, piecesApi, type PredictResult } from "../../api";
import { useCutPlayer } from "../../audio/useCutPlayer";
import PianoRollCanvas, { type RollHandle, type RollMode } from "../../components/notes/PianoRollCanvas";
import RollTimeBar from "../../components/notes/RollTimeBar";
import type { HandFilter } from "../../components/notes/rollPaint";
import StepProgress from "../../components/piece/StepProgress";
import { followJob, type FollowedJob } from "../../hooks/followJob";
import { useEditHistory } from "../../hooks/useEditHistory";
import { ROUTES } from "../../layout/routes";
import { noteName, spanishNoteShort } from "../../music/noteNames";
import { LiveFeed } from "../../notes/liveFeed";
import {
  addNote,
  anyHand,
  applyPrediction,
  baseOf,
  countChanges,
  deleteNotes,
  describeChanges,
  fillRoll,
  idsWithoutHand,
  isLive,
  liveCount,
  mergeChanged,
  moveNotes,
  nextTempId,
  NO_OVERRIDES,
  noteOf,
  resizeNote,
  setHands,
  toOperations,
  type EditContext,
  type EditResult,
  type NotesBase,
  type Overrides,
} from "../../notes/noteEdits";
import { RollNotes } from "../../notes/rollNotes";
import { useLiveTranscription } from "../../notes/useLiveTranscription";
import { useSpacebarPlay } from "../../playback/useSpacebarPlay";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { EmptyState, FloatingBar, IconAction, PillButton, Segmented, timestampSx } from "../../ui";
import { stepStatus, usePiece, useUnsavedChanges } from "./pieceContext";

const FRAME_MS = 10;
const NO_SELECTION: ReadonlySet<number> = new Set();
const NO_CUTS: [number, number][] = [];

/** The backend's stage, in words, before the first rectangle arrives. */
function stageWords(stage: string | null, message: string | null): string | null {
  if (stage === "waiting") return message || "Waiting for another transcription to finish";
  if (stage === "timing") return "Measuring the timing of the notes…";
  if (stage === "transcribe") return "Transcribing…";
  if (stage) return "Starting…";
  return null;
}

/** The saved notes as loaded, and what is known about them on the backend. */
interface Doc {
  uuid: string;
  base: NotesBase;
  /** The changes on top of `base` that are saved on the backend. */
  savedOver: Overrides;
  /** The backend id of every note added on the page and saved. */
  idMap: ReadonlyMap<number, number>;
  revision: number;
  handsRevision: number;
}

interface Edits {
  over: Overrides;
}

const LABELS: Record<keyof Edits, string> = { over: "the edit" };

const plural = (count: number, one: string) => (count === 1 ? `1 ${one}` : `${count} ${one}s`);

/** The Notes step's choice to colour by hand, kept for this browser (a convenience only). */
const HAND_COLOURS_KEY = "aitu.notes.handColours";
function readHandColours(): boolean {
  try {
    return window.localStorage.getItem(HAND_COLOURS_KEY) !== "off";
  } catch {
    return true;
  }
}

/** **Predict hands** while it runs: its stage in words, how far, since when. */
interface Predicting {
  label: string;
  percent: number | null;
  startedAt: number;
  now: number;
}

/** The stages of the prediction job, in words and in a share of the whole bar. */
function predictionProgress(stage: string, fraction: number): { label: string; percent: number } {
  if (stage === "two-hands") return { label: "Predicting the hands…", percent: 10 + fraction * 90 };
  if (stage === "events") return { label: "Building the piano matrix notation…", percent: fraction * 10 };
  return { label: "Starting…", percent: 0 };
}

export type EditorStep = "notes" | "hands";

export function NotesEditor({ step }: { step: EditorStep }) {
  const navigate = useNavigate();
  const { uuid, audio, status, refresh } = usePiece();
  const { artifact } = useWorkingArtifact();
  const here = stepStatus(status, "notes");
  const hands = stepStatus(status, "hands");
  const sheet = stepStatus(status, "sheet");
  const onHands = step === "hands";
  const running = here?.state === "running";
  const jobId = running && typeof here?.details.jobId === "string" ? here.details.jobId : null;

  // ------------------------------------------------------------------ the live transcription

  const [roll] = useState(() => new RollNotes());
  const [feed] = useState(() => new LiveFeed());
  // The job this page followed stays followed after it ends, so the page can say how long it took.
  const [followed, setFollowed] = useState<string | null>(null);
  if (jobId && jobId !== followed) setFollowed(jobId);
  const live = useLiveTranscription(followed ? matrixApi.progressUrl(followed) : null, feed);

  const ended = live.status === "done" || live.status === "error";
  useEffect(() => {
    if (ended) void refresh();
  }, [ended, refresh]);

  // ------------------------------------------------------------------ the saved notes

  const history = useEditHistory<Edits>({ over: NO_OVERRIDES }, LABELS);
  const present = history.state.over;
  const resetHistory = history.reset;
  const [doc, setDoc] = useState<Doc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selection, setSelection] = useState<ReadonlySet<number>>(NO_SELECTION);
  const current = doc && doc.uuid === uuid ? doc : null;

  const statusRevision = status?.revisions.notes ?? null;
  const readable = here?.state === "ready" || here?.state === "stale";
  // Read the notes when there are none yet, or when the backend has newer ones (a transcription).
  // After this page's own save, the page holds the newer revision first, so it does not read again.
  const needLoad = Boolean(uuid) && readable && (!current || (statusRevision !== null && statusRevision > current.revision));

  useEffect(() => {
    if (!uuid || !needLoad) return;
    const controller = new AbortController();
    piecesApi
      .notes(uuid, controller.signal)
      .then((notes) => {
        resetHistory({ over: NO_OVERRIDES });
        setSelection(NO_SELECTION);
        setLoadError(null);
        setDoc({
          uuid,
          base: baseOf(notes),
          savedOver: NO_OVERRIDES,
          idMap: new Map(),
          revision: notes.revision,
          handsRevision: notes.handsRevision,
        });
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setLoadError(caught instanceof Error ? caught.message : "The notes could not be read.");
      });
    return () => controller.abort();
  }, [uuid, needLoad, resetHistory]);

  const base = current?.base ?? null;
  const mode: RollMode = running || !base ? "live" : here?.state === "stale" ? "view" : "edit";
  const durationMs = base?.durationMs ?? (feed.durationMs || (audio?.durationSeconds ?? 0) * 1000);

  // The saved notes, with the page's changes, take the place of what the stream drew.
  useLayoutEffect(() => {
    if (base && !running) fillRoll(roll, base, present);
  }, [roll, base, present, running]);

  // ------------------------------------------------------------------ playback

  const playable = mode === "edit";
  const totalFrames = Math.max(1, Math.round(durationMs / FRAME_MS));
  const audioUrl = useMemo(() => (uuid && playable ? audioApi.fileUrl(uuid) : null), [uuid, playable]);
  const player = useCutPlayer(audioUrl, NO_CUTS, totalFrames);
  const playerPosition = player.position;
  const position = useCallback(() => playerPosition() * FRAME_MS, [playerPosition]);
  const rollRef = useRef<RollHandle | null>(null);
  const [follow, setFollow] = useState(true);
  const playerSeek = player.seek;
  const seek = useCallback(
    (ms: number) => {
      playerSeek(ms / FRAME_MS);
      rollRef.current?.reveal(ms);
    },
    [playerSeek],
  );
  // Playback always follows the playhead: Play turns following back on, even after the reader
  // moved the view away.
  const { toggle: playerToggle, playAll: playerPlayAll, playing: playerPlaying } = player;
  const play = useCallback(() => {
    setFollow(true);
    playerPlayAll();
  }, [playerPlayAll]);
  const toggle = useCallback(() => {
    if (!playable) return;
    if (!playerPlaying) setFollow(true);
    playerToggle();
  }, [playable, playerPlaying, playerToggle]);
  useSpacebarPlay(toggle, playable);

  // ------------------------------------------------------------------ edits

  const [notice, setNotice] = useState<string | null>(null);
  const editing = mode === "edit" && base !== null;
  const { stage, set } = history;

  const context = useCallback(
    (): EditContext | null => (base ? { base, over: present, idsOnKey: (key) => roll.idsOnKey(key) } : null),
    [base, present, roll],
  );

  /** One gesture, one undo step, named for the undo button. */
  const apply = useCallback(
    (label: string, result: EditResult | null) => {
      if (!result) return false;
      if (result.refused) {
        setNotice(result.refused);
        return false;
      }
      if (result.over === present) return false;
      stage(label);
      set.over(result.over);
      return true;
    },
    [present, stage, set],
  );

  const onMove = useCallback(
    (ids: ReadonlySet<number>, dMs: number, dKey: number) => {
      const edit = context();
      apply(`move ${plural(ids.size, "note")}`, edit && moveNotes(edit, ids, dMs, dKey));
    },
    [context, apply],
  );
  const onResize = useCallback(
    (id: number, onMs: number, lenMs: number) => {
      const edit = context();
      apply("change the length of a note", edit && resizeNote(edit, id, onMs, lenMs));
    },
    [context, apply],
  );
  const onAdd = useCallback(
    (key: number, onMs: number) => {
      const edit = context();
      if (!edit || !current) return;
      const tempId = nextTempId(present, current.idMap.keys());
      if (apply(`add ${noteName(key + 21)}`, addNote(edit, tempId, key, onMs))) setSelection(new Set([tempId]));
    },
    [context, apply, present, current],
  );
  /** Set by the hands part below: where to go after a delete while going through the notes without a hand. */
  const nextAfterDelete = useRef<() => number | null>(() => null);
  const goToRef = useRef<(id: number) => void>(() => undefined);
  const deleteSelection = useCallback(() => {
    const edit = context();
    if (!edit || selection.size === 0) return;
    const next = nextAfterDelete.current();
    if (apply(`delete ${plural(selection.size, "note")}`, deleteNotes(edit, selection))) {
      setSelection(NO_SELECTION);
      if (next !== null) goToRef.current(next);
    }
  }, [context, apply, selection]);

  // ------------------------------------------------------------------ save

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const summary = current ? describeChanges(countChanges(current.base, current.savedOver, present)) : null;

  const save = useCallback(async (): Promise<boolean> => {
    if (!uuid || !current) return true;
    const ops = toOperations(current.base, current.savedOver, present, current.idMap);
    if (ops.length === 0) {
      setDoc({ ...current, savedOver: present });
      return true;
    }
    setSaving(true);
    setError(null);
    try {
      const answer = await piecesApi.patchNotes(uuid, {
        baseRevision: current.revision,
        baseHandsRevision: current.handsRevision,
        ops,
      });
      const idMap = new Map(current.idMap);
      for (const { tempId, id } of answer.added ?? []) idMap.set(tempId, id);
      // A note the backend changed beyond the operations (the quick rule gave a hand): the page
      // takes it as the backend has it, and its undo history starts again from there.
      const merged = mergeChanged(current.base, present, answer.changed, idMap);
      if (merged) resetHistory({ over: merged });
      setDoc({
        ...current,
        savedOver: merged ?? present,
        idMap,
        revision: answer.revision,
        handsRevision: answer.handsRevision,
      });
      await refresh();
      return true;
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) setConflict(caught.detail);
      else setError(caught instanceof ApiError ? caught.detail : caught instanceof Error ? caught.message : "The notes could not be saved.");
      return false;
    } finally {
      setSaving(false);
    }
  }, [uuid, current, present, resetHistory, refresh]);

  const discard = useCallback(() => {
    if (!current) return;
    stage("discard the unsaved changes");
    set.over(current.savedOver);
    setSelection(NO_SELECTION);
  }, [current, stage, set]);

  useUnsavedChanges(summary, { save, discard });

  const reload = () => {
    setConflict(null);
    setDoc(null);
  };

  // ------------------------------------------------------------------ hands

  const hasHands = base ? anyHand(base, present) : false;
  const [handColours, setHandColours] = useState(readHandColours);
  // By hand only once the piece has hands: before the first prediction every note would be the
  // red of "no hand", which reads as an error. On the Notes step the reader can turn it off.
  const colourBy = hasHands && (onHands || handColours) ? "hand" : "none";
  const toggleHandColours = () => {
    const next = !handColours;
    setHandColours(next);
    try {
      window.localStorage.setItem(HAND_COLOURS_KEY, next ? "on" : "off");
    } catch {
      // A private window: the choice lasts as long as the page.
    }
  };
  const [handFilter, setHandFilter] = useState<HandFilter>("both");
  const handless = useMemo(() => (base && onHands ? idsWithoutHand(base, present) : []), [base, present, onHands]);

  // ---- the notes without a hand: select them all, then go through them one by one.
  const [reviewing, setReviewing] = useState(false);
  const reviewShown = onHands && reviewing && handless.length > 0;
  const reviewIndex = selection.size === 1 ? handless.indexOf([...selection][0]!) : -1;

  const goTo = useCallback(
    (id: number) => {
      if (!base) return;
      setSelection(new Set([id]));
      const note = noteOf(base, present, id);
      if (note) rollRef.current?.center(note.onMs + note.lenMs / 2);
    },
    [base, present],
  );
  /** The note without a hand `step` places after the current one, round the list. */
  const stepHandless = useCallback(
    (step: number) => {
      if (handless.length === 0) return;
      const at = reviewIndex < 0 ? (step > 0 ? -1 : 0) : reviewIndex;
      goTo(handless[(at + step + handless.length) % handless.length]!);
    },
    [handless, reviewIndex, goTo],
  );
  /** While going through them, the next note without a hand once the current one has one. */
  const afterCurrent = useCallback((): number | null => {
    if (!reviewShown || reviewIndex < 0 || handless.length < 2) return null;
    return handless[(reviewIndex + 1) % handless.length]!;
  }, [reviewShown, reviewIndex, handless]);

  const selectHandless = () => {
    if (handless.length === 0 || !base) return;
    setHandFilter("both");
    setReviewing(true);
    setSelection(new Set(handless));
    const first = noteOf(base, present, handless[0]!);
    if (first) rollRef.current?.reveal(first.onMs);
  };

  const giveHand = useCallback(
    (hand: "r" | "l") => {
      const edit = context();
      if (!edit || selection.size === 0) return;
      const next = afterCurrent();
      if (apply(`give ${plural(selection.size, "note")} to the ${hand === "r" ? "right" : "left"} hand`, setHands(edit, selection, hand)) && next !== null) {
        goTo(next);
      }
    },
    [context, selection, apply, afterCurrent, goTo],
  );

  useLayoutEffect(() => {
    nextAfterDelete.current = afterCurrent;
    goToRef.current = goTo;
  });

  /** The selection, in short Spanish names: "Do# 3", or "3 notes: Do 3 · Mi 3 · Sol 3". */
  const selectionName = useMemo(() => {
    if (!base || selection.size === 0) return "";
    const keys = new Set<number>();
    let count = 0;
    for (const id of selection) {
      const note = noteOf(base, present, id);
      if (!isLive(note)) continue;
      count += 1;
      keys.add(note.key);
    }
    if (count === 0) return "";
    const names = [...keys].sort((a, b) => a - b).map((key) => spanishNoteShort(key + 21));
    if (count === 1) return names[0]!;
    return names.length <= 4 ? `${count} notes: ${names.join(" · ")}` : `${count} notes`;
  }, [base, present, selection]);

  // The prediction is an async flow (save, start, follow, apply), so it reads the latest notes
  // from these, not from the render that started it.
  const presentRef = useRef(present);
  const docRef = useRef(current);
  useLayoutEffect(() => {
    presentRef.current = present;
    docRef.current = current;
  });
  const [predicting, setPredicting] = useState<Predicting | null>(null);
  const [predicted, setPredicted] = useState<{ result: PredictResult; applied: number } | null>(null);
  const followedJob = useRef<FollowedJob | null>(null);
  useEffect(() => () => followedJob.current?.close(), []);

  const predict = async (replace: boolean) => {
    if (!uuid || predicting) return;
    setError(null);
    setPredicted(null);
    const startedAt = performance.now();
    setPredicting({ label: "Saving the notes first…", percent: null, startedAt, now: startedAt });
    try {
      // The backend predicts the saved notes: save what is unsaved first, in the same press.
      if (summary !== null && !(await save())) return;
      const held = docRef.current;
      if (!held) return;
      setPredicting({ label: "Starting…", percent: null, startedAt, now: performance.now() });
      const { jobId } = await piecesApi.predictHands(uuid, { baseRevision: held.revision, frameMs: artifact.frameMs, replace });
      const job = followJob(matrixApi.progressUrl(jobId), (frame) => {
        const shown = predictionProgress(frame.stage, frame.fraction);
        setPredicting({ ...shown, startedAt, now: performance.now() });
      });
      followedJob.current = job;
      const answer = (await job.result) as unknown as PredictResult;
      const latest = docRef.current;
      if (!latest || answer.revision !== latest.revision) {
        setError("The notes changed while the hands were predicted. Press Predict hands again.");
        return;
      }
      const result = applyPrediction(
        { base: latest.base, over: presentRef.current, idsOnKey: (key) => roll.idsOnKey(key) },
        answer,
        latest.idMap,
      );
      if (result.over !== presentRef.current) {
        stage(replace ? "predict every hand again" : "predict hands");
        set.over(result.over);
      }
      setHandFilter("both");
      setPredicted({ result: answer, applied: countChanges(latest.base, presentRef.current, result.over).hands });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : caught instanceof Error ? caught.message : "The hands could not be predicted.");
    } finally {
      followedJob.current = null;
      setPredicting(null);
    }
  };

  // ------------------------------------------------------------------ keys

  const { undo, redo } = history;
  useEffect(() => {
    if (!editing) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      const command = event.metaKey || event.ctrlKey;
      const key = event.key.toLowerCase();
      if (command && key === "z") {
        event.preventDefault();
        void (event.shiftKey ? redo() : undo());
      } else if (command && key === "y") {
        event.preventDefault();
        void redo();
      } else if (command && key === "a") {
        event.preventDefault();
        setSelection(new Set(roll.ids()));
      } else if (!command && (event.key === "Delete" || event.key === "Backspace")) {
        event.preventDefault();
        deleteSelection();
      } else if (event.key === "Escape") {
        setSelection(NO_SELECTION);
      } else if (onHands && !command && !event.altKey && (key === "r" || key === "l") && selection.size > 0) {
        event.preventDefault();
        giveHand(key === "r" ? "r" : "l");
      } else if (!command && selection.size > 0 && event.key.startsWith("Arrow")) {
        // Nudge the selection: one time frame (Shift: 100 ms) sideways, one key (Shift: an octave) up or down.
        event.preventDefault();
        const step = event.shiftKey ? 10 : 1;
        const dMs = event.key === "ArrowLeft" ? -10 * step : event.key === "ArrowRight" ? 10 * step : 0;
        const dKey = event.key === "ArrowUp" ? (event.shiftKey ? 12 : 1) : event.key === "ArrowDown" ? (event.shiftKey ? -12 : -1) : 0;
        onMove(selection, dMs, dKey);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editing, undo, redo, deleteSelection, selection, onMove, roll, onHands, giveHand]);

  // ------------------------------------------------------------------ render

  if (!uuid || !here) return null;

  if (here.state === "missing" && !followed) {
    return (
      <EmptyState
        message={here.reason ?? "This project has no notes yet."}
        action={
          <PillButton kind="primary" onClick={() => navigate(ROUTES.project(uuid, "audio"))}>
            Open the Audio step
          </PillButton>
        }
      />
    );
  }

  const waiting = stageWords(live.stage, live.message);
  const noteCount = base ? liveCount(base, present) : null;
  const cursorMs = player.cursor * FRAME_MS;
  const busy = predicting !== null || saving;

  const next =
    mode === "live" ? null : !onHands ? (
      hands?.enabled ? (
        <PillButton kind="primary" onClick={() => navigate(ROUTES.project(uuid, "hands"))}>
          Continue to Hands
        </PillButton>
      ) : null
    ) : (
      <Stack direction="row" spacing={1}>
        {/* The main action of the Hands step, in words beside Continue (the user's review of
            Phase 5): the wand of the floating toolbox alone was not found. Primary until the
            hands are there. */}
        <PillButton
          kind={hasHands ? "secondary" : "primary"}
          startIcon={<AutoFixHighIcon fontSize="small" />}
          busy={predicting !== null}
          disabled={busy}
          onClick={() => void predict(false)}
        >
          Predict hands
        </PillButton>
        <Tooltip title={sheet?.enabled ? "" : (sheet?.reason ?? "Save the hands first")}>
          <span>
            <PillButton kind="primary" disabled={!sheet?.enabled} onClick={() => navigate(ROUTES.project(uuid, "sheet"))}>
              Continue to Sheet
            </PillButton>
          </span>
        </Tooltip>
      </Stack>
    );

  return (
    // Room under the page, so the floating toolbar can be moved clear of the piano roll.
    <Stack spacing={1.5} sx={{ pb: editing ? 9 : 0 }}>
      {live.status === "error" ? <Alert severity="error">{live.error}</Alert> : null}
      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {player.error ? <Alert severity="warning">{player.error}</Alert> : null}
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {conflict ? (
        <Alert
          severity="error"
          action={
            <PillButton size="small" onClick={reload}>
              Reload the notes
            </PillButton>
          }
        >
          {`The notes changed in another tab, so these changes could not be saved (${conflict}). Reload the notes to continue; the unsaved changes here are lost.`}
        </Alert>
      ) : null}
      {here.state === "stale" ? (
        <Alert
          severity="warning"
          action={
            <PillButton size="small" onClick={() => navigate(ROUTES.project(uuid, "audio"))}>
              Open the Audio step
            </PillButton>
          }
        >
          The cuts changed after this transcription, so these notes no longer match the audio. Transcribe again on the Audio step to edit or play them.
        </Alert>
      ) : null}

      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, minHeight: 40 }}>
        {mode === "live" ? (
          <>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", pr: 1 }} role="status" aria-live="polite">
              {running ? <CircularProgress size={14} /> : null}
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {running ? (waiting ?? "Transcribing…") : ended ? "Reading the saved notes…" : "Loading the notes…"}
              </Typography>
            </Stack>
            <IconAction
              title="Keep the part being transcribed in view"
              icon={<MyLocationIcon fontSize="small" />}
              active={follow}
              onClick={() => setFollow((value) => !value)}
            />
          </>
        ) : null}

        {!onHands && editing ? (
          <Tooltip title={hasHands ? "Colour the notes by hand: blue right, green left, red no hand" : "Predict hands on the Hands step first"}>
            <FormControlLabel
              sx={{ ml: 0, mr: 1 }}
              control={<Switch size="small" checked={hasHands && handColours} disabled={!hasHands} onChange={toggleHandColours} />}
              label={<Typography variant="body2">Hand colours</Typography>}
            />
          </Tooltip>
        ) : null}
        {noteCount !== null ? (
          <Typography variant="body2" color="text.secondary" sx={timestampSx}>
            {plural(noteCount, "note")}
          </Typography>
        ) : null}
        {predicted && !predicting ? (
          <Typography variant="body2" color="text.secondary" data-predicted>
            {`${plural(predicted.applied, "note")} changed hand${predicted.result.unplaced ? ` · ${predicted.result.unplaced} without a hand` : ""}`}
          </Typography>
        ) : null}

        <Box sx={{ flexGrow: 1 }} />

        <IconAction title="Zoom out" icon={<ZoomOutIcon fontSize="small" />} onClick={() => rollRef.current?.zoomBy(0.5)} />
        <IconAction title="Zoom in" icon={<ZoomInIcon fontSize="small" />} onClick={() => rollRef.current?.zoomBy(2)} />
        <IconAction title="Show the whole piece" icon={<FitScreenIcon fontSize="small" />} onClick={() => rollRef.current?.showWhole()} />
        {next ? <Box sx={{ pl: 1 }}>{next}</Box> : null}
      </Stack>

      {predicting ? (
        <StepProgress label={predicting.label} percent={predicting.percent} elapsedSeconds={(predicting.now - predicting.startedAt) / 1000} />
      ) : null}

      <PianoRollCanvas
        ref={rollRef}
        notes={roll}
        mode={mode}
        feed={mode === "live" ? feed : null}
        durationMs={durationMs}
        selection={selection}
        colourBy={colourBy}
        handFilter={onHands ? handFilter : "both"}
        cursorMs={cursorMs}
        playing={player.playing !== null}
        position={position}
        onSeek={playable ? seek : null}
        follow={follow}
        onFollowChange={setFollow}
        onSelect={setSelection}
        onMove={onMove}
        onResize={onResize}
        onAdd={onAdd}
      />

      <RollTimeBar
        durationMs={durationMs}
        feed={mode === "live" ? feed : null}
        waiting={waiting}
        cursorMs={cursorMs}
        playing={player.playing !== null}
        position={position}
        onSeek={playable ? seek : null}
      />

      {/* The editor's toolbox, floating so it stays at hand along the whole piece. */}
      <FloatingBar open={editing} label={onHands ? "the hands toolbox" : "the editing toolbar"}>
        {player.playing ? (
          <IconAction title="Pause" shortcut="Space" icon={<PauseIcon />} onClick={player.pause} />
        ) : (
          <IconAction title="Play from the playhead" shortcut="Space" icon={<PlayArrowIcon />} onClick={play} />
        )}
        {/* On by default; moving the view by hand turns it off, and Play turns it on again. */}
        <IconAction
          title="Follow the playhead"
          icon={<MyLocationIcon fontSize="small" />}
          active={follow}
          onClick={() => setFollow((value) => !value)}
        />
        <IconAction
          title={history.canUndo ? `Undo ${history.undoLabel ?? ""}`.trim() : "Nothing to undo"}
          shortcut="⌘Z"
          icon={<UndoIcon fontSize="small" />}
          disabled={!history.canUndo}
          onClick={() => void history.undo()}
        />
        <IconAction
          title={history.canRedo ? `Redo ${history.redoLabel ?? ""}`.trim() : "Nothing to redo"}
          shortcut="⇧⌘Z"
          icon={<RedoIcon fontSize="small" />}
          disabled={!history.canRedo}
          onClick={() => void history.redo()}
        />
        <IconAction
          title="Delete the selected notes"
          shortcut="Delete"
          disabledTitle="Select notes first"
          icon={<DeleteIcon fontSize="small" />}
          disabled={selection.size === 0}
          onClick={deleteSelection}
        />
        {onHands ? (
          <>
            <Divider orientation="vertical" flexItem />
            {hasHands ? (
              <IconAction
                title="Predict every note again, also the ones you placed"
                icon={<ReplayIcon fontSize="small" />}
                disabled={busy}
                onClick={() => void predict(true)}
              />
            ) : null}
            <Segmented<HandFilter>
              label="Which hand to show"
              value={handFilter}
              onChange={setHandFilter}
              options={[
                { value: "both", label: "Both", tooltip: "Show both hands" },
                { value: "right", label: "Right", tooltip: "Show the right hand only" },
                { value: "left", label: "Left", tooltip: "Show the left hand only" },
              ]}
            />
            <Tooltip title="Give the selected notes to the right hand (R)">
              <span>
                <PillButton kind="quiet" size="small" disabled={selection.size === 0} onClick={() => giveHand("r")}>
                  To right
                </PillButton>
              </span>
            </Tooltip>
            <Tooltip title="Give the selected notes to the left hand (L)">
              <span>
                <PillButton kind="quiet" size="small" disabled={selection.size === 0} onClick={() => giveHand("l")}>
                  To left
                </PillButton>
              </span>
            </Tooltip>
            {handless.length > 0 && hasHands ? (
              <>
                <Tooltip title={`Select the ${plural(handless.length, "note")} without a hand, then give each a hand (L, R) or delete it`}>
                  <IconButton size="small" color="error" onClick={selectHandless} aria-label="Select the notes without a hand">
                    <Badge badgeContent={handless.length} color="error" max={999}>
                      <BackHandIcon fontSize="small" />
                    </Badge>
                  </IconButton>
                </Tooltip>
                {reviewShown ? (
                  <>
                    <IconAction title="Previous note without a hand" icon={<ChevronLeftIcon fontSize="small" />} onClick={() => stepHandless(-1)} />
                    <Typography variant="body2" sx={{ ...timestampSx, minWidth: 44, textAlign: "center" }} data-review>
                      {reviewIndex >= 0 ? `${reviewIndex + 1} / ${handless.length}` : `– / ${handless.length}`}
                    </Typography>
                    <IconAction title="Next note without a hand" icon={<ChevronRightIcon fontSize="small" />} onClick={() => stepHandless(1)} />
                  </>
                ) : null}
              </>
            ) : null}
          </>
        ) : null}
        {selectionName ? (
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: "nowrap", px: 0.5 }} data-selection-name>
            {selectionName}
          </Typography>
        ) : null}
        <Divider orientation="vertical" flexItem />
        <Tooltip title={summary ?? "Nothing to save"}>
          <span>
            <PillButton
              size="small"
              kind={summary === null ? "quiet" : "primary"}
              startIcon={<SaveIcon fontSize="small" />}
              busy={saving}
              disabled={summary === null || busy}
              onClick={() => void save()}
              data-unsaved={summary ?? ""}
            >
              Save
            </PillButton>
          </span>
        </Tooltip>
      </FloatingBar>

      <Snackbar
        open={notice !== null}
        autoHideDuration={4000}
        onClose={() => setNotice(null)}
        message={notice}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      />
    </Stack>
  );
}

export default NotesEditor;
