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
 *
 * **Add audio** (implementation 02, plan section 8.5) puts another file at the end of the audio:
 * the waveform then shows the files end to end, each in its own band with its name, and a cut may
 * cross the join. Adding a file changes the audio, so the notes become stale. With several files a
 * panel on the left lists them by name: a click selects that file's part of the waveform and zooms
 * to it, so a cut can be made inside one file. The names and the order are changed on the Source
 * step.
 *
 * A project made from a video has the **Video** step here instead (`VideoStep`, plan section 10.2).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddCircleIcon from "@mui/icons-material/AddCircleOutlineOutlined";
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
import {
  ApiError,
  audioApi,
  matrixApi,
  SUPPORTED_AUDIO_SUFFIXES,
  type AxisFile,
  type Cut,
  type CutsState,
  type FramePeaks,
} from "../../api";
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
import { ConfirmDialog, FloatingBar, IconAction, PillButton, timestampSx, ui, useScheme } from "../../ui";
import { SAVED_NAVIGATION, stepStatus, usePiece, useUnsavedChanges } from "./pieceContext";
import { VideoStep } from "./VideoStep";

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
  const { audio, readOnly } = usePiece();
  // A version of the library shows its audio: fitting the piano and reading notes are edits.
  return audio?.hasVideo && !readOnly ? <VideoStep /> : <AudioOfProject />;
}

function AudioOfProject() {
  const { uuid } = usePiece();
  const [loaded, setLoaded] = useState<Loaded>({ uuid: null, cuts: null, peaks: null, error: null });
  const current = loaded.uuid === uuid ? loaded : { uuid, cuts: null, peaks: null, error: null };
  // Bumped after **Add audio**: the waveform and the cuts are loaded again, and the editor starts
  // over on them.
  const [version, setVersion] = useState(0);

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
  }, [uuid, version]);

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
  return (
    <AudioEditor
      // The length too: right after **Add audio** the old waveform is still here for a moment, and
      // the editor must start again on the new one, with the whole audio in view.
      key={`${uuid}:${version}:${current.cuts.totalFrames}`}
      uuid={uuid}
      initial={current.cuts}
      peaks={current.peaks}
      onAudioChanged={() => setVersion((count) => count + 1)}
    />
  );
}

