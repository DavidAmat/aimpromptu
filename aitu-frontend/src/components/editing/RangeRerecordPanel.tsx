/**
 * Re-record a marked stretch: choose a speed, play the passage, record, preview, accept.
 *
 * Lives in the Frames toolbox as a new tab. Key and Octave are untouched.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import StopIcon from "@mui/icons-material/Stop";
import {
  editingApi,
  matrixApi,
  type AcceptResult,
  type Confirmation,
  type EditPreview,
  type EditSession,
  type FigureName,
  type SlowdownChoice,
  type SpeedChange,
} from "../../api";
import { fileNameFor, useRecorder } from "../../audio/useRecorder";
import { formatTime, parseTime } from "../../audio/time";
import { useProgress } from "../../hooks/useProgress";
import LiveLevelBars from "../audio/LiveLevelBars";
import ProgressBanner from "../ProgressBanner";
import PeakPlot from "../time/PeakPlot";
import { TimeScoreView } from "../time/TimeScoreView";
import { useClickTrack } from "./useClickTrack";

const SPEEDS: { id: SlowdownChoice | "fit"; label: string }[] = [
  { id: 1, label: "Original speed" },
  { id: 2, label: "2× slower" },
  { id: 4, label: "4× slower" },
  { id: "fit", label: "Fit to the window" },
];

export interface RangeRerecordPanelProps {
  audioUuid: string;
  frameMs: number;
  fromColumn?: number;
  toColumn?: number;
  startSeconds?: number;
  endSeconds?: number;
  anchorFigure?: FigureName;
  anchorMs?: number;
  speedChanges?: SpeedChange[];
  clickIntervalMs?: number;
  onRangeChange?: (startSeconds: number, endSeconds: number) => void;
  onAccepted?: (result: AcceptResult) => void;
}

function windowSecondsOf(props: RangeRerecordPanelProps): number {
  if (props.startSeconds !== undefined && props.endSeconds !== undefined) {
    return Math.max(0, props.endSeconds - props.startSeconds);
  }
  if (props.fromColumn !== undefined && props.toColumn !== undefined) {
    return ((props.toColumn - props.fromColumn) * props.frameMs) / 1000;
  }
  return 0;
}

function startSecondsOf(props: RangeRerecordPanelProps): number {
  if (props.startSeconds !== undefined) return props.startSeconds;
  if (props.fromColumn !== undefined) return (props.fromColumn * props.frameMs) / 1000;
  return 0;
}

function endSecondsOf(props: RangeRerecordPanelProps): number {
  if (props.endSeconds !== undefined) return props.endSeconds;
  if (props.toColumn !== undefined) return (props.toColumn * props.frameMs) / 1000;
  return 0;
}

export function RangeRerecordPanel({
  audioUuid,
  frameMs,
  fromColumn,
  toColumn,
  startSeconds,
  endSeconds,
  anchorFigure = "negra",
  anchorMs,
  speedChanges,
  clickIntervalMs,
  onRangeChange,
  onAccepted,
}: RangeRerecordPanelProps) {
  const recorder = useRecorder();
  const clicks = useClickTrack();
  const playing = useRef<HTMLAudioElement | null>(null);

  const [session, setSession] = useState<EditSession | null>(null);
  const [speed, setSpeed] = useState<SlowdownChoice | "fit">(2);
  const [clickOn, setClickOn] = useState(false);
  const [clickMs, setClickMs] = useState(
    String(Math.round((clickIntervalMs ?? 480) * 2)),
  );
  const [spliceAudio, setSpliceAudio] = useState(true);
  const derivedStart = formatTime(
    session?.startSeconds ??
      startSecondsOf({
        audioUuid,
        frameMs,
        fromColumn,
        toColumn,
        startSeconds,
        endSeconds,
      }),
  );
  const derivedEnd = formatTime(
    session?.endSeconds ??
      endSecondsOf({
        audioUuid,
        frameMs,
        fromColumn,
        toColumn,
        startSeconds,
        endSeconds,
      }),
  );
  const [startDraft, setStartDraft] = useState<{ for: string; value: string } | null>(
    null,
  );
  const [endDraft, setEndDraft] = useState<{ for: string; value: string } | null>(
    null,
  );
  const startText = startDraft?.for === derivedStart ? startDraft.value : derivedStart;
  const endText = endDraft?.for === derivedEnd ? endDraft.value : derivedEnd;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [preview, setPreview] = useState<EditPreview | null>(null);
  const [confirm, setConfirm] = useState<Confirmation | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [result, setResult] = useState<AcceptResult | null>(null);

  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);
  const transcribeFailed = progress.status === "error";
  const working = transcribeFailed ? false : busy || progress.status === "running";
  const displayError = transcribeFailed
    ? (progress.error ?? "Transcription failed.")
    : error;
  const frozen = Boolean(session?.hasTake);
  const windowSeconds = session?.windowSeconds ?? windowSecondsOf({ audioUuid, frameMs, fromColumn, toColumn, startSeconds, endSeconds });
  const expected =
    speed === "fit" ? null : windowSeconds * (speed as number);

  const stopPlayback = () => {
    playing.current?.pause();
    playing.current = null;
  };

  const play = (url: string) => {
    stopPlayback();
    const audio = new Audio(url);
    playing.current = audio;
    void audio.play();
  };

  const ensureSession = useCallback(async (): Promise<EditSession> => {
    if (session) return session;
    const body = fromColumn !== undefined && toColumn !== undefined
      ? { startFrame: fromColumn, endFrame: toColumn, frameMs }
      : {
          startSeconds: parseTime(startText) ?? startSecondsOf({ audioUuid, frameMs, startSeconds, fromColumn }),
          endSeconds: parseTime(endText) ?? endSecondsOf({ audioUuid, frameMs, endSeconds, toColumn }),
          frameMs,
        };
    const created = await editingApi.start(audioUuid, {
      ...body,
      slowdown: speed === "fit" ? null : speed,
      spliceAudio,
      clickIntervalMs: Number(clickMs) || undefined,
    });
    setSession(created);
    return created;
  }, [session, fromColumn, toColumn, frameMs, startText, endText, audioUuid, startSeconds, endSeconds, speed, spliceAudio, clickMs]);

  const applyTimes = () => {
    if (frozen) return;
    const start = parseTime(startText);
    const end = parseTime(endText);
    if (start === null || end === null || end <= start) return;
    onRangeChange?.(start, end);
  };

  const hearOriginal = async (slowed: boolean) => {
    setError(null);
    try {
      const current = await ensureSession();
      play(editingApi.windowUrl(audioUuid, current.sessionUuid, slowed));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not play the passage.");
    }
  };

  const beginRecording = async () => {
    setError(null);
    setPreview(null);
    try {
      await ensureSession();
      if (clickOn) {
        const interval = Number(clickMs);
        if (interval > 0) clicks.start(interval);
      }
      await recorder.start();
    } catch (caught) {
      clicks.stop();
      setError(caught instanceof Error ? caught.message : "Could not start recording.");
    }
  };

  const stopRecording = () => {
    clicks.stop();
    recorder.stop();
  };

  const submitTake = async () => {
    if (!recorder.blob) return;
    const filename = fileNameFor(recorder.blob.type, "take");
    if (!filename) {
      setError("This browser recorded a format we do not recognize.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const current = await ensureSession();
      const file = new File([recorder.blob], filename, { type: recorder.blob.type });
      const updated = await editingApi.uploadTake(audioUuid, current.sessionUuid, file);
      setSession(updated);
      const job = await editingApi.transcribe(audioUuid, current.sessionUuid);
      setJobId(job.jobId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not send the take.");
      setBusy(false);
    }
  };

  useEffect(() => {
    if (progress.status !== "done" || !session) return;
    let cancelled = false;
    editingApi
      .preview(audioUuid, session.sessionUuid, {
        anchorFigure,
        anchorMs,
        speedChanges,
      })
      .then((next) => {
        if (cancelled) return;
        setPreview(next);
        setSession(next.session);
        setBusy(false);
        setJobId(null);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(caught instanceof Error ? caught.message : "Could not preview the take.");
        setBusy(false);
        setJobId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [progress.status, audioUuid, session, anchorFigure, anchorMs, speedChanges]);

  const changeSpeed = async (next: SlowdownChoice | "fit") => {
    setSpeed(next);
    if (!session?.hasEvents) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await editingApi.patch(audioUuid, session.sessionUuid, {
        slowdown: next === "fit" ? undefined : next,
        fit: next === "fit",
      });
      setSession(updated);
      const shown = await editingApi.preview(audioUuid, session.sessionUuid, {
        anchorFigure,
        anchorMs,
        speedChanges,
      });
      setPreview(shown);
      setSession(shown.session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not change the speed.");
    } finally {
      setBusy(false);
    }
  };

  const cancelSession = async () => {
    stopPlayback();
    clicks.stop();
    if (session) {
      try {
        await editingApi.cancel(audioUuid, session.sessionUuid);
      } catch {
        // The folder may already be gone.
      }
    }
    recorder.reset();
    setSession(null);
    setPreview(null);
    setConfirm(null);
    setResult(null);
    setJobId(null);
    setError(null);
  };

  const openConfirm = async () => {
    if (!session) return;
    try {
      setConfirm(await editingApi.confirmation(audioUuid, session.sessionUuid));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not prepare the confirmation.");
    }
  };

  const commit = async () => {
    if (!session) return;
    setAccepting(true);
    try {
      const accepted = await editingApi.accept(audioUuid, session.sessionUuid);
      setResult(accepted);
      setConfirm(null);
      setSession(null);
      onAccepted?.(accepted);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not accept the edit.");
    } finally {
      setAccepting(false);
    }
  };

  return (
    <Box sx={{ maxHeight: "70vh", overflow: "auto", pr: 0.5 }}>
      <Stack spacing={1.5}>
        {displayError ? <Alert severity="error">{displayError}</Alert> : null}
        {result ? (
          <Alert severity="success">
            Version {result.version}. {result.notesArriving} notes in,{" "}
            {result.notesRemoved} out. Length unchanged.
            {result.audioMismatch
              ? " The recording does not match the sheet in this window."
              : ""}
          </Alert>
        ) : null}

        <Typography variant="body2">
          Window <strong>{windowSeconds.toFixed(2)} s</strong>
          {expected !== null ? ` · take should last about ${expected.toFixed(2)} s` : ""}
        </Typography>

        <Stack direction="row" spacing={1}>
          <TextField
            size="small"
            label="From"
            value={startText}
            disabled={frozen}
            onChange={(event) =>
              setStartDraft({ for: derivedStart, value: event.target.value })
            }
            onBlur={applyTimes}
          />
          <TextField
            size="small"
            label="To"
            value={endText}
            disabled={frozen}
            onChange={(event) =>
              setEndDraft({ for: derivedEnd, value: event.target.value })
            }
            onBlur={applyTimes}
          />
        </Stack>

        <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
          {SPEEDS.map((choice) => (
            <Button
              key={String(choice.id)}
              size="small"
              variant={speed === choice.id ? "contained" : "outlined"}
              onClick={() => void changeSpeed(choice.id)}
              disabled={working}
            >
              {choice.label}
            </Button>
          ))}
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
          <Button size="small" onClick={() => void hearOriginal(false)} disabled={working}>
            Hear original
          </Button>
          <Button
            size="small"
            onClick={() => void hearOriginal(true)}
            disabled={working || speed === "fit" || speed === 1}
          >
            Hear slowed
          </Button>
        </Stack>

        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={clickOn}
              onChange={(event) => setClickOn(event.target.checked)}
            />
          }
          label="Click track while recording"
        />
        {clickOn ? (
          <TextField
            size="small"
            label="Click every (ms)"
            value={clickMs}
            onChange={(event) => setClickMs(event.target.value)}
            helperText="Sound only. Nothing about this is stored."
          />
        ) : null}

        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={spliceAudio}
              onChange={(event) => setSpliceAudio(event.target.checked)}
            />
          }
          label="Splice audio on accept"
        />

        {recorder.error ? <Alert severity="error">{recorder.error}</Alert> : null}
        <LiveLevelBars levels={recorder.levels} active={recorder.status === "recording"} height={48} />
        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
          {recorder.status === "recording" ? (
            <Button
              size="small"
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={stopRecording}
            >
              Stop {formatTime(recorder.elapsedSeconds)}
            </Button>
          ) : (
            <Button
              size="small"
              variant="contained"
              color="error"
              startIcon={<FiberManualRecordIcon />}
              onClick={() => void beginRecording()}
              disabled={working}
            >
              Record
            </Button>
          )}
          {recorder.status === "recorded" ? (
            <Button size="small" variant="contained" onClick={() => void submitTake()} disabled={working}>
              {busy ? <CircularProgress size={14} /> : "Transcribe this take"}
            </Button>
          ) : null}
        </Stack>

        {jobId ? <ProgressBanner progress={progress} fallbackLabel="Transcribing the take" /> : null}

        {preview ? (
          <Stack spacing={1}>
            <Typography variant="caption" color="text.secondary">
              {preview.scaledNoteCount} notes scaled into the window. A wrong speed puts every peak
              one step away from the ladder.
            </Typography>
            {preview.peaks.length > 0 ? (
              <PeakPlot peaks={preview.peaks} labelled={preview.labelled} height={140} />
            ) : null}
            <TimeScoreView score={preview.score} readOnly availableWidth={300} />
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
              <Button
                size="small"
                onClick={() => play(editingApi.takeUrl(audioUuid, preview.session.sessionUuid, false))}
              >
                Take as played
              </Button>
              <Button
                size="small"
                onClick={() => play(editingApi.takeUrl(audioUuid, preview.session.sessionUuid, true))}
              >
                Take scaled
              </Button>
              <Button
                size="small"
                onClick={() => play(editingApi.windowUrl(audioUuid, preview.session.sessionUuid, false))}
              >
                Original window
              </Button>
            </Stack>
            <Stack direction="row" spacing={1}>
              <Button size="small" variant="contained" onClick={() => void openConfirm()} disabled={working}>
                Accept
              </Button>
              <Button size="small" color="error" onClick={() => void cancelSession()}>
                Cancel
              </Button>
            </Stack>
          </Stack>
        ) : session ? (
          <Button size="small" color="error" onClick={() => void cancelSession()}>
            Cancel session
          </Button>
        ) : null}
      </Stack>

      <Dialog open={confirm !== null} onClose={() => setConfirm(null)}>
        <DialogTitle>Accept this replacement?</DialogTitle>
        <DialogContent>
          {confirm ? (
            <Stack spacing={0.75} sx={{ pt: 1 }}>
              <Typography variant="body2">{confirm.notesRemoved} notes leave the window.</Typography>
              <Typography variant="body2">{confirm.notesArriving} notes arrive.</Typography>
              <Typography variant="body2">
                Marks dropped: {confirm.droppedMarks.figureOverrides} figure
                {confirm.droppedMarks.figureOverrides === 1 ? "" : "s"},{" "}
                {confirm.droppedMarks.beamBreaks} beam break
                {confirm.droppedMarks.beamBreaks === 1 ? "" : "s"},{" "}
                {confirm.droppedMarks.fingerings} fingering
                {confirm.droppedMarks.fingerings === 1 ? "" : "s"},{" "}
                {confirm.droppedMarks.hiddenNotes} hidden note
                {confirm.droppedMarks.hiddenNotes === 1 ? "" : "s"}.
              </Typography>
              <Typography variant="body2">
                {confirm.spliceAudio
                  ? "The recording in this window will be replaced, pitch preserved."
                  : "The recording is left as it is; this window will be marked as not matching the sheet."}
              </Typography>
              <Typography variant="body2">The piece's length does not change.</Typography>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Back</Button>
          <Button variant="contained" onClick={() => void commit()} disabled={accepting}>
            {accepting ? <CircularProgress size={14} /> : "Accept"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default RangeRerecordPanel;
