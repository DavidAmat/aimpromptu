/**
 * **Songs** (`/library/songs`): the songs of the user's Private Library, finished work (implementation
 * 02, Phase 6, plan sections 6.1 and 15.1).
 *
 * A song comes here from **Save to library** on a project; the page has no button to make one. A
 * table, because songs are compared on the same fields: title, artist, how many versions, when one
 * last changed. The filter above it looks at the title and the artists. A song whose version is being
 * edited in Projects says so beside its title. A row opens the song and its versions.
 *
 * Songs picked with their checkbox are made into a songs playlist with **Make a playlist** (Phase
 * 10, the app context's dynamic playlist), each on its first version.
 */

import { useEffect, useMemo, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";
import { libraryApi, playlistsApi, type SongRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  DataTable,
  EmptyState,
  fullTime,
  PageBody,
  PageHeader,
  PillButton,
  relativeTime,
  type DataColumn,
} from "../../ui";
import { TextDialog } from "./TextDialog";
import { said } from "./shared";

const artistsOf = (row: SongRow) => row.artists.map((artist) => artist.name).join(", ");

export function SongsPage() {
  const navigate = useNavigate();
  const [songs, setSongs] = useState<SongRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [making, setMaking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [makeError, setMakeError] = useState<string | null>(null);

  /** The picked songs, in the order the table lists them by title. */
  const makePlaylist = async (title: string) => {
    const chosen = (songs ?? []).filter((row) => picked.has(String(row.id)));
    setBusy(true);
    setMakeError(null);
    try {
      const made = await playlistsApi.create(
        title,
        chosen.map((row) => ({ songId: row.id })),
      );
      navigate(ROUTES.libraryPlaylist(made.id));
    } catch (caught) {
      setMakeError(said(caught, "The playlist could not be made."));
      setBusy(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .songs(controller.signal)
      .then((list) => {
        setSongs(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The songs could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  const shown = useMemo(() => {
    const wanted = filter.trim().toLocaleLowerCase();
    if (!songs || !wanted) return songs ?? [];
    return songs.filter((row) => `${row.title} ${artistsOf(row)}`.toLocaleLowerCase().includes(wanted));
  }, [songs, filter]);

  const columns: DataColumn<SongRow>[] = [
    {
      key: "title",
      label: "Title",
      sortValue: (row) => row.title.toLocaleLowerCase(),
      render: (row) => (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
          <Typography noWrap title={row.title} sx={{ fontSize: 14, fontWeight: 500 }}>
            {row.title}
          </Typography>
          {row.editing ? (
            <Typography component="span" sx={{ fontSize: 13, color: "text.secondary", flexShrink: 0 }}>
              Editing
            </Typography>
          ) : null}
        </Stack>
      ),
    },
    {
      key: "artist",
      label: "Artist",
      sortValue: (row) => artistsOf(row).toLocaleLowerCase(),
      render: (row) => (
        <Typography noWrap title={artistsOf(row)} sx={{ fontSize: 14, color: "text.secondary" }}>
          {artistsOf(row) || "–"}
        </Typography>
      ),
    },
    {
      key: "versions",
      label: "Versions",
      align: "right",
      width: 96,
      sortValue: (row) => row.versions,
      render: (row) => row.versions,
    },
    {
      key: "changed",
      label: "Changed",
      width: 132,
      sortValue: (row) => row.updatedAt ?? "",
      render: (row) =>
        row.updatedAt ? (
          <Tooltip title={fullTime(row.updatedAt)} placement="left">
            <span>{relativeTime(row.updatedAt)}</span>
          </Tooltip>
        ) : (
          "–"
        ),
    },
  ];

  return (
    <PageBody>
      <PageHeader
        title="Songs"
        actions={
          picked.size > 0 ? (
            <PillButton kind="primary" onClick={() => setMaking(true)} data-testid="make-playlist">
              Make a playlist of {picked.size}
            </PillButton>
          ) : undefined
        }
      />
      {error ? (
        <EmptyState
          message={`The songs could not be loaded: ${error}`}
          action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
        />
      ) : songs === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : songs.length === 0 ? (
        <EmptyState
          message="No songs yet. Save a project to the library to add one."
          action={<PillButton onClick={() => navigate(ROUTES.projects)}>Open Projects</PillButton>}
        />
      ) : (
        <Stack spacing={1.5} sx={{ pt: 1 }}>
          <TextField
            size="small"
            label="Filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            sx={{ maxWidth: 320 }}
          />
          {shown.length === 0 ? (
            <EmptyState
              message={`No song or artist matches “${filter.trim()}”`}
              action={<PillButton onClick={() => setFilter("")}>Clear the filter</PillButton>}
            />
          ) : (
            <DataTable
              columns={columns}
              rows={shown}
              rowKey={(row) => String(row.id)}
              onRowClick={(row) => navigate(ROUTES.librarySong(row.id))}
              initialSort={{ key: "title", direction: "asc" }}
              selected={picked}
              onSelectedChange={setPicked}
            />
          )}
        </Stack>
      )}
      {making ? (
        <TextDialog
          title="Make a playlist"
          label="Title"
          confirmLabel="Make the playlist"
          busy={busy}
          error={makeError}
          onCancel={() => setMaking(false)}
          onConfirm={(title) => void makePlaylist(title)}
        />
      ) : null}
    </PageBody>
  );
}

export default SongsPage;
