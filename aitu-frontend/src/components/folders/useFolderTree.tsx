/**
 * The **Folders** view of My projects and My Library (implementation 04-3, Phase 1, plan sections 4.2 and 4.3): the
 * folders of one tree, which are open, the folder's `⋯` menu and its dialogs, and drag and drop.
 *
 * - **New folder** (next to the pills) makes a folder at the top; the folder's menu has **New folder inside**,
 *   **Rename**, **Move to…**, **New parent folder** (a folder made where this one is, with this one inside it) and
 *   **Delete** (the folder and its folders; the items stay in **All** and in their other folders).
 * - The open folders are kept in the browser, per tree.
 * - A row dragged onto a folder moves into it from the folder it was dragged from (from the top level it is added).
 *   A folder dragged onto another folder moves inside it. The browser sends no click after a drag, so a drag never
 *   opens the row.
 *
 * The page draws the lines (`treeLines`) with its own rows; this hook gives it the props of each one.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode } from "react";
import Typography from "@mui/material/Typography";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolderOutlined";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import DriveFileMoveIcon from "@mui/icons-material/DriveFileMoveOutlined";
import DriveFileRenameIcon from "@mui/icons-material/DriveFileRenameOutline";
import FolderCopyIcon from "@mui/icons-material/FolderCopyOutlined";
import { foldersApi, type FolderArea, type FolderRow } from "../../api";
import { said } from "../../pages/library/shared";
import { TextDialog } from "../../pages/library/TextDialog";
import { ConfirmDialog, type RowMenuItem } from "../../ui";
import { inside, reach, type InFolders } from "./folderTree";
import { MoveFolderDialog } from "./MoveFolderDialog";

type Pending =
  | { kind: "new"; parent: FolderRow | null }
  | { kind: "rename"; folder: FolderRow }
  | { kind: "move"; folder: FolderRow }
  | { kind: "parent"; folder: FolderRow }
  | { kind: "delete"; folder: FolderRow };

type Dragged = { kind: "item"; key: string; from: number | null } | { kind: "folder"; id: number };

function storedOpen(key: string): Set<number> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(key) ?? "[]");
    return new Set(Array.isArray(value) ? value.filter((one): one is number => typeof one === "number") : []);
  } catch {
    return new Set();
  }
}

export interface FolderTree {
  folders: FolderRow[] | null;
  error: string | null;
  open: ReadonlySet<number>;
  toggle: (id: number) => void;
  /** The folder's `⋯` menu. */
  menu: (folder: FolderRow) => RowMenuItem[];
  /** **New folder** at the top. */
  newFolder: () => void;
  /** The dialogs of the menu, to put once on the page. */
  dialogs: ReactNode;
  /** The props of a folder's row: it can be dragged, and items and folders are dropped on it. */
  folderRowProps: (folder: FolderRow) => { draggable: true; "data-drop-over"?: "true" } & DragHandlers;
  /** The props of an item's row, drawn under the folder `from` (`null`: the top level). */
  itemRowProps: (key: string, from: number | null) => { draggable: true } & Pick<DragHandlers, "onDragStart" | "onDragEnd">;
  reload: () => void;
}

