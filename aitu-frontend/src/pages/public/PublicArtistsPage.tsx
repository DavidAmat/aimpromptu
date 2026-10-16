/**
 * **Public library → Artists** (`/public/artists`): the artists of the Public Library (implementation
 * 02, Phase 13, plan section 15.1), searched by any of their names and sorted by popularity (an
 * artist's most popular song), name or number of songs. The backend pages them; the page keeps the
 * search, the sort and the page in its address. A row opens the artist.
 */

import { useEffect, useState } from "react";
import InputAdornment from "@mui/material/InputAdornment";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate, useSearchParams } from "react-router-dom";
import { publicApi, type ArtistSort, type PublicArtistRow } from "../../api";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, PageBody, PageHeader, PillButton, type DataColumn } from "../../ui";
import { said } from "../library/shared";
import { popularityText } from "./shared";

const PER_PAGE = [50, 100, 200];
const SORTS: readonly ArtistSort[] = ["popularity", "name", "songs"];

const columns: DataColumn<PublicArtistRow>[] = [
  {
    key: "name",
    label: "Name",
    sortValue: (row) => row.name,
    render: (row) => (
      <Typography noWrap title={row.name} sx={{ fontSize: 14, fontWeight: 500, maxWidth: 320 }}>
        {row.name}
      </Typography>
    ),
  },
  {
    key: "other",
    label: "Other names",
    render: (row) => (
      <Typography noWrap sx={{ fontSize: 14, color: "text.secondary", maxWidth: 240 }}>
        {row.otherNames.join(", ") || "–"}
      </Typography>
    ),
  },
  { key: "songs", label: "Songs", align: "right", width: 88, firstDirection: "desc", sortValue: (row) => row.songs, render: (row) => row.songs },
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

export function PublicArtistsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const sortKey = (SORTS as readonly string[]).includes(params.get("sort") ?? "") ? (params.get("sort") as ArtistSort) : "popularity";
  const direction = params.get("dir") === "asc" ? "asc" : params.get("dir") === "desc" ? "desc" : sortKey === "name" ? "asc" : "desc";
  const page = Number(params.get("page") ?? 0) || 0;
  const perPage = PER_PAGE.includes(Number(params.get("per"))) ? Number(params.get("per")) : PER_PAGE[0];
  const [typed, setTyped] = useState(q);
  const [answer, setAnswer] = useState<{ total: number; rows: PublicArtistRow[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  const change = (next: Record<string, string | number | null>, keepPage = false) =>
    setParams(
      (current) => {
        const out = new URLSearchParams(current);
        for (const [key, value] of Object.entries(next)) {
          if (value === null || value === "") out.delete(key);
          else out.set(key, String(value));
        }
        if (!keepPage) out.delete("page");
        return out;
      },
      { replace: true },
    );

  useEffect(() => {
    if (typed.trim() === q) return;
    const timer = window.setTimeout(() => change({ q: typed.trim() }), 250);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typed]);

  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .artists({ q: q || undefined, sort: sortKey, dir: direction, offset: page * perPage, limit: perPage }, controller.signal)
      .then((found) => {
        setAnswer(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The artists could not be loaded."));
      });
    return () => controller.abort();
  }, [q, sortKey, direction, page, perPage, reload]);

  return (
    <PageBody>
      <PageHeader title="Public artists" />
      <Stack spacing={1.5} sx={{ pt: 1 }}>
        <Stack direction="row" useFlexGap spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
          <TextField
            size="small"
            placeholder="Search artists"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            slotProps={{
              htmlInput: { "aria-label": "Search artists" },
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ width: { xs: "100%", sm: 320 } }}
          />
          {answer ? (
            <Typography sx={{ fontSize: 13, color: "text.secondary", ml: { sm: "auto" } }}>
              {answer.total.toLocaleString("en")} {answer.total === 1 ? "artist" : "artists"}
            </Typography>
          ) : null}
        </Stack>
        {error ? (
          <EmptyState message={`The artists could not be loaded: ${error}`} action={<PillButton onClick={() => setReload((n) => n + 1)}>Try again</PillButton>} />
        ) : answer === null ? (
          <Stack spacing={1} aria-busy>
            {Array.from({ length: 8 }, (_, row) => (
              <Skeleton key={row} variant="rounded" height={36} />
            ))}
          </Stack>
        ) : answer.total === 0 ? (
          <EmptyState
            message={q ? `No artist matches “${q}”` : "The Public Library has no artists yet"}
            action={
              q ? (
                <PillButton
                  onClick={() => {
                    setTyped("");
                    change({ q: null });
                  }}
                >
                  Clear the search
                </PillButton>
              ) : undefined
            }
          />
        ) : (
          <DataTable
            columns={columns}
            rows={answer.rows}
            rowKey={(row) => String(row.id)}
            onRowClick={(row) => navigate(ROUTES.publicArtist(row.id))}
            sort={{ key: sortKey, direction }}
            onSortChange={(next) => change({ sort: next.key, dir: next.direction })}
            rowsPerPageOptions={PER_PAGE}
            paging={{
              count: answer.total,
              page,
              perPage,
              onPage: (next) => change({ page: next || null }, true),
              onPerPage: (next) => change({ per: next === PER_PAGE[0] ? null : next }),
            }}
          />
        )}
      </Stack>
    </PageBody>
  );
}

export default PublicArtistsPage;
