/**
 * **Artists** (`/library/artists`): the artists of the user's Private Library, each with every name
 * it has (implementation 02, Phase 6, plan section 15.1). An artist is made when a song is saved
 * with a name the library does not know. A row opens the artist: its names and its songs.
 */

import { useEffect, useMemo, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";
import { libraryApi, type ArtistRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, PageBody, PageHeader, PillButton, type DataColumn } from "../../ui";
import { said } from "./shared";

const otherNames = (row: ArtistRow) =>
  row.names
    .filter((one) => !one.isDefault)
    .map((one) => one.name)
    .join(", ");

export function ArtistsPage() {
  const navigate = useNavigate();
  const [artists, setArtists] = useState<ArtistRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .artists(controller.signal)
      .then((list) => {
        setArtists(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The artists could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  const shown = useMemo(() => {
    const wanted = filter.trim().toLocaleLowerCase();
    if (!artists || !wanted) return artists ?? [];
    return artists.filter((row) => row.names.some((one) => one.name.toLocaleLowerCase().includes(wanted)));
  }, [artists, filter]);

  const columns: DataColumn<ArtistRow>[] = [
    {
      key: "name",
      label: "Name",
      sortValue: (row) => row.name.toLocaleLowerCase(),
      render: (row) => (
        <Typography noWrap title={row.name} sx={{ fontSize: 14, fontWeight: 500 }}>
          {row.name}
        </Typography>
      ),
    },
    {
      key: "names",
      label: "Other names",
      render: (row) => (
        <Typography noWrap title={otherNames(row)} sx={{ fontSize: 14, color: "text.secondary" }}>
          {otherNames(row) || "–"}
        </Typography>
      ),
    },
    {
      key: "songs",
      label: "Songs",
      align: "right",
      width: 88,
      sortValue: (row) => row.songs,
      render: (row) => row.songs,
    },
  ];

  return (
    <PageBody>
      <PageHeader title="Artists" />
      {error ? (
        <EmptyState
          message={`The artists could not be loaded: ${error}`}
          action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
        />
      ) : artists === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : artists.length === 0 ? (
        <EmptyState
          message="No artists yet. Save a project to the library to add one."
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
              message={`No artist matches “${filter.trim()}”`}
              action={<PillButton onClick={() => setFilter("")}>Clear the filter</PillButton>}
            />
          ) : (
            <DataTable
              columns={columns}
              rows={shown}
              rowKey={(row) => String(row.id)}
              onRowClick={(row) => navigate(ROUTES.libraryArtist(row.id))}
              initialSort={{ key: "name", direction: "asc" }}
            />
          )}
        </Stack>
      )}
    </PageBody>
  );
}

export default ArtistsPage;
