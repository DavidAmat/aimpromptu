/**
 * `/time` — the wall-clock path: where the rhythm piles up, what to call it, and the score.
 *
 * Three calls, and they are the three things the reader does. Ask where the gaps between notes pile
 * up, point at one pile and say what it is, then read the result on a staff.
 *
 * Nothing here is stored on the backend. Every call re-derives from the recorded notes, so changing
 * the time resolution is another request rather than a rebuild.
 */

import { request } from "./client";

export type FigureName =
  | "redonda"
  | "blanca"
  | "dottedBlanca"
  | "negra"
  | "dottedNegra"
  | "corchea"
  | "semicorchea"
  | "fusa"
  | "semifusa";

export type PrintedHand = "right" | "left";
export type HandChoice = PrintedHand | "both";

/** How a figure is written on screen, in the words the sheet uses. */
export const FIGURE_LABELS: Record<FigureName, string> = {
  redonda: "Redonda (whole)",
  blanca: "Blanca (half)",
  dottedBlanca: "Blanca with a dot",
  negra: "Negra (quarter)",
  dottedNegra: "Negra with a dot",
  corchea: "Corchea (eighth)",
  semicorchea: "Semicorchea (sixteenth)",
  fusa: "Fusa (thirty-second)",
  semifusa: "Semifusa (sixty-fourth)",
};

/** One pile of gaps in the distribution, as the plot draws it. */
export interface Peak {
  /** Where the pile is centred, in milliseconds. This is the number that gets named. */
  centreMs: number;
  medianMs: number;
  meanMs: number;
  count: number;
  /** Between 0 and 1. A pile holding half the gaps is the one worth naming. */
  share: number;
  loMs: number;
  hiMs: number;
}

export interface PeaksResponse {
  audioUuid: string;
  hand: HandChoice;
  frameMs: number;
  startSeconds: number;
  endSeconds: number;
  attackCount: number;
  gapCount: number;
  peaks: Peak[];
  /** Set when the gaps look machine-made rather than played. Plain language, shown as written. */
  warning?: string | null;
}

export interface FigureLadder {
  anchorFigure: FigureName;
  anchorMs: number;
  msByFigure: Record<FigureName, number>;
}

export interface LabelledPeak {
  peak: Peak;
  figure: FigureName;
  figureMs: number;
  /** How far the pile sits from the figure it was given, as a percentage. Small is good. */
  percentOff: number;
  /** Set when the pile is a third of a figure: three of these fill one of those. */
  tresilloOf?: FigureName | null;
  /** What to write next to the pile, for example `corchea de tresillo`. */
  name: string;
}

export interface LadderPreview {
  ladder: FigureLadder;
  /** For example `negra = 337 ms · ≈178 BPM`. */
  headerLabel: string;
  bpm: number;
  labelled: LabelledPeak[];
}

export interface SparseMatrix {
  format: "binary-coo";
  shape: [number, number];
  rows: number[];
  cols: number[];
  onset: number[];
}

export interface TimeMatrixEnvelope {
  schemaVersion: "2.0";
  sparse: true;
  frameMs: number;
  frameCount: number;
  durationSeconds: number;
  title?: string | null;
  keySignature?: string | null;
  matrixProcessingStep: "two-hands";
  rMatrix: SparseMatrix;
  lMatrix: SparseMatrix;
}

export interface Passage {
  id: string;
  startFrame: number;
  endFrame: number;
  ladder: FigureLadder;
  headerLabel: string;
}

export interface PrintedNote {
  hand: PrintedHand;
  row: number;
  startFrame: number;
  printedFrames: number;
  printedMsExact: number;
  figure: FigureName;
  fitError: number;
  groupId: number;
  /** How many notes this one is grouped with against the beat. 3 for a tresillo. */
  tuplet?: number | null;
  /** The notes of one tresillo share this. */
  tupletId?: number | null;
}

export interface LayoutHints {
  frameGroup: number;
  frameMeasure: number;
  silenceGroupPx: number;
  hideLeftHand?: boolean;
  hideRightHand?: boolean;
}

export interface TimeScorePayload {
  schemaVersion: "2.0";
  envelope: TimeMatrixEnvelope;
  passages: Passage[];
  notes: PrintedNote[];
  overrides: unknown[];
  layout: LayoutHints;
}

export interface PeaksQuery {
  hand?: HandChoice;
  frameMs?: number;
  startSeconds?: number;
  endSeconds?: number;
}

export const timeScoreApi = {
  peaks(audioUuid: string, query: PeaksQuery = {}, signal?: AbortSignal) {
    return request<PeaksResponse>(`/time/${audioUuid}/peaks`, {
      query: {
        hand: query.hand,
        frameMs: query.frameMs,
        startSeconds: query.startSeconds,
        endSeconds: query.endSeconds,
      },
      signal,
    });
  },

  ladderPreview(
    audioUuid: string,
    body: { anchorFigure: FigureName; anchorMs: number; hand?: HandChoice; frameMs?: number },
    signal?: AbortSignal,
  ) {
    return request<LadderPreview>(`/time/${audioUuid}/ladder-preview`, {
      method: "POST",
      body,
      signal,
    });
  },

  score(
    audioUuid: string,
    query: {
      anchorFigure?: FigureName;
      anchorMs: number;
      frameMs?: number;
      /** Frames where a new stretch starts. Each stretch needs its own entry in `boundaryMs`. */
      boundaries?: number[];
      boundaryMs?: number[];
    },
    signal?: AbortSignal,
  ) {
    return request<TimeScorePayload>(`/time/${audioUuid}/score`, {
      query: {
        anchorFigure: query.anchorFigure,
        anchorMs: query.anchorMs,
        frameMs: query.frameMs,
        boundaries: query.boundaries?.length ? query.boundaries.join(",") : undefined,
        boundaryMs: query.boundaryMs?.length ? query.boundaryMs.join(",") : undefined,
      },
      signal,
    });
  },
};
