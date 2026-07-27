/**
 * Text notation as an input source — no transcription engine involved.
 *
 * One line per time frame; `*Note` is an onset, `Note` a sustain, `A || B` a
 * chord, an empty line a silence. The full contract is
 * `context/music/notation-logic/02-notation-spec.md`.
 *
 * Two hands use **separate text areas**, which the notation spec prefers over
 * an inline `__` separator: the two hands must have the same number of frames,
 * and two columns of text make a mismatch visible before you press anything.
 */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { scoresApi, type MatrixScore } from "../../api";

const EXAMPLE = `*Do-4 || *Mi-4
*Re-4
Re-4
*Mi-4
Mi-4
Mi-4
Mi-4
*Fa#-5`;

export interface TextNotationInputProps {
  tempoBpm: number;
  timeStepSeconds: number;
  onParsed?: (score: MatrixScore, frames: number) => void;
}

/** Split a textarea into frames, keeping blank lines — they are silences. */
function toFrames(text: string): string[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  // Trailing blank lines are almost always a stray Enter, not a silence.
  while (lines.length > 0 && lines[lines.length - 1].trim() === "") lines.pop();
  return lines;
}

export function TextNotationInput({
  tempoBpm,
  timeStepSeconds,
  onParsed,
}: TextNotationInputProps) {
  const [right, setRight] = useState(EXAMPLE);
  const [left, setLeft] = useState("");
  const [twoHands, setTwoHands] = useState(false);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<string | null>(null);

  const rightFrames = toFrames(right);
  const leftFrames = toFrames(left);
  const misaligned = twoHands && leftFrames.length !== rightFrames.length;

  const submit = async () => {
    setBusy(true);
    setError(null);
    setParsed(null);
    try {
      const score = await scoresApi.fromSequence({
        sequence: rightFrames,
        leftSequence: twoHands ? leftFrames : undefined,
        tempoBpm,
        timeStepSeconds,
        title: title.trim() || undefined,
      });
      setParsed(`Parsed ${rightFrames.length} frame(s).`);
      onParsed?.(score, rightFrames.length);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not parse that notation.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {parsed ? <Alert severity="success">{parsed}</Alert> : null}

      <Typography variant="body2" color="text.secondary">
        One line per time frame. <code>*Do-4</code> strikes a key, <code>Do-4</code> holds it,{" "}
        <code>A || B</code> is a chord, an empty line is silence.
      </Typography>

      <TextField
        label="Title (optional)"
        size="small"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        fullWidth
      />

      <FormControlLabel
        control={
          <Switch checked={twoHands} onChange={(event) => setTwoHands(event.target.checked)} />
        }
        label="Two hands"
      />

      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <TextField
          label={twoHands ? "Right hand (treble)" : "Notation"}
          value={right}
          onChange={(event) => setRight(event.target.value)}
          multiline
          minRows={10}
          fullWidth
          slotProps={{ input: { sx: { fontFamily: "monospace", fontSize: 13 } } }}
          helperText={`${rightFrames.length} frame(s)`}
        />
        {twoHands ? (
          <TextField
            label="Left hand (bass)"
            value={left}
            onChange={(event) => setLeft(event.target.value)}
            multiline
            minRows={10}
            fullWidth
            error={misaligned}
            slotProps={{ input: { sx: { fontFamily: "monospace", fontSize: 13 } } }}
            helperText={
              misaligned
                ? `${leftFrames.length} frame(s) — must match the right hand's ${rightFrames.length}`
                : `${leftFrames.length} frame(s)`
            }
          />
        ) : null}
      </Stack>

      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          onClick={() => void submit()}
          disabled={busy || misaligned || rightFrames.length === 0}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
        >
          Parse notation
        </Button>
        <Button onClick={() => setRight(EXAMPLE)}>Reset to example</Button>
      </Stack>
    </Stack>
  );
}

export default TextNotationInput;
