/**
 * **Shared** (`/library/shared`, implementation 02, Phase 14, plan section 15.4): the Private
 * Libraries other users share with this one, read only.
 *
 * One library at a time: the one of `?from=<owner id>`, or the first. With more than one, the
 * owners are a choice above the list. A row opens the song (`/library/shared/songs/:id`), where its
 * versions play and **Add to my library** copies them. **Share my library** (also in the user menu)
 * chooses who sees this user's own library.
 */

import { useEffect, useState } from "react";
import MenuItem from "@mui/material/MenuItem";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { useNavigate, useSearchParams } from "react-router-dom";
import { sharesApi, type Person, type SharedLibrary } from "../../api";
import { ShareDialog } from "../../layout/ShareDialog";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, PageBody, PageHeader, PillButton, Segmented } from "../../ui";
import { said } from "./shared";

type Row = SharedLibrary["songs"][number];

export function SharedPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [owners, setOwners] = useState<Person[] | null>(null);
  const [library, setLibrary] = useState<{ owner: number; value: SharedLibrary } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    sharesApi
      .list(controller.signal)
      .then((found) => setOwners(found.sharedWithMe))
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The shared libraries could not be loaded."));
      });
    return () => controller.abort();
  }, []);

  const asked = Number(params.get("from"));
  const owner = owners?.find((one) => one.id === asked) ?? owners?.[0] ?? null;

  useEffect(() => {
    if (!owner) return;
    const controller = new AbortController();
    sharesApi
      .library(owner.id, controller.signal)
      .then((found) => setLibrary({ owner: owner.id, value: found }))
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The library could not be loaded."));
      });
    return () => controller.abort();
  }, [owner]);

  const songs = owner && library?.owner === owner.id ? library.value.songs : null;
  const pick = (id: number) => setParams({ from: String(id) }, { replace: true });

  return (
    <PageBody>
      <PageHeader
        title="Shared"
        actions={
          <PillButton kind="secondary" onClick={() => setSharing(true)} data-testid="share-my-library">
            Share my library
          </PillButton>
        }
      />
      {error ? (
        <EmptyState message={error} />
      ) : owners === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : owners.length === 0 || !owner ? (
        <EmptyState message="Nobody shares a library with you yet" />
      ) : (
        <Stack spacing={2}>
          {owners.length > 1 ? (
            owners.length <= 4 ? (
              <Segmented<string>
                label="Whose library"
                value={String(owner.id)}
                onChange={(value) => pick(Number(value))}
                options={owners.map((one) => ({ value: String(one.id), label: one.username }))}
              />
            ) : (
              <TextField
                select
                size="small"
                label="Library of"
                value={owner.id}
                onChange={(event) => pick(Number(event.target.value))}
                sx={{ maxWidth: 260 }}
              >
                {owners.map((one) => (
                  <MenuItem key={one.id} value={one.id}>
                    {one.username}
                  </MenuItem>
                ))}
              </TextField>
            )
          ) : null}
          {songs === null ? (
            <Skeleton variant="rounded" height={160} />
          ) : songs.length === 0 ? (
            <EmptyState message={`${owner.username} has no songs yet`} />
          ) : (
            <DataTable<Row>
              columns={[
                { key: "title", label: `Songs of ${owner.username}`, render: (row) => row.title, sortValue: (row) => row.title.toLocaleLowerCase() },
                {
                  key: "artists",
                  label: "Artist",
                  render: (row) => row.artists.join(", ") || "No artist",
                  sortValue: (row) => (row.artists[0] ?? "").toLocaleLowerCase(),
                },
                { key: "versions", label: "Versions", align: "right", render: (row) => row.versions, sortValue: (row) => row.versions },
              ]}
              rows={songs}
              rowKey={(row) => String(row.id)}
              onRowClick={(row) => navigate(ROUTES.librarySharedSong(row.id))}
            />
          )}
        </Stack>
      )}
      {sharing ? <ShareDialog onClose={() => setSharing(false)} /> : null}
    </PageBody>
  );
}

export default SharedPage;
