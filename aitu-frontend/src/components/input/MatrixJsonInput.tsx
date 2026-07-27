/**
 * Load a matrix JSON previously downloaded from the Matrix tab.
 *
 * The envelope's `sparse` flag says which payload it carries, so a file exported
 * either way loads without the user choosing anything. Validation is local and
 * deliberately shallow — the backend's Pydantic models are the real gate — but
 * catching a wrong-shaped file here gives a much better message than a 422.
 */

import { useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { matrixApi, type ImportedMatrix, type PianoMatrixEnvelope } from "../../api";

export interface MatrixJsonInputProps {
  /** Called once the backend has stored it, with the uuid every tab reads from. */
  onImported?: (imported: ImportedMatrix, label: string) => void;
}

/** Shallow shape check with a message that names what is missing. */
function validate(value: unknown): string | null {
  if (typeof value !== "object" || value === null) return "That file is not a JSON object.";
  const envelope = value as Partial<PianoMatrixEnvelope>;

  if (typeof envelope.tempoBpm !== "number") return "Missing `tempoBpm`.";
  if (typeof envelope.granularity !== "string") return "Missing `granularity`.";
  if (typeof envelope.matrixProcessingStep !== "string") return "Missing `matrixProcessingStep`.";

  const sparse = envelope.sparse !== false;
  if (sparse && !envelope.matrix && !envelope.rMatrix) {
    return "This says `sparse: true` but carries neither `matrix` nor `rMatrix`.";
  }
  if (!sparse && !envelope.denseMatrix && !envelope.denseRMatrix) {
    return "This says `sparse: false` but carries neither `denseMatrix` nor `denseRMatrix`.";
  }
  return null;
}

function describe(envelope: PianoMatrixEnvelope): string {
  const frames = envelope.sparse
    ? (envelope.matrix?.shape?.[1] ?? envelope.rMatrix?.shape?.[1] ?? 0)
    : (envelope.denseMatrix?.length ?? envelope.denseRMatrix?.length ?? 0);
  return `${frames} frame(s)`;
}

export function MatrixJsonInput({ onImported }: MatrixJsonInputProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState<{ envelope: PianoMatrixEnvelope; name: string } | null>(
    null,
  );
  const [normalized, setNormalized] = useState(0);

  const read = async (file: File) => {
    setError(null);
    setLoaded(null);
    setNormalized(0);

    let envelope: PianoMatrixEnvelope;
    try {
      const parsed: unknown = JSON.parse(await file.text());
      const problem = validate(parsed);
      if (problem) {
        setError(problem);
        return;
      }
      envelope = parsed as PianoMatrixEnvelope;
    } catch (caught) {
      setError(
        caught instanceof Error
          ? `Could not read that file: ${caught.message}`
          : "Could not read that file.",
      );
      return;
    }

    // The backend is the real gate: it revalidates, normalizes, and stores the
    // matrix so every Playground tab can read it like a transcription.
    setBusy(true);
    try {
      const imported = await matrixApi.importJson(envelope);
      const label = envelope.title ?? file.name.replace(/\.json$/i, "");
      setLoaded({ envelope, name: label });
      setNormalized(imported.normalizedCells);
      onImported?.(imported, label);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The import was rejected.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Typography variant="body2" color="text.secondary">
        A matrix JSON exported from the Matrix tab. Dense or sparse — the file says which.
      </Typography>

      <Button
        component="label"
        variant="outlined"
        disabled={busy}
        startIcon={busy ? <CircularProgress size={16} /> : <UploadFileIcon />}
      >
        Choose a matrix JSON
        <input
          ref={inputRef}
          type="file"
          hidden
          accept="application/json,.json"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void read(file);
          }}
        />
      </Button>

      {loaded ? (
        <Alert severity="success">
          Loaded <strong>{loaded.name}</strong>
          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", rowGap: 1 }}>
            <Chip size="small" label={`${loaded.envelope.tempoBpm} BPM`} />
            <Chip size="small" label={loaded.envelope.granularity} />
            <Chip size="small" label={loaded.envelope.matrixProcessingStep} />
            <Chip size="small" label={loaded.envelope.sparse ? "sparse" : "dense"} />
            <Chip size="small" label={describe(loaded.envelope)} />
          </Stack>
          {normalized > 0 ? (
            <Typography variant="caption" sx={{ mt: 1, display: "block" }}>
              {normalized} cell{normalized === 1 ? " was" : "s were"} corrected on the way in — a
              held note with nothing before it becomes a struck note.
            </Typography>
          ) : null}
        </Alert>
      ) : null}
    </Stack>
  );
}

export default MatrixJsonInput;
