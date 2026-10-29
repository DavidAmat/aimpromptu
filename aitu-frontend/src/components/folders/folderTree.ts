/**
 * The tree of folders, worked out on the page from the flat list of `GET /folders` and the folder ids each item
 * carries (implementation 04-3, Phase 1, plan section 4.2). A folder knows only its parent's id, so the path of a
 * folder and what is inside it are computed here, never stored.
 */

import type { FolderRow } from "../../api";

/** What the tree needs of an item (a project, a song): the folders it is in. */
export interface InFolders {
  folders: number[];
}

const byName = (a: FolderRow, b: FolderRow) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) || a.id - b.id;

/** `parent id (null: the top) -> its folders, by name`. */
export function childrenOf(folders: readonly FolderRow[]): Map<number | null, FolderRow[]> {
  const out = new Map<number | null, FolderRow[]>();
  for (const folder of folders) {
    const list = out.get(folder.parentId) ?? [];
    list.push(folder);
    out.set(folder.parentId, list);
  }
  for (const list of out.values()) list.sort(byName);
  return out;
}

/** The folder and every folder inside it, at any depth. */
export function inside(folders: readonly FolderRow[], id: number): Set<number> {
  const children = childrenOf(folders);
  const found = new Set<number>();
  const waiting = [id];
  while (waiting.length > 0) {
    const current = waiting.pop() as number;
    if (found.has(current)) continue;
    found.add(current);
    for (const child of children.get(current) ?? []) waiting.push(child.id);
  }
  return found;
}

/** "Work / Films / The Lord of the Rings". */
export function pathOf(folders: readonly FolderRow[], id: number): string {
  const byId = new Map(folders.map((folder) => [folder.id, folder]));
  const names: string[] = [];
  let current = byId.get(id);
  while (current && names.length <= folders.length) {
    names.unshift(current.name);
    current = current.parentId === null ? undefined : byId.get(current.parentId);
  }
  return names.join(" / ");
}

/** What deleting a folder touches: the folders that go (itself included) and the items that leave them. */
export function reach(folders: readonly FolderRow[], items: readonly InFolders[], id: number) {
  const going = inside(folders, id);
  return {
    folders: going.size,
    items: items.filter((item) => item.folders.some((folder) => going.has(folder))).length,
  };
}

export type TreeLine<T> =
  | { kind: "folder"; folder: FolderRow; depth: number; open: boolean; count: number }
  /** `from`: the folder the item is listed under (`null`: the top level, in no folder). */
  | { kind: "item"; item: T; depth: number; from: number | null };

/**
 * The lines the **Folders** view draws, as the Finder's list view: the folders of the top level by name, each open
 * one followed by its folders and its items, one step deeper; then the items that are in no folder. An item in two
 * folders is drawn under each.
 */
export function treeLines<T extends InFolders>(
  folders: readonly FolderRow[],
  items: readonly T[],
  open: ReadonlySet<number>,
  order: (a: T, b: T) => number,
): TreeLine<T>[] {
  const children = childrenOf(folders);
  const known = new Set(folders.map((folder) => folder.id));
  const itemsIn = new Map<number, T[]>();
  for (const item of items) {
    for (const folder of item.folders) {
      if (!known.has(folder)) continue;
      const list = itemsIn.get(folder) ?? [];
      list.push(item);
      itemsIn.set(folder, list);
    }
  }
  const out: TreeLine<T>[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const folder of children.get(parent) ?? []) {
      const mine = itemsIn.get(folder.id) ?? [];
      const isOpen = open.has(folder.id);
      out.push({ kind: "folder", folder, depth, open: isOpen, count: mine.length + (children.get(folder.id)?.length ?? 0) });
      if (!isOpen) continue;
      walk(folder.id, depth + 1);
      for (const item of [...mine].sort(order)) out.push({ kind: "item", item, depth: depth + 1, from: folder.id });
    }
  };
  walk(null, 0);
  const loose = items.filter((item) => !item.folders.some((folder) => known.has(folder)));
  for (const item of [...loose].sort(order)) out.push({ kind: "item", item, depth: 0, from: null });
  return out;
}

/** "3 items", "1 item", "Empty": what a folder row says in its status column. */
export const folderCount = (count: number) => (count === 0 ? "Empty" : count === 1 ? "1 item" : `${count} items`);
