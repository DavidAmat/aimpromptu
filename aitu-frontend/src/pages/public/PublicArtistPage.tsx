/**
 * **One public artist** (`/public/artists/:id`): its names, its songs and its albums, each by
 * popularity (implementation 02, Phase 13, plan section 15.1; the app context: "sort the songs
 * within a given artist"). **Add to my library** adds every song of the artist that has a version,
 * each with its default version; with none yet, the button says why on hover. A song row opens the
 * public song.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import { useNavigate, useParams } from "react-router-dom";
import { publicApi, type PublicArtistDetail } from "../../api";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, PageBody, PageHeader, PillButton, Section, type DataColumn } from "../../ui";
import { said } from "../library/shared";
import { popularityText } from "./shared";

type SongOfArtist = PublicArtistDetail["songs"][number];
type AlbumOfArtist = PublicArtistDetail["albums"][number];

const songColumns: DataColumn<SongOfArtist>[] = [
  {
    key: "title",
    label: "Title",
    sortValue: (row) => row.title.toLocaleLowerCase(),
    render: (row) => (
      <Typography noWrap title={row.title} sx={{ fontSize: 14, fontWeight: 500, maxWidth: 360 }}>
        {row.title}
      </Typography>
    ),
  },
  { key: "year", label: "Year", align: "right", width: 80, firstDirection: "desc", sortValue: (row) => row.year, render: (row) => row.year ?? "–" },
  {
    key: "popularity",
    label: "Popularity",
    align: "right",
    width: 112,
    firstDirection: "desc",
    sortValue: (row) => row.popularity,
    render: (row) => popularityText(row.popularity),
  },
  { key: "versions", label: "Versions", align: "right", width: 88, sortValue: (row) => row.versions, render: (row) => (row.versions > 0 ? row.versions : "–") },
];

const albumColumns: DataColumn<AlbumOfArtist>[] = [
  {
    key: "title",
    label: "Title",
    sortValue: (row) => row.title.toLocaleLowerCase(),
    render: (row) => (
      <Typography noWrap title={row.title} sx={{ fontSize: 14, maxWidth: 360 }}>
        {row.title}
      </Typography>
    ),
  },
  { key: "year", label: "Year", align: "right", width: 80, firstDirection: "desc", sortValue: (row) => row.year, render: (row) => row.year ?? "–" },
  {
    key: "popularity",
    label: "Popularity",
    align: "right",
    width: 112,
    firstDirection: "desc",
    sortValue: (row) => row.popularity,
    render: (row) => popularityText(row.popularity),
  },
];

export function PublicArtistPage() {
  const { id } = useParams();
  const artistId = Number(id);
  const navigate = useNavigate();
  const [artist, setArtist] = useState<PublicArtistDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .artist(artistId, controller.signal)
      .then((found) => {
        setArtist(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The artist could not be loaded."));
      });
    return () => controller.abort();
  }, [artistId, reload]);

  const add = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const pulled = await publicApi.pullArtist(artistId);
      setNotice(
        pulled.versions > 0
          ? `${pulled.songs} ${pulled.songs === 1 ? "song" : "songs"} added to My library`
          : "Every song of this artist with a version is already in My library",
      );
      setReload((count) => count + 1);
    } catch (caught) {
      setActionError(said(caught, "The songs could not be added to your library."));
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <PageBody>
        <PageHeader title="Artist" back={{ to: ROUTES.publicArtists, label: "Back to Public artists" }} />
        <EmptyState message={error} action={<PillButton onClick={() => navigate(ROUTES.publicArtists)}>Open Public artists</PillButton>} />
      </PageBody>
    );
  }

  return (
    <PageBody>
      <PageHeader
        title={artist?.name ?? ""}
        back={{ to: ROUTES.publicArtists, label: "Back to Public artists" }}
        actions={
          artist ? (
            <>
              {artist.inLibrary !== null ? (
                <PillButton kind="secondary" onClick={() => navigate(ROUTES.libraryArtist(artist.inLibrary ?? 0))}>
                  Open in My library
                </PillButton>
              ) : null}
              <Tooltip title={artist.withVersions === 0 ? "No song of this artist has a version yet" : `Adds the ${artist.withVersions} ${artist.withVersions === 1 ? "song" : "songs"} with a version`}>
                <span>
                  <PillButton kind="primary" startIcon={<LibraryAddIcon />} disabled={artist.withVersions === 0} busy={busy} onClick={() => void add()} data-testid="add-artist">
                    Add to my library
                  </PillButton>
                </span>
              </Tooltip>
            </>
          ) : undefined
        }
      />
      {artist === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={36} />
          ))}
        </Stack>
      ) : (
        <Stack spacing={3} sx={{ pt: 0.5, pb: 4 }}>
          {artist.otherNames.length > 0 ? (
            <Typography sx={{ fontSize: 15, color: "text.secondary" }}>Also {artist.otherNames.join(", ")}</Typography>
          ) : null}
          {notice ? <Alert severity="success" onClose={() => setNotice(null)}>{notice}</Alert> : null}
          {actionError ? <Alert severity="error" onClose={() => setActionError(null)}>{actionError}</Alert> : null}
          <Section title={`Songs (${artist.songs.length})`}>
            {artist.songs.length === 0 ? (
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>No songs.</Typography>
            ) : (
              <DataTable
                columns={songColumns}
                rows={artist.songs}
                rowKey={(row) => String(row.id)}
                onRowClick={(row) => navigate(ROUTES.publicSong(row.id))}
                initialSort={{ key: "popularity", direction: "desc" }}
              />
            )}
          </Section>
          {artist.albums.length > 0 ? (
            <Section title={`Albums (${artist.albums.length})`}>
              <DataTable
                columns={albumColumns}
                rows={artist.albums}
                rowKey={(row) => String(row.id)}
                initialSort={{ key: "popularity", direction: "desc" }}
              />
            </Section>
          ) : null}
        </Stack>
      )}
    </PageBody>
  );
}

export default PublicArtistPage;
