/**
 * Start a piece with nothing in it (Epic 13, Subtask 13.1.1.1).
 *
 * The fourth way into the Playground, and the only one that does not begin with a recording. There
 * is no BPM to choose and no granularity to choose, because neither exists any more; the only
 * question is the name, plus the column length to read it at, which is a view like every other and
 * can be changed later without touching the music.
 *
 * What it makes is an empty `events.json`. The piece draws an empty pair of staves and has no
 * ladder — the ladder arrives with the first passage, named from its peak plot the ordinary way.
 */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { editingApi, type AudioItem } from "../../api";

/**
 * Column lengths worth offering. 40 ms is the default (D-01); finer is for playing that lands
 * closer together than one column can tell apart, coarser for a page that should be read loosely.
 */
const FRAME_CHOICES = [20, 40, 60, 80];

export interface ComposeNewPieceProps {
  onCreated: (piece: AudioItem) => void;
}

export function ComposeNewPiece({ onCreated }: ComposeNewPieceProps) {
  const [name, setName] = useState("");
  const [frameMs, setFrameMs] = useState(40);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const piece = await editingApi.createPiece({ name: name.trim(), frameMs });
      setName("");
      onCreated(piece);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the piece.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Typography variant="body2" color="text.secondary">
        An empty piece, built one passage at a time on the <strong>Piano Sheet</strong> tab: play a
        passage, look at it, play it again until it is right, then put it in.
      </Typography>
      <TextField
        label="Name"
        size="small"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Study in progress"
        fullWidth
      />
      <TextField
        label="One column is"
        select
        size="small"
        value={frameMs}
        onChange={(event) => setFrameMs(Number(event.target.value))}
        helperText="How finely the piece is measured. A view, not a decision about the music."
        sx={{ maxWidth: 260 }}
      >
        {FRAME_CHOICES.map((choice) => (
          <MenuItem key={choice} value={choice}>
            {choice} ms
          </MenuItem>
        ))}
      </TextField>
      <Button
        variant="contained"
        onClick={() => void create()}
        disabled={busy || !name.trim()}
        sx={{ alignSelf: "flex-start" }}
      >
        {busy ? <CircularProgress size={16} /> : "Start an empty piece"}
      </Button>
    </Stack>
  );
}

export default ComposeNewPiece;
