/**
 * The fixed values of the Sheet step: the colours of the keyboard panels, the pills of the range
 * toolbox, the figure ladder, and the small helpers several of its modules share.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

import { palette, semantic } from "../../../ui";
import { ApiError, type FigureName } from "../../../api";
import type { Clef, FingerNumber, OttavaKind } from "@aimpromptu/grid-notation";
import type { NoteRef, PrintedHand } from "../../../music/renderOverrides";

export const NAMEABLE_FIGURES: FigureName[] = [
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
];

/** No note is moved by hand any more: a corrected hand is written onto the recording. */
export const NO_HANDS: ReadonlyMap<NoteRef, PrintedHand> = new Map();

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

/** What a decoration note is drawn in on the keyboard, and what the note it leans on is drawn in. */
export const DECORATION_COLOUR = palette.dark.Pink;
export const PRINCIPAL_COLOUR = palette.dark.Lavender;

/**
 * The figures that print with flags, and so can share a beam.
 *
 * A negra and anything longer has no beam to share, which is why **Beam all** stands down on them
 * rather than drawing something that is not a beam. The dotted pair is out for the same reason a
 * dotted figure is not a rung of the ladder: neither of the two this page offers carries a flag.
 */
export const BEAMABLE_FIGURES = new Set<FigureName>([
  "corchea",
  "semicorchea",
  "fusa",
  "semifusa",
]);

/** How much one press of the plus or the minus moves an even run, as a fraction of its own width. */
export const EVEN_SPACING_STEP = 0.15;

/** Thumb to little finger. There is no 0 and no 6. */
export const FINGERS: FingerNumber[] = [1, 2, 3, 4, 5];

/**
 * What a stretch of columns can carry. One pill each, and only that one's controls on screen.
 *
 * Two of them left. **Trill** and **Small** are statements about notes, not about columns — "these
 * notes are a shake", "these notes are decoration" — so they moved to the note toolbox, where the
 * notes they are about are already picked and the panel does not have to ask which hand.
 */
export const FRAME_TABS = [
  { id: "key" as const, label: "Key" },
  { id: "clef" as const, label: "Clef" },
  { id: "octave" as const, label: "Octave" },
  { id: "lyrics" as const, label: "Lyrics" },
  { id: "spacing" as const, label: "Spacing" },
  { id: "rerecord" as const, label: "Re-record" },
];

export type FrameTab = (typeof FRAME_TABS)[number]["id"];

/**
 * Which pill a marked stretch opens when the reader clicks one of its corners, or its bracket.
 *
 * The drawing package names its kinds after the notation; the panel names its pills after what a
 * reader is about to change. `Re-record` and `Spacing` are not in the list because neither draws a
 * corner: nothing about them is a stretch of markup you can lose the edges of.
 */
export const MARKER_TABS: Readonly<Record<string, FrameTab | undefined>> = {
  ottava: "octave",
  clef: "clef",
  key: "key",
  lyric: "lyrics",
};

/**
 * Which staff a marked stretch is about: one hand, or the piece.
 *
 * The first thing the frames toolbox asks, because it changes what every pill below it means and
 * what the highlight on the page covers. A clef and an octave bracket belong to one hand; a key
 * signature is drawn on both clefs and a line of words is sung over the piece, so those ignore it.
 */
export type RangeHand = PrintedHand | "both";

/** Which clef each hand reads when nobody has said otherwise. The page's starting point. */
export const DEFAULT_CLEF: Record<PrintedHand, Clef> = { right: "treble", left: "bass" };

/** The two clefs this page prints, and what each is called. */
export const CLEF_CHOICES: { clef: Clef; label: string; hint: string }[] = [
  { clef: "treble", label: "Treble", hint: "the G clef — where the right hand normally reads" },
  { clef: "bass", label: "Bass", hint: "the F clef — where the left hand normally reads" },
];

/** The four brackets, and what each does to a passage, in the order a reader meets them. */
export const OTTAVA_CHOICES: { kind: OttavaKind; label: string; hint: string }[] = [
  { kind: "8va", label: "8va", hint: "written an octave lower than it sounds" },
  {
    kind: "15ma",
    label: "15ma",
    hint: "written two octaves lower than it sounds",
  },
  {
    kind: "8vb",
    label: "8vb",
    hint: "written an octave higher than it sounds",
  },
  {
    kind: "15mb",
    label: "15mb",
    hint: "written two octaves higher than it sounds",
  },
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

/**
 * The rungs a figure shift walks: the plain figures, each twice the one below it (D-18).
 *
 * The dotted pair is not here. A dot is an exception the vocabulary allows on two figures so a held
 * note can be written; it is not a rung, and stepping onto it would re-scale the ladder by 1.5
 * rather than doubling it. This mirrors `SHIFT_LADDER` in `matrix/ladder.py`, which is the same
 * list on the other side.
 */
export const SHIFT_LADDER: FigureName[] = [
  "semifusa",
  "fusa",
  "semicorchea",
  "corchea",
  "negra",
  "blanca",
  "redonda",
];

/** The figure `steps` rungs away, or `null` when that runs off the end of the vocabulary. */
export function shifted(figure: FigureName, steps: number): FigureName | null {
  const at = SHIFT_LADDER.indexOf(figure);
  if (at < 0) return null;
  return SHIFT_LADDER[at + steps] ?? null;
}

/** One note the keyboard panel can point at: what it is, who holds it, and where it began. */
export interface SoundingNote {
  row: number;
  hand: PrintedHand;
  /** The column the note was struck in, which is how every mark on this page addresses one. */
  onsetFrame: number;
}

/**
 * The backend's own sentence, without the status code in front of it.
 *
 * `ApiError.message` reads "409 — This piece was transcribed before…", which is
 * a number a reader has no use for. The `detail` behind it is written to be shown
 * as it stands, so that is what appears.
 */
export function readable(caught: unknown, fallback: string): string {
  if (caught instanceof ApiError) return caught.detail;
  return caught instanceof Error ? caught.message : fallback;
}

/** A piece with no recorded notes yet: not a failure, just nothing to read. */
export function notTranscribed(caught: unknown): boolean {
  return caught instanceof ApiError && caught.status === 409;
}
