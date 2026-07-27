/**
 * `/playground/matrix` — the debugging heart of the Playground.
 *
 * Four things happen here, and they share one fetch:
 *
 * - **Step pills** switch between raw, collapsed, clean and two-hands. Every
 *   step is derived from the same stored raw matrix, so switching is a request,
 *   not a re-transcription.
 * - **BPM and resolution** can be changed in place. That is a *recompute* —
 *   steps 3-5 of the pipeline redone from raw — which is milliseconds, so the
 *   dropdown feels like a filter rather than a job.
 * - **Frame search** jumps to a frame number or a timestamp.
 * - **Export** downloads the current view, dense or sparse.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DownloadIcon from "@mui/icons-material/Download";
import SearchIcon from "@mui/icons-material/Search";
import { Link } from "react-router-dom";
import {
  matrixApi,
  type Granularity,
  type MatrixEnvelope,
  type MatrixProcessingStep,
} from "../../api";
import MatrixGrid from "../../components/matrix/MatrixGrid";
import { parseTime } from "../../audio/time";
import { ROUTES } from "../../layout/routes";
import { TRANSCRIPTION_GRANULARITIES } from "../../music/granularities";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { PageContainer, Pill, SectionCard, semantic } from "../../ui";

const STEPS: { value: MatrixProcessingStep; help: string }[] = [
  { value: "raw", help: "Straight from the model, at the finest resolution." },
  { value: "collapsed", help: "Merged down to the resolution you chose." },
  { value: "clean", help: "Held notes cut short wherever something else is struck." },
  { value: "two-hands", help: "Split at middle C into right and left." },
];

/** State tagged with the request it belongs to, so nothing stale leaks through. */
interface MatrixState {
  key: string;
  envelope: MatrixEnvelope | null;
  error: string | null;
}

