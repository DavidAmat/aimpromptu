/**
 * `/playground/matrix` — the debugging heart of the Playground.
 *
 * Four things happen here, and they share one fetch:
 *
 * - **Step pills** switch between raw, collapsed, clean and two-hands. Every
 *   step is derived from the same stored raw matrix, so switching is a request,
 *   not a re-transcription.
 * - **BPM and resolution** can be changed in place. That is a *recompute* —
 *   steps 3-5 of the pipeline redone from raw — which is milliseconds, so the
 *   dropdown feels like a filter rather than a job.
 * - **Frame search** jumps to a frame number or a timestamp.
 * - **Export** downloads the current view, dense or sparse.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import SearchIcon from "@mui/icons-material/Search";
import { Link, useSearchParams } from "react-router-dom";
import {
  audioApi,
  matrixApi,
  type AudioItem,
  type Granularity,
  type MatrixCellEdit,
  type MatrixEnvelope,
  type MatrixProcessingStep,
} from "../../api";
import MatrixGrid from "../../components/matrix/MatrixGrid";
import { formatTime, parseTime } from "../../audio/time";
import { ROUTES } from "../../layout/routes";
import { TRANSCRIPTION_GRANULARITIES } from "../../music/granularities";
import { extractMatrixNotes } from "../../playback/matrixNotes";
import { PlaybackTransport } from "../../playback/PlaybackTransport";
import { useMatrixPlayback } from "../../playback/useMatrixPlayback";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { PageContainer, Pill, SectionCard, semantic } from "../../ui";

const STEPS: { value: MatrixProcessingStep; help: string }[] = [
  { value: "raw", help: "Straight from the model, at the finest resolution." },
  { value: "collapsed", help: "Merged down to the resolution you chose." },
  { value: "clean", help: "Held notes cut short wherever something else is struck." },
  { value: "two-hands", help: "Split at middle C into right and left." },
];

/** State tagged with the request it belongs to, so nothing stale leaks through. */
interface MatrixState {
  key: string;
  envelope: MatrixEnvelope | null;
  error: string | null;
}

interface AudioContextState {
  key: string;
  audio: AudioItem | null;
  source: AudioItem | null;
}

