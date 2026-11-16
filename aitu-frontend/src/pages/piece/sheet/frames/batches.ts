/** What the Enhance with AI dialog, its run panel and the sheet share about the batches of an AI run (2026-10-30). */

/** The width of the dialog and of the panel of a run, at the right of the sheet, in pixels; the page lays the sheet out
 * beside them. */
export const ENHANCE_PANEL_WIDTH = 560;

/** One colour per batch, in turn: distinct hues that stay readable under the notes at a light fill. */
export const BATCH_COLOURS = ["#2563eb", "#d97706", "#059669", "#db2777", "#7c3aed", "#0891b2", "#65a30d", "#dc2626"];

/** The colour of the reference of **Copy this style**: apart from the batches'. */
export const REFERENCE_COLOUR = "#334155";

/** The colour of the batch at this place of the list, as the sheet and the panels draw it. */
export const batchColour = (index: number): string => BATCH_COLOURS[index % BATCH_COLOURS.length];

/** The batches of an AI run shown on the sheet: their frames, and the staff when the run writes one hand. */
export interface BatchPreview {
  windows: readonly (readonly [number, number])[];
  staff: 1 | 2 | null;
  /** The place of each window in the dialog's list, when some are left out (a passage not ticked); else their order. */
  places?: readonly number[];
  /** **Copy this style**: the reference, drawn in its own colour and named. */
  reference?: readonly [number, number];
}

/** The key of a passage of Copy this style in the list of ticks. */
export const passageKey = (passage: { start: number; end: number }): string => `${passage.start}-${passage.end}`;
