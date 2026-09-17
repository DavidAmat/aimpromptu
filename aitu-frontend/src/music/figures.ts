/**
 * The shapes a note can be printed as, and what each is called.
 *
 * Beside `FigureGlyph` rather than inside it because they are not a component: the page reads the
 * list to lay out a row of pills and reads the names for the tooltips, and a module that exports
 * both a component and a table of data cannot be hot-reloaded.
 */

import type { FigureName } from "../api";

/**
 * The seven plain figures, longest first.
 *
 * The two dotted ones are left out. A dot is an exception the vocabulary allows so a held note can
 * be written; it is not a rung of the ladder, and a row of pills is a row of the shapes a reader
 * points at rather than the complete grammar. A dotted figure is still drawn where the score names
 * one, and pressing a pill replaces it with the plain figure asked for.
 */
export const PLAIN_FIGURES: FigureName[] = [
  "redonda",
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
  "fusa",
  "semifusa",
];

/** What each one is called on a tooltip and to a screen reader, without the English in brackets. */
export const FIGURE_SHORT: Record<FigureName, string> = {
  redonda: "Redonda",
  blanca: "Blanca",
  dottedBlanca: "Blanca with a dot",
  negra: "Negra",
  dottedNegra: "Negra with a dot",
  corchea: "Corchea",
  semicorchea: "Semicorchea",
  fusa: "Fusa",
  semifusa: "Semifusa",
};
