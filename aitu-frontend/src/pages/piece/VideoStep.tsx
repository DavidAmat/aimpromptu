/**
 * Step 2 of a video project, **Video** (implementation 02, plan section 10.2): the video with the
 * piano fitted on it, and **Read notes**.
 *
 * A project made from a piano roll video (a YouTube link as Video, or a video file) opens here in
 * place of the Audio step. Three moments, each with one thing to do:
 *
 * 1. **Preparing the video**: its frames are taken out once (a job, a thin bar), as soon as the
 *    step opens on a video that has none.
 * 2. **Fit the piano**: one frame from the middle of the video with the rectangle of the
 *    calibration editor; the keys are found when the rectangle settles, and **Save the piano**
 *    keeps them.
 * 3. **The video with the piano on it**, played with its own audio, and **Read notes**: one job
 *    that measures the roll (once per fitting), reads the notes and writes them into the project,
 *    then opens the Notes step. **Fit the piano again** goes back to 2.
 *
 * The video and its frames are temporary files of the project (section 8.5). The development views
 * of the reader (the detection, the measurements, correcting single notes) stay in Lab.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import PianoIcon from "@mui/icons-material/Piano";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useNavigate } from "react-router-dom";
import { audioApi, videoApi, type VideoSummary } from "../../api";
import type { Calibration, FindRequest } from "../../api/frameExamples";
import CalibrationEditor from "../../components/video/CalibrationEditor";
import FramePlayer from "../../components/video/FramePlayer";
import PianoOverlay from "../../components/video/PianoOverlay";
import { useProgress } from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { IconAction, palette, PillButton, progressSx } from "../../ui";
import { buildKeys } from "../../video/overlayGeometry";
import { SAVED_NAVIGATION, stepStatus, usePiece } from "./pieceContext";

/** How often the frames are taken out of the video, in ms: the reader's default (V-04). */
const SAMPLE_MS = 100;

/** The stages of the reading job, in the user's words. */
const STAGE_WORDS: Record<string, string> = {
  sample: "Preparing the video",
  plate: "Measuring the roll",
  follow: "Measuring the roll",
  stitch: "Reading the notes",
  notes: "Reading the notes",
  shapes: "Reading the notes",
  write: "Writing the notes",
};

