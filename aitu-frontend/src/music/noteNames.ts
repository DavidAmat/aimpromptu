/**
 * Note names for the animated views.
 *
 * The keyboard geometry carries both an English and a Spanish name per key, and
 * the roll used to print the Spanish one — `Do#-5`, five characters, inside a
 * rectangle that is often twenty pixels wide. English is two or three: `C#5`.
 * On a view whose whole job is showing a lot of notes at once, that is the
 * difference between a label and a smear, so these views print English and the
 * sheet keeps whatever it prints.
 *
 * The accidental is never dropped. A label short of room falls back to the
 * pitch class alone (`C#`) and then to nothing at all — printing `C` for a C
 * sharp would be a wrong answer rather than a short one.
 */

const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"] as const;

/** `C#5` — pitch class and octave. */
export function noteName(midi: number): string {
  return `${SHARP_NAMES[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
}

/** `C#` — pitch class alone, for a rectangle with no room for the octave. */
export function pitchClassName(midi: number): string {
  return SHARP_NAMES[((midi % 12) + 12) % 12];
}

/** Roughly how wide a label is at a given font size, in pixels. */
function labelWidth(text: string, fontSize: number): number {
  // Montserrat's digits and caps are close to 0.62 em; the sharp is narrower but
  // rounding up is the safe direction when the question is "does it fit".
  return text.length * fontSize * 0.62;
}

/**
 * The longest name that fits the box, or `null` when nothing does.
 *
 * `null` is a real answer and the caller must draw no text for it. A label that
 * overflows its rectangle reads as belonging to the note next door, which is
 * worse than no label — this is the fault the Epic 8 view had with its fixed
 * 10 px name spilling out of short rectangles.
 */
export function fittingNoteLabel(
  midi: number,
  boxWidth: number,
  boxHeight: number,
  fontSize: number,
): string | null {
  // One pixel of air each side, and the cap height has to clear the box.
  if (boxHeight < fontSize + 2) return null;
  const room = boxWidth - 4;

  const full = noteName(midi);
  if (labelWidth(full, fontSize) <= room) return full;

  const short = pitchClassName(midi);
  if (labelWidth(short, fontSize) <= room) return short;

  return null;
}
