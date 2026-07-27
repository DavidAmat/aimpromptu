/**
 * Record from the microphone, listen back, name it, save it.
 *
 * Flow: idle -> recording (live bars) -> recorded (preview + name) -> saved.
 * "Discard" returns to idle without touching the store.
 */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import StopIcon from "@mui/icons-material/Stop";
import { audioApi, type AudioItem } from "../../api";
import { formatTime } from "../../audio/time";
import { fileNameFor, useRecorder } from "../../audio/useRecorder";
import { SectionCard, semantic } from "../../ui";
import LiveLevelBars from "./LiveLevelBars";

export interface AudioRecorderProps {
  /** Called once the take is stored, with the new library entry. */
  onSaved?: (audio: AudioItem) => void;
}

export function AudioRecorder({ onSaved }: AudioRecorderProps) {
  const recorder = useRecorder();
  const [alias, setAlias] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const save = async () => {
    if (!recorder.blob) return;
    // Name the file after the container the browser actually used: the backend
    // reads the format from the suffix.
    const filename = fileNameFor(recorder.blob.type, alias.trim() || "recording");
    if (filename === null) {
      setSaveError("This browser recorded a format we do not recognize.");
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      const file = new File([recorder.blob], filename, { type: recorder.blob.type });
      const stored = await audioApi.storeRecording(file, alias.trim() || undefined);
      recorder.reset();
      setAlias("");
      onSaved?.(stored);
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : "Could not save the recording.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard
      title="Record"
      description="Play into the microphone; the bars react to what the mic hears."
    >
      <Stack spacing={2}>
        {recorder.error ? <Alert severity="error">{recorder.error}</Alert> : null}
        {saveError ? <Alert severity="error">{saveError}</Alert> : null}

        <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
          {recorder.status === "recording" ? (
            <Button
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={recorder.stop}
            >
              Stop
            </Button>
          ) : (
            <Button
              variant="contained"
              startIcon={<FiberManualRecordIcon sx={{ color: semantic.status.error }} />}
              onClick={() => void recorder.start()}
              disabled={recorder.status === "requesting" || saving}
            >
              {recorder.status === "recorded" ? "Record again" : "Record"}
            </Button>
          )}

          <Typography variant="body2" color="text.secondary">
            {recorder.status === "requesting"
              ? "Waiting for microphone permission…"
              : formatTime(recorder.elapsedSeconds)}
          </Typography>
        </Stack>

        <LiveLevelBars levels={recorder.levels} active={recorder.status === "recording"} />

        {recorder.status === "recorded" && recorder.previewUrl ? (
          <Stack spacing={1.5}>
            <Typography variant="body2">Listen back before saving:</Typography>
            <Box
              component="audio"
              controls
              src={recorder.previewUrl}
              sx={{ width: "100%" }}
            />
            <TextField
              label="Name this recording"
              size="small"
              value={alias}
              onChange={(event) => setAlias(event.target.value)}
              placeholder="Do Re Mi at 60 BPM"
              fullWidth
            />
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                onClick={() => void save()}
                disabled={saving}
                startIcon={saving ? <CircularProgress size={16} /> : undefined}
              >
                Save to library
              </Button>
              <Button onClick={recorder.reset} disabled={saving}>
                Discard
              </Button>
            </Stack>
          </Stack>
        ) : null}
      </Stack>
    </SectionCard>
  );
}

export default AudioRecorder;
