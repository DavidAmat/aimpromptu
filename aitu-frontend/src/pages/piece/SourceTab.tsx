/**
 * Step 1, **Source**: where the audio of a project comes from (implementation 02, plan section 10.2).
 *
 * On a new project: one drop zone for an audio file, and one field for a YouTube link with the
 * choice **Audio** or **Video**. Nothing else, and no name is asked for: a project takes the name of
 * its file or of its video, and the user names it later.
 *
 * - An audio file is uploaded and the project opens on its Audio step.
 * - A YouTube link as **Audio** downloads as a job with a thin progress bar, then opens the Audio step.
 * - A YouTube link as **Video** (the master user only, until Phase 5 makes the video a step of the
 *   project) downloads the video (its audio comes with it) and opens it in Lab,
 *   where the piano is fitted and the notes are read. Phase 5 makes those pages steps of the project.
 *
 * On a project that already has its audio, the step says where that audio came from.
 */

import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import UploadFileIcon from "@mui/icons-material/UploadFileOutlined";
import { useNavigate } from "react-router-dom";
import { audioApi, matrixApi, SUPPORTED_AUDIO_SUFFIXES, videoApi, youtubeApi } from "../../api";
import { formatTimeShort } from "../../audio/time";
import { useProgress } from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { useAuth } from "../../state/authContext";
import { writeSelectedVideo } from "../../video/selectedVideo";
import { IconAction, PillButton, Segmented, ui, useScheme } from "../../ui";
import { usePiece } from "./pieceContext";

type LinkKind = "audio" | "video";

const isAudioFile = (file: File) => SUPPORTED_AUDIO_SUFFIXES.some((suffix) => file.name.toLowerCase().endsWith(suffix));

export function SourceTab() {
  const { uuid } = usePiece();
  return uuid ? <SourceOfProject /> : <NewSource />;
}

/** What the audio of an existing project is: the file it was uploaded from, or its YouTube link. */
function SourceOfProject() {
  const { audio } = usePiece();
  if (!audio) return null;
  const from =
    audio.source === "youtube" && audio.sourceUrl ? (
      <Link href={audio.sourceUrl} target="_blank" rel="noreferrer" underline="hover" sx={{ wordBreak: "break-all" }}>
        {audio.sourceUrl}
      </Link>
    ) : (
      <Typography component="span" sx={{ wordBreak: "break-all" }}>
        {audio.originalFilename ?? audio.alias}
      </Typography>
    );
  const kind = { upload: "Audio file", youtube: "YouTube", recording: "Recording", segment: "Part of another project", composed: "Composed" }[audio.source];
  return (
    <Box sx={{ maxWidth: 640, mx: "auto", pt: 4 }}>
      <Stack spacing={0.5}>
        <Typography variant="body2" color="text.secondary">
          {kind}
          {audio.originalDurationSeconds ? ` · ${formatTimeShort(audio.originalDurationSeconds)}` : ""}
        </Typography>
        {from}
      </Stack>
    </Box>
  );
}

function NewSource() {
  useScheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [kind, setKind] = useState<LinkKind>("audio");
  const [jobId, setJobId] = useState<string | null>(null);
  const [downloadingVideo, setDownloadingVideo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);

  const openAudio = useCallback((id: string) => navigate(ROUTES.project(id, "audio")), [navigate]);

  // The YouTube audio job ends with the id of the stored audio.
  const done = progress.status === "done" ? progress.result : null;
  const downloaded = typeof done?.audioUuid === "string" ? done.audioUuid : null;
  useEffect(() => {
    if (downloaded) openAudio(downloaded);
  }, [downloaded, openAudio]);

  const failed = progress.status === "error" ? progress.error : null;
  const busyLink = downloadingVideo || (jobId !== null && progress.status !== "error" && progress.status !== "done");
  const busy = busyLink || uploading !== null;

  const upload = async (file: File | undefined) => {
    if (!file || busy) return;
    if (!isAudioFile(file)) {
      setError(`“${file.name}” is not an audio file this app reads (${SUPPORTED_AUDIO_SUFFIXES.join(", ")}).`);
      return;
    }
    setError(null);
    setUploading(file.name);
    try {
      const stored = await audioApi.upload(file);
      openAudio(stored.uuid);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The file could not be uploaded.");
      setUploading(null);
    }
  };

  const download = async () => {
    const link = url.trim();
    if (!link || busy) return;
    setError(null);
    if (kind === "audio") {
      try {
        const handle = await youtubeApi.startDownload({ url: link });
        setJobId(handle.jobId);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "The download could not start.");
      }
      return;
    }
    setDownloadingVideo(true);
    try {
      const video = await videoApi.download(link);
      writeSelectedVideo(video.audioUuid);
      navigate(ROUTES.labVideoOf(video.audioUuid));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The video could not be downloaded.");
      setDownloadingVideo(false);
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void upload(event.dataTransfer.files?.[0]);
  };

  const percent = progress.event?.total ? progress.event.fraction * 100 : null;

  return (
    <Stack spacing={3} sx={{ maxWidth: 640, mx: "auto", pt: { xs: 2, md: 6 } }}>
      {error || failed ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error ?? failed}
        </Alert>
      ) : null}

      <Box
        onDragOver={(event) => {
          event.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        data-testid="drop-zone"
        sx={(theme) => ({
          border: `1.5px dashed ${dragging ? ui.text : ui.lineStrong}`,
          borderRadius: "16px",
          backgroundColor: dragging ? (theme.vars ?? theme).palette.action.hover : "transparent",
          minHeight: 200,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
          p: 3,
          textAlign: "center",
        })}
      >
        <UploadFileIcon sx={{ color: "text.secondary" }} />
        <Typography color="text.secondary">{uploading ? `Uploading ${uploading}` : "Drop an audio file"}</Typography>
        {uploading ? (
          <LinearProgress sx={{ width: 200 }} />
        ) : (
          <PillButton onClick={() => fileInput.current?.click()} disabled={busy}>
            Choose file
          </PillButton>
        )}
        <input
          ref={fileInput}
          type="file"
          hidden
          accept={SUPPORTED_AUDIO_SUFFIXES.join(",")}
          aria-label="Choose an audio file"
          onChange={(event) => {
            void upload(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </Box>

      <Stack spacing={1.5}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ alignItems: { sm: "center" } }}>
          <TextField
            fullWidth
            label="Paste a YouTube link"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void download();
            }}
            disabled={busy}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconAction
                      title={kind === "audio" ? "Download the audio" : "Download the video"}
                      icon={<ArrowForwardIcon fontSize="small" />}
                      onClick={() => void download()}
                      disabled={!url.trim() || busy}
                    />
                  </InputAdornment>
                ),
              },
            }}
          />
          {/* The video opens in Lab, the master user's, until Phase 5 makes it a step of the project. */}
          {user?.isMaster ? (
            <Segmented<LinkKind>
              label="What to download"
              value={kind}
              onChange={setKind}
              disabled={busy}
              options={[
                { value: "audio", label: "Audio", tooltip: "Download the audio and transcribe it" },
                { value: "video", label: "Video", tooltip: "Download a piano roll video and read its notes" },
              ]}
            />
          ) : null}
        </Stack>
        {busyLink ? (
          <Box role="status" aria-live="polite">
            <LinearProgress variant={percent === null ? "indeterminate" : "determinate"} value={percent ?? 0} />
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
              {downloadingVideo ? "Downloading the video" : percent === null ? "Downloading" : `Downloading · ${Math.round(percent)}%`}
            </Typography>
          </Box>
        ) : null}
      </Stack>
    </Stack>
  );
}

export default SourceTab;
