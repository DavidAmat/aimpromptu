/** `GET /scores`, `POST /sequence` — the text-notation endpoints. */

import type { MatrixScore } from "../music/types";
import { request } from "./client";

export interface SequenceRequest {
  sequence: string[];
  tempoBpm: number;
  timeStepSeconds: number;
  title?: string;
  lyrics?: string[];
  keySignature?: string;
  /** Left hand (bass clef). Same frame count as `sequence` when present. */
  leftSequence?: string[];
}

export const scoresApi = {
  list: (signal?: AbortSignal) => request<MatrixScore[]>("/scores", { signal }),

  fromSequence: (body: SequenceRequest, signal?: AbortSignal) =>
    request<MatrixScore>("/sequence", { method: "POST", body, signal }),
};
