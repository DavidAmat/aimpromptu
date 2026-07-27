/**
 * BPM, granularity, and the Run button that starts the pipeline.
 *
 * Two things worth knowing about the numbers here:
 *
 * **BPM is the single most sensitive input.** The engine's timings are snapped
 * onto a grid derived from it, so a piece played at 63 BPM and declared as 60
 * drifts a whole column every twenty beats. The doc's General Note says as much;
 * the helper text says it to the user.
 *
 * **The granularity you pick is not the one that gets transcribed.** The raw
 * matrix is always built at fusa and then collapsed, which is why changing this
 * later is instant — it re-collapses rather than re-transcribing.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useNavigate } from "react-router-dom";
import { matrixApi, type AudioItem, type Granularity } from "../../api";
import ProgressBanner from "../ProgressBanner";
import { useProgress } from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { formatTime } from "../../audio/time";
import { TRANSCRIPTION_GRANULARITIES } from "../../music/granularities";

export interface TranscriptionSettingsProps {
  /** Disabled when no audio is loaded. */
  audioUuid?: string | null;
  /** Metadata distinguishes a full file from a persisted physical segment. */
  audio?: AudioItem | null;
  /** A selected range must be materialized before the pipeline can run. */
  requiresSegmentCreation?: boolean;
}

export function TranscriptionSettings({
  audioUuid,
  audio,
  requiresSegmentCreation = false,
}: TranscriptionSettingsProps) {
  const navigate = useNavigate();
  const { artifact, update } = useWorkingArtifact();
  const [engines, setEngines] = useState<Record<string, boolean> | null>(null);
  const [engine, setEngine] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const progress = useProgress(jobId ? matrixApi.progressUrl(jobId) : null);

  useEffect(() => {
    const controller = new AbortController();
    matrixApi
      .engines(controller.signal)
      .then((available) => {
        setEngines(available);
        const usable = Object.entries(available).find(
          ([name, ready]) => ready && name !== "silent",
        );
        setEngine(usable ? usable[0] : "silent");
      })
      .catch(() => {
        if (!controller.signal.aborted) setEngines({});
      });
    return () => controller.abort();
  }, []);

  // The pipeline writes its artifacts under the audio uuid, so that is the
  // handoff: the Matrix tab reads them straight back.
  useEffect(() => {
    if (progress.status === "done" && audioUuid) {
      navigate(ROUTES.playgroundMatrix);
    }
  }, [progress.status, audioUuid, navigate]);

  const run = async () => {
    if (!audioUuid) return;
    setStarting(true);
    setError(null);
    progress.reset();
    try {
      const handle = await matrixApi.transcribe({
        audioUuid,
        tempoBpm: artifact.tempoBpm,
        granularity: artifact.granularity,
        engine: engine || undefined,
        // Clicking Run means a fresh transcription of this exact physical
        // audio. Recompute remains available later for BPM/resolution changes.
        force: true,
      });
      setJobId(handle.jobId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the transcription.");
    } finally {
      setStarting(false);
    }
  };

  const noEngine = engines !== null && !Object.entries(engines).some(([n, r]) => r && n !== "silent");

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {noEngine ? (
        <Alert severity="warning">
          No transcription model is installed, so only the <code>silent</code> engine is available
          and every piece will come out empty. Install one with{" "}
          <code>uv sync --extra transcription</code> in <code>aitu-backend/</code>.
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <TextField
          label="BPM"
          type="number"
          size="small"
          value={artifact.tempoBpm}
          onChange={(event) => update({ tempoBpm: Number(event.target.value) || 60 })}
          slotProps={{ htmlInput: { min: 20, max: 300, step: 1 } }}
          sx={{ width: 120 }}
          helperText="The tempo you played at"
        />

        <TextField
          label="Temporal resolution"
          select
          size="small"
          value={artifact.granularity}
          onChange={(event) => update({ granularity: event.target.value as Granularity })}
          sx={{ minWidth: 220 }}
          helperText="Changeable later without re-transcribing"
        >
          {TRANSCRIPTION_GRANULARITIES.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>

        {engines && Object.keys(engines).length > 1 ? (
          <TextField
            label="Engine"
            select
            size="small"
            value={engine}
            onChange={(event) => setEngine(event.target.value)}
            sx={{ minWidth: 170 }}
          >
            {Object.entries(engines).map(([name, ready]) => (
              <MenuItem key={name} value={name} disabled={!ready}>
                {name}
                {ready ? "" : " (not installed)"}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
      </Stack>

      <Typography variant="body2" color="text.secondary">
        {audio?.sourceTimeRange ? (
          <>
            Transcribing the complete saved segment ({formatTime(audio.durationSeconds ?? 0)}).
            It maps to original-audio time{" "}
            <strong style={{ whiteSpace: "nowrap" }}>
              {formatTime(audio.sourceTimeRange.startSeconds)}–{" "}
              {formatTime(audio.sourceTimeRange.endSeconds)}
            </strong>
            .
          </>
        ) : (
          "Transcribing the entire audio file. Choose and create a segment above if you only want part of it."
        )}
      </Typography>

      {requiresSegmentCreation ? (
        <Alert severity="warning">
          Create the selected segment first. Transcription always runs against the exact audio
          shown in the waveform.
        </Alert>
      ) : null}

      <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
        <Button
          variant="contained"
          startIcon={starting ? <CircularProgress size={16} /> : <PlayArrowIcon />}
          onClick={() => void run()}
          disabled={
            !audioUuid ||
            requiresSegmentCreation ||
            starting ||
            progress.status === "running"
          }
        >
          Run transcription
        </Button>
        {!audioUuid ? (
          <Typography variant="body2" color="text.secondary">
            Pick or record an audio first.
          </Typography>
        ) : null}
      </Stack>

      <ProgressBanner progress={progress} fallbackLabel="Starting" />
    </Stack>
  );
}

export default TranscriptionSettings;
