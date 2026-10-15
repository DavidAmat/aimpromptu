/**
 * One songs playlist of My library (`/library/playlists/:id`, implementation 02, plan section 14.2,
 * Phase 10): its songs in the order they play, each with the version chosen and the stretch, if
 * any. Nothing of a song can be changed here, only chosen: a row opens its version (read only), its
 * `⋯` chooses another version, takes the stretch away, moves it or removes it; a row is dragged to
 * another place. **Add a song** puts one of the library's songs at the end.
 *
 * **Play** opens Play mode on the first song, and a click on a row on that song (Phase 11). Closing
 * Play mode comes back here with the song it was on shaded (`?at=`), to choose another or reorder.
 */

import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutlineOutlined";
import LaunchIcon from "@mui/icons-material/Launch";
import PlayIcon from "@mui/icons-material/PlayCircleOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { libraryApi, playlistsApi, type PlaylistDetail, type PlaylistItem, type SongRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  ConfirmDialog,
  EmptyState,
  ListRow,
  movedOrder,
  PageBody,
  PageHeader,
  PillButton,
  RowMenu,
  ui,
  useRowDrag,
  type RowMenuItem,
} from "../../ui";
import { TextDialog } from "./TextDialog";
import { said, stretchLabel } from "./shared";

export function PlaylistPage() {
  const { id } = useParams();
  const playlistId = Number(id);
  const navigate = useNavigate();
  /** The song Play mode was on when it was closed. */
  const [search] = useSearchParams();
  const playedAt = search.has("at") ? Number(search.get("at")) : null;
  const [playlist, setPlaylist] = useState<PlaylistDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    playlistsApi
      .get(playlistId, controller.signal)
      .then(setPlaylist)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlist could not be loaded."));
      });
    return () => controller.abort();
  }, [playlistId]);

  const run = async (action: () => Promise<PlaylistDetail>, fallback: string) => {
    setBusy(true);
    setActionError(null);
    try {
      setPlaylist(await action());
      return true;
    } catch (caught) {
      setActionError(said(caught, fallback));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const items = playlist?.items ?? [];
  const move = (from: number, to: number) => {
    if (!playlist || to < 0 || to >= items.length || from === to) return;
    const order = movedOrder(items.length, from, to).map((index) => items[index]);
    setPlaylist({ ...playlist, items: order });
    void run(() => playlistsApi.reorder(playlistId, order.map((item) => item.id)), "The songs could not be moved.");
  };
  const drag = useRowDrag(items.length, move, busy);

  const remove = async () => {
    setBusy(true);
    try {
      await playlistsApi.remove(playlistId);
      navigate(ROUTES.libraryPlaylists, { replace: true });
    } catch (caught) {
      setActionError(said(caught, "The playlist could not be deleted."));
      setDeleting(false);
      setBusy(false);
    }
  };

  const menuOf = (item: PlaylistItem, index: number): RowMenuItem[] => [
    {
      label: "Play from here",
      icon: <PlayIcon fontSize="small" />,
      onClick: () => navigate(ROUTES.playPlaylist(playlistId, index)),
      disabled: item.parts.length === 0,
    },
    {
      label: "Open",
      icon: <LaunchIcon fontSize="small" />,
      onClick: () => item.parts[0] && navigate(ROUTES.project(item.parts[0], "sheet")),
      disabled: item.parts.length === 0,
    },
    ...item.versions
      .filter((version) => version.projectId !== item.projectId)
      .map((version) => ({
        label: `Use “${version.name}”`,
        icon: <SwapHorizIcon fontSize="small" />,
        onClick: () =>
          void run(
            () => playlistsApi.changeItem(playlistId, item.id, { projectId: version.projectId }),
            "The version could not be changed.",
          ),
      })),
    ...(item.fromMs !== null
      ? [
          {
            label: "The whole song",
            icon: <UnfoldMoreIcon fontSize="small" />,
            onClick: () =>
              void run(() => playlistsApi.changeItem(playlistId, item.id, { whole: true }), "The song could not be changed."),
          },
        ]
      : []),
    { label: "Move up", icon: <ArrowUpwardIcon fontSize="small" />, onClick: () => move(index, index - 1), disabled: index === 0 },
    {
      label: "Move down",
      icon: <ArrowDownwardIcon fontSize="small" />,
      onClick: () => move(index, index + 1),
      disabled: index === items.length - 1,
    },
    {
      label: "Remove from the playlist",
      icon: <DeleteIcon fontSize="small" />,
      danger: true,
      onClick: () => void run(() => playlistsApi.removeItem(playlistId, item.id), "The song could not be removed."),
    },
  ];

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Playlist" back={{ to: ROUTES.libraryPlaylists, label: "Back to Playlists" }} />
        <EmptyState message={error} />
      </PageBody>
    );
  }

  const addSongButton = (kind: "primary" | "secondary") => (
    <PillButton kind={kind} startIcon={<AddIcon />} onClick={() => setAdding(true)} data-testid="playlist-add-song">
      Add a song
    </PillButton>
  );

  return (
    <PageBody>
      <PageHeader
        title={playlist?.title ?? ""}
        back={{ to: ROUTES.libraryPlaylists, label: "Back to Playlists" }}
        actions={
          playlist ? (
            <>
              {items.length > 0 ? addSongButton("secondary") : null}
              {items.length > 0 ? (
                <PillButton
                  kind="primary"
                  startIcon={<PlayIcon />}
                  onClick={() => navigate(ROUTES.playPlaylist(playlistId))}
                  data-testid="playlist-play"
                >
                  Play
                </PillButton>
              ) : null}
              <RowMenu
                title="Playlist actions"
                items={[
                  { label: "Rename", icon: <DriveFileRenameIcon fontSize="small" />, onClick: () => setRenaming(true) },
                  { label: "Delete playlist", icon: <DeleteIcon fontSize="small" />, danger: true, onClick: () => setDeleting(true) },
                ]}
              />
            </>
          ) : undefined
        }
      />
      {actionError ? (
        <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      ) : null}
      {playlist === null ? (
        <Stack spacing={1} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : items.length === 0 ? (
        <EmptyState message="No songs yet." action={addSongButton("primary")} />
      ) : (
        <Box role="list" aria-label="The songs, in the order they play" aria-busy={busy} data-playlist-items>
          {items.map((item, index) => {
            const handlers = drag(index);
            return (
              <Box
                role="listitem"
                key={item.id}
                {...handlers.row}
                data-playlist-item={index}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  opacity: handlers.dragging ? 0.4 : 1,
                  borderRadius: "12px",
                  boxShadow: handlers.dropMark
                    ? `inset 0 ${handlers.dropMark === "below" ? -2 : 2}px 0 ${ui.text}`
                    : "none",
                }}
              >
                <Box
                  {...handlers.handle}
                  title={handlers.handle.draggable ? "Drag to put it in another place" : undefined}
                  aria-hidden
                  sx={{
                    display: "flex",
                    color: handlers.handle.draggable ? "text.secondary" : "text.disabled",
                    cursor: handlers.handle.draggable ? "grab" : "default",
                  }}
                >
                  <DragIndicatorIcon fontSize="small" />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <ListRow
                    title={item.artists.length ? `${item.songTitle}, ${item.artists.join(", ")}` : item.songTitle}
                    leading={
                      <Box component="span" sx={{ width: 20, textAlign: "right", color: "text.secondary", fontVariantNumeric: "tabular-nums" }}>
                        {index + 1}
                      </Box>
                    }
                    status={item.versionName ?? "–"}
                    meta={item.fromMs !== null && item.toMs !== null ? stretchLabel(item.fromMs, item.toMs) : "Whole"}
                    onOpen={() => item.parts[0] && navigate(ROUTES.playPlaylist(playlistId, index))}
                    selected={playedAt === index}
                    menu={menuOf(item, index)}
                  />
                </Box>
              </Box>
            );
          })}
        </Box>
      )}

      {renaming && playlist ? (
        <TextDialog
          title="Rename the playlist"
          label="Title"
          initial={playlist.title}
          confirmLabel="Rename"
          busy={busy}
          error={actionError}
          onCancel={() => setRenaming(false)}
          onConfirm={(title) =>
            void run(() => playlistsApi.rename(playlistId, title), "The playlist could not be renamed.").then((done) => {
              if (done) setRenaming(false);
            })
          }
        />
      ) : null}
      <ConfirmDialog
        open={deleting}
        title={`Delete “${playlist?.title ?? ""}”?`}
        message="Its songs stay in your library."
        confirmLabel="Delete playlist"
        danger
        busy={busy}
        onCancel={() => setDeleting(false)}
        onConfirm={() => void remove()}
      />
      {adding ? (
        <ChooseSongDialog
          onCancel={() => setAdding(false)}
          onChoose={(song) =>
            void run(() => playlistsApi.addItems(playlistId, [{ songId: song.id }]), "The song could not be added.").then(
              (done) => {
                if (done) setAdding(false);
              },
            )
          }
          busy={busy}
        />
      ) : null}
    </PageBody>
  );
}

