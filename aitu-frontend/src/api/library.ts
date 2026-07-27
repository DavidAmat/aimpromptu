/** `/library` — the playground repository and library promotion (Epics 5, 10). */

import type { Granularity, MatrixProcessingStep, PianoMatrixEnvelope } from "../music/types";
import { request } from "./client";

/** One line of a track's version history. Mirrors `VersionHistoryEntry`. */
export interface VersionHistoryEntry {
  /** Folder name, e.g. `v2_gn`. */
  folder: string;
  comment?: string | null;
  createdAt: string;
  parentVersion?: string | null;
  granularity: Granularity;
  matrixProcessingStep: MatrixProcessingStep;
}

/** A playground track. Mirrors `TrackMetadata`. */
export interface PlaygroundTrack {
  artistName: string;
  trackName: string;
  artistSlug: string;
  trackSlug: string;
  createdAt: string;
  updatedAt?: string | null;
  /** Newest last. */
  versions: VersionHistoryEntry[];
}

/** One promoted version. Mirrors `Promotion`. */
export interface Promotion {
  /** Human-facing name, e.g. "Levels (Chill) - Avicii". */
  promotionName: string;
  sourceVersionFolder: string;
  matrixFilename: string;
  promotedAt: string;
  /** Several promotions can be active at once. */
  active: boolean;
}

/** A library track. Mirrors `LibraryTrackMetadata`. */
export interface LibraryTrack {
  artistName: string;
  trackName: string;
  artistSlug: string;
  trackSlug: string;
  tags: string[];
  promotions: Promotion[];
  rollbackTo?: string | null;
  createdAt: string;
  updatedAt?: string | null;
}

export interface SaveVersionRequest {
  artistName: string;
  trackName: string;
  matrix: PianoMatrixEnvelope;
  comment?: string;
  /** Rewrite the existing folder instead of creating a new version. */
  overwrite?: boolean;
  /** Pin the version number — saving the same state at a second granularity. */
  version?: number;
  /** Folder of the version this one was derived from. */
  parentVersion?: string;
  audioUuid?: string;
}

export interface SavedVersion {
  artistSlug: string;
  trackSlug: string;
  folder: string;
  metadata: Record<string, unknown>;
}

/** What the promotion dialog pre-fills itself with. */
export interface PromotionSuggestion {
  suggestedName: string;
  currentPromotions: string[];
}

export interface PromoteRequest {
  artistSlug: string;
  trackSlug: string;
  versionFolder: string;
  /** Defaults to "<Track> - <Artist>". */
  promotionName?: string;
  /** The dialog's "keep the current one too" checkbox. */
  asAdditional?: boolean;
}

export const libraryApi = {
  // ---------------------------------------------------------- playground
  listPlayground: (search?: string, signal?: AbortSignal) =>
    request<PlaygroundTrack[]>("/library/playground", { query: { search }, signal }),

  getPlaygroundTrack: (artistSlug: string, trackSlug: string, signal?: AbortSignal) =>
    request<PlaygroundTrack>(`/library/playground/${artistSlug}/${trackSlug}`, { signal }),

  renamePlaygroundTrack: (
    artistSlug: string,
    trackSlug: string,
    names: { artistName?: string; trackName?: string },
  ) =>
    request<PlaygroundTrack>(`/library/playground/${artistSlug}/${trackSlug}`, {
      method: "PATCH",
      body: names,
    }),

  saveVersion: (body: SaveVersionRequest) =>
    request<SavedVersion>("/library/playground", { method: "POST", body }),

  loadVersion: (artistSlug: string, trackSlug: string, folder: string, signal?: AbortSignal) =>
    request<PianoMatrixEnvelope>(`/library/playground/${artistSlug}/${trackSlug}/${folder}`, {
      signal,
    }),

  deleteVersion: (artistSlug: string, trackSlug: string, folder: string) =>
    request<{ status: string }>(`/library/playground/${artistSlug}/${trackSlug}/${folder}`, {
      method: "DELETE",
    }),

  // ----------------------------------------------------------- promotion
  promotionSuggestion: (artistSlug: string, trackSlug: string, signal?: AbortSignal) =>
    request<PromotionSuggestion>(`/library/promotion-suggestion/${artistSlug}/${trackSlug}`, {
      signal,
    }),

  promote: (body: PromoteRequest) =>
    request<LibraryTrack>("/library/promote", { method: "POST", body }),

  rollback: (artistSlug: string, trackSlug: string) =>
    request<LibraryTrack>("/library/rollback", {
      method: "POST",
      body: { artistSlug, trackSlug },
    }),

  // -------------------------------------------------------------- library
  listTracks: (filters: { tag?: string; search?: string } = {}, signal?: AbortSignal) =>
    request<LibraryTrack[]>("/library/tracks", { query: filters, signal }),

  getTrack: (artistSlug: string, trackSlug: string, signal?: AbortSignal) =>
    request<LibraryTrack>(`/library/tracks/${artistSlug}/${trackSlug}`, { signal }),

  setTags: (artistSlug: string, trackSlug: string, tags: string[]) =>
    request<LibraryTrack>("/library/tags", {
      method: "POST",
      body: { artistSlug, trackSlug, tags },
    }),
};
