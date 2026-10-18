/**
 * **Requests** (`/requests`) and **Review** (`/admin/requests`): the lists of requests to the
 * Public Library (implementation 02, Phase 14, plan sections 16.2 and 16.3).
 *
 * - **Requests**: the user's own, the most recently changed first, each with its status.
 * - **Review** (the master user): the open requests, oldest first, with their kind and author;
 *   **All** shows every request, the newest first.
 *
 * A row opens the request. A request is sent from the thing it is about: **Publish** on a version
 * or a playlist of My library, **Suggest a change** on a public song or artist, **Ask for a fixed
 * version** on the user's own version of a public song, **Propose a song** on Public songs.
 */

import { useEffect, useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";
import { requestsApi, type RequestSummary } from "../../api";
import { ROUTES } from "../../layout/routes";
import { DataTable, EmptyState, fullTime, PageBody, PageHeader, PillButton, relativeTime, Segmented, type DataColumn } from "../../ui";
import { said } from "../library/shared";
import { KIND_LABEL, STATUS_LABEL } from "./words";

function columns(review: boolean, everything: boolean): DataColumn<RequestSummary>[] {
  const time = review && !everything ? "createdAt" : "updatedAt";
  return [
    {
      key: "title",
      label: "Request",
      render: (row) => (
        <Stack sx={{ minWidth: 0, maxWidth: 360 }}>
          <Typography noWrap title={row.title} sx={{ fontSize: 14, fontWeight: 500 }}>
            {row.title || "Untitled"}
          </Typography>
          <Typography noWrap sx={{ fontSize: 13, color: "text.secondary" }}>
            {row.subject}
          </Typography>
        </Stack>
      ),
      sortValue: (row) => row.title.toLocaleLowerCase(),
    },
    { key: "kind", label: "Kind", render: (row) => KIND_LABEL[row.kind], sortValue: (row) => KIND_LABEL[row.kind] },
    ...(review ? [{ key: "author", label: "From", render: (row: RequestSummary) => row.author, sortValue: (row: RequestSummary) => row.author }] : []),
    {
      key: "status",
      label: "Status",
      render: (row) => (
        <Typography sx={{ fontSize: 14, fontWeight: row.status === "changesAsked" && !review ? 600 : 400 }}>
          {STATUS_LABEL[row.status]}
        </Typography>
      ),
      sortValue: (row) => STATUS_LABEL[row.status],
    },
    {
      key: "time",
      label: time === "createdAt" ? "Sent" : "Changed",
      align: "right",
      render: (row) => (
        <Tooltip title={fullTime(row[time])}>
          <span>{relativeTime(row[time])}</span>
        </Tooltip>
      ),
      sortValue: (row) => row[time],
      firstDirection: "desc",
    },
  ];
}

export function RequestsPage({ review = false }: { review?: boolean }) {
  const navigate = useNavigate();
  const [everything, setEverything] = useState(false);
  const [rows, setRows] = useState<{ key: string; value: RequestSummary[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = `${review}:${everything}`;

  useEffect(() => {
    const controller = new AbortController();
    (review ? requestsApi.review(everything, controller.signal) : requestsApi.mine(controller.signal))
      .then((found) => {
        setRows({ key, value: found });
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The requests could not be loaded."));
      });
    return () => controller.abort();
  }, [review, everything, key]);

  const shown = rows?.key === key ? rows.value : null;
  return (
    <PageBody>
      <PageHeader
        title={review ? "Review" : "Requests"}
        actions={
          review ? (
            <Segmented<"open" | "all">
              label="Which requests"
              value={everything ? "all" : "open"}
              onChange={(value) => setEverything(value === "all")}
              options={[
                { value: "open", label: "Waiting" },
                { value: "all", label: "All" },
              ]}
            />
          ) : undefined
        }
      />
      {error ? (
        <EmptyState message={error} />
      ) : shown === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 4 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={52} />
          ))}
        </Stack>
      ) : shown.length === 0 ? (
        <EmptyState
          message={review ? (everything ? "No requests yet" : "Nothing to review") : "No requests yet"}
          action={
            review ? undefined : (
              <PillButton onClick={() => navigate(ROUTES.librarySongs)}>Open My library</PillButton>
            )
          }
        />
      ) : (
        <DataTable<RequestSummary>
          columns={columns(review, everything)}
          rows={shown}
          rowKey={(row) => String(row.id)}
          onRowClick={(row) => navigate(review ? ROUTES.adminRequest(row.id) : ROUTES.request(row.id))}
        />
      )}
    </PageBody>
  );
}

export function ReviewPage() {
  return <RequestsPage review />;
}

export default RequestsPage;
