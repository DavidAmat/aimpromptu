/**
 * `/pieces` — a piece as the flow page sees it (implementation 08, Phases 5 and 6).
 *
 * The flow page asks one question before it draws its tabs: which steps of this piece are ready?
 * The backend compares the revisions of the audio, the notes, the hands and the sheet, and answers
 * every step at once, so the page never works out staleness on its own.
 */

import { request } from "./client";

/** The five steps of the flow page, in order. */
export const PIECE_STEPS = ["source", "audio", "notes", "hands", "sheet"] as const;
export type PieceStep = (typeof PIECE_STEPS)[number];

/**
 * `missing`: never made. `running`: a transcription is working on it. `stale`: made from an older
 * revision of an earlier step, so it must be done again. `ready`: current.
 */
export type StepState = "missing" | "running" | "stale" | "ready";

export interface StepStatus {
  step: PieceStep;
  state: StepState;
  /** Whether its tab may be opened: every step before it is ready. */
  enabled: boolean;
  /** Why the step is not ready, or why its tab is disabled, in words shown as they are. */
  reason: string | null;
  /**
   * What else the backend says about the step. Notes: `noteCount`, `engine`, and `jobId` while a
   * transcription runs. Hands: `withoutHand`, `guessed`, `saved`. Audio: `audioRevision`, `cuts`.
   */
  details: Record<string, unknown>;
}

export interface PieceStatus {
  audioUuid: string;
  steps: StepStatus[];
  /** The step the piece opens on: the furthest one that is ready. */
  resume: PieceStep;
  /** `audio`, `notes`, `notesAudio`, `hands`, `handsNotes`, `sheetHands`. */
  revisions: Record<string, number | null>;
}

/**
 * The notes of a piece as columns, one list per field (plan section 6.4): index `i` of every list
 * is one note. Only the live notes, sorted by onset then key. Times are whole milliseconds of the
 * piece.
 */
export interface PieceNotes {
  /** The notes revision and the hands revision: send both back with an edit. */
  revision: number;
  handsRevision: number;
  durationMs: number;
  /** The selected region changed after the transcription: these notes must be transcribed again. */
  stale: boolean;
  id: number[];
  key: number[];
  onMs: number[];
  lenMs: number[];
  /** One character per note: `r`, `l`, or `-` for no hand yet. */
  hand: string;
  /** The ids of the notes whose hand came from the quick rule. */
  guessed: number[];
}

/**
 * One edit of `PATCH /pieces/{uuid}/notes`. Times are milliseconds of the piece; `key` is 0 to 87.
 *
 * - `move`: new onset and length (a resize is a move), and a new key when it changed;
 * - `delete`: the notes are marked removed and keep their ids; `restore` puts them back;
 * - `add`: a new note, named by a negative `tempId` until the answer gives its id;
 * - `hand`: the notes go to that hand.
 */
export type NotesOperation =
  | { op: "move"; id: number; onMs: number; lenMs: number; key?: number }
  | { op: "delete"; ids: number[] }
  | { op: "restore"; ids: number[] }
  | { op: "add"; tempId: number; key: number; onMs: number; lenMs: number; hand?: "r" | "l" }
  | { op: "hand"; ids: number[]; hand: "r" | "l" };

export interface NotesPatchResult {
  revision: number;
  handsRevision: number;
  /** False when nothing changed and nothing was written. */
  saved: boolean;
  /** The id the backend gave each added note. */
  added?: { tempId: number; id: number }[];
  /**
   * The notes the backend changed beyond the operations, as columns: the added notes, a note the
   * same-key rule shortened, a note the quick rule gave a hand.
   */
  changed?: { id: number[]; key: number[]; onMs: number[]; lenMs: number[]; hand: string; guessed?: number[] };
  /** True when a saved piano sheet was current before and is stale now. */
  sheetStale: boolean;
}

/** The answer of **Predict hands**: the `done` frame of its job, or `POST /hands/predict`. */
export interface PredictResult {
  /** The notes revision the prediction was made for. */
  revision: number;
  handsRevision: number;
  frameMs: number;
  /** The live notes, in the order of `GET /notes`. */
  id: number[];
  /** One character per note of `id`: `r`, `l`, or `-` for a note the split could not place. */
  hand: string;
  /** How many notes would change hand if this is saved. */
  changed: number;
  /** How many notes the split could not place (shorter than one column of the piano sheet). */
  unplaced: number;
  elapsedMs: number;
}

export const piecesApi = {
  status: (audioUuid: string, signal?: AbortSignal) =>
    request<PieceStatus>(`/pieces/${audioUuid}/status`, { signal }),

  /** The saved notes, as columns. */
  notes: (audioUuid: string, signal?: AbortSignal) =>
    request<PieceNotes>(`/pieces/${audioUuid}/notes`, { signal }),

  /**
   * Start **Predict hands** as a job; follow it on `matrixApi.progressUrl(jobId)`, whose `done`
   * frame carries a {@link PredictResult}. Nothing is written. `replace: true` predicts every
   * note again, including the hands the user set.
   */
  predictHands: (
    audioUuid: string,
    body: { baseRevision: number; frameMs?: number; replace?: boolean },
  ) => request<{ jobId: string; status: string }>(`/pieces/${audioUuid}/hands/predict/job`, { method: "POST", body }),

  /**
   * Save edits of the notes. Refused with 409 when `baseRevision` (or `baseHandsRevision`) is not
   * the stored one any more, so a page never writes over a newer version.
   */
  patchNotes: (
    audioUuid: string,
    body: { baseRevision: number; baseHandsRevision?: number; ops: NotesOperation[] },
  ) => request<NotesPatchResult>(`/pieces/${audioUuid}/notes`, { method: "PATCH", body }),
};

export default piecesApi;
