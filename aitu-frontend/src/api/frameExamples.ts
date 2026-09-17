/**
 * `/frame-examples` — the Synthesia example screenshots and their score board.
 *
 * Phase 2 of `04-synthesia-to-notes`. These types mirror
 * `aitu-backend/src/aitu_backend/schemas/video.py` and must stay in step with it.
 *
 * The picture is served at the working resolution, which is the width the
 * detector reads, so every coordinate here means the same thing on both sides.
 */

import { buildUrl, request } from "./client";

export type KeyState = "onset" | "sustain" | "released";
export type MomentumVerdict = "fell" | "static" | "unknown";

/** The one rectangle the user drags over the piano area (V-37), in picture pixels and degrees. */
export interface PianoRect {
  x: number;
  y: number;
  width: number;
  height: number;
  /** Positive clockwise on the screen; the rectangle turns about its top left corner. */
  angle: number;
}

/** The two borders of one black key, along the top edge of the rectangle. */
export interface BlackBorder {
  left: number;
  right: number;
}

/** What the finder said about its own answer, and which borders the user dragged since. */
export interface Found {
  route: string;
  confidence: number;
  extrapolated: number[];
  confirmed: number[];
  /** Indexes into `whiteBorders` the user moved by hand. */
  corrected: number[];
}

/** The piano overlay of one picture: per-key borders (V-38), in the pixels of that picture. */
export interface Calibration {
  imageWidth: number;
  imageHeight: number;
  pianoRect: PianoRect;
  /** The top edge of the piano. A rectangle tip crossing it is an onset (V-11). */
  upperLine: number;
  /** Along the top edge of the rectangle, left to right: one more than the white keys. */
  whiteBorders: number[];
  /** One per black key the pattern puts between the white keys, in pitch order. */
  blackBorders: BlackBorder[];
  /** How far down the rectangle the black keys reach. Drawn, never detected. */
  blackDepth: number;
  /** The median white key width — derived, never set by hand. The unit of V-22 (V-38). */
  whiteWidth: number;
  /** From the black key pattern, never from a colour (V-10). */
  firstWhitePitchClass: number;
  /** The one thing the user says. */
  firstWhiteOctave: number;
  /** Nothing above this row is music (V-28). Zero on a screenshot. */
  rollTop: number;
  /** Where the strike light makes the picture unreadable (V-08). Zero = default. */
  guardBand: number;
  found: Found | null;
  note: string;
}

/** What the finder needs: the rectangle, and the two things the user decides. */
export interface FindRequest {
  pianoRect: PianoRect;
  upperLine?: number | null;
  firstWhiteOctave?: number | null;
}

export interface PianoKey {
  midi: number;
  kind: "white" | "black";
  nameEn: string;
  nameEs: string;
  left: number;
  right: number;
  mid: number;
}

export interface KeyLane {
  midi: number;
  kind: "white" | "black";
  x0: number;
  x1: number;
  mid: number;
}

export interface Geometry {
  keys: PianoKey[];
  lanes: KeyLane[];
  margin: number;
}

/** One rectangle the detector found, on one key, in one picture. */
export interface DetectedRun {
  midi: number;
  /** The last rectangle tip — where the note stops sounding. */
  yTop: number;
  /** The rectangle tip — the side that reaches the piano first. */
  yBottom: number;
  x0: number;
  x1: number;
  mid: number;
  widthKeys: number;
  /** Cut by the upper line rather than tipped there (V-16), so it is sounding. */
  clipped: boolean;
  /** False when the tip sits inside the halo guard band, where it is extrapolated. */
  tipTrusted: boolean;
  entering: boolean;
  verdict: KeyState;
  momentum: MomentumVerdict;
}

export interface Detection {
  slug: string | null;
  offsetPx: number;
  onsets: number[];
  sustains: number[];
  runs: DetectedRun[];
  refused: DetectedRun[];
  elapsedMs: number;
}

/** One reading of one example, by hand, with the offset line in one place. */
export interface Annotation {
  offsetPx: number;
  onsets: number[];
  sustains: number[];
  /** Keys the picture cannot answer for: out of the score on both sides. */
  skip: number[];
  note: string;
}

export interface FrameExample {
  slug: string;
  imageWidth: number;
  imageHeight: number;
  calibration: Calibration | null;
  annotations: Annotation[];
  noRoll: boolean;
  note: string;
}

export interface ExampleSummary {
  slug: string;
  hasCalibration: boolean;
  annotationCount: number;
  noRoll: boolean;
}

export interface Disagreement {
  midi: number;
  nameEn: string;
  truth: KeyState;
  detected: KeyState;
}

export interface ScoreLine {
  slug: string;
  offsetPx: number;
  onsetsFound: number;
  onsetsInvented: number;
  onsetsMissed: number;
  sustainsFound: number;
  sustainsInvented: number;
  sustainsMissed: number;
  disagreements: Disagreement[];
  error: string | null;
}

export interface ScoreBoard {
  lines: ScoreLine[];
  total: ScoreLine;
  /** Examples not scored, and why. An honest failure list is a result. */
  skipped: Record<string, string>;
}

export const frameExamplesApi = {
  list: (signal?: AbortSignal) => request<ExampleSummary[]>("/frame-examples", { signal }),

  get: (slug: string, signal?: AbortSignal) =>
    request<FrameExample>(`/frame-examples/${slug}`, { signal }),

  /** The working-resolution copy — what the detector reads. */
  imageUrl: (slug: string) => buildUrl(`/frame-examples/${slug}/image`),

  /** The one rectangle in, the overlay found inside it out (V-37). Nothing is saved. */
  find: (slug: string, body: FindRequest, signal?: AbortSignal) =>
    request<Calibration>(`/frame-examples/${slug}/find`, { method: "POST", body, signal }),

  putCalibration: (slug: string, calibration: Calibration, signal?: AbortSignal) =>
    request<FrameExample>(`/frame-examples/${slug}/calibration`, {
      method: "PUT",
      body: calibration,
      signal,
    }),

  /** What the backend builds from the same calibration — the drift check. */
  geometry: (slug: string, calibration: Calibration, signal?: AbortSignal) =>
    request<Geometry>(`/frame-examples/${slug}/geometry`, {
      method: "POST",
      body: calibration,
      signal,
    }),

  putAnnotation: (slug: string, annotation: Annotation, signal?: AbortSignal) =>
    request<FrameExample>(`/frame-examples/${slug}/annotation`, {
      method: "PUT",
      body: annotation,
      signal,
    }),

  deleteAnnotation: (slug: string, offsetPx: number, signal?: AbortSignal) =>
    request<FrameExample>(`/frame-examples/${slug}/annotation`, {
      method: "DELETE",
      query: { offsetPx },
      signal,
    }),

  setNoRoll: (slug: string, noRoll: boolean, signal?: AbortSignal) =>
    request<FrameExample>(`/frame-examples/${slug}`, {
      method: "PATCH",
      query: { noRoll },
      signal,
    }),

  detect: (
    slug: string,
    offsetPx: number,
    options: { channel?: string; colourCheck?: boolean } = {},
    signal?: AbortSignal,
  ) =>
    request<Detection>(`/frame-examples/${slug}/detect`, {
      method: "POST",
      query: { offsetPx, channel: options.channel, colourCheck: options.colourCheck },
      signal,
    }),

  score: (options: { channel?: string; colourCheck?: boolean } = {}, signal?: AbortSignal) =>
    request<ScoreBoard>("/frame-examples/score", {
      query: { channel: options.channel, colourCheck: options.colourCheck },
      signal,
    }),
};
