/**
 * How finely to measure the piece, which model to use, and the Run button.
 *
 * There is one number to choose here and it is a length of time. A matrix column is a slice of wall
 * clock, so the question is how fine that slice should be, and the answer decides how precisely the
 * page follows the recording. It does not decide what any note is called: the rhythmic figures are
 * chosen afterwards, on the Rhythm step, from the playing itself.
 *
 * The tempo used to be asked for here, and it was the most damaging field in the app. The engine's
 * timings were snapped onto a grid derived from it, so a piece played at 63 and declared as 60
 * drifted a whole column every twenty beats, and the printed figures described the mistake rather
 * than the music. Nothing is derived from a tempo any more, so the field, and the calculator that
 * helped guess it, are gone.
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
import { matrixApi, type AudioItem } from "../../api";
import ProgressBanner from "../ProgressBanner";
import { useProgress } from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { formatTime } from "../../audio/time";
import { FRAME_MS_CHOICES } from "../../music/granularities";

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

  // Transcribing stores the recorded notes under the audio uuid, and Rhythm is
  // what reads them: naming a gap is the next thing a person does.
  useEffect(() => {
    if (progress.status === "done" && audioUuid) {
      navigate(ROUTES.playgroundRhythm);
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
        frameMs: artifact.frameMs,
        engine: engine || undefined,
        // Clicking Run means a fresh transcription of this exact physical audio.
        force: true,
      });
      setJobId(handle.jobId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the transcription.");
    } finally {
      setStarting(false);
    }
  };

  const noEngine =
    engines !== null && !Object.entries(engines).some(([name, ready]) => ready && name !== "silent");

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
          label="Time resolution"
          select
          size="small"
          value={artifact.frameMs}
          onChange={(event) => update({ frameMs: Number(event.target.value) })}
          sx={{ minWidth: 260 }}
          helperText="How finely the page follows the recording"
        >
          {FRAME_MS_CHOICES.map((option) => (
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
            helperText="Which model listens to the audio"
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
            Transcribing the complete saved segment ({formatTime(audio.durationSeconds ?? 0)}). It
            maps to original-audio time{" "}
            <strong style={{ whiteSpace: "nowrap" }}>
              {formatTime(audio.sourceTimeRange.startSeconds)}–
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
          Create the selected segment first. Transcription always runs against the exact audio shown
          in the waveform.
        </Alert>
      ) : null}

      <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
        <Button
          variant="contained"
          startIcon={starting ? <CircularProgress size={16} /> : <PlayArrowIcon />}
          onClick={() => void run()}
          disabled={
            !audioUuid || requiresSegmentCreation || starting || progress.status === "running"
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
