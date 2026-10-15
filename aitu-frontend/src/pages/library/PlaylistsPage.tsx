/**
 * **Playlists** (`/library/playlists`): the playlists of the user's Private Library (implementation
 * 02, plan section 14.2, Phase 10).
 *
 * A songs playlist is a list of songs of the library, each on a version and maybe a stretch of it;
 * an integrated playlist is a project of its own, saved to the library as a version of a song
 * (made by **From other projects**). Both are listed here; a row opens the playlist, or the song of
 * an integrated one. **New playlist** asks a title; **Make a playlist** on Songs makes one from a
 * selection.
 */

import { useEffect, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";
import { playlistsApi, projectsApi } from "../../api";
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

interface Row {
  key: string;
  title: string;
  kind: "songs" | "integrated";
  /** Songs of a songs playlist, parts of an integrated one. */
  count: number;
  updatedAt: string | null;
  open: string;
}

export function PlaylistsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [making, setMaking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [makeError, setMakeError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([playlistsApi.list(controller.signal), projectsApi.list(["private"], controller.signal)])
      .then(([playlists, projects]) => {
        setRows([
          ...playlists.map(
            (one): Row => ({
              key: `p${one.id}`,
              title: one.title,
              kind: "songs",
              count: one.songs,
              updatedAt: one.updatedAt,
              open: ROUTES.libraryPlaylist(one.id),
            }),
          ),
          ...projects
            .filter((one) => one.kind === "integratedPlaylist" && one.library)
            .map(
              (one): Row => ({
                key: `i${one.id}`,
                title: one.library ? `${one.library.songTitle} (${one.library.versionName})` : one.title,
                kind: "integrated",
                count: one.parts.length,
                updatedAt: one.updatedAt ?? one.createdAt,
                open: one.library ? ROUTES.librarySong(one.library.songId) : ROUTES.project(one.parts[0] ?? one.id),
              }),
            ),
        ]);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlists could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  const make = async (title: string) => {
    setBusy(true);
    setMakeError(null);
    try {
      const made = await playlistsApi.create(title);
      navigate(ROUTES.libraryPlaylist(made.id));
    } catch (caught) {
      setMakeError(said(caught, "The playlist could not be made."));
      setBusy(false);
    }
  };

  const columns: DataColumn<Row>[] = [
    {
      key: "title",
      label: "Title",
      sortValue: (row) => row.title.toLocaleLowerCase(),
      render: (row) => (
        <Typography noWrap title={row.title} sx={{ fontSize: 14, fontWeight: 500 }}>
          {row.title}
        </Typography>
      ),
    },
    {
      key: "kind",
      label: "Kind",
      width: 120,
      sortValue: (row) => row.kind,
      render: (row) => (
        <Tooltip title={row.kind === "songs" ? "Songs of the library, one after the other" : "One project, its sub-songs played without a break"}>
          <span>{row.kind === "songs" ? "Songs" : "Integrated"}</span>
        </Tooltip>
      ),
    },
    {
      key: "count",
      label: "Songs",
      align: "right",
      width: 88,
      sortValue: (row) => row.count,
      render: (row) => row.count,
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

  const newPlaylist = (
    <PillButton kind="primary" startIcon={<AddIcon />} onClick={() => setMaking(true)} data-testid="new-playlist">
      New playlist
    </PillButton>
  );

  return (
    <PageBody>
      <PageHeader title="Playlists" actions={newPlaylist} />
      {error ? (
        <EmptyState
          message={`The playlists could not be loaded: ${error}`}
          action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
        />
      ) : rows === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : rows.length === 0 ? (
        <EmptyState message="No playlists yet." />
      ) : (
        <Stack sx={{ pt: 1 }}>
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => row.key}
            onRowClick={(row) => navigate(row.open)}
            initialSort={{ key: "changed", direction: "desc" }}
          />
        </Stack>
      )}
      {making ? (
        <TextDialog
          title="New playlist"
          label="Title"
          confirmLabel="Make the playlist"
          busy={busy}
          error={makeError}
          onCancel={() => setMaking(false)}
          onConfirm={(title) => void make(title)}
        />
      ) : null}
    </PageBody>
  );
}

export default PlaylistsPage;
