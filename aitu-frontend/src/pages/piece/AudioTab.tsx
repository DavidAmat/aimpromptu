/**
 * Step 2, **Audio**: listen to the audio and choose the selected region (implementation 08, plan
 * section 9.4; restyled by implementation 02, plan section 10.2: the waveform full width, its tools
 * as icon actions in a floating bar, **Transcribe** as the primary action).
 *
 * The audio file is never copied or changed. The reader selects a part of the waveform and presses
 * **Delete**, and that part becomes a cut: a range of 10 ms time frames that the piece leaves out
 * (Q-1). A cut is drawn shaded and crossed; clicking it selects it, and **Restore** puts it back.
 * **Play all** plays the selected region and jumps over the cuts; **Play selection** plays the part
 * selected, cut or not. Undo and redo walk back through every Delete and Restore.
 *
 * Nothing is written until **Save**. **Transcribe** saves first, starts the transcription and opens
 * the Notes tab. A change of the cuts after a transcription makes the notes stale, and the next
 * transcription replaces them; the old notes go to history (Q-2).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RedoIcon from "@mui/icons-material/Redo";
import RestoreIcon from "@mui/icons-material/RestorePage";
import SaveIcon from "@mui/icons-material/Save";
import UndoIcon from "@mui/icons-material/Undo";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomInMapIcon from "@mui/icons-material/ZoomInMap";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import { useNavigate } from "react-router-dom";
import { ApiError, audioApi, matrixApi, type Cut, type CutsState, type FramePeaks } from "../../api";
import {
  addCut,
  cutAt,
  cutFrames,
  overlapsCut,
  restoreRange,
  sameCuts,
} from "../../audio/cuts";
import { clampView, wholeView, zoomView, type FrameView } from "../../audio/frameView";
import { formatTime } from "../../audio/time";
import { useCutPlayer } from "../../audio/useCutPlayer";
import CutWaveform from "../../components/audio/CutWaveform";
import { useEditHistory } from "../../hooks/useEditHistory";
import { ROUTES } from "../../layout/routes";
import { useSpacebarPlay } from "../../playback/useSpacebarPlay";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { ConfirmDialog, FloatingBar, IconAction, PillButton, timestampSx } from "../../ui";
import { SAVED_NAVIGATION, stepStatus, usePiece, useUnsavedChanges } from "./pieceContext";

const FRAMES_PER_SECOND = 100;
const seconds = (frames: number) => frames / FRAMES_PER_SECOND;

/** The cuts and the waveform, tagged with the piece they belong to. */
interface Loaded {
  uuid: string | null;
  cuts: CutsState | null;
  peaks: FramePeaks | null;
  error: string | null;
}

export function AudioTab() {
  const { uuid } = usePiece();
  const [loaded, setLoaded] = useState<Loaded>({ uuid: null, cuts: null, peaks: null, error: null });
  const current = loaded.uuid === uuid ? loaded : { uuid, cuts: null, peaks: null, error: null };

  useEffect(() => {
    if (!uuid) return;
    const controller = new AbortController();
    Promise.all([audioApi.cuts(uuid, controller.signal), audioApi.framePeaks(uuid, controller.signal)])
      .then(([cuts, peaks]) => setLoaded({ uuid, cuts, peaks, error: null }))
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          uuid,
          cuts: null,
          peaks: null,
          error: caught instanceof Error ? caught.message : "Could not load the audio.",
        });
      });
    return () => controller.abort();
  }, [uuid]);

  if (current.error) return <Alert severity="error">{current.error}</Alert>;
  if (!uuid || !current.cuts || !current.peaks) {
    return (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 2 }}>
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Loading the waveform…
        </Typography>
      </Stack>
    );
  }
  return <AudioEditor key={uuid} uuid={uuid} initial={current.cuts} peaks={current.peaks} />;
}

interface AudioEditorProps {
  uuid: string;
  initial: CutsState;
  peaks: FramePeaks;
}

interface Edits {
  cuts: Cut[];
}

const LABELS: Record<keyof Edits, string> = { cuts: "the cuts" };

/** "2 cuts, 00:12.50 removed", the words of the save bar and of the dialog. */
function describe(cuts: readonly Cut[]): string {
  if (cuts.length === 0) return "no cut";
  const count = cuts.length === 1 ? "1 cut" : `${cuts.length} cuts`;
  return `${count}, ${formatTime(seconds(cutFrames(cuts)))} removed`;
}

