/**
 * What the two toolboxes of the new sheet share (implementation 03, Phase 7): the figures as the backend numbers
 * them, the armaduras as fifths, the ornaments, how a note's ref names its column and key, and (Phase 8A) the column
 * and the hand of the note toolbox's chord keyboard.
 */

import { KEY_LABELS, KEY_SIGNATURES, type FigureName, type SheetNote } from "../../../../api";

/** The seven plain figures, longest first, as the backend numbers them (4 is a negra). */
export const FIGURES: { figure: number; name: FigureName }[] = [
  { figure: 1, name: "redonda" },
  { figure: 2, name: "blanca" },
  { figure: 4, name: "negra" },
  { figure: 8, name: "corchea" },
  { figure: 16, name: "semicorchea" },
  { figure: 32, name: "fusa" },
  { figure: 64, name: "semifusa" },
];

export const FINGERS = [1, 2, 3, 4, 5] as const;

/** The ornaments of the note toolbox: written over the first picked onset, the others played inside it. */
export const SPAN_ORNAMENTS = [
  { kind: "trill", glyph: "tr", title: "Write these notes as one held note with a trill" },
  { kind: "mordent", glyph: "mord", title: "Write these notes as one note with a mordent" },
  { kind: "turn", glyph: "turn", title: "Write these notes as one note with a turn (grupetto)" },
] as const;

/** The ornaments of one chord. */
export const CHORD_ORNAMENTS = [
  { kind: "arpeggio", glyph: "arp", title: "Roll the chord (arpeggio)" },
  { kind: "fermata", glyph: "ferm", title: "A fermata over the chord" },
] as const;

/** The armaduras, from seven bemoles to seven sostenidos, with the names of the old sheet's picker. */
export const ARMADURAS: { fifths: number; label: string }[] = KEY_SIGNATURES.map((name) => ({
  fifths: fifthsOf(name),
  label: KEY_LABELS[name],
})).sort((a, b) => a.fifths - b.fifths);

function fifthsOf(name: (typeof KEY_SIGNATURES)[number]): number {
  const sharps = ["C", "G", "D", "A", "E", "B", "F#", "C#"];
  const flats = ["C", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"];
  return sharps.includes(name) ? sharps.indexOf(name) : -flats.indexOf(name);
}

/** The major key of an armadura, for a button: `Use D major here`. */
export function keyName(fifths: number): string {
  const label = ARMADURAS.find((one) => one.fifths === fifths)?.label ?? "";
  return label.split(" / ")[0] ?? "";
}

export function frameOf(ref: string): number {
  return Number(ref.split(":")[0]);
}

/**
 * The frames of a marked stretch (implementation 04-3, Phase 2b): the frame numbers of its first and last columns, as
 * the sheet prints them, so that the user can name the place ("From frame 112 to frame 240"; one column: "Frame 112").
 */
export function framesLabel(range: { start: number; end: number }, columns: readonly { frame: number }[]): string {
  const inside = columns.filter((column) => column.frame >= range.start && column.frame < range.end);
  const first = inside[0]?.frame ?? range.start;
  const last = inside[inside.length - 1]?.frame ?? first;
  return last === first ? `Frame ${first}` : `From frame ${first} to frame ${last}`;
}

export function midiOf(ref: string): number {
  return Number(ref.split(":")[1]);
}

/** The one drawn column the notes are in (both hands share it), or `null` when they are in several or none. */
export function oneColumn(notes: readonly SheetNote[]): number | null {
  const frames = new Set(notes.map((note) => frameOf(note.ref)));
  return frames.size === 1 ? [...frames][0]! : null;
}

/**
 * The hand a key added to the chord keyboard goes to: the hand of the picked notes, or, with both hands picked,
 * the hand of the column's note nearest to the key (the right hand on a tie).
 */
export function handForKey(midi: number, picked: readonly SheetNote[], column: readonly SheetNote[]): SheetNote["hand"] {
  const hands = new Set(picked.map((note) => note.hand));
  if (hands.size === 1) return [...hands][0]!;
  let best: SheetNote | null = null;
  for (const note of column) {
    const away = Math.abs(midiOf(note.ref) - midi);
    const bestAway = best === null ? Infinity : Math.abs(midiOf(best.ref) - midi);
    if (away < bestAway || (away === bestAway && note.hand === "right")) best = note;
  }
  return best?.hand ?? "right";
}

/** A chord of one hand: its notes share the column and the hand. */
export function chordOf(note: SheetNote): string {
  return `${note.hand}:${frameOf(note.ref)}`;
}

/** The main (not grace) columns of each hand, in order: what "the note before" means for a beam. */
export function handColumns(notes: readonly SheetNote[]): Record<SheetNote["hand"], number[]> {
  const out: Record<SheetNote["hand"], Set<number>> = { right: new Set(), left: new Set() };
  for (const note of notes) if (!note.grace) out[note.hand].add(frameOf(note.ref));
  return {
    right: [...out.right].sort((a, b) => a - b),
    left: [...out.left].sort((a, b) => a - b),
  };
}
