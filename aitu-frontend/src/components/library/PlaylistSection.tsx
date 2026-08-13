/** Playlists on the Piano Library page (Epic 10, Story 10.3). */

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useNavigate } from "react-router-dom";
import {
  libraryApi,
  type LibraryTrack,
  type Playlist,
  type PlaylistItem,
  type Promotion,
} from "../../api";
import { ROUTES } from "../../layout/routes";
import { activePromotions, libraryPlayId } from "../../library/playId";
import { SectionCard } from "../../ui";

export function PlaylistSection({
  playlists,
  tracks,
  onChanged,
}: {
  playlists: Playlist[];
  tracks: LibraryTrack[];
  onChanged: () => void;
}) {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Playlist | null>(null);
  const [error, setError] = useState<string | null>(null);

  const play = (playlist: Playlist) => {
    const first = playlist.items[0];
    if (!first) return;
    const path = ROUTES.libraryPlay(libraryPlayId(first.artistSlug, first.trackSlug));
    const query = new URLSearchParams({
      promotion: first.promotionName,
      playlist: playlist.slug,
      index: "0",
    });
    navigate(`${path}?${query.toString()}`);
  };

  return (
    <SectionCard
      title="Playlists"
      description="Order pieces before you start. Next on the stand walks this list."
      actions={
        <Button size="small" variant="outlined" onClick={() => setCreating(true)}>
          New playlist
        </Button>
      }
    >
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {playlists.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No playlists yet. Make one, add two pieces, play through with Next.
        </Typography>
      ) : (
        <Stack spacing={2}>
          {playlists.map((playlist) => (
            <Box key={playlist.slug} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="subtitle1">{playlist.name}</Typography>
                  {playlist.description ? (
                    <Typography variant="body2" color="text.secondary">
                      {playlist.description}
                    </Typography>
                  ) : null}
                  <Typography variant="caption" color="text.secondary">
                    {playlist.items.length} piece{playlist.items.length === 1 ? "" : "s"}
                    {playlist.items[0] ? ` · starts with ${playlist.items[0].promotionName}` : ""}
                  </Typography>
                </Box>
                <Button size="small" onClick={() => setEditing(playlist)}>
                  Edit
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  disabled={playlist.items.length === 0}
                  onClick={() => play(playlist)}
                >
                  Play
                </Button>
                <Tooltip title="Delete playlist">
                  <IconButton
                    size="small"
                    aria-label={`Delete ${playlist.name}`}
                    onClick={() => {
                      void libraryApi
                        .deletePlaylist(playlist.slug)
                        .then(onChanged)
                        .catch((caught: unknown) =>
                          setError(caught instanceof Error ? caught.message : "Could not delete."),
                        );
                    }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Stack>
            </Box>
          ))}
        </Stack>
      )}

      {creating ? (
        <CreatePlaylistDialog
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            onChanged();
          }}
        />
      ) : null}
      {editing ? (
        <EditPlaylistDialog
          playlist={editing}
          tracks={tracks}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            onChanged();
          }}
        />
      ) : null}
    </SectionCard>
  );
}

function CreatePlaylistDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await libraryApi.createPlaylist({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      onCreated();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Could not create.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>New playlist</DialogTitle>
      <DialogContent>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} autoFocus />
          <TextField
            label="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={() => void save()} disabled={saving || !name.trim()}>
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function EditPlaylistDialog({
  playlist,
  tracks,
  onClose,
  onSaved,
}: {
  playlist: Playlist;
  tracks: LibraryTrack[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(playlist.name);
  const [description, setDescription] = useState(playlist.description ?? "");
  const [items, setItems] = useState<PlaylistItem[]>(playlist.items);
  const [addTrackKey, setAddTrackKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragFrom, setDragFrom] = useState<number | null>(null);

  const addChoices = tracks.flatMap((track) =>
    activePromotions(track.promotions).map((promotion) => ({
      key: `${track.artistSlug}/${track.trackSlug}/${promotion.promotionName}`,
      track,
      promotion,
    })),
  );
  const selectedAdd = addChoices.find((choice) => choice.key === addTrackKey);

  const move = (index: number, delta: number) => {
    const next = index + delta;
    if (next < 0 || next >= items.length) return;
    const copy = [...items];
    const [row] = copy.splice(index, 1);
    copy.splice(next, 0, row);
    setItems(copy);
  };

  const drop = (index: number) => {
    if (dragFrom === null || dragFrom === index) {
      setDragFrom(null);
      return;
    }
    const copy = [...items];
    const [row] = copy.splice(dragFrom, 1);
    copy.splice(index, 0, row);
    setItems(copy);
    setDragFrom(null);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await libraryApi.updatePlaylist(playlist.slug, {
        name: name.trim(),
        description: description.trim(),
        items,
      });
      onSaved();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Edit playlist</DialogTitle>
      <DialogContent>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} />
          <TextField
            label="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <Stack spacing={1}>
            {items.map((item, index) => (
              <Stack
                key={`${item.artistSlug}/${item.trackSlug}/${item.promotionName}/${index}`}
                direction="row"
                spacing={0.5}
                draggable
                onDragStart={() => setDragFrom(index)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => drop(index)}
                sx={{
                  alignItems: "center",
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  px: 1,
                  py: 0.5,
                  cursor: "grab",
                }}
              >
                <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }}>
                  {item.promotionName}
                </Typography>
                <IconButton size="small" aria-label="Move up" onClick={() => move(index, -1)} disabled={index === 0}>
                  <KeyboardArrowUpIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  aria-label="Move down"
                  onClick={() => move(index, 1)}
                  disabled={index === items.length - 1}
                >
                  <KeyboardArrowDownIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  aria-label="Remove"
                  onClick={() => setItems(items.filter((_, i) => i !== index))}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField
              select
              size="small"
              label="Add a piece"
              value={addTrackKey}
              onChange={(event) => {
                setAddTrackKey(event.target.value);
              }}
              sx={{ flex: 1, minWidth: 180 }}
            >
              {addChoices.map((choice) => (
                <MenuItem key={choice.key} value={choice.key}>
                  {choice.promotion.promotionName}
                </MenuItem>
              ))}
            </TextField>
            <Button
              size="small"
              disabled={!selectedAdd}
              onClick={() => {
                if (!selectedAdd) return;
                setItems([
                  ...items,
                  {
                    artistSlug: selectedAdd.track.artistSlug,
                    trackSlug: selectedAdd.track.trackSlug,
                    promotionName: selectedAdd.promotion.promotionName,
                  },
                ]);
              }}
            >
              Add
            </Button>
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={() => void save()} disabled={saving || !name.trim()}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function AddToPlaylistDialog({
  track,
  playlists,
  onClose,
  onSaved,
}: {
  track: LibraryTrack;
  playlists: Playlist[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const live = activePromotions(track.promotions);
  const [playlistSlug, setPlaylistSlug] = useState(playlists[0]?.slug ?? "");
  const [newName, setNewName] = useState("");
  const [promotionName, setPromotionName] = useState(live[0]?.promotionName ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    const item: PlaylistItem = {
      artistSlug: track.artistSlug,
      trackSlug: track.trackSlug,
      promotionName,
    };
    setSaving(true);
    setError(null);
    try {
      if (newName.trim()) {
        await libraryApi.createPlaylist({ name: newName.trim(), items: [item] });
      } else {
        const current = playlists.find((entry) => entry.slug === playlistSlug);
        if (!current) throw new Error("Pick a playlist.");
        await libraryApi.updatePlaylist(current.slug, { items: [...current.items, item] });
      }
      onSaved();
      onClose();
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Could not add.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Add to a playlist</DialogTitle>
      <DialogContent>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          {live.length > 1 ? (
            <TextField
              select
              label="Promotion"
              value={promotionName}
              onChange={(event) => setPromotionName(event.target.value)}
            >
              {live.map((promotion: Promotion) => (
                <MenuItem key={promotion.promotionName} value={promotion.promotionName}>
                  {promotion.promotionName}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          {playlists.length > 0 ? (
            <TextField
              select
              label="Existing playlist"
              value={playlistSlug}
              onChange={(event) => setPlaylistSlug(event.target.value)}
              disabled={Boolean(newName.trim())}
            >
              {playlists.map((entry) => (
                <MenuItem key={entry.slug} value={entry.slug}>
                  {entry.name}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          <TextField
            label="Or create a new one"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="Sunday practice"
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => void save()}
          disabled={saving || !promotionName || (!playlistSlug && !newName.trim())}
        >
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default PlaylistSection;
