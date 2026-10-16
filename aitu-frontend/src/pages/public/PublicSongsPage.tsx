/**
 * **Public library → Songs** (`/public/songs`): every song of the Public Library (implementation 02,
 * Phase 13, plan sections 6.1, 15.3 and 15.6).
 *
 * About 9,000 songs, so the backend searches, filters, sorts and pages them; the page keeps what is
 * asked in its address (`?q=…&decade=1980&sort=year&page=2`), so **Back** comes back to the same
 * list. The search looks at titles and artists, words in any order, accents ignored. The filter
 * chips are the song metadata of section 15.3: **Decade**, **Region**, **Genre** and **Tag**; a chip
 * shows only when it has values (genres and tags come by request, Phase 14). Each value says how
 * many songs it would leave.
 *
 * The table sorts by popularity (first), year or title. With a decade chosen, the popularity is the
 * one of that decade's chart weeks, worked out again by the backend (the app context: "if we filter
 * by a given decade, and ask to sort by popularity, these popularities need to be recalculated"),
 * and its column says so. A row opens the song.
 */

import { useEffect, useMemo, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate, useSearchParams } from "react-router-dom";
import { publicApi, type PublicSongPage, type PublicSongRow, type SongSort } from "../../api";
import { ROUTES } from "../../layout/routes";
import {
  DataTable,
  EmptyState,
  FilterChip,
  PageBody,
  PageHeader,
  PillButton,
  type DataColumn,
  type TableSort,
} from "../../ui";
import { said } from "../library/shared";
import { popularityText } from "./shared";

const PER_PAGE = [50, 100, 200];
const SORTS: readonly SongSort[] = ["popularity", "year", "title"];

const artistsOf = (row: PublicSongRow) => row.artists.map((artist) => artist.name).join(", ");
const numberOr = (text: string | null) => (text === null || text === "" || Number.isNaN(Number(text)) ? undefined : Number(text));

