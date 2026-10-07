/**
 * **Projects** (`/projects`): the Personal Vault, the projects being worked on, the most recently
 * changed first (implementation 02, plan section 10.1).
 *
 * Each row says the step the project reached and when it last changed; the whole row opens the
 * project on that step. The `⋯` menu has Open, Duplicate, Export, Rename, Notes Falling and Delete.
 * **New project** opens a small menu: **From source**, **From scratch** and **From other
 * projects** (the last two are built in Phases 8 and 10), and **Import** for a `.aitu` file.
 *
 * The list is one request (`GET /projects`), with the step of every row in it. Finished work is in
 * My library (Phase 6); a copy made there by **Edit** is listed here, says **Editing**, and its menu
 * leads back to its song. Deleting that copy discards the changes; the version stays as it was.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopyOutlined";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import EditNoteIcon from "@mui/icons-material/EditNoteOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import LaunchIcon from "@mui/icons-material/Launch";
import LibraryAddIcon from "@mui/icons-material/LibraryAddOutlined";
import LibraryMusicIcon from "@mui/icons-material/LibraryMusicOutlined";
import MusicNoteIcon from "@mui/icons-material/MusicNoteOutlined";
import UploadFileIcon from "@mui/icons-material/UploadFileOutlined";
import WaterfallIcon from "@mui/icons-material/WaterfallChartOutlined";
import { useNavigate } from "react-router-dom";
import { projectsApi, type ProjectRow } from "../api";
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

/** What a row says about the step the project reached. */
function stepWords(row: ProjectRow): string {
  if (row.running === "transcribing") return "Transcribing";
  if (row.running === "reading") return "Reading";
  if (!row.step) return "–";
  if (row.step === "source") return "New";
  if (row.step === "audio" && row.hasVideo) return "Video";
  return STEP_LABELS[row.step];
}

const message = (caught: unknown, fallback: string) => (caught instanceof Error ? caught.message : fallback);

