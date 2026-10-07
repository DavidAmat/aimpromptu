/**
 * `/projects` — the projects of the Personal Vault (implementation 02, plan sections 8.8 and 10.1),
 * and the way into and out of the Private Library (Phase 6, sections 10.2 and 10.6).
 *
 * A project's id is the id of its first part, the uuid the step routes (`/audio`, `/pieces`,
 * `/time`, `/matrix`) take. Mirrors `aitu-backend/src/aitu_backend/api/projects.py`.
 */

import type { PieceStep } from "./pieces";
import { buildUrl, request, upload } from "./client";

export type ProjectLayer = "vault" | "private";

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

export const projectsApi = {
  /** The user's projects, newest change first: the Personal Vault, or the layers asked for. */
  list: (layers: readonly ProjectLayer[] = ["vault"], signal?: AbortSignal) =>
    request<ProjectRow[]>(`/projects?${layers.map((layer) => `layer=${layer}`).join("&")}`, { signal }),

  get: (id: string, signal?: AbortSignal) => request<ProjectRow>(`/projects/${id}`, { signal }),

  /** An empty project: no audio, no notes (From scratch). */
  create: (title = "") => request<ProjectRow>("/projects", { method: "POST", body: { title } }),

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
};