interface AudioEditorProps {
  uuid: string;
  initial: CutsState;
  peaks: FramePeaks;
  /** The files of the audio changed (**Add audio**): load the waveform again. */
  onAudioChanged: () => void;
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

function AudioEditor({ uuid, initial, peaks, onAudioChanged }: AudioEditorProps) {
  const navigate = useNavigate();
  const { status, refresh, readOnly } = usePiece();
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

  // ------------------------------------------------------------------ add audio

  const addInput = useRef<HTMLInputElement | null>(null);
  const [adding, setAdding] = useState<string | null>(null);

  const addAudio = async (file: File | undefined) => {
    if (!file) return;
    if (!SUPPORTED_AUDIO_SUFFIXES.some((suffix) => file.name.toLowerCase().endsWith(suffix))) {
      setError(`“${file.name}” is not an audio file this app reads (${SUPPORTED_AUDIO_SUFFIXES.join(", ")}).`);
      return;
    }
    setError(null);
    // The cuts are kept where they are, so unsaved ones are saved first.
    if (unsaved && !(await save())) return;
    setAdding(file.name);
    try {
      await audioApi.addAudio(uuid, file);
      await refresh();
      onAudioChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The file could not be added.");
      setAdding(null);
    }
  };

  const waveformFiles = useMemo(
    () => (initial.files.length > 1 ? initial.files.map((file) => ({ startFrame: file.startFrame, name: file.name })) : undefined),
    [initial.files],
  );

  // ------------------------------------------------------------------ edits

  const hasSelection = selection !== null && selection[1] > selection[0];
  const canRestore = hasSelection && overlapsCut(cuts, selection[0], selection[1]);

  const deleteSelection = useCallback(() => {
    if (readOnly || !selection || selection[1] <= selection[0]) return;
    setCuts((current) => addCut(current, selection[0], selection[1], total));
  }, [readOnly, selection, setCuts, total]);

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
  const zoomTo = (range: Cut) => {
    const margin = Math.max(10, (range[1] - range[0]) * 0.2);
    setView(clampView({ start: range[0] - margin, end: range[1] + margin }, total));
  };
  const zoomToSelection = () => {
    if (selection) zoomTo(selection);
  };

  /** A file of the panel: select its whole part of the waveform and show it. */
  const selectFile = (file: AxisFile) => {
    const range: Cut = [file.startFrame, file.startFrame + file.frames];
    setSelection(range);
    zoomTo(range);
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
      data-files={initial.files.length}
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
        {adding ? (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }} role="status">
            <CircularProgress size={14} />
            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 260 }}>
              {`Adding ${adding}`}
            </Typography>
          </Stack>
        ) : null}
        <Box sx={{ flexGrow: 1 }} />
        {readOnly ? null : (
          <PillButton kind="primary" busy={starting} disabled={saving} onClick={onTranscribe} startIcon={<PlayArrowIcon />}>
            {transcribeLabel}
          </PillButton>
        )}
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: "flex-start" }}>
        {initial.files.length > 1 ? (
          <FilePanel
            files={initial.files}
            cuts={cuts}
            selection={selection}
            onSelect={selectFile}
            onAdd={readOnly ? undefined : () => addInput.current?.click()}
            adding={adding !== null}
          />
        ) : null}
        <Box sx={{ flex: 1, minWidth: 0, width: "100%" }}>
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
            files={waveformFiles}
          />
        </Box>
      </Stack>

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
        {readOnly ? null : (
          <>
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
          </>
        )}
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
        {readOnly ? null : (
          <>
            <Divider orientation="vertical" flexItem />
            <IconAction
              title="Add audio at the end"
              icon={<AddCircleIcon fontSize="small" />}
              disabled={adding !== null || saving || starting}
              onClick={() => addInput.current?.click()}
            />
            <input
              ref={addInput}
              type="file"
              hidden
              accept={SUPPORTED_AUDIO_SUFFIXES.join(",")}
              aria-label="Choose an audio file to add"
              onChange={(event) => {
                void addAudio(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
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
          </>
        )}
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

/**
 * The files of the audio, by name, in the order they play (a project of several files). A click
 * selects the file's part of the waveform; the line under the name says how much of it is kept.
 */
function FilePanel({
  files,
  cuts,
  selection,
  onSelect,
  onAdd,
  adding,
}: {
  files: readonly AxisFile[];
  cuts: readonly Cut[];
  selection: Cut | null;
  onSelect: (file: AxisFile) => void;
  /** Absent on a version of the library, which changes only through Edit. */
  onAdd?: () => void;
  adding: boolean;
}) {
  useScheme();
  return (
    <Box
      component="nav"
      aria-label="The audio files"
      data-file-panel
      sx={{ width: { xs: "100%", md: 220 }, flexShrink: 0, borderRight: { md: `1px solid ${ui.line}` }, pr: { md: 1 } }}
    >
      <Typography variant="body2" color="text.secondary" sx={{ px: 1, pb: 0.5 }}>
        Audio files
      </Typography>
      {files.map((file) => {
        const end = file.startFrame + file.frames;
        const cut = cuts.reduce((sum, [a, b]) => sum + Math.max(0, Math.min(end, b) - Math.max(file.startFrame, a)), 0);
        const selected = selection !== null && selection[0] === file.startFrame && selection[1] === end;
        return (
          <ButtonBase
            key={`${file.index}:${file.startFrame}`}
            onClick={() => onSelect(file)}
            aria-pressed={selected}
            data-file={file.index}
            sx={(theme) => ({
              display: "flex",
              width: "100%",
              justifyContent: "flex-start",
              textAlign: "left",
              gap: 1,
              px: 1,
              py: 0.75,
              borderRadius: "10px",
              backgroundColor: selected ? (theme.vars ?? theme).palette.action.selected : "transparent",
              "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
            })}
          >
            <Box
              aria-hidden
              sx={{
                width: 6,
                alignSelf: "stretch",
                borderRadius: "3px",
                // The same grey as the file's band on the waveform: every second file is shaded.
                backgroundColor: file.index % 2 === 1 ? ui.bgHover : "transparent",
                border: `1px solid ${ui.line}`,
              }}
            />
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" noWrap title={file.name} sx={{ fontWeight: 500 }}>
                {file.name}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={timestampSx}>
                {cut > 0
                  ? `${formatTime(seconds(file.frames - cut))} of ${formatTime(seconds(file.frames))}`
                  : formatTime(seconds(file.frames))}
              </Typography>
            </Box>
          </ButtonBase>
        );
      })}
      {onAdd ? (
        <PillButton
          kind="quiet"
          size="small"
          startIcon={<AddCircleIcon fontSize="small" />}
          onClick={onAdd}
          disabled={adding}
          sx={{ mt: 0.5 }}
        >
          Add audio
        </PillButton>
      ) : null}
    </Box>
  );
}

export default AudioTab;