export function MatrixPage() {
  const { artifact, update, hasArtifact } = useWorkingArtifact();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState<MatrixProcessingStep>("clean");
  const [loaded, setLoaded] = useState<MatrixState>({ key: "", envelope: null, error: null });
  const [searchText, setSearchText] = useState("");
  const [focusFrame, setFocusFrame] = useState<number | null>(() => {
    const requested = Number(searchParams.get("frame"));
    return Number.isInteger(requested) && requested >= 0 ? requested : null;
  });
  const [searchError, setSearchError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editTool, setEditTool] = useState<1 | -1>(1);
  const [stagedEdits, setStagedEdits] = useState<MatrixCellEdit[]>([]);
  const [selectedCells, setSelectedCells] = useState<Set<string>>(new Set());
  const [editBusy, setEditBusy] = useState(false);
  const [editMessage, setEditMessage] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [audioContext, setAudioContext] = useState<AudioContextState>({
    key: "",
    audio: null,
    source: null,
  });

  const audioUuid = artifact.audioUuid ?? null;
  const requestKey = audioUuid
    ? `${audioUuid}:${step}:${artifact.granularity}:${artifact.tempoBpm}:${revision}`
    : "";

  // Derived, not assigned in an effect: a new key means "loading", full stop.
  const current = loaded.key === requestKey ? loaded : { key: requestKey, envelope: null, error: null };
  const envelope = current.envelope;
  const currentAudioContext =
    audioContext.key === audioUuid
      ? audioContext
      : { key: audioUuid ?? "", audio: null, source: null };

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();
    audioApi
      .get(audioUuid, controller.signal)
      .then(async (audio) => {
        const source = audio.sourceAudioUuid
          ? await audioApi.get(audio.sourceAudioUuid, controller.signal)
          : null;
        if (!controller.signal.aborted) {
          setAudioContext({ key: audioUuid, audio, source });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setAudioContext({ key: audioUuid, audio: null, source: null });
        }
      });
    return () => controller.abort();
  }, [audioUuid]);

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();

    matrixApi
      .get(
        audioUuid,
        {
          step,
          granularity: artifact.granularity,
          tempoBpm: artifact.tempoBpm,
          sparse: false, // the grid draws the dense form
        },
        controller.signal,
      )
      .then((fetched) => setLoaded({ key: requestKey, envelope: fetched, error: null }))
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: requestKey,
          envelope: null,
          error: caught instanceof Error ? caught.message : "Could not load the matrix.",
        });
      });

    return () => controller.abort();
  }, [audioUuid, step, artifact.granularity, artifact.tempoBpm, requestKey]);

  const previewEdits = useCallback(
    async (edits: MatrixCellEdit[], persist = false) => {
      if (!audioUuid) return;
      setEditBusy(true);
      setEditError(null);
      setEditMessage(null);
      try {
        const result = await matrixApi.edit(audioUuid, {
          tempoBpm: artifact.tempoBpm,
          granularity: artifact.granularity,
          edits,
          persist,
        });
        setLoaded({ key: requestKey, envelope: result.envelope, error: null });
        setStagedEdits(persist ? [] : edits);
        setSelectedCells(new Set());
        setEditMessage(
          persist
            ? "Saved. Every Playground view now uses this edited matrix."
            : `${edits.length} staged change${edits.length === 1 ? "" : "s"} — Save to keep them.`,
        );
      } catch (caught) {
        setEditError(caught instanceof Error ? caught.message : "The edit could not be applied.");
      } finally {
        setEditBusy(false);
      }
    },
    [audioUuid, artifact.tempoBpm, artifact.granularity, requestKey],
  );

  const onCellClick = useCallback(
    (frame: number, key: number, shiftKey: boolean) => {
      if (!editMode || editBusy) return;
      const value = envelope?.denseMatrix?.[frame]?.[key] ?? 0;
      const id = `${frame}:${key}`;

      if (value !== 0) {
        setSelectedCells((current) => {
          const next = shiftKey ? new Set(current) : new Set<string>();
          if (next.has(id)) next.delete(id);
          else next.add(id);
          return next;
        });
        return;
      }

      void previewEdits([...stagedEdits, { frame, key, value: editTool }]);
    },
    [editMode, editBusy, editTool, envelope, previewEdits, stagedEdits],
  );

  const deleteSelected = useCallback(() => {
    if (!selectedCells.size) return;
    const deletions: MatrixCellEdit[] = [...selectedCells].map((id) => {
      const [frame, key] = id.split(":").map(Number);
      return { frame, key, value: 0 };
    });
    void previewEdits([...stagedEdits, ...deletions]);
  }, [previewEdits, selectedCells, stagedEdits]);

  const cancelEdits = useCallback(() => {
    setStagedEdits([]);
    setSelectedCells(new Set());
    setEditMessage(null);
    setEditError(null);
    setRevision((currentRevision) => currentRevision + 1);
  }, []);

  const beginEditing = useCallback(() => {
    setStep("clean");
    setEditMode(true);
    setEditMessage("Click an empty cell to place a note. Click sounding cells to select them.");
    setEditError(null);
  }, []);

  const selectedCount = selectedCells.size;
  const hasStagedEdits = stagedEdits.length > 0;
  const editHelp = useMemo(
    () =>
      editTool === 1
        ? "Onset starts or re-strikes a note."
        : "Sustain is allowed only immediately after the same key is sounding.",
    [editTool],
  );

  const playbackDense = useMemo(
    () => envelope?.denseMatrix ?? envelope?.denseRMatrix ?? [],
    [envelope],
  );
  const playbackLeft = envelope?.denseLMatrix ?? null;
  const playbackStepSeconds = envelope?.timeStepSeconds ?? 1;
  const playbackNotes = useMemo(
    () => extractMatrixNotes(playbackDense, playbackLeft, playbackStepSeconds),
    [playbackDense, playbackLeft, playbackStepSeconds],
  );
  const matrixPlayback = useMatrixPlayback({
    notes: playbackNotes,
    timeStepSeconds: playbackStepSeconds,
    durationSeconds: playbackDense.length * playbackStepSeconds,
    source: "piano",
  });

  const search = useCallback(() => {
    setSearchError(null);
    const text = searchText.trim();
    if (!text) return;

    const frames = envelope?.denseMatrix?.length ?? envelope?.denseRMatrix?.length ?? 0;

    // A bare integer is a frame number; anything with a colon or a dot is a time.
    if (/^\d+$/.test(text)) {
      const frame = Number(text);
      if (frame >= frames) {
        setSearchError(`This piece only has ${frames} frames.`);
        return;
      }
      setFocusFrame(frame);
      return;
    }

    const seconds = parseTime(text);
    if (seconds === null) {
      setSearchError("Type a frame number (e.g. 48) or a time (e.g. 1:23.50).");
      return;
    }
    const step = envelope?.timeStepSeconds ?? 1;
    const frame = Math.floor(seconds / step);
    if (frame >= frames) {
      setSearchError(`That is past the end — the piece lasts ${(frames * step).toFixed(2)} s.`);
      return;
    }
    setFocusFrame(frame);
  }, [searchText, envelope]);

  if (!hasArtifact || !audioUuid) {
    return (
      <PageContainer title="Matrix" wide>
        <Alert
          severity="info"
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Go to Input
            </Button>
          }
        >
          No piece loaded. Pick or record an audio on the Input tab and transcribe it first.
        </Alert>
      </PageContainer>
    );
  }

  const dense = envelope?.denseMatrix ?? envelope?.denseRMatrix ?? null;
  const denseLeft = envelope?.denseLMatrix ?? null;

  return (
    <PageContainer
      title="Matrix"
      subtitle="The 88 x N grid: a filled circle is a struck note, a pale one is that note still held."
      wide
      actions={
        <>
          <Button
            size="small"
            variant={editMode ? "contained" : "outlined"}
            startIcon={editMode ? <CloseIcon /> : <EditIcon />}
            onClick={() => {
              if (editMode) {
                cancelEdits();
                setEditMode(false);
              } else {
                beginEditing();
              }
            }}
          >
            {editMode ? "Exit edit mode" : "Edit cells"}
          </Button>
          <Button
            component="a"
            href={matrixApi.exportUrl(audioUuid, {
              step,
              granularity: artifact.granularity,
              tempoBpm: artifact.tempoBpm,
              sparse: true,
            })}
            size="small"
            startIcon={<DownloadIcon />}
          >
            Sparse JSON
          </Button>
          <Button
            component="a"
            href={matrixApi.exportUrl(audioUuid, {
              step,
              granularity: artifact.granularity,
              tempoBpm: artifact.tempoBpm,
              sparse: false,
            })}
            size="small"
            startIcon={<DownloadIcon />}
          >
            Dense JSON
          </Button>
        </>
      }
    >
      {currentAudioContext.audio?.sourceTimeRange ? (
        <Alert
          severity="info"
          sx={{ mb: 2 }}
          icon={<Chip label="SEGMENT" color="info" size="small" />}
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Change segment
            </Button>
          }
        >
          <strong>{currentAudioContext.audio.alias}</strong> is a saved fragment of{" "}
          <strong>{currentAudioContext.source?.alias ?? "the original audio"}</strong>: original
          time{" "}
          <strong>
            {formatTime(currentAudioContext.audio.sourceTimeRange.startSeconds)}–{" "}
            {formatTime(currentAudioContext.audio.sourceTimeRange.endSeconds)}
          </strong>
          . Matrix and playback time below are local to the fragment, starting at 00:00.00.
        </Alert>
      ) : currentAudioContext.audio ? (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          icon={<Chip label="ENTIRE TRACK" color="success" size="small" />}
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Create segment
            </Button>
          }
        >
          <strong>{currentAudioContext.audio.alias}</strong> is the entire audio
          {currentAudioContext.audio.durationSeconds
            ? ` (${formatTime(currentAudioContext.audio.durationSeconds)})`
            : ""}
          . Matrix time and original-audio time are the same.
        </Alert>
      ) : null}

      <SectionCard>
        <Stack spacing={2}>
          <Box>
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
              {STEPS.map((item) => (
                <Pill
                  key={item.value}
                  label={item.value}
                  title={item.help}
                  selected={step === item.value}
                  color={semantic.steps[item.value]}
                  onClick={editMode ? undefined : () => setStep(item.value)}
                />
              ))}
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
              {STEPS.find((item) => item.value === step)?.help}
            </Typography>
          </Box>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            sx={{ alignItems: { sm: "center" } }}
          >
            <TextField
              label="BPM"
              type="number"
              size="small"
              value={artifact.tempoBpm}
              onChange={(event) => update({ tempoBpm: Number(event.target.value) || 60 })}
              disabled={editMode || editBusy}
              slotProps={{ htmlInput: { min: 20, max: 300, step: 1 } }}
              sx={{ width: 110 }}
            />
            <TextField
              label="Resolution"
              select
              size="small"
              value={artifact.granularity}
              onChange={(event) => update({ granularity: event.target.value as Granularity })}
              disabled={editMode || editBusy}
              sx={{ minWidth: 200 }}
            >
              {TRANSCRIPTION_GRANULARITIES.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>

            <Typography variant="caption" color="text.secondary">
              Recomputed from the stored raw matrix — no re-transcription.
            </Typography>

            <Box sx={{ flexGrow: 1 }} />

            <TextField
              label={
                currentAudioContext.audio?.sourceTimeRange
                  ? "Go to local frame or time"
                  : "Go to frame or time"
              }
              size="small"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && search()}
              placeholder="48  or  1:23.50"
              error={Boolean(searchError)}
              helperText={searchError}
              sx={{ width: 220 }}
            />
            <Button size="small" startIcon={<SearchIcon />} onClick={search}>
              Go
            </Button>
          </Stack>

          {editMode ? (
            <>
              <Divider />
              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={1}
                sx={{ alignItems: { md: "center" } }}
              >
                <Typography variant="subtitle2">Edit palette</Typography>
                <Button
                  size="small"
                  variant={editTool === 1 ? "contained" : "outlined"}
                  onClick={() => setEditTool(1)}
                  disabled={editBusy}
                >
                  ● Onset
                </Button>
                <Button
                  size="small"
                  variant={editTool === -1 ? "contained" : "outlined"}
                  onClick={() => setEditTool(-1)}
                  disabled={editBusy}
                >
                  ○ Sustain
                </Button>
                <Typography variant="caption" color="text.secondary">
                  {editHelp}
                </Typography>
                <Box sx={{ flexGrow: 1 }} />
                <Button
                  size="small"
                  color="error"
                  startIcon={<DeleteIcon />}
                  disabled={!selectedCount || editBusy}
                  onClick={deleteSelected}
                >
                  Delete {selectedCount || ""}
                </Button>
                <Button
                  size="small"
                  startIcon={<CloseIcon />}
                  disabled={!hasStagedEdits || editBusy}
                  onClick={cancelEdits}
                >
                  Cancel
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<SaveIcon />}
                  disabled={!hasStagedEdits || editBusy}
                  onClick={() => void previewEdits(stagedEdits, true)}
                >
                  Save
                </Button>
                {editBusy ? <CircularProgress size={18} /> : null}
              </Stack>
            </>
          ) : null}
        </Stack>
      </SectionCard>

      {envelope && playbackDense.length ? (
        <SectionCard
          title="Matrix player"
        >
          <Stack spacing={1}>
            <Typography variant="body2" color="text.secondary">
              Synthesized piano follows the circles; held cells decay gently instead of
              re-striking.
            </Typography>
            <PlaybackTransport playback={matrixPlayback} />
          </Stack>
        </SectionCard>
      ) : null}

      {current.error ? <Alert severity="error">{current.error}</Alert> : null}
      {editError ? <Alert severity="error">{editError}</Alert> : null}
      {editMessage ? <Alert severity={hasStagedEdits ? "warning" : "info"}>{editMessage}</Alert> : null}

      {!envelope && !current.error ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 3 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading the matrix…
          </Typography>
        </Stack>
      ) : null}

      {envelope && dense && envelope.columnHeaders && envelope.rowTimestamps ? (
        <MatrixGrid
          dense={dense}
          denseLeft={step === "two-hands" ? denseLeft : null}
          columnHeaders={envelope.columnHeaders}
          rowTimestamps={envelope.rowTimestamps}
          timeStepSeconds={envelope.timeStepSeconds}
          focusFrame={focusFrame}
          onCellClick={editMode ? onCellClick : undefined}
          selectedCells={selectedCells}
          cursorFrame={matrixPlayback.currentFrame}
          sourceOffsetSeconds={
            currentAudioContext.audio?.sourceTimeRange?.startSeconds ?? null
          }
        />
      ) : null}

      {envelope && dense && dense.length === 0 ? (
        <Alert severity="warning" sx={{ mt: 2 }}>
          This matrix is empty. If you transcribed with the <code>silent</code> engine, install a
          real one with <code>uv sync --extra transcription</code> and run it again.
        </Alert>
      ) : null}
    </PageContainer>
  );
}

export default MatrixPage;
