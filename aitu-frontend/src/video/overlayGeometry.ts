/**
 * The piano overlay: per-key borders become every key and its lane (V-38).
 *
 * The twin of `aitu-backend/src/aitu_backend/video/geometry.py`. The two cannot
 * share the code — the calibration UI redraws the overlay on every drag, and a
 * round trip per drag is not a UI — so they share a fixture instead:
 * `npm run check:geometry` asserts this file against
 * `aitu-backend/tests/fixtures/video/geometry-fixture.json`, and the backend's
 * own `test_video_geometry.py` asserts the Python against the same file. Neither
 * can drift without one of those failing.
 *
 * Three rules it obeys and never bends:
 *
 * - **The pitch class comes from the black key pattern, the octave from the
 *   user** (V-10). Nothing here looks at a colour.
 * - **A lane is the key widened by a margin on both sides** (V-13), and the
 *   margin is in the **local** white key width — the width of the key being
 *   read — because perspective makes one white key wider than another (V-38).
 * - **A lane is a vertical strip of the picture** whatever the camera did to the
 *   piano, because the rectangles fall straight down the picture (V-39). A
 *   border becomes a picture x by projecting the top edge of the rectangle onto
 *   the horizontal: `x = rect.x + u · cos(angle)`.
 */

import type { Calibration, KeyLane, PianoKey } from "../api/frameExamples";

/** White key index inside an octave, for the seven white pitch classes. */
export const WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11];
/** The white pitch classes a black key follows: C#, D#, F#, G#, A#. */
export const WHITE_WITH_BLACK_AFTER = new Set([0, 2, 5, 7, 9]);

const EN_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const ES_NAMES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"];

/** The lane margin of V-13, in local white key widths. */
export const DEFAULT_LANE_MARGIN = 0.25;

export function isBlackPitchClass(midi: number): boolean {
  return [1, 3, 6, 8, 10].includes(((midi % 12) + 12) % 12);
}

export function noteNames(midi: number): { en: string; es: string } {
  const octave = Math.floor(midi / 12) - 1;
  const pitchClass = ((midi % 12) + 12) % 12;
  return { en: `${EN_NAMES[pitchClass]}${octave}`, es: `${ES_NAMES[pitchClass]}-${octave}` };
}

/** How many black keys the pattern puts between `whiteCount` white keys. */
export function expectedBlackCount(firstWhitePitchClass: number, whiteCount: number): number {
  const first = WHITE_PITCH_CLASSES.indexOf(firstWhitePitchClass);
  let count = 0;
  for (let i = 0; i < whiteCount - 1; i += 1) {
    if (WHITE_WITH_BLACK_AFTER.has(WHITE_PITCH_CLASSES[(first + i) % 7])) count += 1;
  }
  return count;
}

/** Degrees to radians the way Python's `math.radians` does it, so the twins agree to the bit. */
const radians = (degrees: number) => degrees * (Math.PI / 180);

/** The picture x under a point `u` along the top edge of the rectangle. */
export function topEdgeX(cal: Calibration, u: number): number {
  return cal.pianoRect.x + u * Math.cos(radians(cal.pianoRect.angle));
}

/** The inverse: how far along the top edge a picture x sits. */
export function topEdgeU(cal: Calibration, x: number): number {
  return (x - cal.pianoRect.x) / Math.cos(radians(cal.pianoRect.angle));
}

/** The picture x of every white key border, left to right: one more than the keys. */
export function whiteBorders(cal: Calibration): number[] {
  return cal.whiteBorders.map((u) => topEdgeX(cal, u));
}

/**
 * The median white key width, the way the backend derives it: the upper median
 * of the sorted widths. The unit of every length that is not about one key.
 */
export function medianWhiteWidth(cal: Calibration): number {
  const widths = cal.whiteBorders.slice(1).map((b, i) => b - cal.whiteBorders[i]);
  widths.sort((a, b) => a - b);
  return widths[Math.floor(widths.length / 2)];
}

