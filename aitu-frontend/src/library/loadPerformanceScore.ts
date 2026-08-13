/**
 * Build the performance-view sheet from a stored audio and its saved rhythm.
 *
 * Same payload the Rhythm tab asks for. A piece nobody has named yet still draws, using the
 * biggest gap pile as a negra, so the stand is not empty — it just has not been read yet.
 */

import {
  timeScoreApi,
  type FigureName,
  type KeySignatureName,
  type SavedRhythm,
  type TimeScorePayload,
} from "../api";
import type {
  FingerNumber,
  KeyChangeAnnotation,
  KeySignature,
  OttavaAnnotation,
  OttavaKind,
} from "@aimpromptu/grid-notation";
import { DEFAULT_FRAME_MS } from "../music/granularities";

export interface PerformanceReading {
  score: TimeScorePayload;
  rhythm: SavedRhythm | null;
  unnamed: boolean;
  frameMs: number;
  keySignature: KeySignatureName;
  keyChanges: KeyChangeAnnotation[];
  ottavas: OttavaAnnotation[];
  overrides: Record<string, FigureName>;
  beamBreaks: Set<string>;
  fingers: Record<string, FingerNumber>;
}

export async function loadPerformanceScore(
  audioUuid: string,
  signal?: AbortSignal,
  preferredFrameMs: number = DEFAULT_FRAME_MS,
): Promise<PerformanceReading> {
  const rhythm = await timeScoreApi.rhythm(audioUuid, signal);
  const frameMs = rhythm?.frameMs ?? preferredFrameMs;
  const unnamed = !rhythm;
  const anchorFigure: FigureName = rhythm?.anchorFigure ?? "negra";
  let anchorMs = rhythm?.anchorMs ?? 0;

  if (!rhythm) {
    const peaks = await timeScoreApi.peaks(audioUuid, { frameMs }, signal);
    const biggest = [...peaks.peaks].sort((a, b) => b.share - a.share)[0];
    if (!biggest) {
      throw new Error("This piece has no recorded notes to draw.");
    }
    anchorMs = biggest.medianMs;
  }

  const hiddenNotes = (rhythm?.hiddenNotes ?? []).map((note) => ({
    startFrame: note.startFrame,
    row: note.row,
  }));
  const speedChanges = rhythm?.speedChanges ?? [];
  const score = await timeScoreApi.score(
    audioUuid,
    {
      anchorFigure,
      anchorMs,
      frameMs,
      boundaries: speedChanges.map((change) => change.startFrame),
      boundaryMs: [anchorMs, ...speedChanges.map((change) => change.anchorMs)],
      hiddenNotes,
    },
    signal,
  );

  const overrides: Record<string, FigureName> = {};
  for (const one of rhythm?.overrides ?? []) {
    overrides[`${one.hand}:${one.startFrame}`] = one.figure;
  }
  const beamBreaks = new Set(
    (rhythm?.beamBreaks ?? []).map((one) => `${one.hand}:${one.startFrame}`),
  );
  const fingers: Record<string, FingerNumber> = {};
  for (const one of rhythm?.fingers ?? []) {
    fingers[`${one.hand}:${one.startFrame}:${one.row}`] = one.finger as FingerNumber;
  }
  const keyChanges: KeyChangeAnnotation[] = (rhythm?.keyChanges ?? []).map((change) => ({
    fromColumn: change.fromColumn,
    keySignature: change.keySignature as KeySignature,
  }));
  const ottavas: OttavaAnnotation[] = (rhythm?.ottavas ?? []).map((span) => ({
    kind: span.kind as OttavaKind,
    hand: span.hand === "left" ? ("left" as const) : ("right" as const),
    fromColumn: span.fromColumn,
    toColumn: span.toColumn,
  }));

  return {
    score,
    rhythm,
    unnamed,
    frameMs,
    keySignature: (rhythm?.keySignature ?? "C") as KeySignatureName,
    keyChanges,
    ottavas,
    overrides,
    beamBreaks,
    fingers,
  };
}
