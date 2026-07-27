/** `/youtube` — paste a URL, download the audio into the store (Story 3.5). */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DownloadIcon from "@mui/icons-material/Download";
import { Link } from "react-router-dom";
import { youtubeApi, type AudioItem } from "../api";
import AudioLibraryList from "../components/audio/AudioLibraryList";
import { formatTimeShort } from "../audio/time";
import { ROUTES } from "../layout/routes";
import { useWorkingArtifact } from "../state/useWorkingArtifact";
import { PageContainer, SectionCard } from "../ui";

export function YouTubePage() {
  const { update } = useWorkingArtifact();
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [probing, setProbing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<AudioItem | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const probe = async () => {
    if (!url.trim()) return;
    setProbing(true);
    setError(null);
    try {
      const info = await youtubeApi.probe(url.trim());
      // Only prefill; never overwrite a name the user already typed.
      setAlias((current) => current || info.title);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not read that video.");
    } finally {
      setProbing(false);
    }
  };

  const download = async () => {
    if (!url.trim()) return;
    setDownloading(true);
    setError(null);
    setSaved(null);
    try {
      const audio = await youtubeApi.download({
        url: url.trim(),
        alias: alias.trim() || undefined,
      });
      setSaved(audio);
      setUrl("");
      setAlias("");
      setReloadToken((token) => token + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The download failed.");
    } finally {
      setDownloading(false);
    }
  };

  const openInPlayground = (audio: AudioItem) => {
    update({ audioUuid: audio.uuid, label: audio.alias });
  };

  return (
    <PageContainer
      title="YouTube to Audio"
      subtitle="Paste a URL, download the audio with yt-dlp, name it; it lands in the audio store."
    >
      <SectionCard title="Download">
        <Stack spacing={2}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <TextField
            label="YouTube URL"
            size="small"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onBlur={() => void probe()}
            placeholder="https://www.youtube.com/watch?v=…"
            fullWidth
            disabled={downloading}
          />

          <TextField
            label="Name"
            size="small"
            value={alias}
            onChange={(event) => setAlias(event.target.value)}
            placeholder={probing ? "Reading the video title…" : "Defaults to the video title"}
            fullWidth
            disabled={downloading}
            slotProps={{
              input: {
                endAdornment: probing ? <CircularProgress size={16} /> : undefined,
              },
            }}
          />

          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={() => void download()}
              disabled={!url.trim() || downloading}
            >
              Download
            </Button>
            {downloading ? (
              <Typography variant="body2" color="text.secondary">
                Downloading and converting to mp3…
              </Typography>
            ) : null}
          </Stack>

          {downloading ? <LinearProgress /> : null}

          {saved ? (
            <Alert
              severity="success"
              action={
                <Button
                  component={Link}
                  to={ROUTES.playgroundInput}
                  size="small"
                  onClick={() => openInPlayground(saved)}
                >
                  Open in Playground
                </Button>
              }
            >
              Saved <strong>{saved.alias}</strong>
              {saved.durationSeconds ? ` (${formatTimeShort(saved.durationSeconds)})` : ""}.
            </Alert>
          ) : null}
        </Stack>
      </SectionCard>

      <SectionCard
        title="Downloaded audio"
        description="Everything in the store. Selecting one makes it the Playground's working piece."
      >
        <AudioLibraryList onSelect={openInPlayground} reloadToken={reloadToken} />
      </SectionCard>
    </PageContainer>
  );
}

export default YouTubePage;
