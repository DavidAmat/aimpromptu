/**
 * **Projects** (`/projects`): the Personal Vault, the projects being worked on, the most recently
 * changed first (implementation 02, plan section 10.1).
 *
 * Each row says the step the project reached and when it last changed; the whole row opens the
 * project on that step. The `⋯` menu has Open, Duplicate, Export, Rename, Play (Play mode, Phase 11) and Delete.
 * **New project** opens a small menu: **From source**, **From scratch** (Phase 8) and **From other
 * projects** (Phase 10, its own page), and **Import** for a `.aitu` file.
 *
 * Three pills sit above the list (implementation 04-3, Phase 1): **Folders** (the folders of My projects, opened and
 * closed as the Finder's list view, the projects of a folder indented under it, then the projects in no folder),
 * **All** (the list as it was) and **Filter** (Artist and the metadata). The `⋯` menu also has **Folders…** and
 * **Info** (the metadata: an edit copy's is its song's, the same for every version); a row dragged onto a folder
 * moves into it.
 *
 * The list is one request (`GET /projects`), with the step of every row in it. Finished work is in
 * My library (Phase 6); a copy made there by **Edit** is listed here, says **Editing**, and its menu
 * leads back to its song. Deleting that copy discards the changes; the version stays as it was.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import CircularProgress from "@mui/material/CircularProgress";
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
import PlayIcon from "@mui/icons-material/PlayCircleOutlined";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolderOutlined";
import FolderIcon from "@mui/icons-material/FolderOutlined";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import { useNavigate } from "react-router-dom";
import { foldersApi, metadataApi, projectsApi, type ProjectRow, type SheetInfo } from "../api";
import { FoldersDialog } from "../components/folders/FolderChecklist";
import { FolderLeading, TriangleRoom } from "../components/folders/FolderLeading";
import { folderCount, treeLines } from "../components/folders/folderTree";
import { InfoDialog } from "../components/folders/InfoDialog";
import { filtered, useListFilter } from "../components/folders/listFilter";
import { FilterBar } from "../components/folders/FilterBar";
import { useFolderTree } from "../components/folders/useFolderTree";
import { useListView } from "../components/folders/listView";
import { ViewPills } from "../components/folders/ViewPills";
import { AiMark } from "../components/piece/AiMark";
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

/** What a job working on a project now is doing, in the words of the spinner's tooltip. */
const RUNNING_WORDS: Record<NonNullable<ProjectRow["running"]>, string> = {
  transcribing: "Transcribing",
  reading: "Reading the video",
  writing: "The AI is enhancing the sheet",
};

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

