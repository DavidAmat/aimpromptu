/**
 * Where things are on the Notes tab's canvas: the time axis, the 88 key rows, the keyboard strip
 * and the time ruler. Pure functions, shared by the painter and the pointer, so a click always
 * lands on what is drawn under it.
 *
 * The layout, from left to right: the vertical piano keyboard, then the notes. From top to bottom:
 * the time ruler, then one row per key, the highest key at the top. Every key has a row of the same
 * height, as in the MuScriptor examples: a rectangle never overlaps the row of the key next to it,
 * so a click on a rectangle is never ambiguous.
 */

import { KEY_COUNT } from "./rollNotes";

export interface RollView {
  /** The time at the left edge of the notes, in ms of the piece. */
  startMs: number;
  /** Zoom: pixels per second of the piece. */
  pxPerSec: number;
}

export interface RollLayout {
  width: number;
  height: number;
  /** The keys shown, lowest at the bottom: the ones the piece uses, and a few around them. */
  lowKey: number;
  highKey: number;
  /** The keyboard strip on the left. */
  keyboard: number;
  /** The time ruler at the top. */
  ruler: number;
  /** One key row. */
  rowHeight: number;
}

export const KEYBOARD_WIDTH = 46;
export const RULER_HEIGHT = 24;
export const MIN_PX_PER_SEC = 8;
export const MAX_PX_PER_SEC = 2400;
export const DEFAULT_PX_PER_SEC = 90;

export function rollLayout(width: number, height: number, lowKey = 0, highKey = KEY_COUNT - 1): RollLayout {
  return {
    width,
    height,
    lowKey,
    highKey,
    keyboard: KEYBOARD_WIDTH,
    ruler: RULER_HEIGHT,
    rowHeight: Math.max(1, (height - RULER_HEIGHT) / (highKey - lowKey + 1)),
  };
}

/** Keys shown above and below the notes. */
const KEY_MARGIN = 2;
/** The fewest rows shown, so a piece of a few keys does not get rows as tall as a hand. */
const MIN_ROWS = 36;
/** What the live view shows before any note arrived: C2 to C7, where most piano music is. */
export const DEFAULT_KEYS: [number, number] = [15, 75];

/**
 * The keys to show: `current` widened to the notes' keys and a margin, at least {@link MIN_ROWS},
 * inside the keyboard. It only grows, so the rows do not jump while notes arrive or move.
 */
export function widenKeys(current: [number, number] | null, notes: [number, number] | null): [number, number] {
  let low = current?.[0] ?? KEY_COUNT;
  let high = current?.[1] ?? -1;
  if (notes) {
    low = Math.min(low, notes[0] - KEY_MARGIN);
    high = Math.max(high, notes[1] + KEY_MARGIN);
  }
  if (high < low) [low, high] = DEFAULT_KEYS;
  const missing = MIN_ROWS - (high - low + 1);
  if (missing > 0) {
    low -= Math.floor(missing / 2);
    high += Math.ceil(missing / 2);
  }
  if (low < 0) {
    high = Math.min(KEY_COUNT - 1, high - low);
    low = 0;
  }
  if (high > KEY_COUNT - 1) {
    low = Math.max(0, low - (high - (KEY_COUNT - 1)));
    high = KEY_COUNT - 1;
  }
  return [low, high];
}

/** The width of the notes area. */
export function notesWidth(layout: RollLayout): number {
  return Math.max(1, layout.width - layout.keyboard);
}

/** How much time the notes area shows, in ms. */
export function spanMs(layout: RollLayout, view: RollView): number {
  return (notesWidth(layout) / view.pxPerSec) * 1000;
}

export function xOf(layout: RollLayout, view: RollView, ms: number): number {
  return layout.keyboard + ((ms - view.startMs) * view.pxPerSec) / 1000;
}

export function msAt(layout: RollLayout, view: RollView, x: number): number {
  return view.startMs + ((x - layout.keyboard) * 1000) / view.pxPerSec;
}

/** The top of a key's row. Key 0 is A0 (MIDI 21); the highest key shown is at the top. */
export function yOf(layout: RollLayout, key: number): number {
  return layout.ruler + (layout.highKey - key) * layout.rowHeight;
}

/** The key whose row holds `y`, or -1 above or below the rows. */
export function keyAt(layout: RollLayout, y: number): number {
  const row = Math.floor((y - layout.ruler) / layout.rowHeight);
  const key = layout.highKey - row;
  return key < layout.lowKey || key > layout.highKey ? -1 : key;
}

/** The key under `y`, kept inside the rows shown: for a drag that leaves them. */
export function clampedKeyAt(layout: RollLayout, y: number): number {
  const key = layout.highKey - Math.floor((y - layout.ruler) / layout.rowHeight);
  return Math.min(layout.highKey, Math.max(layout.lowKey, key));
}

/** Keep the view inside the piece, with a little room after its end. */
export function clampRollView(view: RollView, layout: RollLayout, durationMs: number): RollView {
  const pxPerSec = Math.min(MAX_PX_PER_SEC, Math.max(MIN_PX_PER_SEC, view.pxPerSec));
  const span = spanMs(layout, { startMs: 0, pxPerSec });
  const last = Math.max(0, durationMs + span * 0.05 - span);
  return { pxPerSec, startMs: Math.min(last, Math.max(0, view.startMs)) };
}

/** Zoom by `factor` (above 1 is in) around `anchorMs`, which stays under the pointer. */
export function zoomRoll(
  view: RollView,
  factor: number,
  anchorMs: number,
  layout: RollLayout,
  durationMs: number,
): RollView {
  const pxPerSec = Math.min(MAX_PX_PER_SEC, Math.max(MIN_PX_PER_SEC, view.pxPerSec * factor));
  const startMs = anchorMs - ((anchorMs - view.startMs) * view.pxPerSec) / pxPerSec;
  return clampRollView({ startMs, pxPerSec }, layout, durationMs);
}

/** The zoom that shows the whole piece. */
export function wholeRollView(layout: RollLayout, durationMs: number): RollView {
  const pxPerSec = (notesWidth(layout) / Math.max(1000, durationMs * 1.02)) * 1000;
  return clampRollView({ startMs: 0, pxPerSec }, layout, durationMs);
}

/** The same zoom with `ms` a little after the left edge: where playback continues. */
export function pageRollTo(view: RollView, ms: number, layout: RollLayout, durationMs: number): RollView {
  return clampRollView({ ...view, startMs: ms - spanMs(layout, view) * 0.05 }, layout, durationMs);
}

/** A time grid step, in seconds, that leaves at least `minPx` between two lines. */
export function gridStep(pxPerSec: number, minPx = 70): number {
  for (const step of [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300]) {
    if (step * pxPerSec >= minPx) return step;
  }
  return 600;
}

/** Move a time by a whole number of time frames (10 ms): what every edit on the roll snaps to. */
export const SNAP_MS = 10;
export function snapDelta(ms: number, step = SNAP_MS): number {
  return Math.round(ms / step) * step;
}
