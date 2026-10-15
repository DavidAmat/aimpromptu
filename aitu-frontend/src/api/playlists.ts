/**
 * `/playlists` — the songs playlists of the user's Private Library (implementation 02, plan section
 * 14.2, Phase 10). An item is a song, the version chosen for it, and optionally a stretch of it.
 * Mirrors `aitu-backend/src/aitu_backend/api/playlists.py`.
 */

import { request } from "./client";

export interface PlaylistRow {
  id: number;
  title: string;
  songs: number;
  updatedAt: string;
}

export interface PlaylistItem {
  id: number;
  songId: number;
  songTitle: string;
  artists: string[];
  /** The version on show: the chosen one, or the song's first. */
  projectId: string | null;
  versionName: string | null;
  /** The parts of that version; the first is the uuid the step routes take. */
  parts: string[];
  versions: { projectId: string; name: string }[];
  fromMs: number | null;
  toMs: number | null;
}

export interface PlaylistDetail {
  id: number;
  title: string;
  updatedAt: string;
  items: PlaylistItem[];
}

export interface NewPlaylistItem {
  songId: number;
  projectId?: string | null;
  fromMs?: number | null;
  toMs?: number | null;
}

export const playlistsApi = {
  list: (signal?: AbortSignal) => request<PlaylistRow[]>("/playlists", { signal }),

  get: (id: number, signal?: AbortSignal) => request<PlaylistDetail>(`/playlists/${id}`, { signal }),

  /** A new playlist, empty or with songs (**Make a playlist** from a selection). */
  create: (title: string, items: NewPlaylistItem[] = []) =>
    request<PlaylistDetail>("/playlists", { method: "POST", body: { title, items } }),

  rename: (id: number, title: string) =>
    request<PlaylistDetail>(`/playlists/${id}`, { method: "PATCH", body: { title } }),

  reorder: (id: number, order: number[]) =>
    request<PlaylistDetail>(`/playlists/${id}`, { method: "PATCH", body: { order } }),

  remove: (id: number) => request<void>(`/playlists/${id}`, { method: "DELETE" }),

  addItems: (id: number, items: NewPlaylistItem[]) =>
    request<PlaylistDetail>(`/playlists/${id}/items`, { method: "POST", body: { items } }),

  /** Another version of the song, a stretch of it, or (`whole`) all of it again. */
  changeItem: (
    id: number,
    item: number,
    body: { projectId?: string; fromMs?: number; toMs?: number; whole?: boolean },
  ) => request<PlaylistDetail>(`/playlists/${id}/items/${item}`, { method: "PATCH", body }),

  removeItem: (id: number, item: number) =>
    request<PlaylistDetail>(`/playlists/${id}/items/${item}`, { method: "DELETE" }),
};
