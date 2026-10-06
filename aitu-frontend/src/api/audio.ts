/** `/audio` — the audio working store (Epic 3, Stories 3.1 and 3.2). */

import { buildUrl, request, upload } from "./client";

export type AudioSource =
  | "upload"
  | "recording"
  | "youtube"
  | "segment"
  /** Started empty and built passage by passage on the Compose tab (Epic 13). */
  | "composed";

export interface AudioTimeRange {
  startSeconds: number;
  endSeconds: number;
}

/** Mirror of `AudioMetadata` in `schemas/metadata.py`. */
export interface AudioItem {
  uuid: string;
  /** Editable display name; defaults to the uploaded file's stem. */
  alias: string;
  source: AudioSource;
  /** Container/codec suffix without the dot, e.g. "mp3". */
  format: string;
  originalFilename?: string | null;
  /** The length of the piece: the original minus its saved cuts. */
  durationSeconds?: number | null;
  /** The length of the untouched original. */
  originalDurationSeconds?: number | null;
  sampleRate?: number | null;
  /** Present when `source` is "youtube". */
  sourceUrl?: string | null;
  /** Root audio and absolute root times when this is a physical segment. */
  sourceAudioUuid?: string | null;
  sourceTimeRange?: AudioTimeRange | null;
  /**
   * The column length a composed piece is meant to be read at, chosen when it was
   * created because there was no recording to infer anything from. Still only a
   * view: any request may ask for a different one.
   */
  frameMs?: number | null;
  createdAt: string;
  /** When the piece last changed (the newest file of its folder); `null` when it cannot be read. */
  updatedAt?: string | null;
  /** True once the engine has run and the recorded notes are on disk. */
  hasNotes?: boolean;
  /**
   * Why this piece cannot be drawn, in words meant to be shown as they are.
   * Set by the migration for a piece with no recorded notes behind it; `null`
   * for every piece that is fine.
   */
  needsRederivation?: string | null;
  /** The project has a video: its Audio step is the Video step. */
  hasVideo?: boolean;
}

/** Min/max peak pairs, one per bucket — computed backend-side. */
export interface WaveformPeaks {
  points: number;
  min: number[];
  max: number[];
  durationSeconds: number;
  sampleRate: number;
}

/** A cut: `[startFrame, endFrame)` of the original audio, in 10 ms time frames. */
export type Cut = [number, number];

/** One row of the frame table: a kept range of the original audio, in frames. */
export interface KeptRange {
  /** Where the range starts in the piece (the original minus the cuts). */
  pieceStart: number;
  /** Where it starts in the original audio file. */
  originalStart: number;
  length: number;
}

/**
 * `GET` and `PUT /audio/{uuid}/cuts`: the selected region (implementation 08, plan section 9.2).
 *
 * The audio file never changes. A cut is a range of 10 ms time frames the user deleted, and the
 * piece is every frame that is not in a cut.
 */
export interface CutsState {
  audioUuid: string;
  /** Goes up by one each time the cuts are saved with a change. Send it back as `baseRevision`. */
  audioRevision: number;
  /** One time frame, in ms (10). */
  frameMs: number;
  totalFrames: number;
  pieceFrames: number;
  /** Sorted, never touching or overlapping. */
  cuts: Cut[];
  kept: KeptRange[];
  /** The stored notes were transcribed from other cuts: transcribe again. */
  notesStale: boolean;
  /** The files of the audio laid end to end, in order (**add audio**): one for most projects. */
  files: AxisFile[];
}

/** One file of the audio of a project, on the axis of the Audio step. */
export interface AxisFile {
  name: string;
  /** Where the file starts, and its length, in 10 ms frames. */
  startFrame: number;
  frames: number;
}

/**
 * The waveform at one pair of values per time frame, decoded into typed arrays.
 *
 * One request covers every zoom level, down to the single frame a cut snaps to.
 */
export interface FramePeaks {
  frameMs: number;
  totalFrames: number;
  /** The loudest sample of the audio (0 to 1); `min` and `max` are scaled so it is 127. */
  peak: number;
  min: Int8Array;
  max: Int8Array;
}

interface FramePeaksWire {
  audioUuid: string;
  frameMs: number;
  totalFrames: number;
  peak: number;
  min: string;
  max: string;
}

/** Base64 of signed bytes, as the backend packs them, into an `Int8Array`. */
function decodeInt8(base64: string): Int8Array {
  const text = atob(base64);
  const bytes = new Uint8Array(text.length);
  for (let index = 0; index < text.length; index += 1) bytes[index] = text.charCodeAt(index);
  return new Int8Array(bytes.buffer);
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

  /** **Add audio**: another file at the end of the project's audio. */
  addAudio: (uuid: string, file: File) => upload<AudioItem>(`/audio/${uuid}/add`, file),

  storeRecording: (file: File, alias?: string) =>
    upload<AudioItem>("/audio/recording", file, alias ? { alias } : {}),

  trim: (
    uuid: string,
    body: { startSeconds: number; endSeconds: number; alias?: string },
  ) => request<AudioItem>(`/audio/${uuid}/trim`, { method: "POST", body }),

  waveform: (uuid: string, points = 1000, signal?: AbortSignal) =>
    request<WaveformPeaks>(`/audio/${uuid}/waveform`, { query: { points }, signal }),

  /** The cuts and the frame table of the selected region. */
  cuts: (uuid: string, signal?: AbortSignal) => request<CutsState>(`/audio/${uuid}/cuts`, { signal }),

  /**
   * Save the cuts. Refused with 409 when `baseRevision` is not the stored one any more, so a page
   * never writes over a selection changed somewhere else.
   */
  saveCuts: (uuid: string, cuts: Cut[], baseRevision: number) =>
    request<CutsState>(`/audio/${uuid}/cuts`, { method: "PUT", body: { cuts, baseRevision } }),

  /** The waveform of the Audio tab, one lowest and one highest sample per 10 ms frame. */
  framePeaks: async (uuid: string, signal?: AbortSignal): Promise<FramePeaks> => {
    const wire = await request<FramePeaksWire>(`/audio/${uuid}/frames/peaks`, { signal });
    return {
      frameMs: wire.frameMs,
      totalFrames: wire.totalFrames,
      peak: wire.peak,
      min: decodeInt8(wire.min),
      max: decodeInt8(wire.max),
    };
  },

  /**
   * Direct URL for an `<audio>` element — no fetch needed.
   *
   * The audio of the piece: once cuts are saved, the edited audio (the original with the cuts
   * removed), which is the time the notes are in. Every player uses this.
   */
  fileUrl: (uuid: string, normalized = false) =>
    buildUrl(`/audio/${uuid}/file`, normalized ? { normalized: true } : undefined),

  /** The untouched original, cuts and all. Only the Audio tab plays it, to show and restore cuts. */
  originalFileUrl: (uuid: string) => buildUrl(`/audio/${uuid}/file`, { original: true }),
};
