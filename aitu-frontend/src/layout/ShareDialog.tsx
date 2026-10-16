/**
 * **Share my library** (implementation 02, Phase 14, plan section 15.4): the other users, each with
 * a switch. A user switched on sees the whole Private Library under **My library → Shared**, read
 * only: they play it, copy from it and add its songs to their own library. A change applies at
 * once. Opened from the user menu and from the Shared page.
 */

import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import { sharesApi, type Shares } from "../api";
import { said } from "../pages/library/shared";
import { PillButton } from "../ui";

export function ShareDialog({ onClose }: { onClose: () => void }) {
  const [shares, setShares] = useState<Shares | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    sharesApi
      .list(controller.signal)
      .then(setShares)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The users could not be loaded."));
      });
    return () => controller.abort();
  }, []);

  const flip = async (userId: number, on: boolean) => {
    setBusy(userId);
    setError(null);
    try {
      setShares(on ? await sharesApi.share(userId) : await sharesApi.stop(userId));
    } catch (caught) {
      setError(said(caught, "That did not work."));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Share my library</DialogTitle>
      <DialogContent>
        {shares === null ? null : shares.people.length === 0 ? (
          <Typography color="text.secondary">There is nobody else to share with yet.</Typography>
        ) : (
          <Stack>
            {shares.people.map((person) => (
              <FormControlLabel
                key={person.id}
                sx={{ justifyContent: "space-between", ml: 0, py: 0.25 }}
                labelPlacement="start"
                label={person.username}
                control={
                  <Switch
                    checked={shares.sharedWith.includes(person.id)}
                    disabled={busy !== null}
                    onChange={(event) => void flip(person.id, event.target.checked)}
                    slotProps={{ input: { "aria-label": `Share with ${person.username}` } }}
                  />
                }
              />
            ))}
          </Stack>
        )}
        {error ? (
          <Typography role="alert" color="error" sx={{ fontSize: 14, pt: 1 }}>
            {error}
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <PillButton kind="primary" onClick={onClose}>
          Done
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ShareDialog;
