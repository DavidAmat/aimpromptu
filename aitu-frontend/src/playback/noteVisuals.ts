/**
 * How a note rectangle is drawn. One module, so the roll and the falling view
 * cannot drift apart.
 *
 * The rules, and why each one:
 *
 * **Fill is the light shade, at 88%.** The label is black, and black on the dark
 * shade of the palette is not readable at 9 px. The light shade plus a little
 * transparency lets the ground through — the waveform watermark on the roll, the
 * dark panel on the falling view — so a rectangle sits *on* the view instead of
 * punching a hole in it, and the text stays legible on both.
 *
 * **Stroke is the dark shade of the same hue**, so the border reads as the same
 * note rather than as an outline someone added.
 *
 * **Stroke width grows with the note's drawn length, and stops at 2.** A short
 * note is a few pixels across; a 1.5 px border on it is mostly border, and a row
 * of them reads as a dotted line. A long note can carry a real edge. So the
 * weight follows the extent, which also makes length legible at a glance from
 * across the room.
 *
 * **Corners round with the short side.** A fixed radius looks square on a long
 * note and swallows a short one.
 */

import { grays, handColors, palette, semantic } from "../ui";
import type { PlayedHand } from "./playedNotes";

/** Alpha applied to the fill, as a two-digit hex suffix. */
const FILL_ALPHA = "E0";
/** Longest drawn extent, in pixels, that still gets a thinner border. */
const FULL_BORDER_AT = 90;
const MIN_STROKE = 0.6;
const MAX_STROKE = 2;

export interface NoteVisualState {
  hand: PlayedHand;
  /** Sounding right now under the playhead. */
  active: boolean;
  /** Picked by the reader, and part of what a delete would take. */
  selected: boolean;
  /** Filtered by the pipeline, or taken off the recording by the reader. */
  ghost: boolean;
  /** Marked to come off — or to come back — and not saved yet. */
  staged: boolean;
}

export interface NoteVisuals {
  fill: string;
  stroke: string;
  strokeWidth: number;
  strokeDasharray?: string;
  rx: number;
}

/**
 * @param extent  The note's length on screen in pixels — width on the roll,
 *                height on the falling view.
 * @param breadth The other side, i.e. the lane.
 */
export function noteVisuals(
  { hand, active, selected, ghost, staged }: NoteVisualState,
  extent: number,
  breadth: number,
): NoteVisuals {
  const rx = Math.min(6, Math.max(2, Math.min(extent, breadth) / 2.4));
  const weight = Math.min(MAX_STROKE, Math.max(MIN_STROKE, (extent / FULL_BORDER_AT) * MAX_STROKE));
  // Selection is lavender rather than red. Red has to stay free to mean "about to
  // be deleted": with both in red, a reader could not tell a note they had merely
  // picked from one they had already marked to remove.
  const selectionStroke = palette.dark.Lavender;

  // Marked to come off and not yet saved. Red, dashed, and washed through — the
  // one state on this view that says a press of Save will change the recording.
  if (staged) {
    return {
      fill: `${semantic.status.error}26`,
      stroke: semantic.status.error,
      strokeWidth: Math.max(1.4, weight),
      strokeDasharray: "5 3",
      rx,
    };
  }

  if (ghost) {
    return {
      fill: "none",
      stroke: selected ? selectionStroke : semantic.status.warning,
      strokeWidth: Math.max(1.2, weight),
      strokeDasharray: "4 3",
      rx,
    };
  }

  const colors = handColors(hand);
  return {
    // `active` borrows the other hand's light shade rather than a colour of its
    // own: the playhead is already on it, so it only has to differ, not shout.
    fill: `${active ? semantic.rightHand.sustain : colors.sustain}${FILL_ALPHA}`,
    stroke: selected ? selectionStroke : colors.onset,
    strokeWidth: selected ? Math.max(2, weight) : weight,
    rx,
  };
}

/** Colour of the line struck through a note that is marked to come off. */
export const STRIKE_COLOR = semantic.status.error;

/** Font size for a label inside a lane of `breadth` pixels. */
export function labelFontSize(breadth: number): number {
  return Math.min(11, Math.max(7, breadth - 3));
}

export const NOTE_LABEL_FILL = grays.ink;
export const NOTE_LABEL_FAMILY = "Montserrat, sans-serif";