/** The browser saves the `.aitu` file; the session cookie goes with the link. */
function download(url: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [renaming, setRenaming] = useState<ProjectRow | null>(null);
  const [deleting, setDeleting] = useState<ProjectRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    projectsApi
      .list(["vault"], controller.signal)
      .then((list) => {
        setRows(list);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(message(caught, "The projects could not be loaded."));
      });
    return () => controller.abort();
  }, [reload]);

  // A running transcription or reading changes the row's step when it ends: look again now and then.
  const anyRunning = rows?.some((row) => row.running !== null) ?? false;
  useEffect(() => {
    if (!anyRunning) return;
    const timer = window.setInterval(() => setReload((count) => count + 1), 5000);
    return () => window.clearInterval(timer);
  }, [anyRunning]);

  const rename = useCallback(async (row: ProjectRow, title: string) => {
    setBusy(true);
    setActionError(null);
    try {
      const renamed = await projectsApi.rename(row.id, title);
      setRenaming(null);
      setRows((list) => list?.map((one) => (one.id === row.id ? renamed : one)) ?? null);
    } catch (caught) {
      setActionError(message(caught, "The project could not be renamed."));
    } finally {
      setBusy(false);
    }
  }, []);

  const remove = useCallback(async (row: ProjectRow) => {
    setBusy(true);
    setActionError(null);
    try {
      await projectsApi.remove(row.id);
      setDeleting(null);
      setRows((list) => list?.filter((one) => one.id !== row.id) ?? null);
    } catch (caught) {
      setActionError(message(caught, "The project could not be deleted."));
    } finally {
      setBusy(false);
    }
  }, []);

  const duplicate = useCallback(async (row: ProjectRow) => {
    setNotice(null);
    try {
      const copy = await projectsApi.duplicate(row.id, `${row.title || "Untitled project"} (copy)`);
      const made = await projectsApi.get(copy.id);
      setRows((list) => (list ? [made, ...list] : [made]));
      setNotice(`“${made.title}” added`);
    } catch (caught) {
      setNotice(null);
      setError(null);
      setActionError(message(caught, "The project could not be duplicated."));
    }
  }, []);

  const [importing, setImporting] = useState(false);
  const importFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      setImporting(true);
      setActionError(null);
      try {
        const made = await projectsApi.import(file);
        navigate(ROUTES.project(made.id));
      } catch (caught) {
        setActionError(message(caught, "The file could not be imported."));
      } finally {
        setImporting(false);
      }
    },
    [navigate],
  );


  const newProject = <NewProjectButton busy={importing} onImport={(file) => void importFile(file)} />;

  const list = (items: ProjectRow[], label: string) => (
    <Box role="list" aria-label={label}>
      {items.map((row) => {
        const changed = row.updatedAt ?? row.createdAt;
        const title = row.title || "Untitled project";
        const first = row.parts[0] ?? row.id;
        return (
          <Box role="listitem" key={row.id}>
            <ListRow
              data-testid={`project-${row.id}`}
              title={title}
              onOpen={() => navigate(ROUTES.project(first))}
              status={
                row.editing ? (
                  <Tooltip title={`Editing “${row.editing.versionName}” of ${row.editing.songTitle}`}>
                    <Typography variant="body2" color="text.secondary" noWrap>
                      Editing
                    </Typography>
                  </Tooltip>
                ) : (
                  stepWords(row)
                )
              }
              meta={
                <Tooltip title={fullTime(changed)} placement="left">
                  <span>{relativeTime(changed)}</span>
                </Tooltip>
              }
              menu={[
                { label: "Open", icon: <LaunchIcon fontSize="small" />, onClick: () => navigate(ROUTES.project(first)) },
                { label: "Duplicate", icon: <ContentCopyIcon fontSize="small" />, onClick: () => void duplicate(row) },
                { label: "Export", icon: <DownloadIcon fontSize="small" />, onClick: () => download(projectsApi.exportUrl(row.id)) },
                { label: "Rename", icon: <DriveFileRenameIcon fontSize="small" />, onClick: () => setRenaming(row) },
                {
                  label: "Notes Falling",
                  icon: <WaterfallIcon fontSize="small" />,
                  onClick: () => navigate(ROUTES.projectNotesFalling(first)),
                  disabled: !row.hasNotes,
                },
                ...(row.editing
                  ? [
                      {
                        label: "Open the song",
                        icon: <LibraryMusicIcon fontSize="small" />,
                        onClick: () => row.editing && navigate(ROUTES.librarySong(row.editing.songId)),
                      },
                    ]
                  : []),
                {
                  label: row.editing ? "Discard changes" : "Delete",
                  icon: <DeleteIcon fontSize="small" />,
                  onClick: () => setDeleting(row),
                  danger: true,
                },
              ]}
            />
          </Box>
        );
      })}
    </Box>
  );

  return (
    <PageBody>
      <PageHeader title="Projects" actions={newProject} />

      {actionError && !renaming && !deleting ? (
        <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      ) : null}
      {notice ? (
        <Alert severity="success" onClose={() => setNotice(null)} sx={{ mb: 2 }} role="status">
          {notice}
        </Alert>
      ) : null}

      {error ? (
        <EmptyState
          message={`The projects could not be loaded: ${error}`}
          action={<PillButton onClick={() => setReload((count) => count + 1)}>Try again</PillButton>}
        />
      ) : rows === null ? (
        <Stack spacing={1} sx={{ pt: 1 }} aria-busy>
          {Array.from({ length: 6 }, (_, row) => (
            <Skeleton key={row} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : rows.length === 0 ? (
        <EmptyState message="No projects yet" action={newProject} />
      ) : (
        <Box sx={{ pt: 1, mb: 4 }}>{list(rows, "Projects")}</Box>
      )}

      {renaming ? (
        <RenameDialog
          key={renaming.id}
          row={renaming}
          busy={busy}
          error={actionError}
          onCancel={() => {
            setRenaming(null);
            setActionError(null);
          }}
          onRename={(title) => void rename(renaming, title)}
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={
          deleting?.editing
            ? `Discard your changes to “${deleting.editing.versionName}”?`
            : `Delete “${deleting?.title || "Untitled project"}”?`
        }
        message={
          <>
            {deleting?.editing
              ? "This copy is deleted. The version in your library stays as it is."
              : "The audio, the notes and the piano sheet of this project are deleted. This cannot be undone."}
            {actionError ? (
              <Typography color="error" sx={{ mt: 1 }}>
                {actionError}
              </Typography>
            ) : null}
          </>
        }
        confirmLabel={deleting?.editing ? "Discard changes" : "Delete project"}
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

/** **New project**: the three ways in, and Import. */
function NewProjectButton({ busy, onImport }: { busy: boolean; onImport: (file: File | undefined) => void }) {
  const navigate = useNavigate();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const close = () => setAnchor(null);
  return (
    <>
      <PillButton
        kind="primary"
        startIcon={<AddIcon />}
        endIcon={<ExpandMoreIcon />}
        busy={busy}
        onClick={(event) => setAnchor(event.currentTarget)}
        aria-haspopup="menu"
        aria-expanded={anchor !== null}
      >
        New project
      </PillButton>
      <Menu
        anchorEl={anchor}
        open={anchor !== null}
        onClose={close}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { minWidth: 260 } } }}
      >
        <MenuItem
          onClick={() => {
            close();
            navigate(ROUTES.projectNew);
          }}
        >
          <ListItemIcon>
            <MusicNoteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="From source" secondary="An audio, a video or a YouTube link" />
        </MenuItem>
        <MenuItem disabled>
          <ListItemIcon>
            <EditNoteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="From scratch" secondary="Not available yet" />
        </MenuItem>
        <MenuItem disabled>
          <ListItemIcon>
            <LibraryAddIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="From other projects" secondary="Not available yet" />
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            close();
            fileInput.current?.click();
          }}
        >
          <ListItemIcon>
            <UploadFileIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Import" secondary="A .aitu file" />
        </MenuItem>
      </Menu>
      <input
        ref={fileInput}
        type="file"
        hidden
        accept=".aitu"
        aria-label="Choose a .aitu file"
        onChange={(event) => {
          onImport(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </>
  );
}

function RenameDialog({
  row,
  busy,
  error,
  onCancel,
  onRename,
}: {
  row: ProjectRow;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onRename: (title: string) => void;
}) {
  const [title, setTitle] = useState(row.title);
  const valid = title.trim().length > 0 && title.trim() !== row.title;
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>Rename project</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label="Title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && valid) onRename(title.trim());
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
        <PillButton kind="primary" onClick={() => onRename(title.trim())} disabled={!valid} busy={busy}>
          Rename
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default ProjectsPage;