interface DragHandlers {
  onDragStart: (event: DragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  onDragOver?: (event: DragEvent<HTMLElement>) => void;
  onDragLeave?: () => void;
  onDrop?: (event: DragEvent<HTMLElement>) => void;
}

export function useFolderTree({
  area,
  items,
  onItemDrop,
  onChanged,
}: {
  area: FolderArea;
  /** The items of the page, for the counts of a deletion. */
  items: readonly InFolders[];
  /** A row dropped on a folder: the page changes the item's folders. */
  onItemDrop: (key: string, from: number | null, to: number) => Promise<void>;
  /** The folders changed in a way that changes the items' rows (a deletion). */
  onChanged: () => void;
}): FolderTree {
  const [folders, setFolders] = useState<FolderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const openKey = `aitu.folders.open.${area}`;
  const [open, setOpen] = useState<Set<number>>(() => storedOpen(openKey));
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const dragged = useRef<Dragged | null>(null);
  const [over, setOver] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    foldersApi
      .list(area, controller.signal)
      .then((found) => {
        setFolders(found);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The folders could not be loaded."));
      });
    return () => controller.abort();
  }, [area, reloads]);

  const reload = useCallback(() => setReloads((count) => count + 1), []);

  const keepOpen = useCallback(
    (next: Set<number>) => {
      setOpen(next);
      try {
        window.localStorage.setItem(openKey, JSON.stringify([...next]));
      } catch {
        // Not kept for the next visit; the folders still open and close.
      }
    },
    [openKey],
  );

  const toggle = useCallback(
    (id: number) => {
      const next = new Set(open);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      keepOpen(next);
    },
    [open, keepOpen],
  );

  const close = () => {
    setPending(null);
    setActionError(null);
  };

  /** One change of the tree; the list is read again after it. */
  const run = async <T,>(change: () => Promise<T>, after?: (result: T) => void) => {
    setBusy(true);
    setActionError(null);
    try {
      const result = await change();
      setPending(null);
      reload();
      after?.(result);
    } catch (caught) {
      setActionError(said(caught, "That did not work."));
    } finally {
      setBusy(false);
    }
  };

  const menu = useCallback(
    (folder: FolderRow): RowMenuItem[] => [
      {
        label: "New folder inside",
        icon: <CreateNewFolderIcon fontSize="small" />,
        onClick: () => setPending({ kind: "new", parent: folder }),
      },
      { label: "Rename", icon: <DriveFileRenameIcon fontSize="small" />, onClick: () => setPending({ kind: "rename", folder }) },
      { label: "Move to…", icon: <DriveFileMoveIcon fontSize="small" />, onClick: () => setPending({ kind: "move", folder }) },
      {
        label: "New parent folder",
        icon: <FolderCopyIcon fontSize="small" />,
        onClick: () => setPending({ kind: "parent", folder }),
      },
      { label: "Delete", icon: <DeleteIcon fontSize="small" />, onClick: () => setPending({ kind: "delete", folder }), danger: true },
    ],
    [],
  );

  const moveFolder = useCallback(
    async (id: number, parentId: number | null) => {
      try {
        await foldersApi.move(id, parentId);
        if (parentId !== null && !open.has(parentId)) keepOpen(new Set([...open, parentId]));
        reload();
      } catch (caught) {
        setError(said(caught, "The folder could not be moved."));
      }
    },
    [open, keepOpen, reload],
  );

  const endDrag = useCallback(() => {
    dragged.current = null;
    setOver(null);
  }, []);

  const folderRowProps = useCallback(
    (folder: FolderRow) => {
      const accepts = () => {
        const now = dragged.current;
        if (!now) return false;
        if (now.kind === "item") return now.from !== folder.id;
        // Not into itself, not into a folder inside it, not where it already is.
        const moving = (folders ?? []).find((one) => one.id === now.id);
        return moving !== undefined && moving.parentId !== folder.id && !inside(folders ?? [], now.id).has(folder.id);
      };
      return {
        draggable: true as const,
        ...(over === folder.id ? { "data-drop-over": "true" as const } : {}),
        onDragStart: (event: DragEvent<HTMLElement>) => {
          dragged.current = { kind: "folder", id: folder.id };
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", `folder:${folder.id}`);
        },
        onDragEnd: endDrag,
        onDragOver: (event: DragEvent<HTMLElement>) => {
          if (!accepts()) return;
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          if (over !== folder.id) setOver(folder.id);
        },
        onDragLeave: () => setOver((current) => (current === folder.id ? null : current)),
        onDrop: (event: DragEvent<HTMLElement>) => {
          event.preventDefault();
          const now = dragged.current;
          const fits = accepts();
          endDrag();
          if (!now || !fits) return;
          if (now.kind === "item") {
            void onItemDrop(now.key, now.from, folder.id).then(() => {
              if (!open.has(folder.id)) keepOpen(new Set([...open, folder.id]));
            });
          } else {
            void moveFolder(now.id, folder.id);
          }
        },
      };
    },
    [folders, over, endDrag, onItemDrop, open, keepOpen, moveFolder],
  );

  const itemRowProps = useCallback(
    (key: string, from: number | null) => ({
      draggable: true as const,
      onDragStart: (event: DragEvent<HTMLElement>) => {
        dragged.current = { kind: "item", key, from };
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", `item:${key}`);
      },
      onDragEnd: endDrag,
    }),
    [endDrag],
  );

  const deleting = pending?.kind === "delete" ? pending.folder : null;
  const deleteReach = useMemo(
    () => (deleting && folders ? reach(folders, items, deleting.id) : null),
    [deleting, folders, items],
  );
  const word = area === "projects" ? "project" : "song";

  const dialogs = (
    <>
      {pending?.kind === "new" ? (
        <TextDialog
          title={pending.parent ? `New folder in “${pending.parent.name}”` : "New folder"}
          label="Name"
          confirmLabel="Make the folder"
          busy={busy}
          error={actionError}
          onCancel={close}
          onConfirm={(name) =>
            void run(
              () => foldersApi.create(area, name, pending.parent?.id ?? null),
              () => {
                if (pending.parent && !open.has(pending.parent.id)) keepOpen(new Set([...open, pending.parent.id]));
              },
            )
          }
        />
      ) : null}
      {pending?.kind === "rename" ? (
        <TextDialog
          title="Rename folder"
          label="Name"
          initial={pending.folder.name}
          confirmLabel="Rename"
          busy={busy}
          error={actionError}
          onCancel={close}
          onConfirm={(name) => void run(() => foldersApi.rename(pending.folder.id, name))}
        />
      ) : null}
      {pending?.kind === "parent" ? (
        <TextDialog
          title={`New parent folder of “${pending.folder.name}”`}
          label="Name"
          confirmLabel="Make the folder"
          busy={busy}
          error={actionError}
          onCancel={close}
          onConfirm={(name) =>
            void run(
              () => foldersApi.newParent(area, name, [pending.folder.id]),
              // Open, so the folder that went inside it stays in sight.
              (made) => keepOpen(new Set([...open, made.id])),
            )
          }
        />
      ) : null}
      {pending?.kind === "move" && folders ? (
        <MoveFolderDialog
          folder={pending.folder}
          folders={folders}
          busy={busy}
          error={actionError}
          onCancel={close}
          onMove={(parentId) => void run(() => foldersApi.move(pending.folder.id, parentId))}
        />
      ) : null}
      <ConfirmDialog
        open={deleting !== null}
        title={`Delete “${deleting?.name ?? ""}”?`}
        message={
          <>
            {deleteReach
              ? [
                  deleteReach.folders > 1 ? `Its ${deleteReach.folders - 1} folder${deleteReach.folders > 2 ? "s" : ""} go too.` : null,
                  deleteReach.items === 0
                    ? `No ${word} is deleted.`
                    : deleteReach.items === 1
                      ? `No ${word} is deleted: the ${word} in it stays in All.`
                      : `No ${word} is deleted: the ${deleteReach.items} ${word}s in it stay in All.`,
                ]
                  .filter(Boolean)
                  .join(" ")
              : null}
            {actionError ? (
              <Typography color="error" sx={{ mt: 1 }}>
                {actionError}
              </Typography>
            ) : null}
          </>
        }
        confirmLabel="Delete folder"
        danger
        busy={busy}
        onConfirm={() => deleting && void run(() => foldersApi.remove(deleting.id), () => onChanged())}
        onCancel={close}
      />
    </>
  );

  return {
    folders,
    error,
    open,
    toggle,
    menu,
    newFolder: () => setPending({ kind: "new", parent: null }),
    dialogs,
    folderRowProps,
    itemRowProps,
    reload,
  };
}
