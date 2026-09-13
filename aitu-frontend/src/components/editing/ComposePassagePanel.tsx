/**
 * Build a piece one passage at a time (Epic 13, Task 13.1.1).
 *
 * Almost all of this is the Re-record panel with the window taken out. You play a passage, look at
 * its own sheet and its own peak plot, throw it away and play it again as often as you like, and
 * only then say where it goes. Nothing is written to the piece until you do.
 *
 * The one thing that is genuinely different is placing it. Re-recording writes a take back into
 * exactly the stretch it replaces and the piece keeps its length; here there is no stretch to fit
 * into, so the passage is as long as it was played (divided by the speed you chose) and the piece
 * gets longer by that much. Inserting one in the middle moves everything after it — notes,
 * fingerings, words, key changes, all of it — and the confirmation says how many of each before
 * anything moves, because a mark that has silently moved looks exactly like one that has not.
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
  type Placement,
  type SlowdownChoice,
  type SpeedChange,
} from "../../api";
import { fileNameFor, useRecorder } from "../../audio/useRecorder";
import { formatTime, parseTime } from "../../audio/time";
import { useProgress } from "../../hooks/useProgress";
import LiveLevelBars from "../audio/LiveLevelBars";
import WaveformRangeSelector, { type AudioRange } from "../audio/WaveformRangeSelector";
import ProgressBanner from "../ProgressBanner";
import PeakPlot from "../time/PeakPlot";
import { TimeScoreView } from "../time/TimeScoreView";
import { useClickTrack } from "./useClickTrack";

/**
 * No "Fit to the window" here, on purpose: there is no window to fit to, so the speed is the whole
 * answer — play at half speed, choose 2× slower, and the passage occupies half the time it took to
 * play (Subtask 13.1.1.4).
 */
const SPEEDS: { id: SlowdownChoice; label: string }[] = [
  { id: 1, label: "Original speed" },
  { id: 2, label: "2× slower" },
  { id: 4, label: "4× slower" },
];

type ComposePlacement = Extract<Placement, "append" | "insert">;

const PLACEMENTS: { id: ComposePlacement; label: string; hint: string }[] = [
  {
    id: "append",
    label: "After the last note",
    hint: "The passage goes at the end, after the silence you set. Nothing already written moves.",
  },
  {
    id: "insert",
    label: "At a moment",
    hint: "The piece opens at that moment and everything after it moves later by the passage's length.",
  },
];

export interface ComposePassagePanelProps {
  audioUuid: string;
  frameMs: number;
  /** How long the piece is now, so a moment can be offered inside it. */
  durationSeconds?: number;
  /** The column the reader had marked, if any: the natural moment to open at. */
  atColumn?: number;
  anchorFigure?: FigureName;
  anchorMs?: number;
  speedChanges?: SpeedChange[];
  clickIntervalMs?: number;
  onPlaced?: (result: AcceptResult) => void;
}

function explain(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback;
}

