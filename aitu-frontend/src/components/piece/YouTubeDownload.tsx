/**
 * Paste a YouTube URL, and the audio arrives as a new piece.
 *
 * The download runs as a job on the backend (`POST /youtube/jobs`), so the page does not wait on
 * one long request: it follows the job's progress stream, which shows the download in percent,
 * then the conversion, and ends with the uuid of the stored audio.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import DownloadIcon from "@mui/icons-material/Download";
import { matrixApi, youtubeApi } from "../../api";
import { useProgress } from "../../hooks/useProgress";
import ProgressBanner from "../ProgressBanner";

export interface YouTubeDownloadProps {
  /** The download is stored: its audio uuid. */
  onDone: (audioUuid: string) => void;
}

export function YouTubeDownload({ onDone }: YouTubeDownloadProps) {
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [probing, setProbing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);
  const busy = starting || progress.status === "running";

  const done = progress.status === "done" ? progress.result : null;
  const audioUuid = typeof done?.audioUuid === "string" ? done.audioUuid : null;
  useEffect(() => {
    if (audioUuid) onDone(audioUuid);
  }, [audioUuid, onDone]);

  const probe = async () => {
    if (!url.trim() || alias) return;
    setProbing(true);
    try {
      const info = await youtubeApi.probe(url.trim());
      // Only prefill; never overwrite a name the reader already typed.
      setAlias((typed) => typed || info.title);
    } catch {
      // The download itself says what is wrong with the URL; a failed title lookup says nothing new.
    } finally {
      setProbing(false);
    }
  };

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      const handle = await youtubeApi.startDownload({
        url: url.trim(),
        alias: alias.trim() || undefined,
      });
      setJobId(handle.jobId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The download could not start.");
    } finally {
      setStarting(false);
    }
  };

  return (
    <Stack spacing={1.5}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField
        label="YouTube URL"
        size="small"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        onBlur={() => void probe()}
        placeholder="https://www.youtube.com/watch?v=…"
        fullWidth
        disabled={busy}
      />
      <TextField
        label="Name"
        size="small"
        value={alias}
        onChange={(event) => setAlias(event.target.value)}
        placeholder={probing ? "Reading the video title…" : "Defaults to the video title"}
        fullWidth
        disabled={busy}
        slotProps={{ input: { endAdornment: probing ? <CircularProgress size={16} /> : undefined } }}
      />
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          startIcon={busy ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
          onClick={() => void start()}
          disabled={!url.trim() || busy}
        >
          Download
        </Button>
      </Stack>
      <ProgressBanner progress={progress} fallbackLabel="Starting the download" />
    </Stack>
  );
}

export default YouTubeDownload;