export function VideoStep() {
  const { uuid, status, refresh } = usePiece();
  const navigate = useNavigate();
  const [video, setVideo] = useState<VideoSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fitting, setFitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!uuid) return;
    const controller = new AbortController();
    videoApi
      .get(uuid, controller.signal)
      .then((found) => {
        setVideo(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "The video could not be loaded.");
      });
    return () => controller.abort();
  }, [uuid]);

  // ------------------------------------------------------------------ preparing

  const [sampleJob, setSampleJob] = useState<string | null>(null);
  const sampling = useProgress(sampleJob ? videoApi.progressUrl(sampleJob) : null);
  const started = useRef(false);
  const noFrames = video !== null && video.metadata.frameCount === 0;
  useEffect(() => {
    if (!uuid || !noFrames || started.current) return;
    started.current = true;
    videoApi
      .sample(uuid, SAMPLE_MS)
      .then((job) => setSampleJob(job.jobId))
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "The video could not be prepared."));
  }, [uuid, noFrames]);
  // The frames are out: load the video again, now with their count and size.
  useEffect(() => {
    if (sampling.status !== "done" || !uuid) return;
    const controller = new AbortController();
    videoApi
      .get(uuid, controller.signal)
      .then(setVideo)
      .catch(() => undefined);
    return () => controller.abort();
  }, [sampling.status, uuid]);

  // ------------------------------------------------------------------ reading

  const notes = stepStatus(status, "notes");
  const runningJob = notes?.state === "running" && typeof notes.details.jobId === "string" ? notes.details.jobId : null;
  const [readJob, setReadJob] = useState<string | null>(null);
  const job = readJob ?? runningJob;
  const reading = useProgress(job ? videoApi.progressUrl(job) : null);
  const [starting, setStarting] = useState(false);

  const read = async () => {
    if (!uuid) return;
    setStarting(true);
    setError(null);
    try {
      const handle = await videoApi.readAndWrite(uuid);
      setReadJob(handle.jobId);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The notes could not be read.");
    } finally {
      setStarting(false);
    }
  };

  const finished = reading.status === "done" || reading.status === "error" ? reading.status : null;
  useEffect(() => {
    if (!job || !finished) return;
    void refresh().then(() => {
      if (finished === "done" && uuid) navigate(ROUTES.project(uuid, "notes"), { state: SAVED_NAVIGATION });
    });
    // Once per job: `refresh` and `navigate` do not start anything new.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job, finished]);
  const jobError =
    sampling.status === "error"
      ? (sampling.error ?? "The video could not be prepared.")
      : finished === "error"
        ? (reading.error ?? "The notes could not be read.")
        : null;
  const readingNow = job !== null && reading.status !== "done" && reading.status !== "error";

  // ------------------------------------------------------------------ fitting

  const middle = video ? Math.max(0, Math.floor(video.metadata.frameCount / 2)) : 0;
  const find = useCallback(
    (body: FindRequest) => (uuid ? videoApi.find(uuid, middle, body) : Promise.reject(new Error("no video"))),
    [uuid, middle],
  );
  const save = async (calibration: Calibration) => {
    if (!uuid) return;
    setSaving(true);
    setError(null);
    try {
      setVideo(await videoApi.putCalibration(uuid, calibration));
      setFitting(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The piano could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const fitted = video?.calibration ?? null;
  const keys = useMemo(() => (fitted ? buildKeys(fitted) : []), [fitted]);

  // ------------------------------------------------------------------ render

  if (error && !video) return <Alert severity="error">{error}</Alert>;
  if (!uuid || !video) {
    return (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 2 }}>
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Loading the video…
        </Typography>
      </Stack>
    );
  }

  const meta = video.metadata;
  const calibration = video.calibration;
  const hasNotes = notes?.state === "ready";
  const readLabel = hasNotes && !readingNow ? "Read notes again" : "Read notes";
  const stage = reading.event ? (STAGE_WORDS[reading.event.stage] ?? "Reading the notes") : "Starting";

  return (
    <Stack spacing={1.5} sx={{ pb: 4 }} data-video-step>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {jobError && !readingNow ? <Alert severity="error">{jobError}</Alert> : null}

      {meta.frameCount === 0 ? (
        <Box role="status" aria-live="polite" sx={{ ...progressSx, py: 2 }}>
          <LinearProgress
            variant={sampling.event?.total ? "determinate" : "indeterminate"}
            value={sampling.percent}
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
            {sampling.event?.total ? `Preparing the video · ${Math.round(sampling.percent)}%` : "Preparing the video"}
          </Typography>
        </Box>
      ) : !calibration || fitting ? (
        <CalibrationEditor
          key={`${uuid}:${middle}:${fitting}`}
          imageUrl={videoApi.frameUrl(uuid, middle)}
          imageWidth={meta.frameWidth}
          imageHeight={meta.frameHeight}
          calibration={calibration}
          onFind={find}
          onSave={(found) => void save(found)}
          saving={saving}
          compact
          onCancel={calibration ? () => setFitting(false) : undefined}
          height={480}
        />
      ) : (
        <>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1, minHeight: 40 }}>
            <IconAction
              title="Fit the piano again"
              icon={<PianoIcon fontSize="small" />}
              disabled={readingNow}
              onClick={() => setFitting(true)}
            />
            {readingNow ? (
              <Box role="status" aria-live="polite" sx={{ flex: 1, minWidth: 200, maxWidth: 420 }}>
                <LinearProgress
                  variant={reading.event?.total ? "determinate" : "indeterminate"}
                  value={reading.event ? reading.event.fraction * 100 : 0}
                />
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                  {stage}
                </Typography>
              </Box>
            ) : null}
            <Box sx={{ flexGrow: 1 }} />
            <PillButton
              kind="primary"
              startIcon={<PlayArrowIcon />}
              busy={starting || readingNow}
              disabled={readingNow}
              onClick={() => void read()}
            >
              {readLabel}
            </PillButton>
          </Stack>
          <FramePlayer
            frameUrl={(at) => videoApi.frameUrl(uuid, at)}
            frameCount={meta.frameCount}
            sampleMs={meta.sampleMs}
            frameWidth={meta.frameWidth}
            frameHeight={meta.frameHeight}
            index={Math.min(index, meta.frameCount - 1)}
            onIndexChange={setIndex}
            audioUrl={audioApi.fileUrl(uuid)}
            height={480}
            quiet
          >
            {(scale) => (
              <>
                <PianoOverlay calibration={calibration} keys={keys} scale={scale} />
                <line
                  x1={0}
                  x2={meta.frameWidth}
                  y1={calibration.upperLine}
                  y2={calibration.upperLine}
                  stroke={palette.dark.Red}
                  strokeWidth={1.5 * scale}
                  style={{ pointerEvents: "none" }}
                />
              </>
            )}
          </FramePlayer>
        </>
      )}
    </Stack>
  );
}

export default VideoStep;
