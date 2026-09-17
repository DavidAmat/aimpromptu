/**
 * Detection — run the detector over the whole video and look at what it found.
 *
 * Story 3.5. The background plate once, then the detector over every sampled
 * frame, writing `frames.jsonl`. The frames are independent, so the pixel work
 * is spread over worker processes.
 *
 * Then the same screen the Examples tab uses to show what the detector saw,
 * stepped through the sampled frames — which is the timeline Phase 2 could not
 * build, because an example screenshot is one frame and has no timeline. A
 * rectangle the momentum rule refused is drawn too, in its own colour, so a
 * refusal is something you can look at rather than something you have to
 * imagine (V-33, V-30).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { DetectedRun, Detection } from "../../api/frameExamples";
import { videoApi, type DetectionReport, type FrameLine, type VideoSummary } from "../../api/video";
import { buildKeys } from "../../video/overlayGeometry";
import useProgress from "../../hooks/useProgress";
import { PageContainer, SectionCard, surface } from "../../ui";
import { readSelectedVideo, writeSelectedVideo } from "../../video/selectedVideo";
import FramePlayer from "../../components/video/FramePlayer";
import PianoOverlay from "../../components/video/PianoOverlay";
import TimeFrameLines from "../../components/video/TimeFrameLines";
import VideoBar from "../../components/video/VideoBar";
import {
  markColours,
  refusedColour,
  runColours,
  type MarkState,
} from "../../components/video/overlayColours";

const runId = (run: DetectedRun) => `${run.midi}:${run.yTop}:${run.yBottom}`;

export function VideoDetectionPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(readSelectedVideo);
  const [jobId, setJobId] = useState<string | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [lines, setLines] = useState<FrameLine[]>([]);
  const [detection, setDetection] = useState<Detection | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const progress = useProgress(jobId ? videoApi.progressUrl(jobId) : null);

  const refresh = useCallback(
    () =>
      videoApi
        .list()
        .then(setVideos)
        .catch((caught: unknown) =>
          setError(caught instanceof Error ? caught.message : String(caught)),
        ),
    [],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const video = videos?.find((one) => one.metadata.audioUuid === selected) ?? null;
  const calibration = video?.calibration ?? null;

  const [seenVideo, setSeenVideo] = useState<string | null>(selected);
  if (seenVideo !== selected) {
    setSeenVideo(selected);
    setIndex(0);
    setDetection(null);
    setReport(null);
    setLines([]);
  }

  // What the last whole-video run did, and the reading it wrote. Both are files
  // on disk, so they are asked for when the video changes and when a job ends.
  useEffect(() => {
    if (!selected || !video?.detected) return;
    const controller = new AbortController();
    videoApi.report(selected, controller.signal).then(setReport).catch(() => setReport(null));
    videoApi.detection(selected, 0, 100000, controller.signal).then(setLines).catch(() => setLines([]));
    return () => controller.abort();
  }, [selected, video?.detected, video?.detectedFrames]);

  const [seenJob, setSeenJob] = useState<string | null>(null);
  if (progress.status === "done" && jobId && seenJob !== jobId) {
    setSeenJob(jobId);
    void refresh();
  }

  // The frame on screen is read on its own, with its two neighbours, so the
  // rectangles can be drawn on the pixels they were found in. It settles first,
  // because stepping through frames is dozens of values and every one of them
  // would otherwise be a request.
  useEffect(() => {
    if (!selected || !calibration) return;
    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      videoApi
        .detectFrame(selected, index, undefined, controller.signal)
        .then(setDetection)
        .catch((caught: unknown) => {
          if (!controller.signal.aborted) setDetection(null);
          void caught;
        });
    }, 180);
    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
  }, [selected, index, calibration]);

  const pick = (audioUuid: string) => {
    setSelected(audioUuid);
    writeSelectedVideo(audioUuid);
  };

  const run = () => {
    if (!video) return;
    setError(null);
    videoApi
      .detect(video.metadata.audioUuid)
      .then((job) => setJobId(job.jobId))
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      );
  };

  const keys = useMemo(() => (calibration ? buildKeys(calibration) : []), [calibration]);

  const marks: Record<number, MarkState> = {};
  for (const midi of detection?.sustains ?? []) marks[midi] = "sustain";
  for (const midi of detection?.onsets ?? []) marks[midi] = "onset";

  const running = jobId !== null && progress.status === "running";
  const ready = Boolean(video?.calibration && video?.measurement?.scrollSpeed.pxPerFrame);
  const line = lines[index] ?? null;

  const drawRun = (one: DetectedRun, scale: number, refused: boolean) => (
    <g key={runId(one)}>
      <rect
        x={one.x0}
        y={one.yTop}
        width={Math.max(0.5, one.x1 - one.x0)}
        height={Math.max(0.5, one.yBottom - one.yTop)}
        fill={refused ? refusedColour : runColours[one.verdict]}
        fillOpacity={refused ? 0.1 : 0.16}
        stroke={refused ? refusedColour : runColours[one.verdict]}
        strokeWidth={1.3 * scale}
        strokeDasharray={refused ? `${4 * scale} ${3 * scale}` : undefined}
        style={{ pointerEvents: "none" }}
      />
      <line
        x1={one.x0}
        x2={one.x1}
        y1={one.yBottom}
        y2={one.yBottom}
        stroke={refused ? refusedColour : runColours[one.verdict]}
        strokeWidth={2.2 * scale}
        style={{ pointerEvents: "none" }}
      />
    </g>
  );

  return (
    <PageContainer
      title="Detection"
      subtitle="Run the detector over the whole video and look at what it found, frame by frame."
      wide
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="Read the video"
        description="The background plate first, then every sampled frame, writing one line per frame: its onsets and its sustains. Released is the default and is never written down."
        actions={
          <Button variant="contained" size="small" onClick={run} disabled={!ready || running}>
            {running ? "Reading…" : video?.detected ? "Read it again" : "Read it"}
          </Button>
        }
      >
        <VideoBar videos={videos} selected={selected} onSelect={pick} />

        {video && !ready ? (
          <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
            {video.calibration
              ? "The scroll speed has not been measured yet. On a video the window of one sampled frame is the measured speed and nothing else, so measure it on the Calibration tab first."
              : "This video has no piano overlay yet. Fit it on the Calibration tab first."}
          </Alert>
        ) : null}

        {running ? (
          <Box sx={{ mb: 2 }}>
            <LinearProgress
              variant={progress.event?.total ? "determinate" : "indeterminate"}
              value={progress.event ? progress.event.fraction * 100 : 0}
            />
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              {progress.event?.stage} · {progress.event?.current} of {progress.event?.total}
            </Typography>
          </Box>
        ) : null}
        {progress.status === "error" ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {progress.error}
          </Alert>
        ) : null}

        {report ? (
          <Stack spacing={0.5}>
            <Typography variant="body2">
              <strong>{report.onsets} onsets</strong> and {report.sustains} sustains over{" "}
              {report.frameCount} sampled frames · {report.onsetsPerSecond.toFixed(2)} onsets a
              second
            </Typography>
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              {report.runsFound} rectangles kept and {report.runsRefused} refused for not falling ·
              frame to frame agreement {(report.agreement * 100).toFixed(1)}% · read in{" "}
              {report.elapsedSeconds.toFixed(1)} s over {report.workers} worker
              {report.workers === 1 ? "" : "s"}
            </Typography>
          </Stack>
        ) : null}
      </SectionCard>

      {video && video.metadata.frameCount > 0 && video.calibration ? (
        <SectionCard
          title="What it saw"
          description="Every rectangle drawn on the pixels it was found in. A rectangle in purple is one the momentum rule refused, because a neighbouring frame holds it in exactly the same place — a rectangle falls, and anything that does not fall is not a note."
        >
          <Stack direction="row" spacing={1} sx={{ mb: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Chip
              size="small"
              label={`${detection?.onsets.length ?? 0} onset`}
              sx={{ backgroundColor: markColours.onset, color: surface.panel }}
            />
            <Chip
              size="small"
              label={`${detection?.sustains.length ?? 0} sustain`}
              sx={{ backgroundColor: markColours.sustain }}
            />
            {detection?.refused.length ? (
              <Chip
                size="small"
                label={`${detection.refused.length} refused`}
                sx={{ backgroundColor: refusedColour, color: surface.panel }}
              />
            ) : null}
            <Box sx={{ flexGrow: 1 }} />
            {line ? (
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                frames.jsonl at t = {line.t.toFixed(1)} s: {line.onsets.length} onsets,{" "}
                {line.sustains.length} sustains
              </Typography>
            ) : null}
            {detection ? (
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                {detection.runs.length} rectangles · {detection.elapsedMs.toFixed(0)} ms
              </Typography>
            ) : null}
          </Stack>

          <FramePlayer
            frameUrl={(at) => videoApi.frameUrl(video.metadata.audioUuid, at)}
            frameCount={video.metadata.frameCount}
            sampleMs={video.metadata.sampleMs}
            frameWidth={video.metadata.frameWidth}
            frameHeight={video.metadata.frameHeight}
            index={Math.min(index, video.metadata.frameCount - 1)}
            onIndexChange={setIndex}
            height={560}
          >
            {(scale) => (
              <>
                <TimeFrameLines
                  upperLine={video.calibration!.upperLine}
                  offsetPx={video.measurement?.offsetPx ?? 0}
                  imageWidth={video.metadata.frameWidth}
                  count={1}
                  rollTop={video.calibration!.rollTop}
                  guardBand={video.calibration!.guardBand}
                  scale={scale}
                />
                {detection?.refused.map((one) => drawRun(one, scale, true))}
                {detection?.runs.map((one) => drawRun(one, scale, false))}
                <PianoOverlay
                  calibration={video.calibration!}
                  keys={keys}
                  scale={scale}
                  marks={marks}
                />
              </>
            )}
          </FramePlayer>
        </SectionCard>
      ) : null}
    </PageContainer>
  );
}

export default VideoDetectionPage;
