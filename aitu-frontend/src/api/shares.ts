/**
 * `/shares` and `/shared` — sharing a Private Library (implementation 02, Phase 14, plan section
 * 15.4). The owner shares their whole library, read only, with the users they choose; the other
 * user sees it under **My library → Shared**, plays it, copies from it and adds its songs to their
 * own library. Mirrors `aitu-backend/src/aitu_backend/api/shares.py`.
 */

import { request } from "./client";

export interface Person {
  id: number;
  username: string;
  /** For a library shared with the user: its songs. */
  songs: number;
}

export interface Shares {
  /** The other users, to choose from. */
  people: Person[];
  /** The ones the user shares their library with. */
  sharedWith: number[];
  /** The users who share their library with this user. */
  sharedWithMe: Person[];
}

export interface SharedLibrary {
  owner: string;
  songs: { id: number; title: string; artists: string[]; versions: number }[];
}

export interface SharedSong {
  id: number;
  title: string;
  artists: string[];
  ownerId: number;
  owner: string;
  versions: { id: number; name: string; projectId: string; parts: string[]; inLibrary: string | null }[];
  /** The user's own song a version of it was added to. */
  inLibrary: number | null;
}

export const sharesApi = {
  list: (signal?: AbortSignal) => request<Shares>("/shares", { signal }),
  share: (userId: number) => request<Shares>(`/shares/${userId}`, { method: "PUT" }),
  stop: (userId: number) => request<Shares>(`/shares/${userId}`, { method: "DELETE" }),
  library: (ownerId: number, signal?: AbortSignal) => request<SharedLibrary>(`/shared/${ownerId}/songs`, { signal }),
  song: (id: number, signal?: AbortSignal) => request<SharedSong>(`/shared/songs/${id}`, { signal }),
  /** **Add to my library**: the chosen versions, or every version of the song. */
  pull: (id: number, versions: number[] = []) =>
    request<{ songId: number; versions: number; already: number }>(`/shared/songs/${id}/pull`, {
      method: "POST",
      body: { versions },
    }),
};
