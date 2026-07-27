/** `/audio` — the audio working store (Epic 3, Stories 3.1 and 3.2). */

import { buildUrl, request, upload } from "./client";

export type AudioSource = "upload" | "recording" | "youtube";

/** Mirror of `AudioMetadata` in `schemas/metadata.py`. */
export interface AudioItem {
  uuid: string;
  /** Editable display name; defaults to the uploaded file's stem. */
  alias: string;
  source: AudioSource;
  /** Container/codec suffix without the dot, e.g. "mp3". */
  format: string;
  originalFilename?: string | null;
  durationSeconds?: number | null;
  sampleRate?: number | null;
  /** Present when `source` is "youtube". */
  sourceUrl?: string | null;
  createdAt: string;
}

/** Min/max peak pairs, one per bucket — computed backend-side. */
export interface WaveformPeaks {
  points: number;
  min: number[];
  max: number[];
  durationSeconds: number;
  sampleRate: number;
}

/**
 * Suffixes the upload endpoint accepts; anything else is a 422.
 * `.webm`/`.ogg` are here for browser recordings — ffmpeg converts them
 * server-side, so Chrome (which records only webm/opus) works too.
 */
export const SUPPORTED_AUDIO_SUFFIXES = [
  ".mp3",
  ".aac",
  ".m4a",
  ".wav",
  ".webm",
  ".ogg",
] as const;

export const audioApi = {
  list: (signal?: AbortSignal) => request<AudioItem[]>("/audio/", { signal }),

  get: (uuid: string, signal?: AbortSignal) => request<AudioItem>(`/audio/${uuid}`, { signal }),

  rename: (uuid: string, alias: string) =>
    request<AudioItem>(`/audio/${uuid}`, { method: "PATCH", body: { alias } }),

  remove: (uuid: string) => request<{ status: string }>(`/audio/${uuid}`, { method: "DELETE" }),

  upload: (file: File, alias?: string) =>
    upload<AudioItem>("/audio/upload", file, alias ? { alias } : {}),

  storeRecording: (file: File, alias?: string) =>
    upload<AudioItem>("/audio/recording", file, alias ? { alias } : {}),

  waveform: (uuid: string, points = 1000, signal?: AbortSignal) =>
    request<WaveformPeaks>(`/audio/${uuid}/waveform`, { query: { points }, signal }),

  /** Direct URL for an `<audio>` element — no fetch needed. */
  fileUrl: (uuid: string, normalized = false) =>
    buildUrl(`/audio/${uuid}/file`, normalized ? { normalized: true } : undefined),
};
