/**
 * The selected region as the Audio tab edits it: a list of cuts, in 10 ms time frames.
 *
 * The audio file is never changed. A cut is `[startFrame, endFrame)` of the original audio, and the
 * piece is every frame that is not in a cut (implementation 08, plan section 9.2). A time frame is
 * also one column of the piano matrix notation at 10 ms, so a cut always falls on a column border.
 *
 * The rules here are the backend's own (`aitu_backend/audio/frames.py`, `normalize_cuts`): sorted,
 * clipped to the audio, empty ranges dropped, and two cuts that overlap or touch stored as one. The
 * page keeps its cuts in that form at every step, so an unsaved list compares equal to the saved
 * one exactly when saving it would change nothing.
 *
 * Pure functions only, so `npm run check:cuts` checks them without a browser.
 */

import type { Cut, KeptRange } from "../api";

/** Sorted, clipped to `[0, totalFrames)`, empty ranges dropped, touching ranges merged. */
export function normalizeCuts(cuts: readonly Cut[], totalFrames?: number): Cut[] {
  const ranges: Cut[] = [];
  for (const [rawStart, rawEnd] of cuts) {
    let start = Math.max(0, Math.round(rawStart));
    let end = Math.round(rawEnd);
    if (totalFrames !== undefined) {
      start = Math.min(start, totalFrames);
      end = Math.min(end, totalFrames);
    }
    if (end > start) ranges.push([start, end]);
  }
  ranges.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Cut[] = [];
  for (const [start, end] of ranges) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

/** The cuts with `[start, end)` deleted too. */
export function addCut(cuts: readonly Cut[], start: number, end: number, totalFrames: number): Cut[] {
  return normalizeCuts([...cuts, [start, end]], totalFrames);
}

/** The cuts with `[start, end)` put back: every cut loses the part inside the range. */
export function restoreRange(cuts: readonly Cut[], start: number, end: number): Cut[] {
  const out: Cut[] = [];
  for (const [cutStart, cutEnd] of cuts) {
    if (cutEnd <= start || cutStart >= end) {
      out.push([cutStart, cutEnd]);
      continue;
    }
    if (cutStart < start) out.push([cutStart, start]);
    if (cutEnd > end) out.push([end, cutEnd]);
  }
  return normalizeCuts(out);
}

/** The cut that holds `frame`, or `null`. */
export function cutAt(cuts: readonly Cut[], frame: number): Cut | null {
  for (const cut of cuts) {
    if (frame >= cut[0] && frame < cut[1]) return cut;
    if (cut[0] > frame) break;
  }
  return null;
}

/** Whether any cut has a frame inside `[start, end)`. */
export function overlapsCut(cuts: readonly Cut[], start: number, end: number): boolean {
  return cuts.some(([cutStart, cutEnd]) => cutStart < end && cutEnd > start);
}

/** Frames removed by the cuts. */
export function cutFrames(cuts: readonly Cut[]): number {
  return cuts.reduce((sum, [start, end]) => sum + (end - start), 0);
}

/** Two normalized lists hold the same cuts. */
export function sameCuts(a: readonly Cut[], b: readonly Cut[]): boolean {
  return a.length === b.length && a.every((cut, index) => cut[0] === b[index]![0] && cut[1] === b[index]![1]);
}

/** The frame table, one row per kept range, as `GET /audio/{uuid}/cuts` answers it. */
export function keptRanges(cuts: readonly Cut[], totalFrames: number): KeptRange[] {
  const rows: KeptRange[] = [];
  let cursor = 0;
  let kept = 0;
  for (const [start, end] of [...normalizeCuts(cuts, totalFrames), [totalFrames, totalFrames] as Cut]) {
    if (start > cursor) {
      rows.push({ pieceStart: kept, originalStart: cursor, length: start - cursor });
      kept += start - cursor;
    }
    cursor = Math.max(cursor, end);
  }
  return rows;
}

/**
 * Where the player must go when it is at `frame` of the original audio, playing only the kept
 * frames: the end of the cut it is in, or the end of a cut that starts less than `lookahead` frames
 * ahead. `null` when it can keep playing.
 *
 * The lookahead is there because the player checks its position once per screen refresh (about
 * 16 ms). Without it, up to one refresh of a deleted part would be heard before each jump.
 */
export function jumpTarget(cuts: readonly Cut[], frame: number, lookahead = 0): number | null {
  for (const [start, end] of cuts) {
    if (frame < start - lookahead) return null;
    if (frame < end) return end;
  }
  return null;
}

/** The first kept frame at or after `frame`, or `null` when every frame after it is cut. */
export function firstKeptFrom(cuts: readonly Cut[], frame: number, totalFrames: number): number | null {
  const cut = cutAt(cuts, frame);
  const at = cut ? cut[1] : frame;
  return at < totalFrames ? at : null;
}
