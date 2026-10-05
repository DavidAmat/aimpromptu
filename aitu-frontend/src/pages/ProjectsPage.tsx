/**
 * **Projects** (`/projects`): the projects being worked on, newest change first (implementation 02,
 * plan section 10.1).
 *
 * Until Phase 3 gives projects their own storage, a project is one of today's pieces. Each row says
 * the step the project reached and when it last changed; the whole row opens the project on that
 * step. The `⋯` menu has the secondary actions. **New project** opens the Source step of a new one.
 *
 * The list arrives in one request. The step of each row needs one small request per project, so
 * the rows are drawn at once and each step fills in when its answer arrives (at most six at a time,
 * the browser's own limit per server).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import LaunchIcon from "@mui/icons-material/Launch";
import WaterfallIcon from "@mui/icons-material/WaterfallChartOutlined";
import { useNavigate } from "react-router-dom";
import { audioApi, piecesApi, type AudioItem, type PieceStatus } from "../api";
import { STEP_LABELS } from "../components/piece/stepLabels";
import { ROUTES } from "../layout/routes";
import {
  ConfirmDialog,
  EmptyState,
  fullTime,
  ListRow,
  PageBody,
  PageHeader,
  PillButton,
  relativeTime,
} from "../ui";

/** How many status requests run at once. */
const PARALLEL = 6;

/** What a row says about the step the project reached. */
function stepWords(status: PieceStatus | undefined): string | null {
  if (!status) return null;
  if (status.steps.some((step) => step.state === "running")) return "Transcribing";
  return STEP_LABELS[status.resume];
}

const newestFirst = (a: AudioItem, b: AudioItem) =>
  (b.updatedAt ?? b.createdAt).localeCompare(a.updatedAt ?? a.createdAt);

export function ProjectsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AudioItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<Record<string, PieceStatus>>({});
  const [reload, setReload] = useState(0);
  const [renaming, setRenaming] = useState<AudioItem | null>(null);
  const [deleting, setDeleting] = useState<AudioItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    audioApi
      .list(controller.signal)
      .then((list) => {
        setItems([...list].sort(newestFirst));
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "The projects could not be loaded.");
      });
    return () => controller.abort();
  }, [reload]);

  // The step of each row, a few requests at a time; a row whose request fails shows a dash.
  useEffect(() => {
    if (!items) return;
    const controller = new AbortController();
    const queue = items.map((item) => item.uuid);
    const worker = async () => {
      for (let uuid = queue.shift(); uuid; uuid = queue.shift()) {
        try {
          const status = await piecesApi.status(uuid, controller.signal);
          setStatuses((known) => ({ ...known, [uuid]: status }));
        } catch {
          if (controller.signal.aborted) return;
        }
      }
    };
    for (let index = 0; index < PARALLEL; index += 1) void worker();
    return () => controller.abort();
  }, [items]);

  const rename = useCallback(
    async (item: AudioItem, alias: string) => {
      setBusy(true);
      setActionError(null);
      try {
        await audioApi.rename(item.uuid, alias);
        setRenaming(null);
        setReload((count) => count + 1);
      } catch (caught) {
        setActionError(caught instanceof Error ? caught.message : "The project could not be renamed.");
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const remove = useCallback(async (item: AudioItem) => {
    setBusy(true);
    setActionError(null);
    try {
      await audioApi.remove(item.uuid);
      setDeleting(null);
      setItems((list) => list?.filter((one) => one.uuid !== item.uuid) ?? null);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "The project could not be deleted.");
    } finally {
      setBusy(false);
    }
  }, []);

  const newProject = (
    <PillButton kind="primary" startIcon={<AddIcon />} onClick={() => navigate(ROUTES.projectNew)}>
      New project
    </PillButton>
  );

  const rows = useMemo(() => items ?? [], [items]);

  return (
    <PageBody>
      <PageHeader title="Projects" actions={newProject} />

      {error ? (
        <EmptyState
          message={`The projects could not be loaded: ${error}`}
          action={
            <PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>
          }
        />
      ) : items === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : rows.length === 0 ? (
        <EmptyState message="No projects yet" action={newProject} />
      ) : (
        <Box sx={{ pt: 1 }} role="list" aria-label="Projects">
          {rows.map((item) => {
            const status = statuses[item.uuid];
            const words = stepWords(status);
            const changed = item.updatedAt ?? item.createdAt;
            return (
              <Box role="listitem" key={item.uuid}>
                <ListRow
                  data-testid={`project-${item.uuid}`}
                  title={item.alias}
                  onOpen={() => navigate(ROUTES.project(item.uuid))}
                  status={
                    words ? (
                      <Typography variant="body2" color="text.secondary">
                        {words}
                      </Typography>
                    ) : status === undefined ? (
                      <Skeleton width={56} />
                    ) : (
                      "–"
                    )
                  }
                  meta={
                    <Tooltip title={fullTime(changed)} placement="left">
                      <span>{relativeTime(changed)}</span>
                    </Tooltip>
                  }
                  menu={[
                    { label: "Open", icon: <LaunchIcon fontSize="small" />, onClick: () => navigate(ROUTES.project(item.uuid)) },
                    {
                      label: "Notes Falling",
                      icon: <WaterfallIcon fontSize="small" />,
                      onClick: () => navigate(ROUTES.projectNotesFalling(item.uuid)),
                      disabled: !item.hasNotes,
                    },
                    { label: "Rename", icon: <DriveFileRenameIcon fontSize="small" />, onClick: () => setRenaming(item) },
                    { label: "Delete", icon: <DeleteIcon fontSize="small" />, onClick: () => setDeleting(item), danger: true },
                  ]}
                />
              </Box>
            );
          })}
        </Box>
      )}

      {renaming ? (
        <RenameDialog
          key={renaming.uuid}
          item={renaming}
          busy={busy}
          error={actionError}
          onCancel={() => {
            setRenaming(null);
            setActionError(null);
          }}
          onRename={(alias) => void rename(renaming, alias)}
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={`Delete “${deleting?.alias ?? ""}”?`}
        message={
          <>
            The audio, the notes and the piano sheet of this project are deleted. This cannot be undone.
            {actionError ? (
              <Typography color="error" sx={{ mt: 1 }}>
                {actionError}
              </Typography>
            ) : null}
          </>
        }
        confirmLabel="Delete project"
        danger
        busy={busy}
        onConfirm={() => deleting && void remove(deleting)}
        onCancel={() => {
          setDeleting(null);
          setActionError(null);
        }}
      />
    </PageBody>
  );
}

function RenameDialog({
  item,
  busy,
  error,
  onCancel,
  onRename,
}: {
  item: AudioItem;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onRename: (alias: string) => void;
}) {
  const [alias, setAlias] = useState(item.alias);
  const valid = alias.trim().length > 0 && alias.trim() !== item.alias;
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>Rename project</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label="Title"
          value={alias}
          onChange={(event) => setAlias(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && valid) onRename(alias.trim());
          }}
          error={error !== null}
          helperText={error ?? undefined}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => onRename(alias.trim())} disabled={!valid} busy={busy}>
          Rename
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ProjectsPage;
