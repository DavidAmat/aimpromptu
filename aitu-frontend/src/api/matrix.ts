/**
 * `/matrix` — transcribing an audio, and reading back what the engine heard.
 *
 * This module used to carry the whole tempo-based Playground: fetching a matrix
 * at a chosen BPM and granularity, recomputing one, exporting, importing and
 * editing cells. P4.2 removed that model from the backend, so what is left here
 * is the part that has nothing to do with a grid.
 *
 * Everything that turns the recorded notes into a page lives in `timeScore.ts`.
 */

import { buildUrl, request } from "./client";

/** Body of `POST /matrix/transcribe`. */
export interface TranscribeRequest {
  audioUuid: string;
  /**
   * Length of one column, in milliseconds. The only timing input, and it is a
   * choice about the page rather than about the music: the same audio at 20 ms
   * and at 40 ms is the same playing on a finer or a coarser grid.
   */
  frameMs?: number;
  startSeconds?: number;
  endSeconds?: number;
  engine?: string;
  /** Run the model again even when this audio was already transcribed. */
  force?: boolean;
}

export interface JobHandle {
  jobId: string;
  status: string;
}

export interface JobStatus {
  jobId: string;
  status: string;
  error: string | null;
  stage: string | null;
  fraction: number | null;
}

/** One note exactly as the engine emitted it: seconds, not columns. */
export interface RawNoteEvent {
  midiNote: number;
  start: number;
  end: number;
  velocity: number;
  /** Discarded as too short to have been played — flagged, not omitted. */
  artifact: boolean;
  /** 12 or 24 when a note that far above was struck alongside it. */
  octaveBelow: number | null;
}

/** `GET /matrix/{id}/events` — the transcription before any grid touched it. */
export interface RawEvents {
  audioUuid: string;
  durationSeconds: number;
  title: string | null;
  /** How many of `events` carry `artifact: true`. */
  artifactCount: number;
  /** Of those, how many sit exactly an octave or two under a struck note. */
  octavePhantomCount: number;
  events: RawNoteEvent[];
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

  /** The stored transcription in seconds, served verbatim. */
  events: (audioUuid: string, signal?: AbortSignal) =>
    request<RawEvents>(`/matrix/${audioUuid}/events`, { signal }),
};

export default matrixApi;
