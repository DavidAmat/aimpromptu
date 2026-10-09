/**
 * The two transpositions of the sheet toolbox (implementation 02, plan section 11.4), as plain
 * functions of the edits: what moves with the notes when every key moves, and what a figures
 * transposition renames or removes.
 *
 * Notes transposition writes the notes on the backend (`POST /time/{id}/transpose`); here is only
 * what the page holds about them. Figures transposition is a page edit and lives entirely here.
 */

import type { FigureName, GraceNote, KeySignatureName, Trill } from "../api";
import { KEY_SIGNATURES } from "../api";
import type { KeyChangeAnnotation, KeySignature } from "@aimpromptu/grid-notation";
import type { NoteRef } from "./renderOverrides";

/** The pitch class of each major key's tonic, Do = 0. */
const TONIC: Record<KeySignatureName, number> = {
  C: 0,
  G: 7,
  D: 2,
  A: 9,
  E: 4,
  B: 11,
  "F#": 6,
  "C#": 1,
  F: 5,
  Bb: 10,
  Eb: 3,
  Ab: 8,
  Db: 1,
  Gb: 6,
  Cb: 11,
};

/** How many sharps or flats each signature prints. */
const ACCIDENTALS: Record<KeySignatureName, number> = {
  C: 0,
  G: 1,
  D: 2,
  A: 3,
  E: 4,
  B: 5,
  "F#": 6,
  "C#": 7,
  F: 1,
  Bb: 2,
  Eb: 3,
  Ab: 4,
  Db: 5,
  Gb: 6,
  Cb: 7,
};

const FLAT_KEYS = new Set<KeySignatureName>(["F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]);

/**
 * The key a signature becomes when every note moves by `semitones`.
 *
 * Of the signatures with that tonic, the one with fewer accidentals: D flat rather than C sharp.
 * Where two print the same number (F sharp and G flat), the side the piece was on: a piece in
 * flats stays in flats.
 */
export function transposeKey(key: KeySignatureName, semitones: number): KeySignatureName {
  const tonic = (((TONIC[key] + semitones) % 12) + 12) % 12;
  const candidates = KEY_SIGNATURES.filter((name) => TONIC[name] === tonic);
  return [...candidates].sort(
    (left, right) =>
      ACCIDENTALS[left] - ACCIDENTALS[right] ||
      Number(FLAT_KEYS.has(right) === FLAT_KEYS.has(key)) -
        Number(FLAT_KEYS.has(left) === FLAT_KEYS.has(key)),
  )[0]!;
}

/** The key changes of the piece, each moved with the notes. */
export function transposeKeyChanges(
  changes: readonly KeyChangeAnnotation[],
  semitones: number,
): KeyChangeAnnotation[] {
  return changes.map((change) => ({
    ...change,
    keySignature: transposeKey(change.keySignature as KeySignatureName, semitones) as KeySignature,
  }));
}

/** "Up 2 semitones", "Down 1 semitone", or "" for none. */
export function intervalWords(semitones: number): string {
  if (semitones === 0) return "";
  const size = Math.abs(semitones);
  return `${semitones > 0 ? "Up" : "Down"} ${size} semitone${size === 1 ? "" : "s"}`;
}

/** Row 0 is the bottom A, row 87 the top C. */
const inKeyboard = (row: number) => row >= 0 && row < 88;

/**
 * The marks addressed by a key, moved with their notes.
 *
 * A fingering, a note taken off the page, a trill and a grace note each name the key of a note.
 * When every note moves, they move with it; one whose note left the keyboard has nothing to name
 * and goes.
 */
export function transposeRowMarks(
  marks: {
    fingers: Record<string, number>;
    hiddenNotes: ReadonlySet<NoteRef>;
    trills: readonly Trill[];
    graceNotes: readonly GraceNote[];
  },
  semitones: number,
) {
  const fingers: Record<string, number> = {};
  for (const [key, finger] of Object.entries(marks.fingers)) {
    const [hand, frame, row] = key.split(":");
    const moved = Number(row) + semitones;
    if (inKeyboard(moved)) fingers[`${hand}:${frame}:${moved}`] = finger;
  }
  const hiddenNotes = new Set<NoteRef>();
  for (const ref of marks.hiddenNotes) {
    const [frame, row] = ref.split(":");
    const moved = Number(row) + semitones;
    if (inKeyboard(moved)) hiddenNotes.add(`${frame}:${moved}` as NoteRef);
  }
  const trills = marks.trills
    .map((trill) => ({ ...trill, row: trill.row + semitones }))
    .filter((trill) => inKeyboard(trill.row));
  const graceNotes = marks.graceNotes
    .map((grace) => ({
      ...grace,
      row: grace.row + semitones,
      targetRow: grace.targetRow + semitones,
    }))
    .filter((grace) => inKeyboard(grace.row) && inKeyboard(grace.targetRow));
  return { fingers, hiddenNotes, trills, graceNotes };
}

/**
 * The rungs a figures transposition walks, shortest first: each twice the one before (D-18).
 * The same list as `SHIFT_LADDER` of the backend's `matrix/ladder.py`.
 */
export const FIGURE_LADDER: readonly FigureName[] = [
  "semifusa",
  "fusa",
  "semicorchea",
  "corchea",
  "negra",
  "blanca",
  "redonda",
];

/** The two dotted figures a reader can set by hand, and the plain rung each stands beside. */
const DOTTED: Partial<Record<FigureName, FigureName>> = {
  dottedNegra: "negra",
  dottedBlanca: "blanca",
};
const DOTTED_OF: Partial<Record<FigureName, FigureName>> = {
  negra: "dottedNegra",
  blanca: "dottedBlanca",
};

/** How many rungs from one figure to another: negative is shorter. */
export function figureSteps(from: FigureName, to: FigureName): number {
  return FIGURE_LADDER.indexOf(to) - FIGURE_LADDER.indexOf(from);
}

/**
 * A figure moved `steps` rungs, or `null` when that runs off the ladder.
 *
 * A dotted figure moves with its rung and stays dotted only where a dotted figure exists (negra
 * and blanca); anywhere else it has nothing to become, and the caller removes it.
 */
export function shiftFigure(figure: FigureName, steps: number): FigureName | null {
  const plain = DOTTED[figure];
  if (plain) {
    const moved = shiftFigure(plain, steps);
    return moved ? (DOTTED_OF[moved] ?? null) : null;
  }
  const at = FIGURE_LADDER.indexOf(figure);
  if (at < 0) return null;
  return FIGURE_LADDER[at + steps] ?? null;
}
