/**
 * `/folders` — the folders of My projects and of My Library (implementation 04-3, Phase 1, plan section 4.2).
 *
 * Two independent trees: `projects` (My projects) and `library` (My Library). A folder has its own id and the id of
 * its parent folder (`null` at the top); a project or a song points at folder ids (`ProjectRow.folders`,
 * `SongRow.folders`), so moving a folder or making a parent folder on top of it changes nothing in the items.
 * Mirrors `aitu-backend/src/aitu_backend/api/folders.py`.
 */

import { request } from "./client";

export type FolderArea = "projects" | "library";

export interface FolderRow {
  id: number;
  /** `null` at the top of the tree. */
  parentId: number | null;
  name: string;
  createdAt: string;
}

export const foldersApi = {
  list: (area: FolderArea, signal?: AbortSignal) => request<FolderRow[]>("/folders", { query: { area }, signal }),

  /** **New folder**, at the top or inside `parentId`. */
  create: (area: FolderArea, name: string, parentId: number | null = null) =>
    request<FolderRow>("/folders", { method: "POST", body: { area, name, parentId } }),

  rename: (id: number, name: string) => request<FolderRow>(`/folders/${id}`, { method: "PATCH", body: { name } }),

  /** **Move to…**: inside another folder, or to the top (`null`). */
  move: (id: number, parentId: number | null) =>
    request<FolderRow>(`/folders/${id}/move`, { method: "POST", body: { parentId } }),

  /** **New parent folder** on top of folders that share a parent. */
  newParent: (area: FolderArea, name: string, children: number[]) =>
    request<FolderRow>("/folders/parent", { method: "POST", body: { area, name, children } }),

  /** The folder and the folders inside it; never a project or a song. */
  remove: (id: number) => request<void>(`/folders/${id}`, { method: "DELETE" }),

  /** Every folder of a project of My projects. */
  setOfProject: (projectId: string, folders: number[]) =>
    request<{ folders: number[] }>(`/folders/projects/${projectId}`, { method: "PUT", body: { folders } }),

  /** Every folder of a song of My Library. */
  setOfSong: (songId: number, folders: number[]) =>
    request<{ folders: number[] }>(`/folders/songs/${songId}`, { method: "PUT", body: { folders } }),
};