/** One song of the library, found by its title or its artists. */
function ChooseSongDialog({
  busy,
  onCancel,
  onChoose,
}: {
  busy: boolean;
  onCancel: () => void;
  onChoose: (song: SongRow) => void;
}) {
  const [songs, setSongs] = useState<SongRow[] | null>(null);
  const [filter, setFilter] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .songs(controller.signal)
      .then(setSongs)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  const wanted = filter.trim().toLocaleLowerCase();
  const shown = useMemo(
    () =>
      (songs ?? []).filter(
        (song) =>
          !wanted ||
          `${song.title} ${song.artists.map((artist) => artist.name).join(" ")}`.toLocaleLowerCase().includes(wanted),
      ),
    [songs, wanted],
  );
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>Add a song</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5} sx={{ pt: 1 }}>
          <TextField size="small" label="Filter" value={filter} onChange={(event) => setFilter(event.target.value)} autoFocus />
          {songs === null ? (
            <Skeleton variant="rounded" height={120} />
          ) : (
            <List dense disablePadding sx={{ maxHeight: 320, overflow: "auto" }} aria-label="Songs of your library">
              {shown.map((song) => (
                <ListItemButton key={song.id} disabled={busy} onClick={() => onChoose(song)} sx={{ borderRadius: 2 }}>
                  <ListItemText
                    primary={song.title}
                    secondary={song.artists.map((artist) => artist.name).join(", ") || undefined}
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default PlaylistPage;
