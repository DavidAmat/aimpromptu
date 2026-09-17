/**
 * `/video` — one YouTube URL becomes a video, sampled frames and a reading.
 *
 * Phase 3 of `04-synthesia-to-notes`. These types mirror
 * `aitu-backend/src/aitu_backend/schemas/video.py` and must stay in step with
 * it. The overlay types are the ones the Examples tab already uses and are
 * re-exported from `frameExamples.ts` rather than written twice: the piano
 * overlay of a video is the piano overlay of a screenshot (V-37).
 *
 * `sampleMs` is how often we look at the video. It is **never** `frameMs`, which
 * is the column length the sheet is read at (V-04).
 */

import { buildUrl, request } from "./client";
import type { Calibration, Detection, FindRequest } from "./frameExamples";

/** `video/metadata_video.json` — what the file is, and how it was sampled. */
export interface VideoMetadata {
  audioUuid: string;
  title: string;
  sourceUrl: string | null;
  width: number;
  height: number;
  durationSeconds: number;
  /** Frames per second of the source. Not the sampling granularity. */
  fps: number;
  sizeBytes: number;
  /** How often we look at the video, in milliseconds. Zero before sampling. */
  sampleMs: number;
  frameCount: number;
  frameWidth: number;
  frameHeight: number;
  framesBytes: number;
}

/** How fast the rectangles fall, measured never assumed (V-06). */
export interface ScrollSpeed {
  pxPerFrame: number;
  pxPerSecond: number;
  q1: number;
  q3: number;
  p5: number;
  p95: number;
  /** Pairs that answered sharply and moved, out of how many there are. */
  usablePairs: number;
  totalPairs: number;
  /** Pairs the roll did not move in at all: the rests. */
  stillPairs: number;
  /** False when the spread says the speed is not stable. */
  stable: boolean;
  /** Why it is not stable, in words. Empty when it is. */
  reason: string;
  series: number[];
}

/** Everything the motion of the roll says about one video. */
export interface VideoMeasurement {
  scrollSpeed: ScrollSpeed;
  /** Nothing above this row is music (V-28). */
  rollTop: number;
  /** Where the strike light makes the picture unreadable (V-08, V-24). */
  guardBand: number;
  /** Not a free parameter: the measured speed times the granularity (V-25). */
  offsetPx: number;
}

export interface VideoSummary {
  metadata: VideoMetadata;
  calibration: Calibration | null;
  measurement: VideoMeasurement | null;
  detected: boolean;
  detectedFrames: number;
  /** How many notes the stitched roll read (V-32). Zero before it has run. */
  noteCount: number;
  /** True once this piece has an `events.json` — from this video or the model. */
  hasPiece: boolean;
}

/**
 * One note read off the stitched roll, before it becomes an event (V-32).
 *
 * It carries where it was read as well as when it sounds, because a note that
 * looks wrong on the sheet has to be findable in the picture it came from.
 */
export interface VideoNote {
  midi: number;
  start: number;
  end: number;
  rowTop: number;
  rowBottom: number;
  widthKeys: number;
  /** How far from the key's midpoint, in white key widths. V-14's own margin. */
  keyDistance: number;
  /** Already sounding when the video started, so its onset is not in the picture. */
  startsBefore: boolean;
  /** Still falling when the video ended, so its release is not in the picture. */
  endsAfter: boolean;
}

/** One shape a gate threw out, with the gate that did it. Reported, never rounded. */
export interface RejectedRun {
  midi: number;
  yTop: number;
  yBottom: number;
  x0: number;
  x1: number;
  mid: number;
  widthKeys: number;
  reason: string;
}

/** What one reading of the stitched roll did, in numbers (V-20). */
export interface NoteReport {
  rows: number;
  width: number;
  megabytes: number;
  stripTop: number;
  stripHeight: number;
  headRows: number;
  frameCount: number;
  notes: number;
  rejected: Record<string, number>;
  notesStartingBefore: number;
  notesEndingAfter: number;
  notesPastTheEnd: number;
  medianWidthKeys: number;
  medianLengthMs: number;
  worstKeyDistance: number;
  notesPerSecond: number;
  /** The same picture read as plain connected shapes — the letter of V-32. */
  connectedShapes: number;
  /** Keys whose lane is foreground more than six tenths of the time; named, not trusted (V-44). */
  busyKeys: number[];
  elapsedSeconds: number;
}

/** `video/notes.json` — what the stitched roll read. It is not the piece. */
export interface VideoNotes {
  audioUuid: string;
  notes: VideoNote[];
  report: NoteReport;
  durationSeconds: number;
  rejected: RejectedRun[];
}

/** One note a person took off, or put on, before the piece was written. */
export interface NoteCorrection {
  midi: number;
  start: number;
  /** Only an addition has an end. */
  end?: number | null;
}

export interface NoteCorrections {
  removed: NoteCorrection[];
  added: NoteCorrection[];
}

