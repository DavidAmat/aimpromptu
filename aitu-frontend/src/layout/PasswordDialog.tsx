/**
 * **Change password**, from the user menu (implementation 02, plan section 9.1). The user's other
 * sessions end; this one stays.
 */

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { ApiError, authApi } from "../api";
import { PillButton } from "../ui";

const MIN_PASSWORD = 8;

export function PasswordDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  /** Closing forgets what was typed, so the next opening starts empty. */
  const close = () => {
    setCurrent("");
    setNext("");
    setError(null);
    setDone(false);
    onClose();
  };

  const ready = current.length > 0 && next.length >= MIN_PASSWORD;
  const submit = async () => {
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      await authApi.changePassword(current, next);
      setDone(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "The password was not changed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs">
      <DialogTitle>Change password</DialogTitle>
      <DialogContent>
        {done ? (
          <Typography sx={{ pt: 1 }}>Your password is changed. Other devices are signed out.</Typography>
        ) : (
          <Stack
            component="form"
            spacing={2}
            sx={{ pt: 1 }}
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <TextField
              label="Current password"
              type="password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              autoComplete="current-password"
              autoFocus
            />
            <TextField
              label="New password"
              type="password"
              value={next}
              onChange={(event) => setNext(event.target.value)}
              autoComplete="new-password"
              helperText={`At least ${MIN_PASSWORD} characters`}
            />
            {error ? (
              <Typography role="alert" sx={{ color: "error.main", fontSize: 14 }}>
                {error}
              </Typography>
            ) : null}
            <button type="submit" hidden />
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        {done ? (
          <PillButton kind="primary" onClick={close}>
            Close
          </PillButton>
        ) : (
          <>
            <PillButton onClick={close}>Cancel</PillButton>
            <PillButton kind="primary" busy={busy} disabled={!ready} onClick={() => void submit()}>
              Change password
            </PillButton>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default PasswordDialog;
