/**
 * The fixed values of the Sheet step that several of its modules share: the colours of the hands on
 * the keyboards, and how a time is written.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2); what only the old sheet used went with
 * it in implementation 03, Phase 10.
 */

import { palette, semantic } from "../../../ui";

/** Which staff a printed note is on. */
export type PrintedHand = "right" | "left";

/**
 * Which hand a colour on the keyboard stands for.
 *
 * The page draws two staves and the keyboard draws one row of keys, so without a colour per hand a
 * reader looking at a chord on it cannot tell which hand is holding which note — which is most of
 * what they opened the panel to find out. Blue is the right hand everywhere in this app already;
 * orange is the left here, rather than the green the roll uses, because green beside blue at this
 * size is two shades of the same thing.
 */
export const HAND_COLOUR: Record<PrintedHand, string> = {
  right: semantic.rightHand.onset,
  left: palette.dark.Orange,
};

/**
 * The same two, paler, for a key **still sounding** from a note struck in an earlier column.
 *
 * Without the second shade the panel says something it does not mean. At f103 of Superestrella the
 * right hand strikes B6 and is still holding the B5 it struck at f97, so two Si light up while the
 * sheet draws one notehead at that column — and a reader comparing the two reasonably concludes the
 * keyboard is wrong. It is not: both keys really are down. What it could not say is *which* of them
 * begins here.
 *
 * It matters more than it used to, because a key is now something you click. Clicking the pale B5
 * takes off a note that starts three columns back, and the reader has to be able to see that before
 * they press rather than after.
 *
 * The pale blue is the one the roll already uses for a held note, so a reader who has seen one has
 * seen both.
 */
export const HELD_COLOUR: Record<PrintedHand, string> = {
  right: semantic.rightHand.sustain,
  left: palette.light.Orange,
};

/**
 * The four things a lit key can mean, in the order they are read.
 *
 * Each hand twice: struck in the column under the cursor, and still sounding from a note struck
 * earlier — whose notehead is back where it began rather than under the cursor. Naming both is what
 * answers "why are two Si lit when the page draws one", and it answers it beside the colours
 * instead of in a paragraph under the keyboard.
 */
export const KEY_LEGEND: { colour: string; label: string }[] = [
  { colour: HAND_COLOUR.right, label: "Right hand (RH) onset" },
  { colour: HELD_COLOUR.right, label: "RH sustain" },
  { colour: HAND_COLOUR.left, label: "Left hand (LH) onset" },
  { colour: HELD_COLOUR.left, label: "LH sustain" },
];

/** `mm:ss.cc`, so a column range can be read as a moment in the recording. */
export function formatSeconds(seconds: number): string {
  const total = Math.max(0, Math.round(seconds * 100));
  const minutes = Math.floor(total / 6000);
  const rest = Math.floor((total % 6000) / 100);
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}.${String(
    total % 100,
  ).padStart(2, "0")}`;
}

/** One note the keyboard panel can point at: what it is, who holds it, and where it began. */
export interface SoundingNote {
  row: number;
  hand: PrintedHand;
  /** The column the note was struck in, which is how every mark on this page addresses one. */
  onsetFrame: number;
}
