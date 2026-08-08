/**
 * How a timestamp is *shown*. The format itself lives in `src/audio/time.ts`;
 * this is the presentation half of the same rule.
 *
 * A timestamp must never wrap. Wrapped times turn a table into a ragged mess
 * and cost more vertical space than the column ever saved horizontally — so
 * any cell holding one gets `timestampSx` and, if it is a column, a width from
 * here rather than a guess.
 */

import type { SxProps, Theme } from "@mui/material/styles";

/**
 * Monospace, tabular figures, no wrapping. Callers add size and colour.
 *
 * `tabular-nums` matters as much as the font: without it the digits shift
 * sideways as a counter ticks, which reads as flicker.
 */
export const timestampSx: SxProps<Theme> = {
  fontFamily: "monospace",
  fontVariantNumeric: "tabular-nums",
  whiteSpace: "nowrap",
};

/**
 * Width of a frame-label column (`f:1234 · 01:23.45` at 11px monospace, plus
 * padding). Deliberately roomy: the column is cheap, a wrapped label is not.
 */
export const FRAME_LABEL_WIDTH = 140;

/**
 * Width of a frame-*number* column — `1234` at 10px monospace, plus padding.
 *
 * The matrix grid prints the number alone. Its timestamp has not been lost, it
 * has been moved: the transport above the grid shows the cursor's time once,
 * which is the only place it was ever read from, and reclaiming the other ~90px
 * per row is most of what lets all 88 keys fit on screen without scrolling.
 */
export const FRAME_NUMBER_WIDTH = 52;
