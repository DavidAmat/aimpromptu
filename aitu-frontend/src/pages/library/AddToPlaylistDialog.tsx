/**
 * **Add to a playlist** (implementation 02, plan section 14.2, Phase 10): a version of a song, or a
 * stretch of it, put at the end of one of the user's songs playlists, or of a new one.
 *
 * Opened from a version's `⋯` on its song page (the whole song) and from a stretch marked on a
 * version's read-only sheet.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
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
import { useNavigate } from "react-router-dom";
import { playlistsApi, projectsApi, type PlaylistRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { PillButton } from "../../ui";
import { said, stretchLabel } from "./shared";

export interface AddToPlaylistDialogProps {
  /** The version: its library project. */
  projectId: string;
  /** Its song, when the caller knows it; read from the project otherwise. */
  songId?: number;
  stretch?: { fromMs: number; toMs: number } | null;
  onClose: () => void;
}

export function AddToPlaylistDialog({ projectId, songId, stretch, onClose }: AddToPlaylistDialogProps) {
  const navigate = useNavigate();
  const [playlists, setPlaylists] = useState<PlaylistRow[] | null>(null);
  const [song, setSong] = useState<number | null>(songId ?? null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<{ id: number; title: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    playlistsApi
      .list(controller.signal)
      .then(setPlaylists)
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlists could not be loaded."));
      });
    if (songId === undefined) {
      projectsApi
        .get(projectId, controller.signal)
        .then((row) => setSong(row.library?.songId ?? null))
        .catch(() => undefined);
    }
    return () => controller.abort();
  }, [projectId, songId]);

  const item = song === null ? null : { songId: song, projectId, ...(stretch ?? {}) };

  const addTo = async (target: PlaylistRow | null) => {
    if (!item) return;
    setBusy(true);
    setError(null);
    try {
      const done = target
        ? await playlistsApi.addItems(target.id, [item])
        : await playlistsApi.create(title.trim(), [item]);
      setAdded({ id: done.id, title: done.title });
    } catch (caught) {
      setError(said(caught, "The song could not be added."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{stretch ? `Add ${stretchLabel(stretch.fromMs, stretch.toMs)} to a playlist` : "Add to a playlist"}</DialogTitle>
      <DialogContent>
        {added ? (
          <Alert severity="success">Added to “{added.title}”.</Alert>
        ) : (
          <Stack spacing={2}>
            {playlists === null ? (
              <Skeleton variant="rounded" height={88} />
            ) : playlists.length > 0 ? (
              <List dense disablePadding aria-label="Your playlists" sx={{ maxHeight: 280, overflow: "auto" }}>
                {playlists.map((playlist) => (
                  <ListItemButton
                    key={playlist.id}
                    disabled={busy || item === null}
                    onClick={() => void addTo(playlist)}
                    sx={{ borderRadius: 2 }}
                  >
                    <ListItemText
                      primary={playlist.title}
                      secondary={`${playlist.songs} song${playlist.songs === 1 ? "" : "s"}`}
                    />
                  </ListItemButton>
                ))}
              </List>
            ) : null}
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <TextField
                size="small"
                label="New playlist"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && title.trim()) void addTo(null);
                }}
                sx={{ flex: 1 }}
              />
              <PillButton
                kind="secondary"
                disabled={!title.trim() || item === null}
                busy={busy}
                onClick={() => void addTo(null)}
              >
                Create
              </PillButton>
            </Stack>
            {error ? <Alert severity="error">{error}</Alert> : null}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        {added ? (
          <PillButton kind="quiet" onClick={() => navigate(ROUTES.libraryPlaylist(added.id))}>
            Open the playlist
          </PillButton>
        ) : null}
        <PillButton kind={added ? "primary" : "quiet"} onClick={onClose} disabled={busy}>
          {added ? "Done" : "Cancel"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default AddToPlaylistDialog;