export function ComposePassagePanel({
  audioUuid,
  frameMs,
  durationSeconds = 0,
  atColumn,
  anchorFigure = "negra",
  anchorMs,
  speedChanges,
  clickIntervalMs,
  onPlaced,
}: ComposePassagePanelProps) {
  const recorder = useRecorder();
  const clicks = useClickTrack();
  const playing = useRef<HTMLAudioElement | null>(null);

  const empty = durationSeconds <= 0;
  const [session, setSession] = useState<EditSession | null>(null);
  const [placement, setPlacement] = useState<ComposePlacement>("append");
  const [gapText, setGapText] = useState("1.0");
  const [atText, setAtText] = useState(
    formatTime(atColumn !== undefined ? (atColumn * frameMs) / 1000 : 0),
  );
  const [speed, setSpeed] = useState<SlowdownChoice>(1);
  const [clickOn, setClickOn] = useState(false);
  const [clickMs, setClickMs] = useState(String(Math.round(clickIntervalMs ?? 480)));
  const [spliceAudio, setSpliceAudio] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [preview, setPreview] = useState<EditPreview | null>(null);
  const [confirm, setConfirm] = useState<Confirmation | null>(null);
  const [placingNow, setPlacingNow] = useState(false);
  const [result, setResult] = useState<AcceptResult | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [takeRange, setTakeRange] = useState<AudioRange | null>(null);

  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);
  const transcribeFailed = progress.status === "error";
  const working = transcribeFailed ? false : busy || progress.status === "running";
  const displayError = transcribeFailed ? (progress.error ?? "Transcription failed.") : error;
  /** Once a take exists, where the passage goes is still open but how it was played is not. */
  const frozen = Boolean(session?.hasTake);
  const passageSeconds = session?.windowSeconds ?? 0;

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

  useEffect(() => stopPlayback, []);

  const ensureSession = useCallback(async (): Promise<EditSession> => {
    if (session) return session;
    const created = await editingApi.start(audioUuid, {
      placement,
      frameMs,
      slowdown: speed,
      spliceAudio,
      clickIntervalMs: Number(clickMs) || undefined,
      ...(placement === "append"
        ? { gapSeconds: Math.max(0, Number(gapText) || 0) }
        : { startSeconds: parseTime(atText) ?? 0 }),
    });
    setSession(created);
    return created;
  }, [session, audioUuid, placement, frameMs, speed, spliceAudio, clickMs, gapText, atText]);

  /** Moving the passage must not cost the take, so a live session is re-anchored rather than re-made. */
  const moveTo = async (next: {
    placement?: ComposePlacement;
    gapSeconds?: number;
    atSeconds?: number;
  }) => {
    const target = next.placement ?? placement;
    if (next.placement) setPlacement(next.placement);
    if (!session) return;
    if (target !== session.placement) {
      // A session is opened for one placement. Changing it before a take exists is free; after one
      // exists it would throw the recording away, so the panel simply keeps the session it has and
      // lets the reader cancel if they really meant to start again.
      if (session.hasTake) {
        setError("This take was staged to be appended. Cancel it to place it somewhere else.");
        return;
      }
      await editingApi.cancel(audioUuid, session.sessionUuid).catch(() => undefined);
      setSession(null);
      return;
    }
    setError(null);
    try {
      const moved = await editingApi.patch(audioUuid, session.sessionUuid, {
        gapSeconds: next.gapSeconds,
        atSeconds: next.atSeconds,
      });
      setSession(moved);
      if (preview) setPreview({ ...preview, session: moved });
    } catch (caught) {
      setError(explain(caught, "Could not move the passage."));
    }
  };

  const applyGap = () => {
    const seconds = Number(gapText);
    if (!Number.isFinite(seconds) || seconds < 0) return;
    void moveTo({ gapSeconds: seconds });
  };

  const applyMoment = () => {
    const seconds = parseTime(atText);
    if (seconds === null) return;
    void moveTo({ atSeconds: seconds });
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
      setError(explain(caught, "Could not start recording."));
    }
  };

  const stopRecording = () => {
    clicks.stop();
    recorder.stop();
  };

  const openReview = async () => {
    if (!recorder.blob) return;
    const filename = fileNameFor(recorder.blob.type, "passage");
    if (!filename) {
      setError("This browser recorded a format we do not recognize.");
      return;
    }
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      const current = await ensureSession();
      const file = new File([recorder.blob], filename, { type: recorder.blob.type });
      const updated = await editingApi.uploadTake(audioUuid, current.sessionUuid, file);
      setSession(updated);
      setTakeRange(
        updated.untrimmedDurationSeconds
          ? { startSeconds: 0, endSeconds: updated.untrimmedDurationSeconds }
          : null,
      );
      setReviewOpen(true);
    } catch (caught) {
      setError(explain(caught, "Could not store the take."));
    } finally {
      setBusy(false);
    }
  };

  const runTranscribe = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      if (takeRange) {
        await editingApi.patch(audioUuid, session.sessionUuid, {
          takeStartSeconds: takeRange.startSeconds,
          takeEndSeconds: takeRange.endSeconds,
        });
      }
      const job = await editingApi.transcribe(audioUuid, session.sessionUuid);
      setJobId(job.jobId);
    } catch (caught) {
      setError(explain(caught, "Could not transcribe the passage."));
      setBusy(false);
    }
  };

  const sessionUuid = session?.sessionUuid;

  const loadTakeWaveform = useCallback(
    (points: number, signal: AbortSignal) => {
      if (!sessionUuid) return Promise.reject(new Error("Record a passage first."));
      return editingApi.takeWaveform(audioUuid, sessionUuid, points, signal);
    },
    [audioUuid, sessionUuid],
  );

  useEffect(() => {
    if (progress.status !== "done" || !jobId || !sessionUuid) return;
    let cancelled = false;
    editingApi
      .get(audioUuid, sessionUuid)
      .then((refreshed) => {
        if (cancelled) return;
        setSession(refreshed);
        if (!refreshed.hasEvents) {
          throw new Error("Transcription finished but no notes were stored. Play it again.");
        }
        return editingApi.preview(audioUuid, sessionUuid, {
          anchorFigure,
          anchorMs,
          speedChanges,
        });
      })
      .then((next) => {
        if (cancelled || !next) return;
        setPreview(next);
        setSession(next.session);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(explain(caught, "Could not draw the passage."));
      })
      .finally(() => {
        if (cancelled) return;
        setBusy(false);
        setJobId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [progress.status, jobId, audioUuid, sessionUuid, anchorFigure, anchorMs, speedChanges]);

  const changeSpeed = async (next: SlowdownChoice) => {
    setSpeed(next);
    if (!session?.hasEvents) return;
    setBusy(true);
    setError(null);
    try {
      await editingApi.patch(audioUuid, session.sessionUuid, { slowdown: next });
      const shown = await editingApi.preview(audioUuid, session.sessionUuid, {
        anchorFigure,
        anchorMs,
        speedChanges,
      });
      setPreview(shown);
      setSession(shown.session);
    } catch (caught) {
      setError(explain(caught, "Could not change the speed."));
    } finally {
      setBusy(false);
    }
  };

  const discard = async () => {
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
    setJobId(null);
    setError(null);
    setReviewOpen(false);
    setTakeRange(null);
  };

  const playAgain = () => {
    stopPlayback();
    setPreview(null);
    setJobId(null);
    setTakeRange(null);
    setReviewOpen(false);
    recorder.reset();
  };

  const openConfirm = async () => {
    if (!session) return;
    try {
      setConfirm(await editingApi.confirmation(audioUuid, session.sessionUuid));
    } catch (caught) {
      setError(explain(caught, "Could not prepare the confirmation."));
    }
  };

  const commit = async () => {
    if (!session) return;
    setPlacingNow(true);
    try {
      const placed = await editingApi.accept(audioUuid, session.sessionUuid);
      setResult(placed);
      setConfirm(null);
      setSession(null);
      setPreview(null);
      setReviewOpen(false);
      recorder.reset();
      onPlaced?.(placed);
    } catch (caught) {
      setError(explain(caught, "Could not place the passage."));
    } finally {
      setPlacingNow(false);
    }
  };

  const chosen = PLACEMENTS.find((item) => item.id === placement);

  return (
    <Box sx={{ maxHeight: "70vh", overflow: "auto", pr: 0.5 }}>
      <Stack spacing={1.5}>
        {displayError ? <Alert severity="error">{displayError}</Alert> : null}
        {result ? (
          <Alert severity="success">
            Version {result.version}. {result.notesArriving} notes in, the piece is now{" "}
            {result.durationSeconds.toFixed(2)} s.
            {result.notesMoved > 0
              ? ` ${result.notesMoved} notes and ${result.movedMarks.total} marks moved ${result.movedMarks.frames} columns later.`
              : ""}
            {result.audioMismatch ? " The recording does not match the sheet here." : ""}
          </Alert>
        ) : null}

        {empty ? (
          <Typography variant="body2" color="text.secondary">
            This piece has nothing in it yet. Play a passage, look at it, play it again until it is
            right, then put it in.
          </Typography>
        ) : null}

        <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
          {PLACEMENTS.map((choice) => (
            <Button
              key={choice.id}
              size="small"
              variant={placement === choice.id ? "contained" : "outlined"}
              disabled={working || (choice.id === "insert" && empty)}
              onClick={() => void moveTo({ placement: choice.id })}
            >
              {choice.label}
            </Button>
          ))}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          {empty ? "The first passage starts the piece." : chosen?.hint}
        </Typography>

        {placement === "append" ? (
          <TextField
            size="small"
            label="Silence before it (s)"
            value={gapText}
            disabled={empty}
            onChange={(event) => setGapText(event.target.value)}
            onBlur={applyGap}
            helperText={
              empty
                ? "Ignored: there is no passage before this one to be distant from."
                : "Measured from the last note that is still on the page."
            }
          />
        ) : (
          <TextField
            size="small"
            label="Opens at"
            value={atText}
            onChange={(event) => setAtText(event.target.value)}
            onBlur={applyMoment}
            helperText={`mm:ss.cc — the piece is ${durationSeconds.toFixed(2)} s long.`}
          />
        )}

        {session ? (
          <Typography variant="body2">
            Starts at <strong>{formatTime(session.startSeconds)}</strong>
            {passageSeconds > 0
              ? ` · the passage lasts ${passageSeconds.toFixed(2)} s`
              : " · play it to find out how long it is"}
          </Typography>
        ) : null}

        <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
          {SPEEDS.map((choice) => (
            <Button
              key={choice.id}
              size="small"
              variant={speed === choice.id ? "contained" : "outlined"}
              onClick={() => void changeSpeed(choice.id)}
              disabled={working}
            >
              {choice.label}
            </Button>
          ))}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          {speed === 1
            ? "The passage lasts as long as you played it."
            : `Played slowly and written back ${speed}× shorter, so it goes at the speed you mean.`}
        </Typography>

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
              disabled={frozen}
            />
          }
          label="Add it to the recording too"
        />

        {recorder.error ? <Alert severity="error">{recorder.error}</Alert> : null}
        <LiveLevelBars
          levels={recorder.levels}
          active={recorder.status === "recording"}
          height={48}
        />
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
              Record a passage
            </Button>
          )}
          {recorder.status === "recorded" ? (
            <Button
              size="small"
              variant="contained"
              onClick={() => void openReview()}
              disabled={working}
            >
              {busy ? <CircularProgress size={14} /> : "Look at it"}
            </Button>
          ) : null}
          {session?.hasEvents && !reviewOpen ? (
            <Button size="small" onClick={() => setReviewOpen(true)}>
              Back to the passage
            </Button>
          ) : null}
        </Stack>

        {session ? (
          <Button size="small" color="error" onClick={() => void discard()}>
            Throw this passage away
          </Button>
        ) : null}
      </Stack>

      <Dialog
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        fullWidth
        maxWidth="lg"
        sx={{ zIndex: (theme) => theme.zIndex.modal + 2 }}
      >
        <DialogTitle>This passage</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {displayError ? <Alert severity="error">{displayError}</Alert> : null}
            <Typography variant="body2" color="text.secondary">
              Cut the recording the way the Input tab does, transcribe only that stretch, and read
              the passage on its own. Nothing goes into the piece until you place it.
            </Typography>

            {session?.hasTake ? (
              <WaveformRangeSelector
                key={`${session.sessionUuid}:${session.untrimmedDurationSeconds ?? 0}`}
                audioUrl={editingApi.takeUrl(audioUuid, session.sessionUuid, { untrimmed: true })}
                loadWaveform={loadTakeWaveform}
                durationSeconds={session.untrimmedDurationSeconds ?? undefined}
                onRangeChange={setTakeRange}
              />
            ) : null}

            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => void runTranscribe()}
                disabled={working || !session?.hasTake}
              >
                {busy && !preview ? <CircularProgress size={14} /> : "Read this stretch"}
              </Button>
              <Button size="small" onClick={playAgain} disabled={working}>
                Play it again
              </Button>
            </Stack>

            {jobId ? (
              <ProgressBanner progress={progress} fallbackLabel="Reading the passage" />
            ) : null}

            {preview ? (
              <Stack spacing={1.5}>
                <Typography variant="caption" color="text.secondary">
                  {preview.scaledNoteCount} notes over{" "}
                  {preview.session.windowSeconds.toFixed(2)} s, starting at{" "}
                  {formatTime(preview.session.startSeconds)}.
                </Typography>
                {preview.peaks.length > 0 ? (
                  <PeakPlot peaks={preview.peaks} labelled={preview.labelled} height={140} />
                ) : null}
                <Box sx={{ minHeight: 180, overflow: "auto" }}>
                  <TimeScoreView score={preview.score} readOnly />
                </Box>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                  <Button
                    size="small"
                    onClick={() => play(editingApi.takeUrl(audioUuid, preview.session.sessionUuid))}
                  >
                    As you played it
                  </Button>
                  <Button
                    size="small"
                    onClick={() =>
                      play(
                        editingApi.takeUrl(audioUuid, preview.session.sessionUuid, {
                          scaled: true,
                        }),
                      )
                    }
                  >
                    At the speed it will go
                  </Button>
                </Stack>
              </Stack>
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => void discard()} color="error">
            Throw it away
          </Button>
          <Button onClick={() => setReviewOpen(false)}>Back</Button>
          <Button
            variant="contained"
            onClick={() => void openConfirm()}
            disabled={working || !preview}
          >
            Put it in the piece
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        sx={{ zIndex: (theme) => theme.zIndex.modal + 3 }}
      >
        <DialogTitle>Place this passage?</DialogTitle>
        <DialogContent>
          {confirm ? (
            <Stack spacing={0.75} sx={{ pt: 1 }}>
              <Typography variant="body2">
                {confirm.notesArriving} notes arrive, over {confirm.windowSeconds.toFixed(2)} s.
              </Typography>
              <Typography variant="body2">
                The piece becomes {confirm.durationSeconds.toFixed(2)} s long.
              </Typography>
              {confirm.placement === "insert" ? (
                <Typography variant="body2">
                  {confirm.notesMoved} notes and {confirm.movedMarks.total} editorial mark
                  {confirm.movedMarks.total === 1 ? "" : "s"} move{" "}
                  {confirm.movedMarks.frames} columns later. Nothing is lost — everything keeps
                  pointing at the note it was put on.
                </Typography>
              ) : (
                <Typography variant="body2">
                  Nothing already written moves: the passage goes after the last note.
                </Typography>
              )}
              <Typography variant="body2">
                {confirm.spliceAudio
                  ? "The passage is written into the recording too, at the speed it will go."
                  : "The recording is left as it is; this stretch will be marked as not matching the sheet."}
              </Typography>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Back</Button>
          <Button variant="contained" onClick={() => void commit()} disabled={placingNow}>
            {placingNow ? <CircularProgress size={14} /> : "Place it"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ComposePassagePanel;