/** What `POST /video/{uuid}/events` did, in the words the screen shows. */
export interface WriteResult {
  audioUuid: string;
  title: string;
  durationSeconds: number;
  notes: number;
  removed: number;
  added: number;
  unmatched: number;
  musicVersion: number;
}

/** One line of `frames.jsonl`: what the detector saw in one sampled frame. */
export interface FrameLine {
  t: number;
  onsets: number[];
  sustains: number[];
}

/** What one run of the detector over a whole video did, in numbers (V-20). */
export interface DetectionReport {
  frameCount: number;
  runsFound: number;
  runsRefused: number;
  onsets: number;
  sustains: number;
  onsetsPerSecond: number;
  /** Frame to frame agreement (V-31): the score when there is no ground truth. */
  agreement: number;
  elapsedSeconds: number;
  workers: number;
}

export interface VideoJobHandle {
  jobId: string;
  status: string;
}

export const videoApi = {
  /** Every piece that has a downloaded video. */
  list: (signal?: AbortSignal) => request<VideoSummary[]>("/video", { signal }),

  get: (uuid: string, signal?: AbortSignal) =>
    request<VideoSummary>(`/video/${uuid}`, { signal }),

  /** One URL in, a video and the audio of that same video beside it (V-03). */
  download: (url: string, alias?: string, signal?: AbortSignal) =>
    request<VideoMetadata>("/video/download", {
      method: "POST",
      body: { url, fileName: alias },
      signal,
    }),

  /** Sample the frames, as a job with progress. */
  sample: (uuid: string, sampleMs: number, signal?: AbortSignal) =>
    request<VideoJobHandle>(`/video/${uuid}/sample`, {
      method: "POST",
      query: { sampleMs },
      signal,
    }),

  /** One sampled frame, at the working resolution — what the detector reads. */
  frameUrl: (uuid: string, index: number) => buildUrl(`/video/${uuid}/frames/${index}`),

  /** SSE endpoint for a sampling, measuring or detection job. */
  progressUrl: (jobId: string) => buildUrl(`/video/progress/${jobId}`),

  /** The one rectangle in, the overlay found inside one frame out (V-37). */
  find: (uuid: string, index: number, body: FindRequest, signal?: AbortSignal) =>
    request<Calibration>(`/video/${uuid}/find`, {
      method: "POST",
      query: { index },
      body,
      signal,
    }),

  putCalibration: (uuid: string, calibration: Calibration, signal?: AbortSignal) =>
    request<VideoSummary>(`/video/${uuid}/calibration`, {
      method: "PUT",
      body: calibration,
      signal,
    }),

  /** The scroll speed and the two edges of the roll, as a job (V-06, V-28). */
  measure: (uuid: string, signal?: AbortSignal) =>
    request<VideoJobHandle>(`/video/${uuid}/measure`, { method: "POST", signal }),

  /** The detector over every sampled frame, as a job (Task 3.5.1). */
  detect: (uuid: string, channel?: string, signal?: AbortSignal) =>
    request<VideoJobHandle>(`/video/${uuid}/detect`, {
      method: "POST",
      query: { channel },
      signal,
    }),

  /** `frames.jsonl` as it was written. */
  detection: (uuid: string, start = 0, limit = 5000, signal?: AbortSignal) =>
    request<FrameLine[]>(`/video/${uuid}/detection`, { query: { start, limit }, signal }),

  report: (uuid: string, signal?: AbortSignal) =>
    request<DetectionReport>(`/video/${uuid}/report`, { signal }),

  /** Stitch the whole video into one picture and read the notes out (V-32). */
  readNotes: (uuid: string, signal?: AbortSignal) =>
    request<VideoJobHandle>(`/video/${uuid}/notes`, { method: "POST", signal }),

  /** What the stitched roll read — which is what will be written, not the piece. */
  notes: (uuid: string, signal?: AbortSignal) =>
    request<VideoNotes>(`/video/${uuid}/notes`, { signal }),

  corrections: (uuid: string, signal?: AbortSignal) =>
    request<NoteCorrections>(`/video/${uuid}/corrections`, { signal }),

  putCorrections: (uuid: string, corrections: NoteCorrections, signal?: AbortSignal) =>
    request<NoteCorrections>(`/video/${uuid}/corrections`, {
      method: "PUT",
      body: corrections,
      signal,
    }),

  /** Write the piece. This is the step that changes it, so it moves the version. */
  writeEvents: (uuid: string, signal?: AbortSignal) =>
    request<WriteResult>(`/video/${uuid}/events`, { method: "POST", signal }),

  /** One sampled frame read with its two neighbours, for the screen to draw. */
  detectFrame: (uuid: string, index: number, channel?: string, signal?: AbortSignal) =>
    request<Detection>(`/video/${uuid}/frames/${index}/detect`, {
      method: "POST",
      query: { channel },
      signal,
    }),
};
