/**
 * Two short requests (implementation 02, Phase 14, plan section 16.1):
 *
 * - **Ask for a fixed version**: the user's own version in the Public Library (accepted before) as
 *   Hard, Medium, Easy, or a new name of that song only;
 * - **Publish** a songs playlist of My library: its songs that are in the Public Library with a
 *   public version go into a public playlist; the dialog names the ones left out.
 */

import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { requestsApi, type PlaylistInfo, type Proposal } from "../../api";
import { PillButton, Segmented } from "../../ui";
import { said } from "../library/shared";
import { NAME_RULE, validName } from "./words";

type Fixed = "hard" | "medium" | "easy" | "other";

export function FixedVersionDialog({
  songTitle,
  version,
  resend,
  onClose,
  onSent,
}: {
  songTitle: string;
  /** The user's version: its public project and its name. */
  version: { projectId: string; name: string };
  resend?: { requestId: number; proposal: Proposal };
  onClose: () => void;
  onSent: (requestId: number) => void;
}) {
  const start = resend?.proposal.name ?? "hard";
  const [choice, setChoice] = useState<Fixed>(["hard", "medium", "easy"].includes(start) ? (start as Fixed) : "other");
  const [other, setOther] = useState(["hard", "medium", "easy"].includes(start) ? version.name : start);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const name = choice === "other" ? other : choice;

  const send = async () => {
    setBusy(true);
    setError(null);
    const proposal: Proposal = { kind: "fixedVersion", userVersion: version.projectId, name, note: note.trim() || null };
    try {
      if (resend) {
        await requestsApi.sendAgain(resend.requestId, proposal);
        onSent(resend.requestId);
      } else {
        onSent((await requestsApi.send(proposal)).id);
      }
    } catch (caught) {
      setError(said(caught, "The request could not be sent."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{resend ? "Change and send again" : "Ask for a fixed version"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
            Your “{version.name}” of {songTitle} as
          </Typography>
          <Segmented<Fixed>
            label="Fixed version"
            value={choice}
            onChange={setChoice}
            options={[
              { value: "hard", label: "Hard" },
              { value: "medium", label: "Medium" },
              { value: "easy", label: "Easy" },
              { value: "other", label: "Other", tooltip: "A new name, for this song only" },
            ]}
          />
          {choice === "other" ? (
            <TextField
              label="Name"
              autoFocus
              value={other}
              onChange={(event) => setOther(event.target.value.toLowerCase().replace(/\s/g, "-"))}
              error={other !== "" && !validName(other)}
              helperText={other !== "" && !validName(other) ? NAME_RULE : undefined}
              slotProps={{ htmlInput: { maxLength: 24 } }}
            />
          ) : null}
          <TextField
            label="Note for the reviewer"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            multiline
            maxRows={4}
          />
          {error ? (
            <Typography role="alert" color="error" sx={{ fontSize: 14 }}>
              {error}
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => void send()} disabled={!validName(name)} busy={busy} data-testid="send-request">
          {resend ? "Send again" : "Send request"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export function PublishPlaylistDialog({
  playlistId,
  resend,
  onClose,
  onSent,
}: {
  playlistId: number;
  resend?: { requestId: number; proposal: Proposal };
  onClose: () => void;
  onSent: (requestId: number) => void;
}) {
  const [info, setInfo] = useState<PlaylistInfo | null>(null);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What the dialog opened on: read once, so a redraw of the page behind it keeps what is typed.
  const [opened] = useState(() => ({ playlistId, resend }));
  useEffect(() => {
    const controller = new AbortController();
    requestsApi
      .playlistInfo(opened.playlistId, controller.signal)
      .then((found) => {
        setInfo(found);
        setTitle(opened.resend?.proposal.title ?? found.title);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlist could not be opened."));
      });
    return () => controller.abort();
  }, [opened]);

  const send = async () => {
    setBusy(true);
    setError(null);
    const proposal: Proposal = { kind: "playlist", playlist: playlistId, title: title.trim(), note: note.trim() || null };
    try {
      if (resend) {
        await requestsApi.sendAgain(resend.requestId, proposal);
        onSent(resend.requestId);
      } else {
        onSent((await requestsApi.send(proposal)).id);
      }
    } catch (caught) {
      setError(said(caught, "The request could not be sent."));
    } finally {
      setBusy(false);
    }
  };

  const songs = info?.items.length ?? 0;
  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{resend ? "Change and send again" : "Publish to the Public library"}</DialogTitle>
      <DialogContent>
        {info ? (
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              label="Title"
              required
              autoFocus
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              slotProps={{ htmlInput: { maxLength: 300 } }}
            />
            <Stack spacing={0.5}>
              <Typography sx={{ fontSize: 14 }}>
                {songs === 0
                  ? "No song of this playlist has a version in the Public library yet."
                  : `${songs} ${songs === 1 ? "song" : "songs"}: ${info.items.map((one) => one.title).join(", ")}`}
              </Typography>
              {info.left.length > 0 ? (
                <Typography sx={{ fontSize: 14, color: "text.secondary" }} data-testid="left-out">
                  Left out, not in the Public library with a version: {info.left.join(", ")}
                </Typography>
              ) : null}
            </Stack>
            <TextField label="Note for the reviewer" value={note} onChange={(event) => setNote(event.target.value)} multiline maxRows={4} />
          </Stack>
        ) : null}
        {error ? (
          <Typography role="alert" color="error" sx={{ fontSize: 14, pt: 1 }}>
            {error}
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton
          kind="primary"
          onClick={() => void send()}
          disabled={songs === 0 || !title.trim()}
          busy={busy}
          data-testid="send-request"
        >
          {resend ? "Send again" : "Send request"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}
