/** `/audio/{uuid}/edits` — staged range re-recording (Epic 11). */

import { buildUrl, request, upload } from "./client";
import type { FigureName, LabelledPeak, Peak, SpeedChange, TimeScorePayload } from "./timeScore";

export type SlowdownChoice = 1 | 2 | 4;

export interface DroppedMarks {
  figureOverrides: number;
  beamBreaks: number;
  hiddenNotes: number;
  fingerings: number;
}

export interface EditSession {
  sessionUuid: string;
  audioUuid: string;
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
}

export interface Confirmation {
  notesRemoved: number;
  notesArriving: number;
  droppedMarks: DroppedMarks;
  spliceAudio: boolean;
  lengthUnchanged: boolean;
  windowSeconds: number;
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
  durationSeconds: number;
  notesRemoved: number;
  notesArriving: number;
  droppedMarks: DroppedMarks;
  audioSpliced: boolean;
  audioMismatch: boolean;
}

export interface StartEditBody {
  startFrame?: number;
  endFrame?: number;
  startSeconds?: number;
  endSeconds?: number;
  frameMs?: number;
  slowdown?: SlowdownChoice | null;
  spliceAudio?: boolean;
  clickIntervalMs?: number;
}

export const editingApi = {
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

  takeUrl: (audioUuid: string, sessionUuid: string, scaled = false) =>
    buildUrl(`/audio/${audioUuid}/edits/${sessionUuid}/take`, scaled ? { scaled: true } : undefined),
};
