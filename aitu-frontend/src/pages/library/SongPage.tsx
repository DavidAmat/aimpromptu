/**
 * **One song** (`/library/songs/:id`) of the user's Private Library: its title, its artists and its
 * versions (implementation 02, Phase 6, plan sections 10.6 and 15.2).
 *
 * Each version is a project. A row opens it, read only. Its `⋯` menu:
 *
 * - **Edit** makes a copy in Projects that points at the version (no audio copied) and opens it; the
 *   version itself does not change until the copy is saved over it. While a copy is open the row
 *   says **Editing**, and the menu says **Continue editing**.
 * - **Duplicate** adds an independent copy to Projects; **Export** saves its `.aitu` file.
 * - **History** lists the earlier states the version kept when it was replaced, each with
 *   **Restore** (the state it replaces is kept too, so nothing is lost).
 * - **Rename** and **Delete**.
 *
 * The header's `⋯` renames the song, changes its artists, or deletes it with every version.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ContentCopyIcon from "@mui/icons-material/ContentCopyOutlined";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import EditIcon from "@mui/icons-material/EditOutlined";
import HistoryIcon from "@mui/icons-material/HistoryOutlined";
import LaunchIcon from "@mui/icons-material/Launch";
import PersonIcon from "@mui/icons-material/PersonOutlined";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import {
  libraryApi,
  projectsApi,
  type ArtistRow,
  type EarlierState,
  type SongDetail,
  type VersionRow,
} from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  ConfirmDialog,
  EmptyState,
  fullTime,
  ListRow,
  PageBody,
  PageHeader,
  PillButton,
  relativeTime,
  RowMenu,
  Section,
} from "../../ui";
import { download, said } from "./shared";
import { TextDialog } from "./TextDialog";

type Renaming = { kind: "song" } | { kind: "version"; version: VersionRow };
type Deleting = { kind: "song" } | { kind: "version"; version: VersionRow };

export function SongPage() {
  const { id } = useParams();
  const songId = Number(id);
  const navigate = useNavigate();
  const [song, setSong] = useState<SongDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<Renaming | null>(null);
  const [deleting, setDeleting] = useState<Deleting | null>(null);
  const [history, setHistory] = useState<VersionRow | null>(null);
  const [artists, setArtists] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .song(songId, controller.signal)
      .then((found) => {
        setSong(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The song could not be loaded."));
      });
    return () => controller.abort();
  }, [songId, reload]);

  /** Run one change; on success take the song it answers (or load it again). */
  const run = useCallback(
    async (change: () => Promise<SongDetail | void>, after?: () => void) => {
      setBusy(true);
      setActionError(null);
      try {
        const answer = await change();
        if (answer) setSong(answer);
        else setReload((count) => count + 1);
        after?.();
        return true;
      } catch (caught) {
        setActionError(said(caught, "That did not work."));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const edit = useCallback(
    async (version: VersionRow) => {
      setActionError(null);
      try {
        const copy = await projectsApi.edit(version.projectId);
        navigate(ROUTES.project(copy.parts[0] ?? copy.id));
      } catch (caught) {
        setActionError(said(caught, "The version could not be opened for editing."));
      }
    },
    [navigate],
  );

  const duplicate = useCallback(
    async (version: VersionRow) => {
      setActionError(null);
      setNotice(null);
      try {
        const title = song ? `${song.title} (${version.name})` : undefined;
        const copy = await projectsApi.duplicate(version.projectId, title);
        setNotice(`“${copy.title}” added to Projects`);
      } catch (caught) {
        setActionError(said(caught, "The version could not be duplicated."));
      }
    },
    [song],
  );

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Song" back={{ to: ROUTES.librarySongs, label: "Back to Songs" }} />
        <EmptyState
          message={error}
          action={<PillButton onClick={() => navigate(ROUTES.librarySongs)}>Open Songs</PillButton>}
        />
      </PageBody>
    );
  }

  return (
    <PageBody>
      <PageHeader
        title={song?.title ?? ""}
        back={{ to: ROUTES.librarySongs, label: "Back to Songs" }}
        actions={
          song ? (
            <RowMenu
              title="Song actions"
              items={[
                {
                  label: "Rename song",
                  icon: <DriveFileRenameIcon fontSize="small" />,
                  onClick: () => setRenaming({ kind: "song" }),
                },
                { label: "Artists", icon: <PersonIcon fontSize="small" />, onClick: () => setArtists(true) },
                {
                  label: "Delete song",
                  icon: <DeleteIcon fontSize="small" />,
                  onClick: () => setDeleting({ kind: "song" }),
                  danger: true,
                },
              ]}
            />
          ) : undefined
        }
      />

      {song === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          <Skeleton variant="text" width={180} />
          {Array.from({ length: 3 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : (
        <>
          <Typography sx={{ color: "text.secondary", fontSize: 14, mb: 2, px: { xs: 0, sm: 0.5 } }}>
            {song.artists.length === 0
              ? "No artist"
              : song.artists.map((artist, index) => (
                  <Box component="span" key={artist.nameId}>
                    {index > 0 ? ", " : null}
                    <Link component={RouterLink} to={ROUTES.libraryArtist(artist.artistId)} color="inherit">
                      {artist.name}
                    </Link>
                  </Box>
                ))}
          </Typography>

          {actionError && !renaming && !deleting && !history && !artists ? (
            <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
              {actionError}
            </Alert>
          ) : null}
          {notice ? (
            <Alert
              severity="success"
              onClose={() => setNotice(null)}
              sx={{ mb: 2 }}
              role="status"
              action={
                <PillButton kind="quiet" size="small" onClick={() => navigate(ROUTES.projects)}>
                  Open Projects
                </PillButton>
              }
            >
              {notice}
            </Alert>
          ) : null}

          <Section title="Versions">
            {song.versions.length === 0 ? (
              <Typography color="text.secondary" sx={{ px: 1.5, py: 1.25 }}>
                No versions
              </Typography>
            ) : (
              <Box role="list" aria-label="Versions">
                {song.versions.map((version) => {
                  const changed = version.updatedAt ?? version.createdAt;
                  const first = version.parts[0] ?? version.projectId;
                  return (
                    <Box role="listitem" key={version.id}>
                      <ListRow
                        data-testid={`version-${version.id}`}
                        title={version.name}
                        onOpen={() => navigate(ROUTES.project(first))}
                        status={version.editCopy ? "Editing" : undefined}
                        meta={
                          <Tooltip title={fullTime(changed)} placement="left">
                            <span>{relativeTime(changed)}</span>
                          </Tooltip>
                        }
                        menu={[
                          { label: "Open", icon: <LaunchIcon fontSize="small" />, onClick: () => navigate(ROUTES.project(first)) },
                          {
                            label: version.editCopy ? "Continue editing" : "Edit",
                            icon: <EditIcon fontSize="small" />,
                            onClick: () => void edit(version),
                          },
                          {
                            label: "Duplicate",
                            icon: <ContentCopyIcon fontSize="small" />,
                            onClick: () => void duplicate(version),
                          },
                          {
                            label: "Export",
                            icon: <DownloadIcon fontSize="small" />,
                            onClick: () => download(projectsApi.exportUrl(version.projectId)),
                          },
                          {
                            label: "Rename",
                            icon: <DriveFileRenameIcon fontSize="small" />,
                            onClick: () => setRenaming({ kind: "version", version }),
                          },
                          {
                            label: "History",
                            icon: <HistoryIcon fontSize="small" />,
                            onClick: () => setHistory(version),
                            disabled: version.history === 0,
                          },
                          {
                            label: "Delete",
                            icon: <DeleteIcon fontSize="small" />,
                            onClick: () => setDeleting({ kind: "version", version }),
                            danger: true,
                          },
                        ]}
                      />
                    </Box>
                  );
                })}
              </Box>
            )}
          </Section>
        </>
      )}

      {renaming && song ? (
        <TextDialog
          title={renaming.kind === "song" ? "Rename song" : "Rename version"}
          label={renaming.kind === "song" ? "Title" : "Version name"}
          initial={renaming.kind === "song" ? song.title : renaming.version.name}
          confirmLabel="Rename"
          busy={busy}
          error={actionError}
          onCancel={() => {
            setRenaming(null);
            setActionError(null);
          }}
          onConfirm={(value) =>
            void run(
              () =>
                renaming.kind === "song"
                  ? libraryApi.changeSong(song.id, { title: value })
                  : libraryApi.renameVersion(renaming.version.id, value),
              () => setRenaming(null),
            )
          }
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={
          deleting?.kind === "version"
            ? `Delete the version “${deleting.version.name}”?`
            : `Delete “${song?.title ?? ""}”?`
        }
        message={
          <>
            {deleting?.kind === "version"
              ? "Its notes, piano sheet, audio and history are deleted. This cannot be undone."
              : `The song and its ${song?.versions.length ?? 0} versions are deleted, with their notes, piano sheets and audio. This cannot be undone.`}
            {actionError ? (
              <Typography color="error" sx={{ mt: 1 }}>
                {actionError}
              </Typography>
            ) : null}
          </>
        }
        confirmLabel={deleting?.kind === "version" ? "Delete version" : "Delete song"}
        danger
        busy={busy}
        onCancel={() => {
          setDeleting(null);
          setActionError(null);
        }}
        onConfirm={() => {
          if (!deleting || !song) return;
          if (deleting.kind === "version") {
            void run(() => libraryApi.deleteVersion(deleting.version.id), () => setDeleting(null));
          } else {
            void run(
              () => libraryApi.deleteSong(song.id),
              () => navigate(ROUTES.librarySongs, { replace: true }),
            );
          }
        }}
      />

      {history && song ? (
        <HistoryDialog
          version={history}
          onClose={() => setHistory(null)}
          onRestored={(answer) => {
            setSong(answer);
            setHistory(null);
            setNotice(`“${history.name}” restored`);
          }}
        />
      ) : null}

      {artists && song ? (
        <ArtistsDialog
          song={song}
          onClose={() => setArtists(false)}
          onSaved={(answer) => {
            setSong(answer);
            setArtists(false);
          }}
        />
      ) : null}
    </PageBody>
  );
}

/** The earlier states of a version, each with **Restore**. */
function HistoryDialog({
  version,
  onClose,
  onRestored,
}: {
  version: VersionRow;
  onClose: () => void;
  onRestored: (song: SongDetail) => void;
}) {
  const [states, setStates] = useState<EarlierState[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<EarlierState | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .history(version.id, controller.signal)
      .then(setStates)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The history could not be loaded."));
      });
    return () => controller.abort();
  }, [version.id]);

  const restore = async (state: EarlierState) => {
    setBusy(true);
    setError(null);
    try {
      onRestored(await libraryApi.restore(version.id, state.number));
    } catch (caught) {
      setError(said(caught, "The version could not be restored."));
      setRestoring(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>History of “{version.name}”</DialogTitle>
      <DialogContent>
        {error ? (
          <Typography color="error" sx={{ mb: 1 }}>
            {error}
          </Typography>
        ) : null}
        {states === null && !error ? (
          <Stack spacing={1} aria-busy>
            <Skeleton variant="rounded" height={40} />
            <Skeleton variant="rounded" height={40} />
          </Stack>
        ) : (
          <Stack spacing={0.5} role="list" aria-label="Earlier states">
            {states?.map((state) => (
              <Stack
                key={state.number}
                role="listitem"
                direction="row"
                spacing={2}
                sx={{ alignItems: "center", justifyContent: "space-between", py: 0.75 }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: 14 }}>{fullTime(state.savedAt)}</Typography>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{state.reason}</Typography>
                </Box>
                <PillButton kind="secondary" size="small" disabled={busy} onClick={() => setRestoring(state)}>
                  Restore
                </PillButton>
              </Stack>
            ))}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Close
        </PillButton>
      </DialogActions>
      <ConfirmDialog
        open={restoring !== null}
        title={`Restore the state of ${restoring ? fullTime(restoring.savedAt) : ""}?`}
        message="The version as it is now is kept in its history."
        confirmLabel="Restore"
        busy={busy}
        onCancel={() => setRestoring(null)}
        onConfirm={() => restoring && void restore(restoring)}
      />
    </Dialog>
  );
}

/** The artists of a song, by name: pick known names or type new ones. */
function ArtistsDialog({
  song,
  onClose,
  onSaved,
}: {
  song: SongDetail;
  onClose: () => void;
  onSaved: (song: SongDetail) => void;
}) {
  const [known, setKnown] = useState<ArtistRow[]>([]);
  const [names, setNames] = useState<string[]>(song.artists.map((artist) => artist.name));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .artists(controller.signal)
      .then(setKnown)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const options = Array.from(new Set(known.flatMap((artist) => artist.names.map((one) => one.name))));
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      onSaved(await libraryApi.changeSong(song.id, { artists: names }));
    } catch (caught) {
      setError(said(caught, "The artists could not be saved."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Artists of “{song.title}”</DialogTitle>
      <DialogContent>
        <Autocomplete
          multiple
          freeSolo
          options={options}
          value={names}
          onChange={(_, value) => setNames(value.map((one) => one.trim()).filter(Boolean))}
          renderInput={(params) => (
            <TextField
              {...params}
              autoFocus
              label="Artists"
              error={error !== null}
              helperText={error ?? "Enter adds a name"}
              sx={{ mt: 1 }}
            />
          )}
        />
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onClose} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => void save()} busy={busy}>
          Save artists
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default SongPage;
