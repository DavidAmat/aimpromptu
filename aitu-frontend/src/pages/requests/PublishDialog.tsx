/**
 * **Publish** a version of My library to the Public Library (implementation 02, Phase 14, plan
 * section 16.2): one dialog, three things.
 *
 * 1. **Public song**: the Public Library's songs, searched from the song's own title (a song that
 *    already stands for a public song starts on it). When it is not there, **Propose this song**
 *    opens its fields, its artists each a public artist or a new one.
 * 2. **Version name**: the simple form of the version's own name (lowercase letters, digits and
 *    hyphens). A name the user already has on that song replaces their version there.
 * 3. **Send request**. The project is copied now, so later edits do not change what is reviewed.
 *
 * With `resend`, the dialog opens on a request with changes asked, filled as it was sent, and
 * **Send again** replaces the items that were not accepted.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";
import {
  publicApi,
  requestsApi,
  type Proposal,
  type PublicLists,
  type PublicSongRow,
  type PublishInfo,
} from "../../api";
import { ROUTES } from "../../layout/routes";
import { PillButton } from "../../ui";
import { said } from "../library/shared";
import { draftOf, draftReady, EMPTY_SONG, toFields, type SongDraft } from "./songDraft";
import { SongFieldsForm } from "./SongFieldsForm";
import { NAME_RULE, validName } from "./words";

export interface PublishDialogProps {
  versionId: number;
  /** A request with changes asked, to send again. */
  resend?: { requestId: number; proposal: Proposal };
  onClose: () => void;
  onSent: (requestId: number) => void;
}

type Chosen = { id: number; title: string; artists: string };

