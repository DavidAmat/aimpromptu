/** Programmatic geometry for the 88-key placeholder keyboard. */

export type PianoKeyType = "white" | "black";

export interface PianoKeyPosition {
  row: number;
  midi: number;
  en: string;
  es: string;
  type: PianoKeyType;
  x: number;
  y: number;
  width: number;
  height: number;
  frequency: number;
}

export const PIANO_WIDTH = 1248;
export const PIANO_HEIGHT = 160;
export const WHITE_KEY_WIDTH = 24;
export const BLACK_KEY_WIDTH = 16;
export const BLACK_KEY_HEIGHT = 100;

const EN_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const ES_NAMES = [
  "Do",
  "Do#",
  "Re",
  "Re#",
  "Mi",
  "Fa",
  "Fa#",
  "Sol",
  "Sol#",
  "La",
  "La#",
  "Si",
];

function buildKeyPositions(): PianoKeyPosition[] {
  const keys: PianoKeyPosition[] = [];
  let whiteIndex = 0;

  for (let midi = 21; midi <= 108; midi += 1) {
    const pitchClass = midi % 12;
    const octave = Math.floor(midi / 12) - 1;
    const black = EN_NAMES[pitchClass].includes("#");
    const x = black
      ? whiteIndex * WHITE_KEY_WIDTH - BLACK_KEY_WIDTH / 2
      : whiteIndex * WHITE_KEY_WIDTH;

    keys.push({
      row: midi - 21,
      midi,
      en: `${EN_NAMES[pitchClass]}${octave}`,
      es: `${ES_NAMES[pitchClass]}-${octave}`,
      type: black ? "black" : "white",
      x,
      y: 0,
      width: black ? BLACK_KEY_WIDTH : WHITE_KEY_WIDTH,
      height: black ? BLACK_KEY_HEIGHT : PIANO_HEIGHT,
      frequency: 440 * 2 ** ((midi - 69) / 12),
    });

    if (!black) whiteIndex += 1;
  }
  return keys;
}

export const pianoKeyPositions = buildKeyPositions();
export const pianoKeyByRow = new Map(pianoKeyPositions.map((key) => [key.row, key]));

/**
 * Top edge of a key's lane when the keyboard stands on its end, pitch running
 * **upward** — the piano-roll convention, and the one the vertical `Piano`
 * draws.
 *
 * The geometry above is a keyboard lying flat, so `x` grows with pitch. Standing
 * it up naively maps that straight onto screen `y`, which grows downward, and the
 * roll comes out with the treble at the bottom. This is the one place that flip
 * is handled; every lane in the roll goes through it.
 */
export function laneTop(key: PianoKeyPosition): number {
  return PIANO_WIDTH - key.x - key.width;
}

export function nearestPianoKey(x: number): PianoKeyPosition {
  return pianoKeyPositions.reduce((nearest, key) =>
    Math.abs(key.x + key.width / 2 - x) < Math.abs(nearest.x + nearest.width / 2 - x)
      ? key
      : nearest,
  );
}
