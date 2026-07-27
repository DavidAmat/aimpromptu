/** `/matrix` — transcription pipeline, matrix retrieval and operations. */

import type { Granularity, MatrixProcessingStep, PianoMatrixEnvelope } from "../music/types";
import { buildUrl, request } from "./client";

// The contracts live in `src/music/types.ts`, mirroring the backend's
// `schemas/matrix.py`. Re-exported here so callers can import either way.
export type { Granularity, MatrixProcessingStep, PianoMatrixEnvelope };

/** Alias kept for readability at call sites. */
export type MatrixEnvelope = PianoMatrixEnvelope;

export interface TranscribeRequest {
  audioUuid: string;
  tempoBpm: number;
  granularity: Granularity;
  /** Optional restriction to a time range of the source audio, in seconds. */
  startSeconds?: number;
  endSeconds?: number;
  /** Engine name; see `matrixApi.engines()`. Defaults to the backend's default. */
  engine?: string;
  /** Re-transcribe even if a raw matrix already exists. */
  force?: boolean;
}

export interface JobHandle {
  jobId: string;
  status: string;
}

export interface JobStatus {
  jobId: string;
  status: "running" | "done" | "error";
  error?: string | null;
  stage?: string | null;
  fraction?: number | null;
}

export interface MatrixCellEdit {
  frame: number;
  key: number;
  value: -1 | 0 | 1;
}

export interface EditedMatrix {
  envelope: MatrixEnvelope;
  persisted: boolean;
  editCount: number;
}

export const matrixApi = {
  /** Which engines can actually run on this machine. `false` = not installed. */
  engines: (signal?: AbortSignal) => request<Record<string, boolean>>("/matrix/engines", { signal }),

  /** Starts the pipeline in the background; follow `progressUrl(jobId)`. */
  transcribe: (body: TranscribeRequest, signal?: AbortSignal) =>
    request<JobHandle>("/matrix/transcribe", { method: "POST", body, signal }),

  /** SSE endpoint consumed by `useProgress`. */
  progressUrl: (jobId: string) => buildUrl(`/matrix/progress/${jobId}`),

  /** Polling fallback for the same job. */
  job: (jobId: string, signal?: AbortSignal) =>
    request<JobStatus>(`/matrix/jobs/${jobId}`, { signal }),

  /** Steps 3-5 from the stored raw matrix. Synchronous and fast. */
  recompute: (
    body: { audioUuid: string; tempoBpm: number; granularity: Granularity },
    signal?: AbortSignal,
  ) => request<MatrixEnvelope>("/matrix/recompute", { method: "POST", body, signal }),

  get: (
    audioUuid: string,
    options: {
      step?: MatrixProcessingStep;
      granularity?: Granularity;
      tempoBpm?: number;
      sparse?: boolean;
    } = {},
    signal?: AbortSignal,
  ) =>
    request<MatrixEnvelope>(`/matrix/${audioUuid}`, {
      query: {
        step: options.step,
        granularity: options.granularity,
        tempo_bpm: options.tempoBpm,
        sparse: options.sparse,
      },
      signal,
    }),

  transpose: (
    audioUuid: string,
    semitones: number,
    options: { granularity?: Granularity; tempoBpm?: number } = {},
  ) =>
    request<MatrixEnvelope>(`/matrix/${audioUuid}/transpose`, {
      method: "POST",
      query: { semitones, granularity: options.granularity, tempo_bpm: options.tempoBpm },
    }),

  /** Direct URL for a download link — the browser saves the file itself. */
  exportUrl: (
    audioUuid: string,
    options: {
      step?: MatrixProcessingStep;
      granularity?: Granularity;
      tempoBpm?: number;
      sparse?: boolean;
    } = {},
  ) =>
    buildUrl(`/matrix/${audioUuid}/export`, {
      step: options.step,
      granularity: options.granularity,
      tempo_bpm: options.tempoBpm,
      sparse: options.sparse,
    }),

  importJson: (envelope: MatrixEnvelope) =>
    request<ImportedMatrix>("/matrix/import", { method: "POST", body: envelope }),

  /** Preview or persist the complete staged edit list. */
  edit: (
    audioUuid: string,
    body: {
      tempoBpm: number;
      granularity: Granularity;
      edits: MatrixCellEdit[];
      persist?: boolean;
    },
    signal?: AbortSignal,
  ) =>
    request<EditedMatrix>(`/matrix/${audioUuid}/edit`, {
      method: "POST",
      body,
      signal,
    }),
};

/** What an import reports back. */
export interface ImportedMatrix {
  audioUuid: string;
  granularity: Granularity;
  matrixProcessingStep: MatrixProcessingStep;
  frameCount: number;
  /** Cells the validator corrected on the way in. */
  normalizedCells: number;
}