export function PublishDialog({ versionId, resend, onClose, onSent }: PublishDialogProps) {
  const [info, setInfo] = useState<PublishInfo | null>(null);
  const [lists, setLists] = useState<PublicLists | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [proposing, setProposing] = useState(false);
  const [chosen, setChosen] = useState<Chosen | null>(null);
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<PublicSongRow[]>([]);
  const [draft, setDraft] = useState<SongDraft>(EMPTY_SONG);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What the dialog opened on: read once, so a redraw of the page behind it keeps what is typed.
  const [opened] = useState(() => ({ versionId, resend }));
  useEffect(() => {
    const { versionId, resend } = opened;
    const controller = new AbortController();
    Promise.all([requestsApi.publishInfo(versionId, controller.signal), publicApi.lists(controller.signal)])
      .then(async ([found, fixed]) => {
        setLists(fixed);
        setInfo(found);
        const song = resend?.proposal.song;
        if (song?.new) {
          setDraft(await draftOf(song.new));
          setProposing(true);
        } else {
          setDraft({
            ...EMPTY_SONG,
            title: found.songTitle,
            artists: found.artists.length
              ? found.artists.map((one) => ({
                  name: one.publicName ?? one.name,
                  publicId: one.publicId,
                  privateId: one.privateId,
                }))
              : EMPTY_SONG.artists,
          });
        }
        const publicId = song?.publicId ?? (resend ? null : found.publicSongId);
        if (publicId) {
          const detail = await publicApi.song(publicId, controller.signal);
          setChosen({ id: detail.id, title: detail.title, artists: detail.artists.map((one) => one.name).join(", ") });
          setSearch(detail.title);
        } else {
          setSearch(found.songTitle);
        }
        setName(resend?.proposal.versionName ?? found.suggestedName);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setLoadError(said(caught, "This version could not be opened."));
      });
    return () => controller.abort();
  }, [opened]);

  // The Public Library's songs follow what is typed, after a pause.
  useEffect(() => {
    const typed = search.trim();
    if (typed.length < 2 || chosen?.title === search) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      publicApi
        .suggest(typed, { limit: 8 }, controller.signal)
        .then((found) => setOptions(found.songs))
        .catch(() => undefined);
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [search, chosen]);

  const nameOk = validName(name);
  const replaces = info !== null && chosen !== null && info.publicSongId === chosen.id && info.ownVersions.includes(name);
  const ready =
    info !== null && info.ready && nameOk && (proposing ? draftReady(draft) : chosen !== null) && !busy;

  const send = async () => {
    if (!info) return;
    setBusy(true);
    setError(null);
    const proposal: Proposal = {
      kind: "userVersion",
      version: info.versionId,
      versionName: name,
      song: proposing
        ? { new: toFields(draft), privateId: info.songId }
        : { publicId: chosen?.id ?? null, privateId: info.songId },
      note: note.trim() || null,
    };
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
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{resend ? "Change and send again" : "Publish to the Public library"}</DialogTitle>
      <DialogContent>
        {loadError ? (
          <Typography role="alert" color="error" sx={{ pt: 1 }}>
            {loadError}
          </Typography>
        ) : info === null ? null : (
          <Stack spacing={2.5} sx={{ pt: 1 }}>
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
              {info.songTitle}, version “{info.versionName}”
            </Typography>
            {!info.ready ? <Alert severity="error">Save the piano sheet of this version first.</Alert> : null}
            {info.waitingRequest !== null && !resend ? (
              <Alert severity="info">
                <Link component={RouterLink} to={ROUTES.request(info.waitingRequest)} color="inherit">
                  Request {info.waitingRequest}
                </Link>{" "}
                already waits for this version.
              </Alert>
            ) : null}

            {proposing ? (
              <Stack spacing={1}>
                <Stack direction="row" sx={{ alignItems: "baseline", justifyContent: "space-between" }}>
                  <Typography sx={{ fontWeight: 600, fontSize: 14 }}>New song</Typography>
                  <PillButton kind="quiet" size="small" onClick={() => setProposing(false)}>
                    Choose a public song
                  </PillButton>
                </Stack>
                <SongFieldsForm value={draft} onChange={setDraft} lists={lists} />
              </Stack>
            ) : (
              <Stack spacing={0.5}>
                <Autocomplete<PublicSongRow, false, false, true>
                  freeSolo
                  options={search.trim().length >= 2 ? options : []}
                  filterOptions={(found) => found}
                  getOptionLabel={(option) => (typeof option === "string" ? option : option.title)}
                  renderOption={(props, option) => (
                    <li {...props} key={option.id}>
                      <Stack sx={{ minWidth: 0 }}>
                        <Typography noWrap sx={{ fontSize: 14 }}>
                          {option.title}
                        </Typography>
                        <Typography noWrap sx={{ fontSize: 13, color: "text.secondary" }}>
                          {option.artists.map((one) => one.name).join(", ") || "No artist"}
                          {option.year ? `, ${option.year}` : ""}
                        </Typography>
                      </Stack>
                    </li>
                  )}
                  inputValue={search}
                  onInputChange={(_, typed, reason) => {
                    setSearch(typed);
                    if (reason === "input") setChosen(null);
                  }}
                  onChange={(_, value) => {
                    if (value && typeof value !== "string") {
                      setChosen({ id: value.id, title: value.title, artists: value.artists.map((one) => one.name).join(", ") });
                    }
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      autoFocus
                      label="Public song"
                      required
                      helperText={chosen ? chosen.artists || "No artist" : "Search the Public library"}
                    />
                  )}
                />
                <Box>
                  <PillButton kind="quiet" size="small" onClick={() => setProposing(true)} data-testid="propose-song">
                    Propose this song
                  </PillButton>
                </Box>
              </Stack>
            )}

            <TextField
              label="Version name"
              required
              value={name}
              onChange={(event) => setName(event.target.value.toLowerCase().replace(/\s/g, "-"))}
              error={name !== "" && !nameOk}
              helperText={
                name !== "" && !nameOk ? NAME_RULE : replaces ? `Replaces your “${name}” in the Public library` : undefined
              }
              slotProps={{ htmlInput: { maxLength: 24 } }}
            />
            <TextField
              label="Note for the reviewer"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              multiline
              minRows={1}
              maxRows={4}
              slotProps={{ htmlInput: { maxLength: 2000 } }}
            />
            {error ? (
              <Typography role="alert" color="error" sx={{ fontSize: 14 }}>
                {error}
              </Typography>
            ) : null}
          </Stack>
        )}
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

export default PublishDialog;