function AudioEditor({ uuid, initial, peaks }: AudioEditorProps) {
  const navigate = useNavigate();
  const { status, refresh } = usePiece();
  const { artifact } = useWorkingArtifact();
  const total = initial.totalFrames;

  const history = useEditHistory<Edits>({ cuts: initial.cuts }, LABELS);
  const cuts = history.state.cuts;
  const setCuts = history.set.cuts;
  const [saved, setSaved] = useState<CutsState>(initial);
  const [selection, setSelection] = useState<Cut | null>(null);
  const [view, setView] = useState<FrameView>(() => wholeView(total));
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmAgain, setConfirmAgain] = useState(false);

  const player = useCutPlayer(useMemo(() => audioApi.originalFileUrl(uuid), [uuid]), cuts, total);
  const unsaved = !sameCuts(cuts, saved.cuts);
  const summary = unsaved ? `Unsaved: ${describe(cuts)}` : null;

  // ------------------------------------------------------------------ save

  const save = useCallback(async (): Promise<boolean> => {
    setSaving(true);
    setError(null);
    try {
      const answer = await audioApi.saveCuts(uuid, cuts, saved.audioRevision);
      setSaved(answer);
      await refresh();
      return true;
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? `${caught.detail}`
          : caught instanceof Error
            ? caught.message
            : "The cuts could not be saved.",
      );
      return false;
    } finally {
      setSaving(false);
    }
  }, [uuid, cuts, saved.audioRevision, refresh]);

  const discard = useCallback(() => setCuts(saved.cuts), [setCuts, saved.cuts]);

  useUnsavedChanges(summary, { save, discard });

  // ------------------------------------------------------------------ edits

  const hasSelection = selection !== null && selection[1] > selection[0];
  const canRestore = hasSelection && overlapsCut(cuts, selection[0], selection[1]);

  const deleteSelection = useCallback(() => {
    if (!selection || selection[1] <= selection[0]) return;
    setCuts((current) => addCut(current, selection[0], selection[1], total));
  }, [selection, setCuts, total]);

  const restoreSelection = useCallback(() => {
    if (!selection) return;
    setCuts((current) => restoreRange(current, selection[0], selection[1]));
  }, [selection, setCuts]);

  // A single click never moves the playhead: that is the ruler's job, or a double-click's.
  const clickFrame = useCallback(
    (frame: number, shift: boolean) => {
      if (shift && selection) {
        const at = Math.round(frame);
        setSelection([Math.min(selection[0], at), Math.max(selection[1], at)]);
        return;
      }
      const cut = cutAt(cuts, frame);
      setSelection(cut ? [cut[0], cut[1]] : null);
    },
    [selection, cuts],
  );

  useSpacebarPlay(player.toggle);

  const { undo, redo } = history;
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      const command = event.metaKey || event.ctrlKey;
      if (command && event.key.toLowerCase() === "z") {
        event.preventDefault();
        void (event.shiftKey ? redo() : undo());
      } else if (command && event.key.toLowerCase() === "y") {
        event.preventDefault();
        void redo();
      } else if (!command && (event.key === "Delete" || event.key === "Backspace")) {
        event.preventDefault();
        deleteSelection();
      } else if (event.key === "Escape") {
        setSelection(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [undo, redo, deleteSelection]);

  // ------------------------------------------------------------------ transcribe

  const notes = stepStatus(status, "notes");

  const transcribe = async (again: boolean) => {
    setConfirmAgain(false);
    setStarting(true);
    setError(null);
    try {
      if (unsaved && !(await save())) return;
      await matrixApi.transcribe({ audioUuid: uuid, frameMs: artifact.frameMs, force: again });
      await refresh();
      navigate(ROUTES.project(uuid, "notes"), { state: SAVED_NAVIGATION });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The transcription could not start.");
    } finally {
      setStarting(false);
    }
  };

  const onTranscribe = () => {
    if (notes?.state === "running") {
      navigate(ROUTES.project(uuid, "notes"));
      return;
    }
    // Current notes are replaced only when the reader says so; stale or missing ones are not
    // worth keeping (Q-2), and Save already said what saving the cuts does to them.
    if (notes?.state === "ready" && !unsaved) {
      setConfirmAgain(true);
      return;
    }
    void transcribe(false);
  };

  const transcribeLabel =
    notes?.state === "running"
      ? "Show the transcription"
      : notes?.state === "ready" || notes?.state === "stale"
        ? unsaved
          ? "Save and transcribe again"
          : "Transcribe again"
        : unsaved
          ? "Save and transcribe"
          : "Transcribe";

  // ------------------------------------------------------------------ render

  /** Zoom around what the reader is working on: the selection, else the playhead, else the middle. */
  const zoom = (factor: number) => {
    const visible = (frame: number) => frame >= view.start && frame <= view.end;
    const middle = (view.start + view.end) / 2;
    const center = selection ? (selection[0] + selection[1]) / 2 : player.cursor;
    setView(zoomView(view, factor, visible(center) ? center : middle, total));
  };

  /** The selection with a margin of a fifth of its length each side, so both edges can be grabbed. */
  const zoomToSelection = () => {
    if (!selection) return;
    const margin = Math.max(10, (selection[1] - selection[0]) * 0.2);
    setView(clampView({ start: selection[0] - margin, end: selection[1] + margin }, total));
  };
  const onViewChange = useCallback((next: FrameView) => setView(clampView(next, total)), [total]);
  const keptFrames = total - cutFrames(cuts);
  const notesHaveCuts = notes && notes.state !== "missing";

  const cutWords = cuts.length === 0 ? null : `${describe(cuts)} · ${formatTime(seconds(keptFrames))} kept`;

  return (
    // Room under the waveform, so the floating bar can be moved clear of it. The data attributes
    // are for the browser checks (`check:flow`): what the old readout lines printed, not shown.
    <Stack
      spacing={1.5}
      sx={{ pb: 10 }}
      data-audio
      data-selection={hasSelection ? `${selection[0]}-${selection[1]}` : ""}
      data-view={`${Math.round(view.start)}-${Math.round(view.end)}`}
      data-cuts={describe(cuts)}
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {player.error ? <Alert severity="warning">{player.error}</Alert> : null}
      {saved.notesStale && !unsaved ? (
        <Alert severity="warning">The notes were made before the last change of the cuts. Transcribe again to update them.</Alert>
      ) : null}
      {unsaved && notesHaveCuts && !saved.notesStale ? (
        <Alert severity="warning">
          Saving these cuts puts the current notes out of date. They go to history when the audio is transcribed again.
        </Alert>
      ) : null}

      <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, minHeight: 40 }}>
        <Typography variant="body2" sx={{ ...timestampSx, fontWeight: 600 }} aria-label="Playhead">
          {formatTime(seconds(player.cursor))}
          <Box component="span" sx={{ color: "text.secondary", fontWeight: 400 }}>
            {` / ${formatTime(seconds(total))}`}
          </Box>
        </Typography>
        {hasSelection ? (
          <Typography variant="body2" color="text.secondary" sx={timestampSx} data-selection>
            {`Selection ${formatTime(seconds(selection[0]))} – ${formatTime(seconds(selection[1]))}`}
          </Typography>
        ) : null}
        {cutWords ? (
          <Typography variant="body2" color="text.secondary" sx={timestampSx}>
            {cutWords}
          </Typography>
        ) : null}
        <Box sx={{ flexGrow: 1 }} />
        <PillButton kind="primary" busy={starting} disabled={saving} onClick={onTranscribe} startIcon={<PlayArrowIcon />}>
          {transcribeLabel}
        </PillButton>
      </Stack>

      <CutWaveform
        peaks={peaks}
        cuts={cuts}
        selection={selection}
        onSelectionChange={setSelection}
        onClickFrame={clickFrame}
        onSeek={player.seek}
        view={view}
        onViewChange={onViewChange}
        cursor={player.cursor}
        playing={player.playing !== null}
        position={player.position}
      />

      <FloatingBar open label="the audio toolbar">
        {player.playing ? (
          <IconAction title="Pause" shortcut="Space" icon={<PauseIcon />} onClick={player.pause} />
        ) : (
          <IconAction title="Play, jumping over the cuts" shortcut="Space" icon={<PlayArrowIcon />} onClick={player.playAll} />
        )}
        <IconAction
          title="Play the selection"
          disabledTitle="Select a part of the waveform first"
          icon={<GraphicEqIcon fontSize="small" />}
          disabled={!hasSelection}
          onClick={() => selection && player.playSelection(selection)}
        />
        <Divider orientation="vertical" flexItem />
        <IconAction
          title="Cut the selection"
          shortcut="Delete"
          disabledTitle="Select a part of the waveform first"
          icon={<ContentCutIcon fontSize="small" />}
          disabled={!hasSelection}
          onClick={deleteSelection}
        />
        <IconAction
          title="Restore the cuts in the selection"
          disabledTitle="Click a cut to select it"
          icon={<RestoreIcon fontSize="small" />}
          disabled={!canRestore}
          onClick={restoreSelection}
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
        <Divider orientation="vertical" flexItem />
        <IconAction title="Zoom out" icon={<ZoomOutIcon fontSize="small" />} onClick={() => zoom(2)} />
        <IconAction title="Zoom in" icon={<ZoomInIcon fontSize="small" />} onClick={() => zoom(0.5)} />
        <IconAction
          title="Zoom to the selection"
          disabledTitle="Select a part of the waveform first"
          icon={<ZoomInMapIcon fontSize="small" />}
          disabled={!hasSelection}
          onClick={zoomToSelection}
        />
        <IconAction title="Show the whole audio" icon={<FitScreenIcon fontSize="small" />} onClick={() => setView(wholeView(total))} />
        <Divider orientation="vertical" flexItem />
        {unsaved ? (
          <IconAction title="Discard the changes" icon={<CloseIcon fontSize="small" />} onClick={discard} disabled={saving} />
        ) : null}
        <Tooltip title={summary ?? "Nothing to save"}>
          <span>
            <PillButton
              kind={unsaved ? "primary" : "quiet"}
              size="small"
              startIcon={<SaveIcon fontSize="small" />}
              disabled={!unsaved || starting}
              busy={saving}
              onClick={() => void save()}
              data-unsaved={summary ?? ""}
            >
              Save
            </PillButton>
          </span>
        </Tooltip>
      </FloatingBar>

      <ConfirmDialog
        open={confirmAgain}
        title="Transcribe again?"
        message="The current notes and their edits go to history, and the hands and the piano sheet must be done again."
        confirmLabel="Transcribe again"
        onCancel={() => setConfirmAgain(false)}
        onConfirm={() => void transcribe(true)}
      />
    </Stack>
  );
}

export default AudioTab;
