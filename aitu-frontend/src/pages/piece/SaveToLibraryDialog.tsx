/**
 * **Save to library** (implementation 02, Phase 6, plan sections 10.2 and 10.6): three things in one
 * dialog, **Artist**, **Song** and **Version name**, asked only now that the piano sheet is ready.
 *
 * Artist and Song offer what the user's library already has, and take a new name as it is typed
 * (a new name makes a new artist or a new song). Choosing a known song fills its artist. A copy
 * made by **Edit** opens on **Replace “<version>”** (the version gets this project's content and
 * keeps its earlier state in its history), with **New version** beside it.
 *
 * Suggestions from the Public Library join the two lists in Phase 13, when it exists.
 */

import { useEffect, useMemo, useState } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  libraryApi,
  projectsApi,
  type ArtistRow,
  type LibraryLink,
  type SavedToLibrary,
  type SongRow,
} from "../../api";
import { PillButton, Segmented } from "../../ui";
import { said } from "../library/shared";

export interface SaveToLibraryDialogProps {
  projectId: string;
  /** The project's title: the song's title at first. */
  title: string;
  /** The version this project edits, when it is a copy made by **Edit**. */
  editing: LibraryLink | null;
  onClose: () => void;
  onSaved: (saved: SavedToLibrary) => void;
}

type Mode = "replace" | "new";

const same = (a: string, b: string) => a.trim().toLocaleLowerCase() === b.trim().toLocaleLowerCase();

export function SaveToLibraryDialog({ projectId, title, editing, onClose, onSaved }: SaveToLibraryDialogProps) {
  const [mode, setMode] = useState<Mode>(editing ? "replace" : "new");
  const [songs, setSongs] = useState<SongRow[]>([]);
  const [artists, setArtists] = useState<ArtistRow[]>([]);
  const [artist, setArtist] = useState(editing?.artists[0] ?? "");
  const [song, setSong] = useState(editing?.songTitle ?? title);
  const [songId, setSongId] = useState<number | null>(editing?.songId ?? null);
  const [version, setVersion] = useState(editing ? "" : "original");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([libraryApi.songs(controller.signal), libraryApi.artists(controller.signal)])
      .then(([songList, artistList]) => {
        setSongs(songList);
        setArtists(artistList);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const artistNames = useMemo(
    () => Array.from(new Set(artists.flatMap((one) => one.names.map((name) => name.name)))).sort(),
    [artists],
  );
  // With a known artist typed, its songs only; otherwise every song.
  const songOptions = useMemo(() => {
    const known = artists.find((one) => one.names.some((name) => same(name.name, artist)));
    if (!known) return songs;
    return songs.filter((one) => one.artists.some((credit) => credit.artistId === known.id));
  }, [songs, artists, artist]);

  const replacing = mode === "replace" && editing !== null;
  const valid = replacing || (song.trim().length > 0 && version.trim().length > 0);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const saved = await projectsApi.saveToLibrary(
        projectId,
        replacing
          ? { replace: true }
          : songId !== null
            ? { songId, version: version.trim() }
            : { song: song.trim(), artist: artist.trim() || undefined, version: version.trim() },
      );
      onSaved(saved);
    } catch (caught) {
      setError(said(caught, "The project could not be saved to the library."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Save to library</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {editing ? (
            <Segmented<Mode>
              label="How to save"
              value={mode}
              onChange={(value) => {
                setMode(value);
                setError(null);
              }}
              options={[
                { value: "replace", label: `Replace “${editing.versionName}”` },
                { value: "new", label: "New version" },
              ]}
            />
          ) : null}
          {replacing ? (
            <Typography sx={{ fontSize: 14 }}>
              “{editing.versionName}” of {editing.songTitle} becomes this project. What it is now stays in its
              history.
            </Typography>
          ) : (
            <>
              <Autocomplete
                freeSolo
                options={artistNames}
                inputValue={artist}
                onInputChange={(_, value) => {
                  setArtist(value);
                  setSongId(null);
                }}
                renderInput={(params) => <TextField {...params} autoFocus label="Artist" />}
              />
              <Autocomplete<SongRow, false, false, true>
                freeSolo
                options={songOptions}
                getOptionLabel={(option) => (typeof option === "string" ? option : option.title)}
                renderOption={(props, option) => (
                  <li {...props} key={option.id}>
                    <Stack sx={{ minWidth: 0 }}>
                      <Typography noWrap sx={{ fontSize: 14 }}>
                        {option.title}
                      </Typography>
                      <Typography noWrap sx={{ fontSize: 13, color: "text.secondary" }}>
                        {option.artists.map((credit) => credit.name).join(", ") || "No artist"}
                      </Typography>
                    </Stack>
                  </li>
                )}
                inputValue={song}
                onInputChange={(_, value, reason) => {
                  setSong(value);
                  if (reason === "input") setSongId(null);
                }}
                onChange={(_, value) => {
                  if (value && typeof value !== "string") {
                    setSongId(value.id);
                    if (value.artists[0]) setArtist(value.artists[0].name);
                  }
                }}
                renderInput={(params) => <TextField {...params} label="Song" required />}
              />
              <TextField
                label="Version name"
                required
                value={version}
                onChange={(event) => setVersion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && valid && !busy) void save();
                }}
                slotProps={{ htmlInput: { maxLength: 60 } }}
              />
            </>
          )}
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
        <PillButton kind="primary" onClick={() => void save()} disabled={!valid} busy={busy}>
          {replacing ? "Replace the version" : "Save to library"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default SaveToLibraryDialog;
