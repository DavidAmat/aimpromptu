/**
 * Video — bring the video in, sample its frames, and step through them.
 *
 * Stories 3.1, 3.2 and 3.3. The user pastes a YouTube URL and gets a video they
 * can play; **the audio is there too and they are never asked about it** (V-03),
 * because the Piano Sheet tab plays the original audio later and the piece has
 * to have one for that to work.
 *
 * The player draws the sampled frames rather than a video element, so what is on
 * this screen is exactly what the detector reads (V-35).
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { audioApi } from "../../api/audio";
import { videoApi, type VideoSummary } from "../../api/video";
import useProgress from "../../hooks/useProgress";
import { PageContainer, SectionCard, surface } from "../../ui";
import { readSelectedVideo, writeSelectedVideo } from "../../video/selectedVideo";
import FramePlayer from "../../components/video/FramePlayer";
import VideoBar from "../../components/video/VideoBar";

/** The sampling granularities worth offering, in milliseconds (V-04). */
const GRANULARITIES = [
  { value: 50, label: "50 ms · 20 frames a second" },
  { value: 100, label: "100 ms · 10 frames a second" },
  { value: 200, label: "200 ms · 5 frames a second" },
];

export function VideoPlayerPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(readSelectedVideo);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sampleMs, setSampleMs] = useState(100);
  const [jobId, setJobId] = useState<string | null>(null);
  const [index, setIndex] = useState(0);

  const progress = useProgress(jobId ? videoApi.progressUrl(jobId) : null);

  const refresh = useCallback(
    () =>
      videoApi
        .list()
        .then((rows) => {
          setVideos(rows);
          return rows;
        })
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : String(caught));
          return [] as VideoSummary[];
        }),
    [],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // A finished job changed what is on disk, so what the page shows has to be
  // asked for again. Derived from the stream's status rather than assigned in
  // the callback, so a reconnect cannot ask twice.
  const [seenJob, setSeenJob] = useState<string | null>(null);
  if (progress.status === "done" && jobId && seenJob !== jobId) {
    setSeenJob(jobId);
    void refresh();
  }

  const pick = (audioUuid: string) => {
    setSelected(audioUuid);
    writeSelectedVideo(audioUuid);
    setIndex(0);
  };

  const download = () => {
    setBusy(true);
    setError(null);
    videoApi
      .download(url.trim())
      .then((metadata) => {
        setUrl("");
        pick(metadata.audioUuid);
        return refresh();
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : String(caught)))
      .finally(() => setBusy(false));
  };

  const sample = () => {
    if (!selected) return;
    setError(null);
    videoApi
      .sample(selected, sampleMs)
      .then((job) => setJobId(job.jobId))
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : String(caught)));
  };

  const video = videos?.find((one) => one.metadata.audioUuid === selected) ?? null;
  const running = jobId !== null && progress.status === "running";

  return (
    <PageContainer
      title="Video"
      subtitle="Paste a YouTube URL, download the video, and step through its sampled frames."
      wide
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="Bring a video in"
        description="One URL gives one piece: the video, and the audio of that same video beside it. You are not asked about the audio — the Piano Sheet tab plays it later."
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <TextField
            size="small"
            fullWidth
            label="YouTube URL"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && url.trim() && !busy) download();
            }}
            placeholder="https://www.youtube.com/watch?v=…"
          />
          <Button variant="contained" onClick={download} disabled={busy || !url.trim()}>
            {busy ? "Downloading…" : "Download"}
          </Button>
        </Stack>
        {busy ? (
          <Typography variant="caption" sx={{ color: surface.mutedText }}>
            The picture is capped at 720p, because every picture is read at 1280 px wide and the
            file stays small. The audio is taken out of that same file with ffmpeg.
          </Typography>
        ) : null}
      </SectionCard>

      <SectionCard
        title="The video"
        description="Sampling writes one picture per sampling granularity. The video is the source and the frames are a cache, so sampling again at another granularity replaces them and nothing is lost."
      >
        <VideoBar videos={videos} selected={selected} onSelect={pick}>
          <TextField
            select
            size="small"
            label="Sampling granularity"
            value={sampleMs}
            onChange={(event) => setSampleMs(Number(event.target.value))}
            sx={{ minWidth: 220 }}
          >
            {GRANULARITIES.map((one) => (
              <MenuItem key={one.value} value={one.value}>
                {one.label}
              </MenuItem>
            ))}
          </TextField>
          <Button variant="outlined" size="small" onClick={sample} disabled={!selected || running}>
            {running ? "Sampling…" : "Sample the frames"}
          </Button>
        </VideoBar>

        {running ? (
          <Box sx={{ mb: 2 }}>
            <LinearProgress
              variant={progress.event?.total ? "determinate" : "indeterminate"}
              value={progress.event ? progress.event.fraction * 100 : 0}
            />
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              {progress.event?.stage} · {progress.event?.message}
            </Typography>
          </Box>
        ) : null}
        {progress.status === "error" ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {progress.error}
          </Alert>
        ) : null}

        {video && video.metadata.frameCount > 0 ? (
          <FramePlayer
            frameUrl={(at) => videoApi.frameUrl(video.metadata.audioUuid, at)}
            frameCount={video.metadata.frameCount}
            sampleMs={video.metadata.sampleMs}
            frameWidth={video.metadata.frameWidth}
            frameHeight={video.metadata.frameHeight}
            index={Math.min(index, video.metadata.frameCount - 1)}
            onIndexChange={setIndex}
            audioUrl={audioApi.fileUrl(video.metadata.audioUuid)}
          />
        ) : video ? (
          <Alert severity="info" variant="outlined">
            This video has no sampled frames yet. Sample it, then fit the piano on the Calibration
            tab.
          </Alert>
        ) : videos === null ? (
          <CircularProgress size={20} />
        ) : null}
      </SectionCard>
    </PageContainer>
  );
}

export default VideoPlayerPage;
