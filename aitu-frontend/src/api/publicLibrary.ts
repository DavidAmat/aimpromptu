/**
 * `/public` — the Public Library (implementation 02, Phase 13, plan sections 15.1 to 15.3 and
 * 15.6): its songs with search, filters and sort (one page at a time), one song with its metadata
 * and versions, its artists, its playlists, likes, the suggestions of **Save to library** and
 * **Search**, and **Add to my library**.
 *
 * Mirrors `aitu-backend/src/aitu_backend/api/public.py`.
 */

import { request } from "./client";

export interface PublicCredit {
  artistId: number;
  name: string;
}

export interface PublicSongRow {
  id: number;
  title: string;
  artists: PublicCredit[];
  year: number | null;
  /** 0 to 100: all time, or in the decade the list is filtered by. */
  popularity: number;
  versions: number;
}

export interface FacetValue {
  /** What the filter takes: a decade's first year ("1980"), a region's code, a genre's or tag's id. */
  value: string;
  label: string;
  count: number;
  /** A tag's category ("films"). */
  group: string | null;
}

export interface Facets {
  decades: FacetValue[];
  regions: FacetValue[];
  genres: FacetValue[];
  tags: FacetValue[];
}

export interface PublicSongPage {
  total: number;
  rows: PublicSongRow[];
  facets: Facets;
}

export type SongSort = "popularity" | "year" | "title";
export type ArtistSort = "popularity" | "name" | "songs";
export type SortDirection = "asc" | "desc";

export interface SongQuery {
  q?: string;
  decade?: number;
  region?: string;
  genre?: number;
  tag?: number;
  sort?: SongSort;
  dir?: SortDirection;
  offset?: number;
  limit?: number;
}

export interface PublicVersion {
  projectId: string;
  /** The parts of the project; the first is the id Play mode takes. */
  parts: string[];
  /** `hard`, `medium`, `easy` or a custom name; a user version's own name. */
  name: string;
  creator: string | null;
  likes: number;
  liked: boolean;
  createdAt: string | null;
  ready: boolean;
  /** The user's library copy of it, if pulled. */
  inLibrary: string | null;
}

export interface PublicUserVersions {
  username: string;
  versions: PublicVersion[];
}

export interface PublicChart {
  name: string;
  best: number;
  weeks: number;
  first: string;
  last: string;
  /** `[week, rank]`, oldest first. */
  history: [string, number][];
}

export interface PublicSongDetail {
  id: number;
  title: string;
  year: number | null;
  decade: string | null;
  popularity: number;
  artists: PublicCredit[];
  albums: { id: number; title: string; year: number | null; track: number | null }[];
  genres: string[];
  regions: string[];
  /** `[category, value]`. */
  tags: [string, string][];
  charts: PublicChart[];
  hasLyrics: boolean;
  /** The fixed version Default points at. */
  defaultVersion: string;
  fixed: PublicVersion[];
  others: PublicUserVersions[];
  /** The user's own song for it (pulled, or saved on it). */
  inLibrary: number | null;
}

export interface PublicArtistRow {
  id: number;
  name: string;
  otherNames: string[];
  songs: number;
  /** Its most popular song's. */
  popularity: number;
  /** Songs that have a version. */
  withVersions: number;
}

export interface PublicArtistDetail {
  id: number;
  name: string;
  otherNames: string[];
  songs: { id: number; title: string; year: number | null; popularity: number; versions: number }[];
  albums: { id: number; title: string; year: number | null; popularity: number }[];
  withVersions: number;
  inLibrary: number | null;
}

export interface PublicPlaylistRow {
  id: number;
  title: string;
  songs: number;
  updatedAt: string;
}

export interface PublicPlaylistItem {
  id: number;
  songId: number | null;
  songTitle: string;
  artists: string[];
  projectId: string | null;
  parts: string[];
  versionName: string | null;
  fromMs: number | null;
  toMs: number | null;
}

export interface PublicPlaylistDetail extends PublicPlaylistRow {
  items: PublicPlaylistItem[];
}

export interface Suggestions {
  songs: PublicSongRow[];
  artists: PublicArtistRow[];
}

export interface Pulled {
  /** The song, artist or playlist of My library. */
  id: number;
  songs: number;
  versions: number;
  already: number;
}

/** The fixed lists a song's metadata takes its values from (section 15.3; Phase 14). */
export interface PublicLists {
  genres: string[];
  regions: { code: string; name: string }[];
  tagCategories: string[];
}

export const publicApi = {
  lists: (signal?: AbortSignal) => request<PublicLists>("/public/lists", { signal }),
  songs: (query: SongQuery, signal?: AbortSignal) =>
    request<PublicSongPage>("/public/songs", { query: { ...query }, signal }),
  song: (id: number, signal?: AbortSignal) => request<PublicSongDetail>(`/public/songs/${id}`, { signal }),
  lyrics: (id: number, signal?: AbortSignal) =>
    request<{ text: string }>(`/public/songs/${id}/lyrics`, { signal }),
  /** **Add to my library**: the chosen versions, or the song's default one. */
  pullSong: (id: number, projects: string[] = []) =>
    request<Pulled>(`/public/songs/${id}/pull`, { method: "POST", body: { projects } }),
  artists: (
    query: { q?: string; sort?: ArtistSort; dir?: SortDirection; offset?: number; limit?: number },
    signal?: AbortSignal,
  ) => request<{ total: number; rows: PublicArtistRow[] }>("/public/artists", { query: { ...query }, signal }),
  artist: (id: number, signal?: AbortSignal) => request<PublicArtistDetail>(`/public/artists/${id}`, { signal }),
  pullArtist: (id: number) => request<Pulled>(`/public/artists/${id}/pull`, { method: "POST" }),
  playlists: (signal?: AbortSignal) => request<PublicPlaylistRow[]>("/public/playlists", { signal }),
  playlist: (id: number, signal?: AbortSignal) =>
    request<PublicPlaylistDetail>(`/public/playlists/${id}`, { signal }),
  pullPlaylist: (id: number) => request<Pulled>(`/public/playlists/${id}/pull`, { method: "POST" }),
  like: (projectId: string) =>
    request<{ likes: number; liked: boolean }>(`/public/likes/${projectId}`, { method: "PUT" }),
  unlike: (projectId: string) =>
    request<{ likes: number; liked: boolean }>(`/public/likes/${projectId}`, { method: "DELETE" }),
  suggest: (q: string, options: { artist?: string; limit?: number } = {}, signal?: AbortSignal) =>
    request<Suggestions>("/public/suggest", { query: { q, artist: options.artist, limit: options.limit }, signal }),
};
