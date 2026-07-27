/** Pick a file, optionally name it, upload it to the store. */

import { useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { audioApi, SUPPORTED_AUDIO_SUFFIXES, type AudioItem } from "../../api";

export interface AudioUploadProps {
  onUploaded?: (audio: AudioItem) => void;
}

export function AudioUpload({ onUploaded }: AudioUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [alias, setAlias] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const stored = await audioApi.upload(file, alias.trim() || undefined);
      setFile(null);
      setAlias("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.(stored);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={1.5}>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
        {file ? file.name : "Choose an audio file"}
        <input
          ref={inputRef}
          type="file"
          hidden
          accept={SUPPORTED_AUDIO_SUFFIXES.join(",")}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
          }}
        />
      </Button>

      <Typography variant="caption" color="text.secondary">
        Accepted: {SUPPORTED_AUDIO_SUFFIXES.join(", ")}
      </Typography>

      <TextField
        label="Name (optional)"
        size="small"
        value={alias}
        onChange={(event) => setAlias(event.target.value)}
        placeholder="Defaults to the file name"
        fullWidth
      />

      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          onClick={() => void submit()}
          disabled={!file || busy}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
        >
          Upload
        </Button>
      </Stack>
    </Stack>
  );
}

export default AudioUpload;
