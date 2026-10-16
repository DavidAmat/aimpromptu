/**
 * `/requests` and `/admin/requests` — requests to the Public Library and their review
 * (implementation 02, Phase 14, plan section 16).
 *
 * A request has a kind and is made of items, one per proposed change, each with its own decision,
 * so the master user can accept part of it. The author sends one, sends it again when changes are
 * asked, or withdraws it; the master user decides it. Mirrors
 * `aitu-backend/src/aitu_backend/api/requests.py` and the review routes of `api/admin.py`.
 */

import { request } from "./client";

export type RequestKind = "userVersion" | "metadata" | "fixedVersion" | "playlist";
export type RequestStatus = "open" | "changesAsked" | "accepted" | "partlyAccepted" | "refused" | "withdrawn";
export type ItemKind = "newArtist" | "newSong" | "metadata" | "project" | "versionPointer" | "playlist";
export type ItemDecisionValue = "accepted" | "refused" | "changesAsked";

export interface RequestSummary {
  id: number;
  kind: RequestKind;
  status: RequestStatus;
  author: string;
  /** The song, artist or playlist it is about. */
  title: string;
  /** What it asks, in a few words: the version name, "new song", "changes", "easy as hard". */
  subject: string;
  createdAt: string;
  updatedAt: string;
  decidedAt: string | null;
  /** Items waiting for a decision, and in all. */
  waiting: number;
  items: number;
}

/** One side of a project item: the Public Library's version now, or the proposal. */
export interface ProjectSide {
  projectId: string;
  parts: string[];
  creator: string;
  name: string;
  /** False once the project is no longer kept. */
  kept: boolean;
}

/** An artist of a song in a request: a public one, or a new one proposed by name. */
export interface ArtistInRequest {
  publicId?: number;
  ref?: string;
  name: string;
  isNew: boolean;
}

/** The fields of a song in a request: a new song, or a public song before and after. */
export interface SongState {
  title: string;
  year: number | null;
  artists: ArtistInRequest[];
  genres: string[];
  regions: string[];
  regionNames?: string[];
  /** `[category, value]`. */
  tags: [string, string][];
}

/** What an accepted item made. */
export interface Made {
  artistId?: number;
  songId?: number;
  projectId?: string;
  playlistId?: number;
}

export interface RequestItem {
  id: number;
  kind: ItemKind;
  decision: ItemDecisionValue | null;
  comment: string | null;
  /** Its proposal, with names: see the item kinds in `library/requests.py`. */
  payload: Record<string, unknown> & { made?: Made };
  compare: { current: ProjectSide | null; proposed: ProjectSide | null } | null;
}

export interface RequestComment {
  author: string;
  body: string;
  createdAt: string;
}

export interface RequestDetail extends RequestSummary {
  /** The viewer is its author. */
  mine: boolean;
  itemList: RequestItem[];
  comments: RequestComment[];
  /** The proposal as it would be sent again. */
  proposal: Proposal;
}

export interface ArtistRef {
  publicId?: number;
  newName?: string;
  privateId?: number;
}

export interface SongFields {
  title: string;
  year?: number | null;
  artists: ArtistRef[];
  genres?: string[];
  regions?: string[];
  tags?: { category: string; value: string }[];
}

/** What the author asks for: the body that sends a request and sends it again. */
export interface Proposal {
  kind: RequestKind;
  note?: string | null;
  /** userVersion: a version of My library, as `versionName` of `song`. */
  version?: number | null;
  versionName?: string | null;
  song?: { publicId?: number | null; new?: SongFields | null; privateId?: number | null } | null;
  /** metadata: `song.publicId` with `changes`; `song.new`; or `artist`. */
  changes?: SongFields | null;
  artist?: { publicId?: number | null; name?: string | null; addNames?: string[] } | null;
  /** fixedVersion: the author's user version (its public project) as `name`. */
  userVersion?: string | null;
  name?: string | null;
  /** playlist: a songs playlist of My library, as `title`. */
  playlist?: number | null;
  title?: string | null;
}

export interface PublishInfo {
  versionId: number;
  versionName: string;
  /** The simple form of the version name: lowercase letters, digits and hyphens. */
  suggestedName: string;
  ready: boolean;
  songId: number;
  songTitle: string;
  artists: { privateId: number; name: string; publicId: number | null; publicName: string | null }[];
  publicSongId: number | null;
  publicSongTitle: string | null;
  /** The user's own versions of that public song: a request of the same name replaces one. */
  ownVersions: string[];
  waitingRequest: number | null;
}

export interface PlaylistInfo {
  title: string;
  items: { songId: number; projectId: string; title: string; versionName: string | null }[];
  /** The songs left out: not in the Public Library with a public version. */
  left: string[];
}

export interface ItemDecision {
  id: number;
  decision: ItemDecisionValue;
  comment?: string;
  /** The master user's change on accepting: `name`, `title`, `year`, `versionName`. */
  changes?: Record<string, string | number | null>;
}

export const requestsApi = {
  mine: (signal?: AbortSignal) => request<RequestSummary[]>("/requests", { signal }),
  counts: (signal?: AbortSignal) => request<{ mine: number; review: number }>("/requests/counts", { signal }),
  one: (id: number, signal?: AbortSignal) => request<RequestDetail>(`/requests/${id}`, { signal }),
  publishInfo: (version: number, signal?: AbortSignal) =>
    request<PublishInfo>("/requests/publish-info", { query: { version }, signal }),
  playlistInfo: (playlist: number, signal?: AbortSignal) =>
    request<PlaylistInfo>("/requests/playlist-info", { query: { playlist }, signal }),
  send: (proposal: Proposal) => request<{ id: number }>("/requests", { method: "POST", body: proposal }),
  sendAgain: (id: number, proposal: Proposal) =>
    request<RequestDetail>(`/requests/${id}`, { method: "PUT", body: proposal }),
  withdraw: (id: number) => request<RequestDetail>(`/requests/${id}/withdraw`, { method: "POST" }),

  /** The master user: the open requests, oldest first; or every request. */
  review: (everything: boolean, signal?: AbortSignal) =>
    request<RequestSummary[]>("/admin/requests", { query: { everything: everything || undefined }, signal }),
  decide: (id: number, items: ItemDecision[], comment?: string) =>
    request<RequestDetail>(`/admin/requests/${id}/decision`, { method: "POST", body: { items, comment } }),
};