/** The artist of a project: the one of the song it edits, when it is an edit copy of My library; else none. */
const artistsOf = (row: ProjectRow) => row.editing?.artists ?? row.levelSong?.artists ?? row.library?.artists ?? [];
const byTitle = (a: ProjectRow, b: ProjectRow) =>
  (a.title || "Untitled project").localeCompare(b.title || "Untitled project", undefined, { sensitivity: "base" });

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
  const [view, setView] = useListView("aitu.projects.view");
  const [choice, changeFilter] = useListFilter();
  const [foldering, setFoldering] = useState<ProjectRow | null>(null);
  const [informing, setInforming] = useState<SheetInfo | null>(null);

  /** A row's folders changed (the dialog, a drag): the row is updated where it is. */
  const setFolders = useCallback(async (row: ProjectRow, folders: number[]) => {
    const answer = await foldersApi.setOfProject(row.id, folders);
    setRows((list) => list?.map((one) => (one.id === row.id ? { ...one, folders: answer.folders } : one)) ?? null);
  }, []);
  const tree = useFolderTree({
    area: "projects",
    items: rows ?? [],
    onItemDrop: async (key, from, to) => {
      const row = rows?.find((one) => one.id === key);
      if (!row) return;
      const next = [...row.folders.filter((one) => one !== from), to];
      try {
        await setFolders(row, [...new Set(next)]);
      } catch (caught) {
        setActionError(message(caught, "The project could not be moved."));
      }
    },
    onChanged: () => setReload((count) => count + 1),
  });
  const lines = useMemo(
    () => (tree.folders && rows ? treeLines(tree.folders, rows, tree.open, byTitle) : []),
    [tree.folders, rows, tree.open],
  );
  const shown = useMemo(
    () => (rows ? filtered(rows, choice, artistsOf, (row) => row.tags) : []),
    [rows, choice],
  );

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

  // A running transcription, reading or AI run changes the row when it ends: look again now and then.
  const anyRunning = rows?.some((row) => row.running !== null) ?? false;
  useEffect(() => {
    if (!anyRunning) return;
    const timer = window.setInterval(() => setReload((count) => count + 1), 5000);
    return () => window.clearInterval(timer);
  }, [anyRunning]);

  /** The info of a row, as the sheet's info button reads it: an edit copy shows its song's metadata. */
  const openInfo = useCallback(async (row: ProjectRow) => {
    setActionError(null);
    try {
      setInforming(await metadataApi.info(row.id));
    } catch (caught) {
      setActionError(message(caught, "The info could not be read."));
    }
  }, []);

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


  /** **From scratch** (Phase 8): a blank piano sheet, opened on its Sheet step. */
  const fromScratch = useCallback(async () => {
    setImporting(true);
    setActionError(null);
    try {
      const made = await projectsApi.create("", true);
      navigate(ROUTES.project(made.parts[0] ?? made.id, "sheet"));
    } catch (caught) {
      setActionError(message(caught, "The project could not be made."));
    } finally {
      setImporting(false);
    }
  }, [navigate]);

  const newProject = (
    <NewProjectButton
      busy={importing}
      onImport={(file) => void importFile(file)}
      onScratch={() => void fromScratch()}
    />
  );

  /** One project's row; in the Folders view, indented under its folder and draggable. */
  const projectRow = (row: ProjectRow, place?: { depth: number; from: number | null }) => {
    const changed = row.updatedAt ?? row.createdAt;
    const title = row.title || "Untitled project";
    const first = row.parts[0] ?? row.id;
    return (
      <ListRow
        data-testid={`project-${row.id}`}
        title={title}
        indent={place?.depth}
        rowProps={place ? tree.itemRowProps(row.id, place.from) : undefined}
        // One small slot before every name, so the names stay aligned: a spinner while a job works
        // on the project (the AI enhancing its sheet, above all: minutes, in the background), else the
        // green AI mark once the AI has enhanced it (the icon of Enhance with AI), the same mark faint and
        // hollow on a project with notes the AI has not enhanced yet, else nothing.
        leading={
          <Box component="span" sx={{ display: "inline-flex", alignItems: "center", flexShrink: 0 }}>
            {place ? <TriangleRoom /> : null}
            <AiMark
              enhanced={row.enhanced}
              could={row.step === "notes" || row.step === "sheet"}
              busy={
                row.running ? (
                  <Tooltip title={RUNNING_WORDS[row.running]}>
                    <CircularProgress size={14} thickness={5} aria-label={RUNNING_WORDS[row.running]} data-running={row.running} />
                  </Tooltip>
                ) : undefined
              }
            />
          </Box>
        }
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
          { label: "Folders…", icon: <FolderIcon fontSize="small" />, onClick: () => setFoldering(row) },
          { label: "Info", icon: <InfoIcon fontSize="small" />, onClick: () => void openInfo(row) },
          {
            label: "Play",
            icon: <PlayIcon fontSize="small" />,
            onClick: () => navigate(ROUTES.play(row.id)),
            disabled: row.step !== "sheet",
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
    );
  };

  const list = (items: ProjectRow[], label: string) => (
    <Box role="list" aria-label={label}>
      {items.map((row) => (
        <Box role="listitem" key={row.id}>
          {projectRow(row)}
        </Box>
      ))}
    </Box>
  );

  /** **Folders**: the tree as the Finder's list view. */
  const folderList = () =>
    tree.error ? (
      <EmptyState message={tree.error} action={<PillButton onClick={tree.reload}>Try again</PillButton>} />
    ) : (
      <Box role="tree" aria-label="Folders" data-testid="folder-tree">
        {lines.map((line) =>
          line.kind === "folder" ? (
            <Box role="treeitem" aria-expanded={line.open} key={`folder-${line.folder.id}`}>
              <ListRow
                data-testid={`folder-${line.folder.id}`}
                title={line.folder.name}
                indent={line.depth}
                leading={<FolderLeading open={line.open} />}
                onOpen={() => tree.toggle(line.folder.id)}
                status={folderCount(line.count)}
                menu={tree.menu(line.folder)}
                rowProps={tree.folderRowProps(line.folder)}
              />
            </Box>
          ) : (
            <Box role="treeitem" key={`item-${line.from ?? "top"}-${line.item.id}`}>
              {projectRow(line.item, { depth: line.depth, from: line.from })}
            </Box>
          ),
        )}
      </Box>
    );

  return (
    <PageBody>
      <PageHeader title="Projects" actions={newProject} />
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 1, minHeight: 36 }}>
        <ViewPills value={view} onChange={setView} />
        {view === "folders" ? (
          <PillButton kind="quiet" size="small" startIcon={<CreateNewFolderIcon />} onClick={tree.newFolder} data-testid="new-folder">
            New folder
          </PillButton>
        ) : null}
      </Stack>
      {view === "filter" && rows && rows.length > 0 ? (
        <Box sx={{ mb: 1 }}>
          <FilterBar rows={rows} choice={choice} onChange={changeFilter} artistsOf={artistsOf} tagsOf={(row) => row.tags} />
        </Box>
      ) : null}

      {actionError && !renaming && !deleting && !foldering ? (
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
      ) : rows.length === 0 && view !== "folders" ? (
        <EmptyState message="No projects yet" action={newProject} />
      ) : view === "folders" ? (
        <Box sx={{ pt: 1, mb: 4 }}>{folderList()}</Box>
      ) : view === "filter" && shown.length === 0 ? (
        <EmptyState message="No project matches the filter" />
      ) : (
        <Box sx={{ pt: 1, mb: 4 }}>{list(view === "filter" ? shown : rows, "Projects")}</Box>
      )}
      {tree.dialogs}
      {foldering && tree.folders ? (
        <FoldersDialog
          title={`Folders of “${foldering.title || "Untitled project"}”`}
          folders={tree.folders}
          initial={foldering.folders}
          busy={busy}
          error={actionError}
          onCancel={() => {
            setFoldering(null);
            setActionError(null);
          }}
          onSave={(folders) => {
            setBusy(true);
            setActionError(null);
            setFolders(foldering, folders)
              .then(() => setFoldering(null))
              .catch((caught: unknown) => setActionError(message(caught, "The folders could not be saved.")))
              .finally(() => setBusy(false));
          }}
        />
      ) : null}
      {informing ? (
        <InfoDialog
          target={informing}
          onClose={() => setInforming(null)}
          // An edit copy's metadata is its song's: another copy of the same song changes too.
          onSaved={() => setReload((count) => count + 1)}
        />
      ) : null}

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
function NewProjectButton({
  busy,
  onImport,
  onScratch,
}: {
  busy: boolean;
  onImport: (file: File | undefined) => void;
  onScratch: () => void;
}) {
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
        <MenuItem
          onClick={() => {
            close();
            onScratch();
          }}
        >
          <ListItemIcon>
            <EditNoteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="From scratch" secondary="A blank sheet: record or paste" />
        </MenuItem>
        <MenuItem
          onClick={() => {
            close();
            navigate(ROUTES.projectCompose);
          }}
        >
          <ListItemIcon>
            <LibraryAddIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="From other projects" secondary="Passages of your projects and songs" />
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
