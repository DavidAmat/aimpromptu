/**
 * `/passages` — Recording in Sheet (implementation 02, plan section 13, Phase 9).
 *
 * A passage is a stretch of a part being re-recorded, or a moment where a new passage goes. Its
 * `current` is a part: the copy of the marked frames, drawn as **Current**. Each take is a part too,
 * drawn as **Proposal** once it is read (`state: "ready"`). Both answer every route of a part
 * (`/time`, `/audio`, `/pieces`). Mirrors `aitu-backend/src/aitu_backend/api/passages.py`.
 */

import type { SavedRhythm } from "./timeScore";
import { postForm, request } from "./client";

export interface PassageTake {
  id: string;
  name: string;
  /** Audio only; the condensed steps running; notes, hands and a sheet. */
  state: "recorded" | "reading" | "ready";
  /** The length of the recording, and the stretch of it kept. */
  seconds: number;
  fromSeconds: number;
  toSeconds: number;
  /** The job of **Write the proposal**, while it runs. */
  jobId: string | null;
  /** Played on a MIDI piano: its notes are the keys played, not a transcription. */
  midi: boolean;
  /** Rises when the stretch kept changes: the take is played at a new address then. */
  audioRevision: number;
}

export interface OpenPassage {
  id: string;
  /** The part the passage is of, and its project. */
  part: string;
  projectId: string;
  title: string;
  /** The part holding the copy of the marked frames. */
  current: string;
  fromMs: number;
  /** Equal to `fromMs` for a new passage. */
  toMs: number;
  /** What the song's figure lasts where the passage starts; `null` on a song with no sheet. */
  anchorMs: number | null;
  anchorFigure: string;
  takes: PassageTake[];
  take: string | null;
  /** How many times as fast the take is played into the song (×0.25 to ×4). */
  speed: number;
  /** Where the window starts over the take, in ms of the take as played. */
  windowMs: number;
  /** The kept length of the take on show, in ms. */
  takeMs: number | null;
}

/** A key played on a MIDI piano during a take, in seconds from the start of its recording. */
export interface PlayedNote {
  midiNote: number;
  start: number;
  end: number;
  velocity: number;
}

export type PromotionMode = "window" | "whole";
export type PromotionAudio = "original" | "recording";

export interface PromotionFacts {
  mode: PromotionMode;
  audio: PromotionAudio;
  notesOut: number;
  notesIn: number;
  /** The marks of the passage that go, by their field of `sheet.json`. */
  marksDropped: Record<string, number>;
  /** How much longer (below zero, shorter) the song gets. */
  lengthChangeMs: number;
  durationSeconds: number;
}

export interface Promoted {
  part: string;
  projectId: string;
  /** The earlier state of the part: its restore is the undo. */
  beforeVersion: number;
  atMs: number;
  lengthMs: number;
  sheet: SavedRhythm | null;
}

interface PromoteBody {
  mode: PromotionMode;
  audio: PromotionAudio;
  sheet?: SavedRhythm;
}

export const passagesApi = {
  open: (part: string, fromMs: number, toMs: number) =>
    request<OpenPassage>("/passages", { method: "POST", body: { part, fromMs, toMs } }),
  get: (id: string, signal?: AbortSignal) => request<OpenPassage>(`/passages/${id}`, { signal }),
  update: (id: string, body: { take?: string; speed?: number; windowMs?: number }) =>
    request<OpenPassage>(`/passages/${id}`, { method: "PATCH", body }),
  discard: (id: string) => request<void>(`/passages/${id}`, { method: "DELETE" }),
  /** A take: a recording, the keys played on a MIDI piano, or both. */
  addTake: (id: string, file: File | null, notes?: readonly PlayedNote[]) => {
    const form = new FormData();
    if (file) form.append("file", file);
    if (notes) form.append("notes", JSON.stringify(notes));
    return postForm<OpenPassage>(`/passages/${id}/takes`, form);
  },
  deleteTake: (id: string, take: string) =>
    request<OpenPassage>(`/passages/${id}/takes/${take}`, { method: "DELETE" }),
  /** **Write the proposal**: a job; follow it on `matrixApi.progressUrl(jobId)`. */
  readTake: (id: string, take: string, fromSeconds: number, toSeconds: number) =>
    request<{ jobId: string; status: string }>(`/passages/${id}/takes/${take}/read`, {
      method: "POST",
      body: { fromSeconds, toSeconds },
    }),
  facts: (id: string, body: PromoteBody) =>
    request<PromotionFacts>(`/passages/${id}/promotion`, { method: "POST", body }),
  promote: (id: string, body: PromoteBody) =>
    request<Promoted>(`/passages/${id}/promote`, { method: "POST", body }),
};
