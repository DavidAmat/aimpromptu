/** A dialog with one text field and one button: rename a song, a version, an artist's name. */

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import { PillButton } from "../../ui";

export interface TextDialogProps {
  title: string;
  label: string;
  initial?: string;
  confirmLabel: string;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: (value: string) => void;
}

/** One field and one button. Mounted only while it is open, so it starts from `initial`. */
export function TextDialog({ title, label, initial = "", confirmLabel, busy, error, onCancel, onConfirm }: TextDialogProps) {
  const [value, setValue] = useState(initial);
  const cleaned = value.trim();
  const valid = cleaned.length > 0 && cleaned !== initial.trim();
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label={label}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && valid) onConfirm(cleaned);
          }}
          error={error !== null}
          helperText={error ?? undefined}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => onConfirm(cleaned)} disabled={!valid} busy={busy}>
          {confirmLabel}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}
