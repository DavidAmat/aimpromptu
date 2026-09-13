/**
 * `/audio/{uuid}/edits` — staged re-recording (Epic 11) and composing live (Epic 13).
 *
 * One session serves both. A `replace` session is given a marked window and may never change the
 * piece's length; an `append` or `insert` session is given a moment, and the passage it records is
 * what makes the piece longer — the one place in the product where that is allowed.
 */

import { buildUrl, request, upload } from "./client";
import type { AudioItem, WaveformPeaks } from "./audio";
import type { FigureName, LabelledPeak, Peak, SpeedChange, TimeScorePayload } from "./timeScore";

export type SlowdownChoice = 1 | 2 | 4;

/** Where an accepted take goes. Only the last two change the piece's length. */
export type Placement = "replace" | "append" | "insert";

export interface DroppedMarks {
  figureOverrides: number;
  beamBreaks: number;
  hiddenNotes: number;
  fingerings: number;
}

/** Marks an insertion pushed later, and by how many columns. */
export interface MovedMarks {
  total: number;
  frames: number;
}

export interface EditSession {
  sessionUuid: string;
  audioUuid: string;
  placement: Placement;
  /** Append only: the silence asked for after the last note. */
  gapSeconds: number | null;
  startFrame: number;
  endFrame: number;
  startSeconds: number;
  endSeconds: number;
  frameMs: number;
  windowSeconds: number;
  slowdown: number | null;
  factor: number;
  spliceAudio: boolean;
  clickIntervalMs: number | null;
  hasTake: boolean;
  hasEvents: boolean;
  firstOnsetSeconds: number | null;
  trimLengthSeconds: number | null;
  untrimmedDurationSeconds: number | null;
  expectedTakeSeconds: number | null;
  takeStartSeconds: number | null;
  takeEndSeconds: number | null;
}

export interface Confirmation {
  placement: Placement;
  notesRemoved: number;
  notesArriving: number;
  droppedMarks: DroppedMarks;
  /** Composing only: what an insertion pushes later. */
  movedMarks: MovedMarks;
  notesMoved: number;
  spliceAudio: boolean;
  lengthUnchanged: boolean;
  windowSeconds: number;
  /** What the piece will be once this is accepted. */
  durationSeconds: number;
  nextVersion: number;
}

export interface EditPreview {
  session: EditSession;
  confirmation: Confirmation;
  score: TimeScorePayload;
  peaks: Peak[];
  labelled: LabelledPeak[];
  takeNoteCount: number;
  scaledNoteCount: number;
}

export interface AcceptResult {
  version: number;
  placement: Placement;
  durationSeconds: number;
  notesRemoved: number;
  notesArriving: number;
  droppedMarks: DroppedMarks;
  movedMarks: MovedMarks;
  notesMoved: number;
  audioSpliced: boolean;
  audioMismatch: boolean;
}

export interface StartEditBody {
  placement?: Placement;
  startFrame?: number;
  endFrame?: number;
  startSeconds?: number;
  endSeconds?: number;
  /** Append only: the silence to leave after the last note. */
  gapSeconds?: number;
  frameMs?: number;
  slowdown?: SlowdownChoice | null;
  spliceAudio?: boolean;
  clickIntervalMs?: number;
}

export const editingApi = {
  /**
   * Start a piece with nothing in it: an empty `events.json` and a `frameMs` (Subtask 13.1.1.1).
   * No BPM, no granularity — the only question is the name.
   */
  createPiece: (body: { name: string; frameMs?: number }) =>
    request<AudioItem>("/audio/compose", { method: "POST", body }),

  start: (audioUuid: string, body: StartEditBody) =>
    request<EditSession>(`/audio/${audioUuid}/edits`, { method: "POST", body }),

  get: (audioUuid: string, sessionUuid: string, signal?: AbortSignal) =>
    request<EditSession>(`/audio/${audioUuid}/edits/${sessionUuid}`, { signal }),

  patch: (
    audioUuid: string,
    sessionUuid: string,
    body: {
      slowdown?: SlowdownChoice | null;
      fit?: boolean;
      spliceAudio?: boolean;
      clickIntervalMs?: number;
      trimLengthSeconds?: number;
      takeStartSeconds?: number;
      takeEndSeconds?: number;
      gapSeconds?: number;
      atSeconds?: number;
    },
  ) => request<EditSession>(`/audio/${audioUuid}/edits/${sessionUuid}`, { method: "PATCH", body }),

  cancel: (audioUuid: string, sessionUuid: string) =>
    request<{ status: string }>(`/audio/${audioUuid}/edits/${sessionUuid}`, { method: "DELETE" }),

  uploadTake: (audioUuid: string, sessionUuid: string, file: File) =>
    upload<EditSession>(`/audio/${audioUuid}/edits/${sessionUuid}/take`, file),

  transcribe: (audioUuid: string, sessionUuid: string) =>
    request<{ jobId: string; status: string }>(
      `/audio/${audioUuid}/edits/${sessionUuid}/transcribe`,
      { method: "POST" },
    ),

  preview: (
    audioUuid: string,
    sessionUuid: string,
    body?: { anchorFigure?: FigureName; anchorMs?: number; speedChanges?: SpeedChange[] },
  ) =>
    request<EditPreview>(`/audio/${audioUuid}/edits/${sessionUuid}/preview`, {
      method: "POST",
      body: body ?? {},
    }),

  confirmation: (audioUuid: string, sessionUuid: string) =>
    request<Confirmation>(`/audio/${audioUuid}/edits/${sessionUuid}/confirmation`),

  accept: (audioUuid: string, sessionUuid: string) =>
    request<AcceptResult>(`/audio/${audioUuid}/edits/${sessionUuid}/accept`, { method: "POST" }),

  windowUrl: (audioUuid: string, sessionUuid: string, slowed = false) =>
    buildUrl(`/audio/${audioUuid}/edits/${sessionUuid}/window`, slowed ? { slowed: true } : undefined),

  takeUrl: (audioUuid: string, sessionUuid: string, options?: { scaled?: boolean; untrimmed?: boolean }) =>
    buildUrl(`/audio/${audioUuid}/edits/${sessionUuid}/take`, {
      scaled: options?.scaled || undefined,
      untrimmed: options?.untrimmed || undefined,
    }),

  takeWaveform: (audioUuid: string, sessionUuid: string, points = 1000, signal?: AbortSignal) =>
    request<WaveformPeaks>(`/audio/${audioUuid}/edits/${sessionUuid}/waveform`, {
      query: { points },
      signal,
    }),
};
