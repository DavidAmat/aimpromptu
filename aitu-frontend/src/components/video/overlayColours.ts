/**
 * The colours the video overlays draw with, and the states they stand for.
 *
 * Kept out of the components so each of those exports components only — Vite's
 * fast refresh stops working for a file that exports both. Every colour comes
 * from the palette; no component in this folder writes a hex literal.
 */

import type { KeyState } from "../../api/frameExamples";
import { palette, semantic } from "../../ui";

/** What one key is marked as. `skip` is the answer "the picture cannot say". */
export type MarkState = KeyState | "skip";

/**
 * A key marked by hand, or called by the detector.
 *
 * Released is transparent because released is the default and is never written
 * down (V-19): there is nothing to draw.
 */
export const markColours: Record<MarkState, string> = {
  onset: semantic.rightHand.onset,
  sustain: semantic.rightHand.sustain,
  skip: palette.dark.Orange,
  released: "transparent",
};

/** The two rectangles the user places on the picture to build the overlay. */
export const rectColours = {
  white: palette.dark.Blue,
  black: palette.dark.Pink,
} as const;

/** A run the detector found, coloured by what the frame window rule made of it. */
export const runColours: Record<KeyState, string> = {
  onset: semantic.rightHand.onset,
  sustain: semantic.leftHand.onset,
  released: palette.dark.Gray,
};

/**
 * A run the momentum rule refused, because a neighbouring sampled frame holds it
 * in exactly the same place (V-33). It is drawn rather than hidden: a rule may
 * flag a run, and a refusal has to be something you can look at (V-30).
 */
export const refusedColour = palette.dark.Lavender;
