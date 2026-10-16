/**
 * **Save to library** (implementation 02, Phase 6, plan sections 10.2 and 10.6): three things in one
 * dialog, **Artist**, **Song** and **Version name**, asked only now that the piano sheet is ready.
 *
 * Artist and Song offer what the user's library already has, and take a new name as it is typed
 * (a new name makes a new artist or a new song). Choosing a known song fills its artist. A copy
 * made by **Edit** opens on **Replace “<version>”** (the version gets this project's content and
 * keeps its earlier state in its history), with **New version** beside it.
 *
 * The two lists also suggest the Public Library's artists and songs (Phase 13), the most popular
 * first, under their own heading: the app context makes the Public Library the source of the
 * names. Choosing a public song (or a public artist) files the project under the user's own song
 * (or artist) that stands for it, made with a link to the public one when there is none, so the
 * Private Library and the Public Library name the same song.
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
  publicApi,
  type ArtistRow,
  type LibraryLink,
  type PublicArtistRow,
  type PublicSongRow,
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

/** A name the Artist field offers: one of the user's, or a public artist. */
type ArtistOption = { name: string; publicId: number | null };
/** A song the Song field offers: one of the user's, or a public song. */
type SongOption = { title: string; artists: string; id: number; isPublic: boolean };

const MINE = "My library";
const PUBLIC = "Public library";

const same = (a: string, b: string) => a.trim().toLocaleLowerCase() === b.trim().toLocaleLowerCase();

export function SaveToLibraryDialog({ projectId, title, editing, onClose, onSaved }: SaveToLibraryDialogProps) {
  const [mode, setMode] = useState<Mode>(editing ? "replace" : "new");
  const [songs, setSongs] = useState<SongRow[]>([]);
  const [artists, setArtists] = useState<ArtistRow[]>([]);
  const [artist, setArtist] = useState(editing?.artists[0] ?? "");
  const [song, setSong] = useState(editing?.songTitle ?? title);
  const [songId, setSongId] = useState<number | null>(editing?.songId ?? null);
  const [publicSongId, setPublicSongId] = useState<number | null>(null);
  const [publicArtistId, setPublicArtistId] = useState<number | null>(null);
  const [publicSongs, setPublicSongs] = useState<PublicSongRow[]>([]);
  const [publicArtists, setPublicArtists] = useState<PublicArtistRow[]>([]);
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

  // The Public Library's suggestions follow what is typed, after a pause.
  useEffect(() => {
    if (artist.trim().length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      publicApi
        .suggest(artist.trim(), { limit: 8 }, controller.signal)
        .then((found) => setPublicArtists(found.artists))
        .catch(() => undefined);
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [artist]);
  useEffect(() => {
    if (song.trim().length < 2 && artist.trim().length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      publicApi
        .suggest(song.trim(), { artist: artist.trim() || undefined, limit: 8 }, controller.signal)
        .then((found) => setPublicSongs(found.songs))
        .catch(() => undefined);
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [song, artist]);

  const artistOptions = useMemo((): ArtistOption[] => {
    const mine = Array.from(new Set(artists.flatMap((one) => one.names.map((name) => name.name)))).sort();
    const known = new Set(mine.map((name) => name.toLocaleLowerCase()));
    return [
      ...mine.map((name) => ({ name, publicId: null })),
      ...(artist.trim().length >= 2 ? publicArtists : [])
        .filter((one) => !known.has(one.name.toLocaleLowerCase()))
        .map((one) => ({ name: one.name, publicId: one.id })),
    ];
  }, [artists, publicArtists, artist]);
  // With a known artist typed, its songs only; otherwise every song. Then the public ones.
  const songOptions = useMemo((): SongOption[] => {
    const known = artists.find((one) => one.names.some((name) => same(name.name, artist)));
    const mine = known ? songs.filter((one) => one.artists.some((credit) => credit.artistId === known.id)) : songs;
    return [
      ...mine.map((one) => ({
        title: one.title,
        artists: one.artists.map((credit) => credit.name).join(", "),
        id: one.id,
        isPublic: false,
      })),
      ...(song.trim().length >= 2 || artist.trim().length >= 2 ? publicSongs : []).map((one) => ({
        title: one.title,
        artists: one.artists.map((credit) => credit.name).join(", "),
        id: one.id,
        isPublic: true,
      })),
    ];
  }, [songs, artists, artist, song, publicSongs]);

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
            : publicSongId !== null
              ? { publicSongId, version: version.trim() }
              : {
                  song: song.trim(),
                  artist: artist.trim() || undefined,
                  publicArtistId: publicArtistId ?? undefined,
                  version: version.trim(),
                },
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
              <Autocomplete<ArtistOption, false, false, true>
                freeSolo
                options={artistOptions}
                groupBy={(option) => (option.publicId === null ? MINE : PUBLIC)}
                getOptionLabel={(option) => (typeof option === "string" ? option : option.name)}
                filterOptions={(options, state) => {
                  const typed = state.inputValue.trim().toLocaleLowerCase();
                  // The public ones are already the backend's matches (accents ignored).
                  return options.filter((one) => one.publicId !== null || one.name.toLocaleLowerCase().includes(typed));
                }}
                renderOption={(props, option) => (
                  <li {...props} key={`${option.publicId ?? "mine"}-${option.name}`}>
                    {option.name}
                  </li>
                )}
                inputValue={artist}
                onInputChange={(_, value, reason) => {
                  setArtist(value);
                  if (reason === "input") {
                    setSongId(null);
                    setPublicSongId(null);
                    setPublicArtistId(null);
                  }
                }}
                onChange={(_, value) => {
                  setPublicArtistId(value && typeof value !== "string" ? value.publicId : null);
                }}
                renderInput={(params) => <TextField {...params} autoFocus label="Artist" />}
              />
              <Autocomplete<SongOption, false, false, true>
                freeSolo
                options={songOptions}
                groupBy={(option) => (option.isPublic ? PUBLIC : MINE)}
                getOptionLabel={(option) => (typeof option === "string" ? option : option.title)}
                filterOptions={(options, state) => {
                  const typed = state.inputValue.trim().toLocaleLowerCase();
                  return options.filter((one) => one.isPublic || one.title.toLocaleLowerCase().includes(typed));
                }}
                renderOption={(props, option) => (
                  <li {...props} key={`${option.isPublic ? "public" : "mine"}-${option.id}`}>
                    <Stack sx={{ minWidth: 0 }}>
                      <Typography noWrap sx={{ fontSize: 14 }}>
                        {option.title}
                      </Typography>
                      <Typography noWrap sx={{ fontSize: 13, color: "text.secondary" }}>
                        {option.artists || "No artist"}
                      </Typography>
                    </Stack>
                  </li>
                )}
                inputValue={song}
                onInputChange={(_, value, reason) => {
                  setSong(value);
                  if (reason === "input") {
                    setSongId(null);
                    setPublicSongId(null);
                  }
                }}
                onChange={(_, value) => {
                  if (value && typeof value !== "string") {
                    setSongId(value.isPublic ? null : value.id);
                    setPublicSongId(value.isPublic ? value.id : null);
                    setPublicArtistId(null);
                    const first = value.artists.split(", ")[0];
                    if (first) setArtist(first);
                  }
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Song"
                    required
                    helperText={publicSongId !== null ? "From the Public Library" : undefined}
                  />
                )}
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
