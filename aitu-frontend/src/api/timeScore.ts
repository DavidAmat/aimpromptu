/**
 * `/time` — the wall-clock path: where the rhythm piles up, what to call it, and the score.
 *
 * Three calls, and they are the three things the reader does. Ask where the gaps between notes pile
 * up, point at one pile and say what it is, then read the result on a staff.
 *
 * Nothing here is stored on the backend. Every call re-derives from the recorded notes, so changing
 * the time resolution is another request rather than a rebuild.
 */

import { ApiError, request } from "./client";

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

  /**
   * The reading saved for this piece, or `null` when nobody has saved one.
   *
   * Everything else about a score is worked out from the recorded notes on each request. This is
   * the part that cannot be: nothing in a recording says which pile of gaps is the beat, or where a
   * phrase restarts. A 404 is the normal answer for a piece nobody has read yet, so it comes back
   * as `null` rather than throwing.
   */
  async rhythm(audioUuid: string, signal?: AbortSignal): Promise<SavedRhythm | null> {
    try {
      return await request<SavedRhythm>(`/time/${audioUuid}/rhythm`, { signal });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) return null;
      throw caught;
    }
  },

  saveRhythm(audioUuid: string, body: SavedRhythm, signal?: AbortSignal) {
    return request<SavedRhythm>(`/time/${audioUuid}/rhythm`, { method: "PUT", body, signal });
  },

  forgetRhythm(audioUuid: string, signal?: AbortSignal) {
    return request<void>(`/time/${audioUuid}/rhythm`, { method: "DELETE", signal });
  },
};

/** Where the piece changes speed, and what a gap is worth from there on. */
export interface SpeedChange {
  startFrame: number;
  anchorMs: number;
}

/**
 * The fifteen signatures a staff can be written in, sharpest to flattest.
 *
 * A transcription arrives with no key at all: the recording says which keys were pressed and
 * nothing about how they should be spelled. Until someone chooses, everything is written in C and
 * every black key prints an accidental.
 */
export const KEY_SIGNATURES = [
  "C",
  "G",
  "D",
  "A",
  "E",
  "B",
  "F#",
  "C#",
  "F",
  "Bb",
  "Eb",
  "Ab",
  "Db",
  "Gb",
  "Cb",
] as const;

export type KeySignatureName = (typeof KEY_SIGNATURES)[number];

/**
 * What each signature is called on a picker, with the major key first.
 *
 * Both names are shown because a reader who knows the piece is in D minor should not have to
 * remember that D minor and F major print the same one flat.
 */
export const KEY_LABELS: Record<KeySignatureName, string> = {
  C: "C major / A minor — no sharps or flats",
  G: "G major / E minor — 1 sharp",
  D: "D major / B minor — 2 sharps",
  A: "A major / F# minor — 3 sharps",
  E: "E major / C# minor — 4 sharps",
  B: "B major / G# minor — 5 sharps",
  "F#": "F# major / D# minor — 6 sharps",
  "C#": "C# major / A# minor — 7 sharps",
  F: "F major / D minor — 1 flat",
  Bb: "Bb major / G minor — 2 flats",
  Eb: "Eb major / C minor — 3 flats",
  Ab: "Ab major / F minor — 4 flats",
  Db: "Db major / Bb minor — 5 flats",
  Gb: "Gb major / Eb minor — 6 flats",
  Cb: "Cb major / Ab minor — 7 flats",
};

/** One reader's reading of one piece: everything about a score that is not derived. */
export interface SavedRhythm {
  schemaVersion?: string;
  hand: HandChoice;
  /** The column length the columns below were numbered at. */
  frameMs: number;
  /**
   * The signature the whole piece is written in.
   *
   * Part of the reading rather than of the recording, exactly like the anchor: nothing in the
   * recorded notes says whether a black key is an F sharp or a G flat.
   */
  keySignature?: KeySignatureName;
  /**
   * Where the piece leaves that signature, and what it changes to, keyed by column.
   *
   * Transitions rather than ranges: at any column exactly one signature is sounding, so two edits
   * cannot disagree about what a reader is looking at. Giving a passage its own key writes two,
   * one where it starts and one where the piece goes back.
   */
  keyChanges?: { fromColumn: number; keySignature: KeySignatureName }[];
  anchorFigure: FigureName;
  anchorMs: number;
  speedChanges: SpeedChange[];
  overrides: { hand: string; row: number; startFrame: number; figure: FigureName }[];
  beamBreaks: { hand: string; startFrame: number }[];
  /**
   * Where a hand is written an octave or two from where it sounds, as half-open column ranges.
   *
   * Part of the reading, not of the recording: the page proposes brackets where a hand runs far
   * outside its own staff, and the reader keeps, moves or clears them. Absent on a reading saved
   * before brackets existed, which is why it is optional — absent means "never decided", and the
   * page then takes its own suggestion, while an empty list means "decided, none".
   */
  ottavas?: { kind: string; hand: string; fromColumn: number; toColumn: number }[];
  savedAt?: string;
}
