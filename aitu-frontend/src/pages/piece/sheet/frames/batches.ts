/** What the Enhance with AI dialog, its run panel and the sheet share about the batches of an AI run (2026-10-30). */

/** The width of the dialog and of the panel of a run, at the right of the sheet, in pixels; the page lays the sheet out
 * beside them. */
export const ENHANCE_PANEL_WIDTH = 560;

/** One colour per batch, in turn: distinct hues that stay readable under the notes at a light fill. */
export const BATCH_COLOURS = ["#2563eb", "#d97706", "#059669", "#db2777", "#7c3aed", "#0891b2", "#65a30d", "#dc2626"];

/** The batches of an AI run shown on the sheet: their frames, and the staff when the run writes one hand. */
export interface BatchPreview {
  windows: readonly (readonly [number, number])[];
  staff: 1 | 2 | null;
}
