/**
 * Canonical 88-key grand piano row order and Spanish -> VexFlow mapping.
 * Mirrors `build_grand_piano_rows()` in the aitu-backend service.
 */

const CHROMATIC_NOTES = [
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

/** Spanish solfège base -> VexFlow letter, plus accidental when sharp. */
const SPANISH_TO_VEXFLOW: Record<string, { letter: string; accidental?: string }> = {
  Do: { letter: "c" },
  "Do#": { letter: "c", accidental: "#" },
  Re: { letter: "d" },
  "Re#": { letter: "d", accidental: "#" },
  Mi: { letter: "e" },
  Fa: { letter: "f" },
  "Fa#": { letter: "f", accidental: "#" },
  Sol: { letter: "g" },
  "Sol#": { letter: "g", accidental: "#" },
  La: { letter: "a" },
  "La#": { letter: "a", accidental: "#" },
  Si: { letter: "b" },
};

/** 88-key row order, lowest to highest: La-0, La#-0, Si-0, Do-1, …, Do-8. */
export function buildGrandPianoRows(): string[] {
  const rows: string[] = ["La-0", "La#-0", "Si-0"];

  for (let octave = 1; octave < 8; octave++) {
    for (const note of CHROMATIC_NOTES) {
      rows.push(`${note}-${octave}`);
    }
  }

  rows.push("Do-8");

  if (rows.length !== 88) {
    throw new Error(`Expected 88 rows, built ${rows.length}`);
  }
  return rows;
}

/** Cached canonical rows; rebuilt list is identical every call. */
export const GRAND_PIANO_ROWS = buildGrandPianoRows();

/** Map row index to its custom note name using the score's `rows` (or the canonical table). */
export function rowIndexToCustomNote(rowIndex: number, rows?: string[]): string {
  const table = rows ?? GRAND_PIANO_ROWS;
  const note = table[rowIndex];
  if (note === undefined) {
    throw new Error(`Row index ${rowIndex} out of range (0..${table.length - 1})`);
  }
  return note;
}

/** "Do-3" -> { key: "c/3" }; "Fa#-5" -> { key: "f/5", accidental: "#" }. */
export function customNoteToVexFlow(noteName: string): { key: string; accidental?: string } {
  const dash = noteName.lastIndexOf("-");
  if (dash === -1) {
    throw new Error(`Malformed note name '${noteName}' (expected e.g. "Do-3")`);
  }

  const base = noteName.slice(0, dash);
  const octave = noteName.slice(dash + 1);
  const mapped = SPANISH_TO_VEXFLOW[base];
  if (!mapped) {
    throw new Error(`Unknown note '${base}' in '${noteName}'`);
  }

  return {
    key: `${mapped.letter}/${octave}`,
    accidental: mapped.accidental,
  };
}

/**
 * Major key signatures. `label` is the Spanish name shown in the UI,
 * `accidentals` is the visual hint, `vex` is the VexFlow key spec passed
 * to `stave.addKeySignature`. The empty `vex` ("C") draws no accidentals.
 */
export const KEY_SIGNATURES: { label: string; accidentals: string; vex: string }[] = [
  { label: "Do-Mayor", accidentals: "", vex: "C" },
  { label: "Sol-Mayor", accidentals: "#", vex: "G" },
  { label: "Re-Mayor", accidentals: "##", vex: "D" },
  { label: "La-Mayor", accidentals: "###", vex: "A" },
  { label: "Mi-Mayor", accidentals: "####", vex: "E" },
  { label: "Si-Mayor", accidentals: "#####", vex: "B" },
  { label: "Fa#-Mayor", accidentals: "######", vex: "F#" },
  { label: "Do#-Mayor", accidentals: "#######", vex: "C#" },
  { label: "Fa-Mayor", accidentals: "b", vex: "F" },
  { label: "Sib-Mayor", accidentals: "bb", vex: "Bb" },
  { label: "Mib-Mayor", accidentals: "bbb", vex: "Eb" },
  { label: "Lab-Mayor", accidentals: "bbbb", vex: "Ab" },
  { label: "Reb-Mayor", accidentals: "bbbbb", vex: "Db" },
  { label: "Solb-Mayor", accidentals: "bbbbbb", vex: "Gb" },
  { label: "Dob-Mayor", accidentals: "bbbbbbb", vex: "Cb" },
];
