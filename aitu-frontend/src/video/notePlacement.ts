/**
 * Where a note that will be written sits on the frame it came from.
 *
 * Its own module because a file that exports a component may not also export a
 * function: Vite's fast refresh stops working for it, and the lint says so.
 *
 * The arithmetic is V-05 read backwards. A note sounds when its rectangle tip
 * touches the upper line, so at time `t` that tip is `(start - t) x scrollSpeed`
 * pixels above the line and its last tip is `(end - t) x scrollSpeed` above it.
 * Putting the reading back on the picture this way is what makes it checkable:
 * if the reading is right every box lands on a rectangle.
 */

import type { Calibration, PianoKey } from "../api/frameExamples";
import type { VideoNote } from "../api/video";

/** A note as this overlay draws it, with the id the selection holds it by. */
export interface PlacedNote {
  id: string;
  note: VideoNote;
  /** Which key it is on, so the box is as wide as the key and no wider. */
  key: PianoKey;
  /** Rows of the picture: the tip is the bottom, the last tip is the top. */
  yTop: number;
  yBottom: number;
}

/** The id a note is picked by. Its pitch and its onset name it uniquely. */
export function noteId(note: VideoNote): string {
  return `${note.midi}:${note.start.toFixed(4)}`;
}

/**
 * Every note whose rectangle is somewhere on this frame, with the rows it is at.
 *
 * Only between the roll top and the upper line: below the line the rectangle has
 * gone under the keyboard and above the roll top there is no roll (V-28).
 */
export function place(
  notes: VideoNote[],
  keys: PianoKey[],
  calibration: Calibration,
  seconds: number,
  pxPerSecond: number,
): PlacedNote[] {
  if (pxPerSecond <= 0) return [];
  const byMidi = new Map(keys.map((key) => [key.midi, key]));
  const top = calibration.rollTop;
  const bottom = calibration.upperLine;
  const out: PlacedNote[] = [];
  for (const note of notes) {
    const key = byMidi.get(note.midi);
    if (!key) continue;
    const yBottom = bottom - (note.start - seconds) * pxPerSecond;
    const yTop = bottom - (note.end - seconds) * pxPerSecond;
    if (yBottom < top || yTop > bottom) continue;
    out.push({ id: noteId(note), note, key, yTop, yBottom });
  }
  return out;
}

