/**
 * **Public library → Playlists** (`/public/playlists`): the songs playlists of the Public Library
 * (implementation 02, Phase 13, plan section 15.1). They are published by request (Phase 14), so the
 * list starts empty. A row opens the playlist.
 */

import { useEffect, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";
import { publicApi, type PublicPlaylistRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, fullTime, PageBody, PageHeader, PillButton, relativeTime, type DataColumn } from "../../ui";
import { said } from "../library/shared";

const columns: DataColumn<PublicPlaylistRow>[] = [
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
  { key: "songs", label: "Songs", align: "right", width: 88, sortValue: (row) => row.songs, render: (row) => row.songs },
  {
    key: "changed",
    label: "Changed",
    width: 132,
    sortValue: (row) => row.updatedAt,
    render: (row) => (
      <Tooltip title={fullTime(row.updatedAt)} placement="left">
        <span>{relativeTime(row.updatedAt)}</span>
      </Tooltip>
    ),
  },
];

export function PublicPlaylistsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<PublicPlaylistRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .playlists(controller.signal)
      .then((found) => {
        setRows(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The playlists could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  return (
    <PageBody>
      <PageHeader title="Public playlists" />
      {error ? (
        <EmptyState message={`The playlists could not be loaded: ${error}`} action={<PillButton onClick={() => setReload((n) => n + 1)}>Try again</PillButton>} />
      ) : rows === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 3 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : rows.length === 0 ? (
        <EmptyState message="No public playlists yet." />
      ) : (
        <Stack sx={{ pt: 1 }}>
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => String(row.id)}
            onRowClick={(row) => navigate(ROUTES.publicPlaylist(row.id))}
            initialSort={{ key: "title", direction: "asc" }}
          />
        </Stack>
      )}
    </PageBody>
  );
}

export default PublicPlaylistsPage;
