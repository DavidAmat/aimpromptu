/**
 * `/projects` — the projects of the Personal Vault (implementation 02, plan sections 8.8 and 10.1),
 * the way into and out of the Private Library (Phase 6, sections 10.2 and 10.6), and **From other
 * projects** with the parts of a project (Phase 10, sections 10.4 and 14.1).
 *
 * A project's id is the id of its first part, the uuid the step routes (`/audio`, `/pieces`,
 * `/time`, `/matrix`) take. Mirrors `aitu-backend/src/aitu_backend/api/projects.py`.
 */

import type { PieceStep } from "./pieces";
import type { SavedRhythm } from "./timeScore";
import { buildUrl, request, upload } from "./client";

/** `request`: the copy of a project a request sent (Phase 14), read by its author and the master user. */
export type ProjectLayer = "vault" | "private" | "public" | "request";

/** The song and version a project is, or, for a copy being edited, the one it edits. */
export interface LibraryLink {
  songId: number;
  songTitle: string;
  artists: string[];
  versionId: number;
  versionName: string;
  /** The library project of that version. */
  projectId: string;
}

/** One project, as the Projects page lists it. */
export interface ProjectRow {
  id: string;
  title: string;
  kind: "song" | "integratedPlaylist";
  layer: ProjectLayer;
  /** The user owns it; a library project of another user is one shared with them (Phase 14). */
  mine: boolean;
  /** The lowest step its parts reached; `null` when it could not be worked out. */
  step: PieceStep | null;
  /** A job working on a part right now. */
  running: "transcribing" | "reading" | null;
  /** The ids of the parts, in order. */
  parts: string[];
  /** Where the audio of the first part came from. */
  source: string | null;
  hasVideo: boolean;
  hasNotes: boolean;
  basedOn: string | null;
  createdAt: string;
  updatedAt: string | null;
  /** A project of the Private Library: its song and version. */
  library: LibraryLink | null;
  /** A project of the Personal Vault that edits a version: that version. */
  editing: LibraryLink | null;
}

/** **Save to library**: an existing song by id, or a title and an artist; or `replace` for a copy. */
export interface SaveToLibrary {
  songId?: number;
  song?: string;
  artist?: string;
  /** A song or an artist of the Public Library chosen in the dialog (Phase 13). */
  publicSongId?: number;
  publicArtistId?: number;
  version?: string;
  replace?: boolean;
}

export interface SavedToLibrary {
  songId: number;
  versionId: number;
  projectId: string;
}

export interface DuplicatedProject {
  id: string;
  title: string;
  parts: string[];
}

/** One passage of **From other projects**: a part and a stretch of it, or all of it. */
export interface ChosenPassage {
  part: string;
  fromMs?: number | null;
  toMs?: number | null;
  /** How it joins the passage before it: in the same part, or a new part with a title. */
  join: "sequential" | "subheader";
  subheader?: string | null;
}

/** One part of a project: the title above it and its length. */
export interface PartRow {
  id: string;
  subheader: string | null;
  durationMs: number;
}

export interface PartsAnswer {
  parts: PartRow[];
  /** The part a change left on show: the one joined into, or the new one of a split. */
  part: string | null;
}

export const projectsApi = {
  /** The user's projects, newest change first: the Personal Vault, or the layers asked for. */
  list: (layers: readonly ProjectLayer[] = ["vault"], signal?: AbortSignal) =>
    request<ProjectRow[]>(`/projects?${layers.map((layer) => `layer=${layer}`).join("&")}`, { signal }),

  get: (id: string, signal?: AbortSignal) => request<ProjectRow>(`/projects/${id}`, { signal }),

  /** An empty project. `scratch`: a blank piano sheet, filled by Record and Paste (From scratch). */
  create: (title = "", scratch = false) =>
    request<ProjectRow>("/projects", { method: "POST", body: { title, scratch } }),

  rename: (id: string, title: string) =>
    request<ProjectRow>(`/projects/${id}`, { method: "PATCH", body: { title } }),

  remove: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),

  /** A copy in the user's Personal Vault; the audio is shared, not copied. */
  duplicate: (id: string, title?: string) =>
    request<DuplicatedProject>(`/projects/${id}/duplicate`, { method: "POST", body: { title } }),

  /** The `.aitu` file of a project, for a link the browser downloads. */
  exportUrl: (id: string) => buildUrl(`/projects/${id}/export`),

  /** A `.aitu` file made into a new project of the Personal Vault. */
  import: (file: File) => upload<ProjectRow>("/projects/import", file),

  /** Move the project into the Private Library, as a version of a song (Phase 6). */
  saveToLibrary: (id: string, body: SaveToLibrary) =>
    request<SavedToLibrary>(`/projects/${id}/library`, { method: "POST", body }),

  /** The copy in Projects that edits a version of the library: the one open, or a new one. */
  edit: (id: string) => request<ProjectRow>(`/projects/${id}/edit`, { method: "POST" }),

  /** **From other projects** (Phase 10): a new project made of the passages, in order. */
  compose: (body: { title: string; kind: "song" | "integratedPlaylist"; passages: ChosenPassage[] }) =>
    request<ProjectRow>("/projects/compose", { method: "POST", body }),

  /** The parts of a project in order (the sub-songs of an integrated playlist). */
  parts: (id: string, signal?: AbortSignal) => request<PartsAnswer>(`/projects/${id}/parts`, { signal }),

  reorderParts: (id: string, order: string[]) =>
    request<PartsAnswer>(`/projects/${id}/parts`, { method: "PUT", body: { order } }),

  renamePart: (id: string, part: string, subheader: string | null) =>
    request<PartsAnswer>(`/projects/${id}/parts/${part}`, { method: "PATCH", body: { subheader } }),

  /** The part joined to the one before it, played without a break. */
  joinPart: (id: string, part: string) =>
    request<PartsAnswer>(`/projects/${id}/parts/${part}/join`, { method: "POST" }),

  /** What follows `atMs` becomes a new part after it; the page's sheet is saved with it. */
  splitPart: (id: string, part: string, body: { atMs: number; subheader?: string | null; sheet?: SavedRhythm | null }) =>
    request<PartsAnswer>(`/projects/${id}/parts/${part}/split`, { method: "POST", body }),
};
