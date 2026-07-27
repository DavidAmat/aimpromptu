/** `/notation` — the backend-built, VexFlow-ready score document (Epic 9). */

import { request } from "./client";

/** Shape firmed up by Task 9.1; kept open until then. */
export interface ScoreDocument {
  artifactId: string;
  tempoBpm: number;
  keySignature?: string;
  [key: string]: unknown;
}

export interface AnnotationOverlay {
  lyrics?: Record<string, string>;
  fingers?: Record<string, number>;
  [key: string]: unknown;
}

export const notationApi = {
  get: (artifactId: string, signal?: AbortSignal) =>
    request<ScoreDocument>(`/notation/${artifactId}`, { signal }),

  saveAnnotations: (artifactId: string, overlay: AnnotationOverlay) =>
    request<ScoreDocument>(`/notation/${artifactId}/annotations`, {
      method: "POST",
      body: overlay,
    }),

  previewRange: (artifactId: string, body: { fromColumn: number; toColumn: number }) =>
    request<ScoreDocument>(`/notation/${artifactId}/preview`, { method: "POST", body }),
};