export function MatrixPage() {
  const { artifact, update, hasArtifact } = useWorkingArtifact();
  const [step, setStep] = useState<MatrixProcessingStep>("clean");
  const [loaded, setLoaded] = useState<MatrixState>({ key: "", envelope: null, error: null });
  const [searchText, setSearchText] = useState("");
  const [focusFrame, setFocusFrame] = useState<number | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const audioUuid = artifact.audioUuid ?? null;
  const requestKey = audioUuid
    ? `${audioUuid}:${step}:${artifact.granularity}:${artifact.tempoBpm}`
    : "";

  // Derived, not assigned in an effect: a new key means "loading", full stop.
  const current = loaded.key === requestKey ? loaded : { key: requestKey, envelope: null, error: null };
  const envelope = current.envelope;

  useEffect(() => {
    if (!audioUuid) return;
    const controller = new AbortController();

    matrixApi
      .get(
        audioUuid,
        {
          step,
          granularity: artifact.granularity,
          tempoBpm: artifact.tempoBpm,
          sparse: false, // the grid draws the dense form
        },
        controller.signal,
      )
      .then((fetched) => setLoaded({ key: requestKey, envelope: fetched, error: null }))
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: requestKey,
          envelope: null,
          error: caught instanceof Error ? caught.message : "Could not load the matrix.",
        });
      });

    return () => controller.abort();
  }, [audioUuid, step, artifact.granularity, artifact.tempoBpm, requestKey]);

  const search = useCallback(() => {
    setSearchError(null);
    const text = searchText.trim();
    if (!text) return;

    const frames = envelope?.denseMatrix?.length ?? envelope?.denseRMatrix?.length ?? 0;

    // A bare integer is a frame number; anything with a colon or a dot is a time.
    if (/^\d+$/.test(text)) {
      const frame = Number(text);
      if (frame >= frames) {
        setSearchError(`This piece only has ${frames} frames.`);
        return;
      }
      setFocusFrame(frame);
      return;
    }

    const seconds = parseTime(text);
    if (seconds === null) {
      setSearchError("Type a frame number (e.g. 48) or a time (e.g. 1:23.500).");
      return;
    }
    const step = envelope?.timeStepSeconds ?? 1;
    const frame = Math.floor(seconds / step);
    if (frame >= frames) {
      setSearchError(`That is past the end — the piece lasts ${(frames * step).toFixed(2)} s.`);
      return;
    }
    setFocusFrame(frame);
  }, [searchText, envelope]);

  if (!hasArtifact || !audioUuid) {
    return (
      <PageContainer title="Matrix" wide>
        <Alert
          severity="info"
          action={
            <Button component={Link} to={ROUTES.playgroundInput} size="small">
              Go to Input
            </Button>
          }
        >
          No piece loaded. Pick or record an audio on the Input tab and transcribe it first.
        </Alert>
      </PageContainer>
    );
  }

  const dense = envelope?.denseMatrix ?? envelope?.denseRMatrix ?? null;
  const denseLeft = envelope?.denseLMatrix ?? null;

  return (
    <PageContainer
      title="Matrix"
      subtitle="The 88 x N grid: a filled circle is a struck note, a pale one is that note still held."
      wide
      actions={
        <>
          <Button
            component="a"
            href={matrixApi.exportUrl(audioUuid, {
              step,
              granularity: artifact.granularity,
              tempoBpm: artifact.tempoBpm,
              sparse: true,
            })}
            size="small"
            startIcon={<DownloadIcon />}
          >
            Sparse JSON
          </Button>
          <Button
            component="a"
            href={matrixApi.exportUrl(audioUuid, {
              step,
              granularity: artifact.granularity,
              tempoBpm: artifact.tempoBpm,
              sparse: false,
            })}
            size="small"
            startIcon={<DownloadIcon />}
          >
            Dense JSON
          </Button>
        </>
      }
    >
      <SectionCard>
        <Stack spacing={2}>
          <Box>
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
              {STEPS.map((item) => (
                <Pill
                  key={item.value}
                  label={item.value}
                  title={item.help}
                  selected={step === item.value}
                  color={semantic.steps[item.value]}
                  onClick={() => setStep(item.value)}
                />
              ))}
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
              {STEPS.find((item) => item.value === step)?.help}
            </Typography>
          </Box>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            sx={{ alignItems: { sm: "center" } }}
          >
            <TextField
              label="BPM"
              type="number"
              size="small"
              value={artifact.tempoBpm}
              onChange={(event) => update({ tempoBpm: Number(event.target.value) || 60 })}
              slotProps={{ htmlInput: { min: 20, max: 300, step: 1 } }}
              sx={{ width: 110 }}
            />
            <TextField
              label="Resolution"
              select
              size="small"
              value={artifact.granularity}
              onChange={(event) => update({ granularity: event.target.value as Granularity })}
              sx={{ minWidth: 200 }}
            >
              {TRANSCRIPTION_GRANULARITIES.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>

            <Typography variant="caption" color="text.secondary">
              Recomputed from the stored raw matrix — no re-transcription.
            </Typography>

            <Box sx={{ flexGrow: 1 }} />

            <TextField
              label="Go to frame or time"
              size="small"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && search()}
              placeholder="48  or  1:23.500"
              error={Boolean(searchError)}
              helperText={searchError}
              sx={{ width: 220 }}
            />
            <Button size="small" startIcon={<SearchIcon />} onClick={search}>
              Go
            </Button>
          </Stack>
        </Stack>
      </SectionCard>

      {current.error ? <Alert severity="error">{current.error}</Alert> : null}

      {!envelope && !current.error ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 3 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading the matrix…
          </Typography>
        </Stack>
      ) : null}

      {envelope && dense && envelope.columnHeaders && envelope.rowTimestamps ? (
        <MatrixGrid
          dense={dense}
          denseLeft={step === "two-hands" ? denseLeft : null}
          columnHeaders={envelope.columnHeaders}
          rowTimestamps={envelope.rowTimestamps}
          timeStepSeconds={envelope.timeStepSeconds}
          focusFrame={focusFrame}
        />
      ) : null}

      {envelope && dense && dense.length === 0 ? (
        <Alert severity="warning" sx={{ mt: 2 }}>
          This matrix is empty. If you transcribed with the <code>silent</code> engine, install a
          real one with <code>uv sync --extra transcription</code> and run it again.
        </Alert>
      ) : null}
    </PageContainer>
  );
}

export default MatrixPage;
