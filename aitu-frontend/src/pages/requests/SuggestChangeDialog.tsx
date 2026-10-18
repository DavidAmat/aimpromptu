/**
 * A **metadata** request (implementation 02, Phase 14, plan section 16.1): the app context's "PR
 * for changing the metadata of a public song", and the way to propose a song or an artist the
 * Public Library does not have.
 *
 * - **Suggest a change** on a public song: its fields, filled as they are; the request carries
 *   what changed.
 * - **Suggest a change** on a public artist: a new default name, and more names ("Jackson Five"
 *   for "The Jackson 5").
 * - **Propose a song** (the Public songs page): a new song with its artists.
 *
 * With `resend`, the dialog opens on a request with changes asked, filled as it was sent.
 */

import { useEffect, useState } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  publicApi,
  requestsApi,
  type Proposal,
  type PublicArtistDetail,
  type PublicLists,
  type PublicSongDetail,
} from "../../api";
import { PillButton } from "../../ui";
import { said } from "../library/shared";
import { draftOf, draftReady, EMPTY_SONG, toFields, type SongDraft } from "./songDraft";
import { SongFieldsForm } from "./SongFieldsForm";

export type ChangeTarget =
  | { kind: "song"; song: PublicSongDetail }
  | { kind: "artist"; artist: PublicArtistDetail }
  | { kind: "newSong" };

export interface SuggestChangeDialogProps {
  target: ChangeTarget;
  resend?: { requestId: number; proposal: Proposal };
  onClose: () => void;
  onSent: (requestId: number) => void;
}

/** A public song as a draft: its own fields, its regions by code. */
function draftOfSong(song: PublicSongDetail, lists: PublicLists): SongDraft {
  return {
    title: song.title,
    year: song.year ? String(song.year) : "",
    artists: song.artists.map((one) => ({ name: one.name, publicId: one.artistId })),
    genres: song.genres,
    regions: song.regions.map((name) => lists.regions.find((one) => one.name === name)?.code ?? name),
    tags: song.tags.map(([category, value]) => ({ category, value })),
  };
}

export function SuggestChangeDialog({ target, resend, onClose, onSent }: SuggestChangeDialogProps) {
  const [lists, setLists] = useState<PublicLists | null>(null);
  const [draft, setDraft] = useState<SongDraft | null>(target.kind === "newSong" && !resend ? EMPTY_SONG : null);
  const [name, setName] = useState(target.kind === "artist" ? (resend?.proposal.artist?.name ?? target.artist.name) : "");
  const [added, setAdded] = useState<string[]>(target.kind === "artist" ? (resend?.proposal.artist?.addNames ?? []) : []);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What the dialog opened on: read once, so a redraw of the page behind it keeps what is typed.
  const [opened] = useState(() => ({ target, resend }));
  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .lists(controller.signal)
      .then(async (found) => {
        setLists(found);
        const fields = opened.resend?.proposal.changes ?? opened.resend?.proposal.song?.new;
        if (fields) setDraft(await draftOf(fields));
        else if (opened.target.kind === "song") setDraft(draftOfSong(opened.target.song, found));
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "This could not be opened."));
      });
    return () => controller.abort();
  }, [opened]);

  const proposal = (): Proposal => {
    const base = { kind: "metadata" as const, note: note.trim() || null };
    if (target.kind === "artist") {
      return {
        ...base,
        artist: {
          publicId: target.artist.id,
          name: name.trim() && name.trim() !== target.artist.name ? name.trim() : null,
          addNames: added,
        },
      };
    }
    if (target.kind === "song") return { ...base, song: { publicId: target.song.id }, changes: toFields(draft ?? EMPTY_SONG) };
    return { ...base, song: { new: toFields(draft ?? EMPTY_SONG) } };
  };

  const ready =
    !busy &&
    (target.kind === "artist" ? name.trim().length > 0 && (name.trim() !== target.artist.name || added.length > 0) : draft !== null && draftReady(draft));

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      if (resend) {
        await requestsApi.sendAgain(resend.requestId, proposal());
        onSent(resend.requestId);
      } else {
        onSent((await requestsApi.send(proposal())).id);
      }
    } catch (caught) {
      setError(said(caught, "The request could not be sent."));
    } finally {
      setBusy(false);
    }
  };

  const title = resend ? "Change and send again" : target.kind === "newSong" ? "Propose a song" : "Suggest a change";
  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {target.kind === "artist" ? (
            <>
              <TextField
                label="Name"
                required
                autoFocus
                value={name}
                onChange={(event) => setName(event.target.value)}
                slotProps={{ htmlInput: { maxLength: 300 } }}
              />
              <Autocomplete<string, true, false, true>
                multiple
                freeSolo
                options={[]}
                value={added}
                onChange={(_, values) => setAdded(values.map((one) => one.trim()).filter(Boolean))}
                renderValue={(values, getItemProps) =>
                  values.map((option, index) => <Chip {...getItemProps({ index })} key={option} label={option} size="small" />)
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Other names"
                    helperText={
                      target.artist.otherNames.length > 0
                        ? `It has: ${target.artist.otherNames.join(", ")}. Type a name and press Enter.`
                        : "Type a name and press Enter"
                    }
                  />
                )}
              />
            </>
          ) : draft ? (
            <SongFieldsForm value={draft} onChange={setDraft} lists={lists} autoFocus />
          ) : null}
          <TextField
            label="Note for the reviewer"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            multiline
            maxRows={4}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
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
        <PillButton kind="primary" onClick={() => void send()} disabled={!ready} busy={busy} data-testid="send-request">
          {resend ? "Send again" : "Send request"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default SuggestChangeDialog;
