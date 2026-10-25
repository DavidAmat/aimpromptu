/**
 * **Enhance with AI** for one stretch, with the user's own words (implementation 03, Phase 7, plan task 7.5): the
 * stretch of the notes picked, or of the frames marked. The user writes a short instruction (optional: without words
 * the AI writes the stretch as it always does); the AI writes the hands, beams, clefs and ornaments of that stretch
 * again, in about half a minute, while the stretch has the pale veil of plan section 3.6. The answer is one step of
 * undo.
 */

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import { PillButton } from "../../../../ui";

/** As the backend takes them (`REQUEST_CHARS`). */
const MAX_WORDS = 1000;

export function EnhanceStretchDialog({
  open,
  what,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  /** What is about to be written again, said for the title: "these 4 notes", "this stretch of the left hand". */
  what: string;
  onConfirm: (instruction: string) => void;
  onCancel: () => void;
}) {
  const [words, setWords] = useState("");
  const send = () => {
    onConfirm(words.trim());
    setWords("");
  };
  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Enhance {what} with AI</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          The AI writes this stretch again, both hands, following your words first: the hands, beams, clefs and
          ornaments, and it can take notes off the sheet when you ask (for example single notes instead of octaves).
          Leave it empty to let the AI decide. It takes a few seconds and about one cent of the monthly credits; undo
          takes it back.
        </DialogContentText>
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={2}
          maxRows={6}
          label="What should the AI change?"
          placeholder="All these notes are in the left hand: share them between the two hands."
          value={words}
          onChange={(event) => setWords(event.target.value.slice(0, MAX_WORDS))}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) send();
          }}
          slotProps={{ htmlInput: { "data-testid": "stretch-words" } }}
        />
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={send} data-testid="stretch-confirm">
          Enhance with AI
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default EnhanceStretchDialog;