export function PublicSongsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const decade = numberOr(params.get("decade"));
  const region = params.get("region") ?? undefined;
  const genre = numberOr(params.get("genre"));
  const tag = numberOr(params.get("tag"));
  const sortKey = (SORTS as readonly string[]).includes(params.get("sort") ?? "") ? (params.get("sort") as SongSort) : "popularity";
  const direction = params.get("dir") === "asc" ? "asc" : params.get("dir") === "desc" ? "desc" : sortKey === "title" ? "asc" : "desc";
  const page = numberOr(params.get("page")) ?? 0;
  const perPage = PER_PAGE.includes(numberOr(params.get("per")) ?? 0) ? Number(params.get("per")) : PER_PAGE[0];

  const [typed, setTyped] = useState(q);
  const [answered, setAnswered] = useState<{ key: string; page: PublicSongPage } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const askKey = params.toString();
  const answer = answered?.page ?? null;
  // The table stays while the next page loads, dimmed.
  const loading = answered?.key !== askKey;

  /** A change of the list: the other settings stay, the page goes back to the first. */
  const change = (next: Record<string, string | number | null | undefined>, keepPage = false) => {
    setParams(
      (current) => {
        const out = new URLSearchParams(current);
        for (const [key, value] of Object.entries(next)) {
          if (value === null || value === undefined || value === "") out.delete(key);
          else out.set(key, String(value));
        }
        if (!keepPage) out.delete("page");
        return out;
      },
      { replace: true },
    );
  };

  // The search waits for a pause in the typing.
  useEffect(() => {
    if (typed.trim() === q) return;
    const timer = window.setTimeout(() => change({ q: typed.trim() }), 250);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typed]);

  useEffect(() => {
    const controller = new AbortController();
    publicApi
      .songs(
        { q: q || undefined, decade, region, genre, tag, sort: sortKey, dir: direction, offset: page * perPage, limit: perPage },
        controller.signal,
      )
      .then((found) => {
        setAnswered({ key: askKey, page: found });
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The songs could not be loaded."));
      });
    return () => controller.abort();
    // askKey is the address these values come from.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, decade, region, genre, tag, sortKey, direction, page, perPage, reload]);

  const decadeLabel = decade !== undefined ? answer?.facets.decades.find((one) => Number(one.value) === decade)?.label : undefined;
  const columns: DataColumn<PublicSongRow>[] = useMemo(
    () => [
      {
        key: "title",
        label: "Title",
        sortValue: (row) => row.title,
        render: (row) => (
          <Typography noWrap title={row.title} sx={{ fontSize: 14, fontWeight: 500, maxWidth: 360 }}>
            {row.title}
          </Typography>
        ),
      },
      {
        key: "artist",
        label: "Artist",
        render: (row) => (
          <Typography noWrap title={artistsOf(row)} sx={{ fontSize: 14, color: "text.secondary", maxWidth: 260 }}>
            {artistsOf(row) || "–"}
          </Typography>
        ),
      },
      {
        key: "year",
        label: "Year",
        align: "right",
        width: 80,
        firstDirection: "desc",
        sortValue: (row) => row.year,
        render: (row) => row.year ?? "–",
      },
      {
        key: "popularity",
        label: decadeLabel ? `Popularity in the ${decadeLabel}` : "Popularity",
        align: "right",
        width: decadeLabel ? 168 : 112,
        firstDirection: "desc",
        sortValue: (row) => row.popularity,
        render: (row) => popularityText(row.popularity),
      },
      {
        key: "versions",
        label: "Versions",
        align: "right",
        width: 88,
        render: (row) => (row.versions > 0 ? row.versions : "–"),
      },
    ],
    [decadeLabel],
  );

  const facets = answer?.facets;
  const filtered = q !== "" || decade !== undefined || region !== undefined || genre !== undefined || tag !== undefined;
  const sort: TableSort = { key: sortKey, direction };

  return (
    <PageBody>
      <PageHeader title="Public songs" />
      <Stack spacing={1.5} sx={{ pt: 1 }}>
        <Stack direction="row" useFlexGap spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
          <TextField
            size="small"
            placeholder="Search songs and artists"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") change({ q: typed.trim() });
            }}
            slotProps={{
              htmlInput: { "aria-label": "Search songs and artists", "data-testid": "public-search" },
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
          {facets && (facets.decades.length > 0 || decade !== undefined) ? (
            <FilterChip
              data-testid="filter-decade"
              label="Decade"
              anyLabel="Any decade"
              options={facets.decades}
              value={decade !== undefined ? String(decade) : null}
              onChange={(value) => change({ decade: value })}
            />
          ) : null}
          {facets && (facets.regions.length > 0 || region !== undefined) ? (
            <FilterChip
              data-testid="filter-region"
              label="Region"
              anyLabel="Any region"
              options={facets.regions}
              value={region ?? null}
              onChange={(value) => change({ region: value })}
            />
          ) : null}
          {facets && (facets.genres.length > 0 || genre !== undefined) ? (
            <FilterChip
              label="Genre"
              anyLabel="Any genre"
              options={facets.genres}
              value={genre !== undefined ? String(genre) : null}
              onChange={(value) => change({ genre: value })}
            />
          ) : null}
          {facets && (facets.tags.length > 0 || tag !== undefined) ? (
            <FilterChip
              label="Tag"
              anyLabel="Any tag"
              options={facets.tags}
              value={tag !== undefined ? String(tag) : null}
              onChange={(value) => change({ tag: value })}
            />
          ) : null}
          {answer ? (
            <Typography sx={{ fontSize: 13, color: "text.secondary", ml: { sm: "auto" } }} data-testid="public-total">
              {answer.total.toLocaleString("en")} {answer.total === 1 ? "song" : "songs"}
            </Typography>
          ) : null}
        </Stack>

        {error ? (
          <EmptyState
            message={`The songs could not be loaded: ${error}`}
            action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
          />
        ) : answer === null ? (
          <Stack spacing={1} aria-busy>
            {Array.from({ length: 8 }, (_, row) => (
              <Skeleton key={row} variant="rounded" height={36} />
            ))}
          </Stack>
        ) : answer.total === 0 ? (
          <EmptyState
            message={filtered ? "No song matches this search and these filters" : "The Public Library has no songs yet"}
            action={
              filtered ? (
                <PillButton
                  onClick={() => {
                    setTyped("");
                    change({ q: null, decade: null, region: null, genre: null, tag: null });
                  }}
                >
                  Clear the search and filters
                </PillButton>
              ) : undefined
            }
          />
        ) : (
          <div aria-busy={loading} style={{ opacity: loading ? 0.6 : 1, transition: "opacity 120ms" }}>
            <DataTable
              columns={columns}
              rows={answer.rows}
              rowKey={(row) => String(row.id)}
              onRowClick={(row) => navigate(ROUTES.publicSong(row.id))}
              sort={sort}
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
          </div>
        )}
      </Stack>
    </PageBody>
  );
}

export default PublicSongsPage;
