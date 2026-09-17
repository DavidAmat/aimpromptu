/**
 * Calibration — fit the piano on a frame, then measure how fast the roll falls.
 *
 * Stories 3.3 and 3.4. Task 3.3.2 is the calibration UI of implementation 05
 * opened on a sampled frame instead of on a screenshot: **the same component,
 * unchanged**, because it takes a picture URL and a size and knows nothing about
 * where the picture came from.
 *
 * Then Task 3.4.1 measures the scroll speed, and with it the two edges of the
 * roll (V-28), because the roll scrolls and nothing else does. That is also what
 * fixes the offset line: on a video it is not a free parameter, it is the
 * measured speed times the sampling granularity and nothing else (V-25), so this
 * screen draws it rather than offering it (Task 3.4.2).
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { Calibration, FindRequest } from "../../api/frameExamples";
import { videoApi, type VideoSummary } from "../../api/video";
import useProgress from "../../hooks/useProgress";
import { PageContainer, SectionCard, surface } from "../../ui";
import { readSelectedVideo, writeSelectedVideo } from "../../video/selectedVideo";
import CalibrationEditor from "../../components/video/CalibrationEditor";
import FramePlayer from "../../components/video/FramePlayer";
import TimeFrameLines from "../../components/video/TimeFrameLines";
import VideoBar from "../../components/video/VideoBar";

export function VideoCalibrationPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(readSelectedVideo);
  const [frame, setFrame] = useState<number | null>(null);
  const [index, setIndex] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
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

  const [seenJob, setSeenJob] = useState<string | null>(null);
  if (progress.status === "done" && jobId && seenJob !== jobId) {
    setSeenJob(jobId);
    void refresh();
  }

  const video = videos?.find((one) => one.metadata.audioUuid === selected) ?? null;

  // The middle frame by default: the piano is static for the whole video, so any
  // frame will do, and the middle one is the likeliest to have the piece playing
  // rather than a title card. Derived during render, not in an effect.
  const [seenVideo, setSeenVideo] = useState<string | null>(selected);
  if (seenVideo !== selected) {
    setSeenVideo(selected);
    setFrame(null);
    setIndex(0);
  }
  const chosen = frame ?? (video ? Math.floor(video.metadata.frameCount / 2) : 0);

  const pick = (audioUuid: string) => {
    setSelected(audioUuid);
    writeSelectedVideo(audioUuid);
  };

  const find = useCallback(
    (body: FindRequest) => {
      if (!video) return Promise.reject(new Error("no video"));
      return videoApi.find(video.metadata.audioUuid, chosen, body);
    },
    [video, chosen],
  );

  const save = (calibration: Calibration) => {
    if (!video) return;
    setSaving(true);
    videoApi
      .putCalibration(video.metadata.audioUuid, calibration)
      .then(() => refresh())
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      )
      .finally(() => setSaving(false));
  };

  const measure = () => {
    if (!video) return;
    setError(null);
    videoApi
      .measure(video.metadata.audioUuid)
      .then((job) => setJobId(job.jobId))
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      );
  };

  const running = jobId !== null && progress.status === "running";
  const speed = video?.measurement?.scrollSpeed ?? null;

  return (
    <PageContainer
      title="Calibration"
      subtitle="Fit the piano overlay onto a frame of the video, then measure how fast the rectangles fall."
      wide
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="Fit the piano"
        description="Drag one rectangle over the piano area and every key inside it is found. The piano does not move, so this is done once, on any frame."
      >
        <VideoBar videos={videos} selected={selected} onSelect={pick}>
          {video && video.metadata.frameCount > 0 ? (
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              fitting on frame {chosen + 1} of {video.metadata.frameCount}
            </Typography>
          ) : null}
        </VideoBar>

        {video && video.metadata.frameCount > 0 ? (
          <CalibrationEditor
            key={`${video.metadata.audioUuid}:${chosen}`}
            imageUrl={videoApi.frameUrl(video.metadata.audioUuid, chosen)}
            imageWidth={video.metadata.frameWidth}
            imageHeight={video.metadata.frameHeight}
            calibration={video.calibration}
            onFind={find}
            onSave={save}
            saving={saving}
          />
        ) : video ? (
          <Alert severity="info" variant="outlined">
            This video has no sampled frames yet. Sample it on the Video tab first.
          </Alert>
        ) : null}
      </SectionCard>

      {video?.calibration ? (
        <SectionCard
          title="How fast the roll falls"
          description="The rectangles measure it themselves: every one is followed from one sampled frame into the next and the fall of its edges is averaged, one estimate per pair of frames. The same pass finds where the roll starts and where the strike light begins, because the roll scrolls and nothing else does."
          actions={
            <Button variant="outlined" size="small" onClick={measure} disabled={running}>
              {running ? "Measuring…" : speed ? "Measure again" : "Measure"}
            </Button>
          }
        >
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

          {speed && !speed.stable ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {speed.reason || "The scroll speed is not stable."} This video is reported, not
              transcribed: a distance becomes a time with one speed, and this one has not got one.
            </Alert>
          ) : null}

          {speed && video.measurement ? (
            <Stack spacing={0.5} sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>{speed.pxPerSecond.toFixed(1)} px a second</strong> ·{" "}
                {speed.pxPerFrame.toFixed(2)} px per sampled frame · quartiles{" "}
                {speed.q1.toFixed(2)} to {speed.q3.toFixed(2)}
              </Typography>
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                {speed.usablePairs} of {speed.totalPairs} pairs of frames answered; {speed.stillPairs}{" "}
                had nothing falling in them at all. The roll starts at row{" "}
                {video.measurement.rollTop.toFixed(0)} and the strike light reaches{" "}
                {video.measurement.guardBand.toFixed(0)} rows above the upper line.
              </Typography>
            </Stack>
          ) : null}

          {video.metadata.frameCount > 0 ? (
            <FramePlayer
              frameUrl={(at) => videoApi.frameUrl(video.metadata.audioUuid, at)}
              frameCount={video.metadata.frameCount}
              sampleMs={video.metadata.sampleMs}
              frameWidth={video.metadata.frameWidth}
              frameHeight={video.metadata.frameHeight}
              index={Math.min(index, video.metadata.frameCount - 1)}
              onIndexChange={setIndex}
            >
              {(scale) => (
                <TimeFrameLines
                  upperLine={video.calibration!.upperLine}
                  offsetPx={video.measurement?.offsetPx ?? 0}
                  imageWidth={video.metadata.frameWidth}
                  rollTop={video.calibration!.rollTop}
                  guardBand={video.calibration!.guardBand}
                  scale={scale}
                />
              )}
            </FramePlayer>
          ) : null}

          <Typography variant="caption" sx={{ color: surface.mutedText }}>
            The red line is the upper line: a rectangle tip crossing it is an onset. Each yellow band
            above it is one sampled frame of travel, so the bands say which rectangles land in which
            frame. The dashed blue line is where the roll starts and the red band is where the strike
            light makes the picture unreadable.
          </Typography>
        </SectionCard>
      ) : null}
    </PageContainer>
  );
}

export default VideoCalibrationPage;