/**
 * Every key the picture shows, sorted by pitch.
 *
 * The white keys come from their borders. A black key sits between two white
 * keys whose pitch classes differ by two semitones — that is the whole rule, and
 * it is why no black key appears between Mi and Fa or between Si and Do — and
 * its own borders are the next entry of the calibration's list.
 */
export function buildKeys(cal: Calibration): PianoKey[] {
  const borders = whiteBorders(cal);
  const keys: PianoKey[] = [];

  const firstIndex = WHITE_PITCH_CLASSES.indexOf(cal.firstWhitePitchClass);
  const whites: number[] = [];

  for (let i = 0; i < borders.length - 1; i += 1) {
    const step = firstIndex + i;
    const octave = cal.firstWhiteOctave + Math.floor(step / 7);
    const midi = 12 * (octave + 1) + WHITE_PITCH_CLASSES[step % 7];
    whites.push(midi);
    const names = noteNames(midi);
    keys.push({
      midi,
      kind: "white",
      nameEn: names.en,
      nameEs: names.es,
      left: borders[i],
      right: borders[i + 1],
      mid: (borders[i] + borders[i + 1]) / 2,
    });
  }

  let slot = 0;
  for (let i = 0; i < whites.length - 1; i += 1) {
    if (!WHITE_WITH_BLACK_AFTER.has(((whites[i] % 12) + 12) % 12)) continue;
    const black = cal.blackBorders[slot];
    slot += 1;
    const blackMidi = whites[i] + 1;
    const left = topEdgeX(cal, black.left);
    const right = topEdgeX(cal, black.right);
    const names = noteNames(blackMidi);
    keys.push({
      midi: blackMidi,
      kind: "black",
      nameEn: names.en,
      nameEs: names.es,
      left,
      right,
      mid: (left + right) / 2,
    });
  }

  keys.sort((a, b) => a.midi - b.midi);
  return keys;
}

/**
 * The local white key width of every key, by MIDI pitch (V-38): a white key's
 * own width; for a black key, the mean of the two white keys it stands between.
 */
export function localWidths(cal: Calibration): Map<number, number> {
  const keys = buildKeys(cal);
  const whiteWidth = new Map<number, number>();
  for (const key of keys) if (key.kind === "white") whiteWidth.set(key.midi, key.right - key.left);
  const out = new Map<number, number>();
  for (const key of keys) {
    if (key.kind === "white") out.set(key.midi, whiteWidth.get(key.midi) as number);
    else {
      const below = whiteWidth.get(key.midi - 1) as number;
      const above = whiteWidth.get(key.midi + 1) as number;
      out.set(key.midi, (below + above) / 2);
    }
  }
  return out;
}

/** One vertical lane per key, widened by `margin` local white key widths (V-13). */
export function buildLanes(cal: Calibration, margin = DEFAULT_LANE_MARGIN): KeyLane[] {
  const widths = localWidths(cal);
  return buildKeys(cal).map((key) => {
    const width = widths.get(key.midi) as number;
    return {
      midi: key.midi,
      kind: key.kind,
      x0: key.left - margin * width,
      x1: key.right + margin * width,
      mid: key.mid,
    };
  });
}

/**
 * How many rows above the upper line are not trusted (V-08, V-24).
 *
 * A video measures it from the motion of the roll and stores it; a screenshot
 * has no motion to measure it from, so it falls back to the measured default of
 * 1.75 median white key widths — the median over the 21 examples was 1.73.
 */
export function guardBandPx(cal: Calibration, defaultKeys = 1.75): number {
  return cal.guardBand > 0 ? cal.guardBand : defaultKeys * cal.whiteWidth;
}

/**
 * The octave to offer for the leftmost white key, from how many keys there are.
 *
 * 88 keys start at A0 and 61 start at C2. It is a default the user can change,
 * never an inference (V-10). The thresholds sit below the counts they stand for
 * on purpose: a screenshot often crops one or two keys off an end.
 */
export function defaultOctaveFor(whiteCount: number): number {
  if (whiteCount >= 45) return 0;
  if (whiteCount >= 30) return 2;
  return 3;
}
