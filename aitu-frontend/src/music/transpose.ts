/**
 * The two transpositions of the sheet toolbox (implementation 02, plan section 11.4): the words of a
 * notes transposition, and the figure ladder a figures transposition walks.
 *
 * Both are written by the backend on the new sheet (`POST /sheet/{id}/transpose`, the `figures`
 * reading edit); the key changes and the marks that moved with the notes on the old sheet went with
 * it in implementation 03, Phase 10.
 */

import type { FigureName } from "../api";

/** "Up 2 semitones", "Down 1 semitone", or "" for none. */
export function intervalWords(semitones: number): string {
  if (semitones === 0) return "";
  const size = Math.abs(semitones);
  return `${semitones > 0 ? "Up" : "Down"} ${size} semitone${size === 1 ? "" : "s"}`;
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
