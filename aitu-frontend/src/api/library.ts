/**
 * `/library` — the user's Private Library (implementation 02, Phase 6, plan sections 15.1 and
 * 15.2): songs with their versions, artists with their names, and the history of a version.
 *
 * A project goes into the library with `projectsApi.saveToLibrary` and comes out of it, as a copy
 * to edit, with `projectsApi.edit`. Mirrors `aitu-backend/src/aitu_backend/api/library.py`.
 */

import type { PieceStep } from "./pieces";
import { request } from "./client";

/** One artist of a song, by the name the song uses. */
export interface Credit {
  artistId: number;
  nameId: number;
  name: string;
}

export interface SongRow {
  id: number;
  title: string;
  artists: Credit[];
  versions: number;
  /** A version of the song is being edited in Projects. */
  editing: boolean;
  updatedAt: string | null;
}

export interface VersionRow {
  id: number;
  name: string;
  projectId: string;
  /** The parts of the project; the first is the id the step pages take. */
  parts: string[];
  step: PieceStep | null;
  createdAt: string;
  updatedAt: string | null;
  /** The project in Projects that edits this version, if one is open. */
  editCopy: string | null;
  /** How many earlier states the version keeps. */
  history: number;
}

export interface SongDetail {
  id: number;
  title: string;
  artists: Credit[];
  versions: VersionRow[];
}

export interface ArtistNameRow {
  id: number;
  name: string;
  isDefault: boolean;
}

export interface ArtistRow {
  id: number;
  /** The default name. */
  name: string;
  names: ArtistNameRow[];
  songs: number;
}

export interface ArtistDetail extends ArtistRow {
  songList: { id: number; title: string; versions: number }[];
}

/** An earlier state of a version. */
export interface EarlierState {
  number: number;
  savedAt: string;
  reason: string;
}

export const libraryApi = {
  songs: (signal?: AbortSignal) => request<SongRow[]>("/library/songs", { signal }),
  song: (id: number, signal?: AbortSignal) => request<SongDetail>(`/library/songs/${id}`, { signal }),
  /** Rename a song, or give it its artists by name (a new name makes a new artist). */
  changeSong: (id: number, change: { title?: string; artists?: string[] }) =>
    request<SongDetail>(`/library/songs/${id}`, { method: "PATCH", body: change }),
  deleteSong: (id: number) => request<void>(`/library/songs/${id}`, { method: "DELETE" }),

  renameVersion: (id: number, name: string) =>
    request<SongDetail>(`/library/versions/${id}`, { method: "PATCH", body: { name } }),
  deleteVersion: (id: number) => request<void>(`/library/versions/${id}`, { method: "DELETE" }),
  history: (id: number, signal?: AbortSignal) =>
    request<EarlierState[]>(`/library/versions/${id}/history`, { signal }),
  /** Make an earlier state the version again; the state it replaces goes to the history. */
  restore: (id: number, number: number) =>
    request<SongDetail>(`/library/versions/${id}/history/${number}/restore`, { method: "POST" }),

  artists: (signal?: AbortSignal) => request<ArtistRow[]>("/library/artists", { signal }),
  artist: (id: number, signal?: AbortSignal) => request<ArtistDetail>(`/library/artists/${id}`, { signal }),
  addName: (id: number, name: string) =>
    request<ArtistDetail>(`/library/artists/${id}/names`, { method: "POST", body: { name } }),
  changeName: (id: number, nameId: number, change: { name?: string; isDefault?: boolean }) =>
    request<ArtistDetail>(`/library/artists/${id}/names/${nameId}`, { method: "PATCH", body: change }),
  removeName: (id: number, nameId: number) =>
    request<ArtistDetail>(`/library/artists/${id}/names/${nameId}`, { method: "DELETE" }),
  /** Every name of `id` becomes a name of `into`, which keeps its default name. */
  merge: (id: number, into: number) =>
    request<ArtistDetail>(`/library/artists/${id}/merge`, { method: "POST", body: { into } }),
  deleteArtist: (id: number) => request<void>(`/library/artists/${id}`, { method: "DELETE" }),
};
