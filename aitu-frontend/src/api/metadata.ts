/**
 * `/metadata` — the metadata of a song of My Library or of a project of My projects (implementation 04-3, Phase 1,
 * plan section 4.4): rows of a **primary key** (the Public Library's list: films, tv_shows, video_games, adverts)
 * and a **secondary key** of the user's own ("The Lord of the Rings").
 *
 * Mirrors `aitu-backend/src/aitu_backend/api/metadata.py`.
 */

import { request } from "./client";

export interface TagRow {
  /** The primary key: `films`, `tv_shows`, `video_games` or `adverts`. */
  category: string;
  /** The secondary key. */
  value: string;
}

export interface TagSuggestion extends TagRow {
  /** The user's own value; else one of the Public Library. */
  mine: boolean;
}

export interface MetadataKeys {
  categories: string[];
  suggestions: TagSuggestion[];
}

/** What the info button of the sheet page shows. */
export interface SheetInfo {
  /**
   * `project`: a project of My projects with no song; `song`: a song of My Library (one of its versions, an edit
   * copy of one, or a library shared with the user), the same for every version; `public`: the Public Library.
   */
  kind: "project" | "song" | "public" | "none";
  projectId: string;
  songId: number | null;
  title: string;
  artists: string[];
  tags: TagRow[];
  folders: number[];
  editable: boolean;
}

export const metadataApi = {
  keys: (signal?: AbortSignal) => request<MetadataKeys>("/metadata/keys", { signal }),

  info: (projectId: string, signal?: AbortSignal) => request<SheetInfo>(`/metadata/info/${projectId}`, { signal }),

  setOfProject: (projectId: string, tags: TagRow[]) =>
    request<{ tags: TagRow[] }>(`/metadata/projects/${projectId}`, { method: "PUT", body: { tags } }),

  setOfSong: (songId: number, tags: TagRow[]) =>
    request<{ tags: TagRow[] }>(`/metadata/songs/${songId}`, { method: "PUT", body: { tags } }),
};
