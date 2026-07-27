/**
 * "Current working artifact" — the piece the Playground tabs share.
 *
 * Switching between Input / Matrix / Piano Roll / Notes Falling / Notation must
 * not lose what you loaded, so the selection lives above the routes. Context and
 * types live in this module (no components) so React Fast Refresh stays happy.
 */

import { createContext } from "react";
import type { Granularity, MatrixProcessingStep } from "../api";

export interface WorkingArtifact {
  /** Backend artifact id once the pipeline has produced one. */
  artifactId?: string;
  /** Source audio in the store, when the piece came from audio. */
  audioUuid?: string;
  /** Display name shown in the Playground header. */
  label?: string;
  tempoBpm: number;
  granularity: Granularity;
  matrixProcessingStep: MatrixProcessingStep;
  /** Optional restriction to a range of the source audio, in seconds. */
  rangeStartSeconds?: number;
  rangeEndSeconds?: number;
}

export const DEFAULT_WORKING_ARTIFACT: WorkingArtifact = {
  tempoBpm: 60,
  granularity: "semicorchea",
  matrixProcessingStep: "clean",
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
