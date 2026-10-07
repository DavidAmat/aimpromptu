/**
 * **One artist** (`/library/artists/:id`): its names and its songs (implementation 02, Phase 6,
 * plan section 15.1; the app context: "The Jackson 5" and "Jackson Five" are two names of one
 * artist).
 *
 * The default name is the artist's title everywhere. Each name's `⋯` makes it the default, renames
 * it, or removes it (a song saved with a removed name shows the default name). **Add a name** is
 * beside the names. The header's `⋯` merges this artist into another one (every name moves there)
 * or deletes an artist with no songs.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import CallMergeIcon from "@mui/icons-material/CallMergeOutlined";
import CheckIcon from "@mui/icons-material/Check";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import { useNavigate, useParams } from "react-router-dom";
import { libraryApi, type ArtistDetail, type ArtistNameRow, type ArtistRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { ConfirmDialog, EmptyState, ListRow, PageBody, PageHeader, PillButton, RowMenu, Section } from "../../ui";
import { said } from "./shared";
import { TextDialog } from "./TextDialog";

type Naming = { kind: "add" } | { kind: "rename"; name: ArtistNameRow };

export function ArtistPage() {
  const { id } = useParams();
  const artistId = Number(id);
  const navigate = useNavigate();
  const [artist, setArtist] = useState<ArtistDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [naming, setNaming] = useState<Naming | null>(null);
  const [removing, setRemoving] = useState<ArtistNameRow | null>(null);
  const [merging, setMerging] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .artist(artistId, controller.signal)
      .then((found) => {
        setArtist(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The artist could not be loaded."));
      });
    return () => controller.abort();
  }, [artistId]);

  const run = useCallback(async (change: () => Promise<ArtistDetail>, after?: () => void) => {
    setBusy(true);
    setActionError(null);
    try {
      setArtist(await change());
      after?.();
    } catch (caught) {
      setActionError(said(caught, "That did not work."));
    } finally {
      setBusy(false);
    }
  }, []);

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Artist" back={{ to: ROUTES.libraryArtists, label: "Back to Artists" }} />
        <EmptyState
          message={error}
          action={<PillButton onClick={() => navigate(ROUTES.libraryArtists)}>Open Artists</PillButton>}
        />
      </PageBody>
    );
  }

  const dialogOpen = naming !== null || removing !== null || merging || deleting;

  return (
    <PageBody>
      <PageHeader
        title={artist?.name ?? ""}
        back={{ to: ROUTES.libraryArtists, label: "Back to Artists" }}
        actions={
          artist ? (
            <RowMenu
              title="Artist actions"
              items={[
                {
                  label: "Merge into another artist",
                  icon: <CallMergeIcon fontSize="small" />,
                  onClick: () => setMerging(true),
                },
                {
                  label: "Delete artist",
                  icon: <DeleteIcon fontSize="small" />,
                  onClick: () => setDeleting(true),
                  disabled: artist.songs > 0,
                  danger: true,
                },
              ]}
            />
          ) : undefined
        }
      />

      {actionError && !dialogOpen ? (
        <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      ) : null}

      {artist === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : (
        <>
          <Section
            title="Names"
            actions={
              <PillButton kind="quiet" size="small" startIcon={<AddIcon />} onClick={() => setNaming({ kind: "add" })}>
                Add a name
              </PillButton>
            }
          >
            <Box role="list" aria-label="Names">
              {artist.names.map((name) => (
                <Box role="listitem" key={name.id}>
                  <ListRow
                    title={name.name}
                    status={name.isDefault ? "Default" : undefined}
                    menu={[
                      {
                        label: "Make default",
                        icon: <CheckIcon fontSize="small" />,
                        onClick: () =>
                          void run(() => libraryApi.changeName(artist.id, name.id, { isDefault: true })),
                        disabled: name.isDefault,
                      },
                      {
                        label: "Rename",
                        icon: <DriveFileRenameIcon fontSize="small" />,
                        onClick: () => setNaming({ kind: "rename", name }),
                      },
                      {
                        label: "Remove",
                        icon: <DeleteIcon fontSize="small" />,
                        onClick: () => setRemoving(name),
                        disabled: name.isDefault,
                        danger: true,
                      },
                    ]}
                  />
                </Box>
              ))}
            </Box>
          </Section>

          <Section title="Songs">
            {artist.songList.length === 0 ? (
              <Typography color="text.secondary" sx={{ px: 1.5, py: 1.25 }}>
                No songs
              </Typography>
            ) : (
              <Box role="list" aria-label="Songs">
                {artist.songList.map((song) => (
                  <Box role="listitem" key={song.id}>
                    <ListRow
                      title={song.title}
                      meta={song.versions === 1 ? "1 version" : `${song.versions} versions`}
                      onOpen={() => navigate(ROUTES.librarySong(song.id))}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </Section>
        </>
      )}

      {naming && artist ? (
        <TextDialog
          title={naming.kind === "add" ? `Another name of ${artist.name}` : "Rename"}
          label="Name"
          initial={naming.kind === "rename" ? naming.name.name : ""}
          confirmLabel={naming.kind === "add" ? "Add name" : "Rename"}
          busy={busy}
          error={actionError}
          onCancel={() => {
            setNaming(null);
            setActionError(null);
          }}
          onConfirm={(value) =>
            void run(
              () =>
                naming.kind === "add"
                  ? libraryApi.addName(artist.id, value)
                  : libraryApi.changeName(artist.id, naming.name.id, { name: value }),
              () => setNaming(null),
            )
          }
        />
      ) : null}

      <ConfirmDialog
        open={removing !== null}
        title={`Remove the name “${removing?.name ?? ""}”?`}
        message={
          <>
            Songs saved with it show “{artist?.name}” instead.
            {actionError ? (
              <Typography color="error" sx={{ mt: 1 }}>
                {actionError}
              </Typography>
            ) : null}
          </>
        }
        confirmLabel="Remove name"
        danger
        busy={busy}
        onCancel={() => {
          setRemoving(null);
          setActionError(null);
        }}
        onConfirm={() =>
          artist && removing && void run(() => libraryApi.removeName(artist.id, removing.id), () => setRemoving(null))
        }
      />

      <ConfirmDialog
        open={deleting}
        title={`Delete ${artist?.name ?? ""}?`}
        message={actionError ?? undefined}
        confirmLabel="Delete artist"
        danger
        busy={busy}
        onCancel={() => {
          setDeleting(false);
          setActionError(null);
        }}
        onConfirm={() => {
          if (!artist) return;
          setBusy(true);
          libraryApi
            .deleteArtist(artist.id)
            .then(() => navigate(ROUTES.libraryArtists, { replace: true }))
            .catch((caught: unknown) => setActionError(said(caught, "The artist could not be deleted.")))
            .finally(() => setBusy(false));
        }}
      />

      {merging && artist ? (
        <MergeDialog
          artist={artist}
          onClose={() => setMerging(false)}
          onMerged={(into) => {
            setMerging(false);
            navigate(ROUTES.libraryArtist(into.id), { replace: true });
          }}
        />
      ) : null}
    </PageBody>
  );
}

/** Choose the artist this one merges into: every name of this artist becomes one of its names. */
function MergeDialog({
  artist,
  onClose,
  onMerged,
}: {
  artist: ArtistDetail;
  onClose: () => void;
  onMerged: (into: ArtistDetail) => void;
}) {
  const [others, setOthers] = useState<ArtistRow[]>([]);
  const [into, setInto] = useState<ArtistRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .artists(controller.signal)
      .then((list) => setOthers(list.filter((one) => one.id !== artist.id)))
      .catch(() => undefined);
    return () => controller.abort();
  }, [artist.id]);

  const merge = async () => {
    if (!into) return;
    setBusy(true);
    setError(null);
    try {
      onMerged(await libraryApi.merge(artist.id, into.id));
    } catch (caught) {
      setError(said(caught, "The artists could not be merged."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Merge {artist.name} into another artist</DialogTitle>
      <DialogContent>
        <Autocomplete
          options={others}
          value={into}
          onChange={(_, value) => setInto(value)}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(option, value) => option.id === value.id}
          renderInput={(params) => (
            <TextField
              {...params}
              autoFocus
              label="Artist"
              error={error !== null}
              helperText={
                error ??
                (into ? `${artist.name} becomes another name of ${into.name}, with its ${artist.songs} songs` : undefined)
              }
              sx={{ mt: 1 }}
            />
          )}
        />
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => void merge()} disabled={!into} busy={busy}>
          Merge
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ArtistPage;
