/**
 * "Current working artifact" — the piece the Playground tabs share.
 *
 * Switching between Upload / Input and Rhythm must not lose what you loaded, so
 * the selection lives above the routes. Context and types live in this module
 * (no components) so React Fast Refresh stays happy.
 */

import { createContext } from "react";

export interface WorkingArtifact {
  /** Backend artifact id once the pipeline has produced one. */
  artifactId?: string;
  /** Source audio in the store, when the piece came from audio. */
  audioUuid?: string;
  /** Display name shown in the Playground header. */
  label?: string;
  /**
   * Length of one matrix column, in milliseconds. The one number that decides how finely the piece
   * is measured. It is a choice about the page, never about the music: changing it re-runs from the
   * recorded notes and moves the columns, but no note changes its printed figure.
   */
  frameMs: number;
}

export const DEFAULT_WORKING_ARTIFACT: WorkingArtifact = {
  frameMs: 40,
};

export interface WorkingArtifactContextValue {
  artifact: WorkingArtifact;
  /** Merge a partial update into the current artifact. */
  update: (patch: Partial<WorkingArtifact>) => void;
  /** Replace it wholesale — used when a new piece is loaded. */
  replace: (next: WorkingArtifact) => void;
  clear: () => void;
  /** True once something real is loaded (an artifact or an audio source). */
  hasArtifact: boolean;
}

export const WorkingArtifactContext = createContext<WorkingArtifactContextValue | null>(null);

/** Key used to survive a page reload; the Playground is a long session. */
export const WORKING_ARTIFACT_STORAGE_KEY = "aitu.workingArtifact";
