/**
 * The confirmation before a costly or destructive action. The confirm button repeats the action
 * ("Delete 3 projects"), never "Yes" or "OK"; the other button is **Cancel** (guidelines 4.3).
 */

import type { ReactNode } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import PillButton from "./PillButton";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** What happens, in one or two sentences, when it is not obvious from the title. */
  message?: ReactNode;
  /** The action, repeated: "Delete 3 projects". */
  confirmLabel: string;
  cancelLabel?: string;
  /** Draws the confirm button in the danger colour: the action cannot be undone. */
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  /** A third choice between the two, such as **Discard** when leaving unsaved changes. */
  extra?: ReactNode;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel = "Cancel",
  danger,
  busy,
  onConfirm,
  onCancel,
  extra,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      {message ? (
        <DialogContent>
          <DialogContentText component="div">{message}</DialogContentText>
        </DialogContent>
      ) : null}
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </PillButton>
        {extra}
        <PillButton kind={danger ? "danger" : "primary"} onClick={onConfirm} busy={busy}>
          {confirmLabel}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ConfirmDialog;
