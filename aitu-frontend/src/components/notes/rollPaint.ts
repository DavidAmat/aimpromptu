/**
 * Painting the Notes tab's piano roll visualization on two canvases (plan section 9.5).
 *
 * **The lower canvas** holds what changes when the notes, the view or the selection change: the
 * key rows, the time grid and ruler, the vertical keyboard, and the rectangles. It is painted only
 * then, and only the rectangles of the visible time range are looked at.
 *
 * **The upper canvas** holds what moves during playback: the playhead, the keys lit on the
 * keyboard, and the rectangles sounding under the playhead (black, with a thick border in their
 * colour, as on the other views). Playback repaints this one alone, which is a line and a handful
 * of rectangles, whatever the number of notes.
 *
 * Pure functions of what to draw; `PianoRollCanvas` decides when.
 */

import { formatTimeShort } from "../../audio/time";
import { fittingNoteLabel, noteName } from "../../music/noteNames";
import {
  FLAG_GUESSED,
  HAND_LEFT,
  HAND_NONE,
  HAND_RIGHT,
  type RollNotes,
} from "../../notes/rollNotes";
import { gridStep, msAt, spanMs, xOf, yOf, type RollLayout, type RollView } from "../../notes/rollView";
import { grays, palette, semantic } from "../../ui";

const roll = semantic.roll;
const LABEL_FONT = "600 10px Montserrat, Geist, sans-serif";
const RULER_FONT = "11px Geist, system-ui, sans-serif";
/** How long a new rectangle takes to grow to its full length. */
export const REVEAL_MS = 250;

/** `key` 0 to 87: a black key or not. */
function isBlack(key: number): boolean {
  const pitchClass = (key + 21) % 12;
  return pitchClass === 1 || pitchClass === 3 || pitchClass === 6 || pitchClass === 8 || pitchClass === 10;
}

/** The dark space between two rows, so notes on neighbouring keys read as separate bars. */
function rowGap(rowHeight: number): number {
  return rowHeight >= 9 ? 1.5 : rowHeight >= 6 ? 1 : 0.5;
}

/** Ease-out: fast at first, slow at the end. */
function easeOut(t: number): number {
  const u = 1 - t;
  return 1 - u * u * u;
}

/** How the rectangles are coloured: one colour, or by hand (red for a note with no hand). */
export type ColourBy = "none" | "hand";

/** Which hand is shown in full; the other one is drawn faint and cannot be picked. */
export type HandFilter = "both" | "right" | "left";

/** Whether a note of `hand` is shown in full under `filter`. A note with no hand always is. */
export function shownBy(filter: HandFilter, hand: number): boolean {
  if (filter === "both" || hand === HAND_NONE) return true;
  return filter === "right" ? hand === HAND_RIGHT : hand === HAND_LEFT;
}

/** How visible a note of the hand the filter leaves out is. */
const FILTERED_ALPHA = 0.14;

/** A drag in progress, drawn before it is committed: every id in `ids` moves by the same amount. */
export type DragPreview =
  | { kind: "move"; ids: ReadonlySet<number>; dMs: number; dKey: number }
  | { kind: "resize"; id: number; onMs: number; lenMs: number };

export interface BaseScene {
  notes: RollNotes;
  durationMs: number;
  selection: ReadonlySet<number>;
  colourBy: ColourBy;
  handFilter: HandFilter;
  preview: DragPreview | null;
  /** The live frontier: nothing is drawn after it. `null` when not transcribing. */
  frontierMs: number | null;
  /** Where an open note of the live stream is drawn up to. */
  openUntilMs: number;
  /** `performance.now()`, for the reveal of new rectangles. */
  now: number;
  /** The notes that a band drag would select, drawn as selected. */
  banded: ReadonlySet<number> | null;
}

export interface NoteColours {
  fill: string;
  border: string;
}

/** The fill and the border of a rectangle that is not selected. */
export function noteColours(hand: number, colourBy: ColourBy): NoteColours {
  if (colourBy === "hand") {
    if (hand === HAND_RIGHT) return { fill: semantic.rightHand.sustain, border: semantic.rightHand.onset };
    if (hand === HAND_LEFT) return { fill: semantic.leftHand.sustain, border: semantic.leftHand.onset };
    return { fill: palette.light.Red, border: palette.dark.Red };
  }
  return { fill: roll.note, border: roll.noteBorder };
}

/** Size the canvas for the screen's pixel density, and give back a context in CSS pixels. */
export function prepareCanvas(
  canvas: HTMLCanvasElement,
  width: number,
  height: number,
): CanvasRenderingContext2D | null {
  const ratio = window.devicePixelRatio || 1;
  const pixelWidth = Math.round(width * ratio);
  const pixelHeight = Math.round(height * ratio);
  if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
  if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  return context;
}

/** Where a note is drawn, with the drag preview applied. */
function placed(
  scene: BaseScene,
  slot: number,
): { key: number; on: number; end: number } {
  const notes = scene.notes;
  const id = notes.id[slot]!;
  const preview = scene.preview;
  let key = notes.key[slot]!;
  let on = notes.onMs[slot]!;
  let end = notes.endOf(slot, scene.openUntilMs);
  if (preview?.kind === "move" && preview.ids.has(id)) {
    key += preview.dKey;
    on += preview.dMs;
    end += preview.dMs;
  } else if (preview?.kind === "resize" && preview.id === id) {
    on = preview.onMs;
    end = preview.onMs + preview.lenMs;
  }
  return { key, on, end };
}

/** The rows, the grid, the rectangles, the ruler and the keyboard. */
export function paintBase(context: CanvasRenderingContext2D, layout: RollLayout, view: RollView, scene: BaseScene): void {
  const { width, height, keyboard, ruler, rowHeight } = layout;
  const fromMs = view.startMs;
  const toMs = view.startMs + spanMs(layout, view);

  // --- the rows
  context.fillStyle = roll.background;
  context.fillRect(keyboard, ruler, width - keyboard, height - ruler);
  const { lowKey, highKey } = layout;
  context.fillStyle = roll.blackRow;
  for (let key = lowKey; key <= highKey; key += 1) {
    if (isBlack(key)) context.fillRect(keyboard, yOf(layout, key), width - keyboard, rowHeight);
  }
  context.fillStyle = roll.octaveLine;
  for (let key = 3; key <= highKey; key += 12) {
    // The bottom edge of every C row.
    if (key >= lowKey) context.fillRect(keyboard, Math.round(yOf(layout, key) + rowHeight) - 1, width - keyboard, 1);
  }

  // --- the time grid
  const step = gridStep(view.pxPerSec);
  const first = Math.ceil(fromMs / 1000 / step) * step;
  for (let seconds = first; seconds * 1000 <= toMs; seconds += step) {
    const x = Math.round(xOf(layout, view, seconds * 1000)) + 0.5;
    const strong = Math.abs(seconds / (step * 5) - Math.round(seconds / (step * 5))) < 1e-6;
    context.fillStyle = strong ? roll.gridStrong : roll.grid;
    context.fillRect(x - 0.5, ruler, 1, height - ruler);
  }

  // --- what the live transcription has covered, and what is after the end
  if (scene.frontierMs !== null) {
    const right = Math.min(width, xOf(layout, view, scene.frontierMs));
    if (right > keyboard) {
      context.fillStyle = roll.transcribed;
      context.fillRect(keyboard, ruler, right - keyboard, height - ruler);
    }
  }
  const endX = xOf(layout, view, scene.durationMs);
  if (endX < width) {
    context.fillStyle = roll.afterEnd;
    context.fillRect(Math.max(keyboard, endX), ruler, width - Math.max(keyboard, endX), height - ruler);
  }

  // --- the rectangles
  paintNotes(context, layout, view, scene, fromMs, toMs);

  // --- the ruler and the keyboard, over everything that scrolls
  paintRuler(context, layout, view, step, fromMs, toMs);
  paintKeyboard(context, layout);
}

function paintNotes(
  context: CanvasRenderingContext2D,
  layout: RollLayout,
  view: RollView,
  scene: BaseScene,
  fromMs: number,
  toMs: number,
): void {
  const { width, height, keyboard, ruler, rowHeight } = layout;
  const notes = scene.notes;
  const gap = rowGap(rowHeight);
  const noteHeight = Math.max(1, rowHeight - gap);
  const bordered = noteHeight >= 8;
  const pxPerMs = view.pxPerSec / 1000;
  const clipMs = scene.frontierMs ?? Infinity;
  const labels = rowHeight >= 11;
  const moving = scene.preview?.kind === "move" ? scene.preview : null;
  // The notes being dragged may come from outside the view; widen the query by the drag.
  const margin = moving ? Math.abs(moving.dMs) : scene.preview?.kind === "resize" ? toMs - fromMs : 0;

  context.save();
  context.beginPath();
  context.rect(keyboard, ruler, width - keyboard, height - ruler);
  context.clip();
  if (labels) {
    context.font = LABEL_FONT;
    context.textBaseline = "middle";
  }

  const selected: number[] = [];
  let fill = "";
  const draw = (slot: number, colours: NoteColours, chosen: boolean) => {
    const { key, on, end } = placed(scene, slot);
    if (key < layout.lowKey || key > layout.highKey) return;
    let right = Math.min(end, clipMs);
    if (right <= on) return;
    const spawn = notes.spawn[slot]!;
    if (spawn > 0) {
      const t = (scene.now - spawn) / REVEAL_MS;
      if (t < 1) right = on + (right - on) * easeOut(Math.max(0, t));
    }
    const x = keyboard + (on - view.startMs) * pxPerMs;
    const w = Math.max(1.5, (right - on) * pxPerMs - 1);
    if (x > width || x + w < keyboard) return;
    const y = yOf(layout, key) + gap / 2;
    if (colours.fill !== fill) {
      fill = colours.fill;
      context.fillStyle = fill;
    }
    context.fillRect(x, y, w, noteHeight);
    if (chosen || (bordered && w >= 4)) {
      context.strokeStyle = colours.border;
      context.lineWidth = chosen ? 1.5 : 1;
      const dashed = (notes.flags[slot]! & FLAG_GUESSED) !== 0 && scene.colourBy === "hand";
      if (dashed) context.setLineDash([3, 2]);
      context.strokeRect(x + 0.5, y + 0.5, Math.max(0.5, w - 1), Math.max(0.5, noteHeight - 1));
      if (dashed) context.setLineDash([]);
    }
    if (labels) {
      const label = fittingNoteLabel(key + 21, w, noteHeight, 10);
      if (label) {
        context.fillStyle = grays.ink;
        context.fillText(label, x + 3, y + noteHeight / 2 + 0.5);
        fill = "";
      }
    }
  };

  const faint: number[] = [];
  notes.forEachIn(fromMs - margin, toMs + margin, scene.openUntilMs, (slot) => {
    const id = notes.id[slot]!;
    if (!shownBy(scene.handFilter, notes.hand[slot]!)) {
      faint.push(slot);
      return;
    }
    if (scene.selection.has(id) || scene.banded?.has(id)) {
      selected.push(slot);
      return;
    }
    draw(slot, noteColours(notes.hand[slot]!, scene.colourBy), false);
  });
  // The hand the filter leaves out, faint and under the others, so the shown hand reads alone.
  if (faint.length) {
    context.globalAlpha = FILTERED_ALPHA;
    for (const slot of faint) draw(slot, noteColours(notes.hand[slot]!, scene.colourBy), false);
    context.globalAlpha = 1;
  }
  // The selection last, so it is on top of any note it now overlaps.
  const chosen: NoteColours = { fill: roll.selected, border: roll.selectedBorder };
  for (const slot of selected) draw(slot, chosen, true);
  context.restore();
}

function paintRuler(
  context: CanvasRenderingContext2D,
  layout: RollLayout,
  view: RollView,
  step: number,
  fromMs: number,
  toMs: number,
): void {
  const { width, keyboard, ruler } = layout;
  context.fillStyle = roll.ruler;
  context.fillRect(0, 0, width, ruler);
  context.font = RULER_FONT;
  context.textBaseline = "middle";
  context.fillStyle = roll.rulerText;
  const labelEvery = step * (step * view.pxPerSec >= 110 ? 1 : 2);
  const first = Math.ceil(fromMs / 1000 / step) * step;
  for (let seconds = first; seconds * 1000 <= toMs; seconds += step) {
    const x = Math.round(xOf(layout, view, seconds * 1000)) + 0.5;
    if (x < keyboard) continue;
    context.fillRect(x - 0.5, ruler - 6, 1, 6);
    const multiple = seconds / labelEvery;
    if (Math.abs(multiple - Math.round(multiple)) < 1e-6) {
      const text = step < 1 ? `${formatTimeShort(seconds)}.${Math.round((seconds % 1) * 10)}` : formatTimeShort(seconds);
      context.fillText(text, x + 4, ruler / 2);
    }
  }
}

/** The vertical keyboard: one row per key, the black keys dark, and the name of every C. */
function paintKeyboard(context: CanvasRenderingContext2D, layout: RollLayout): void {
  const { keyboard, ruler, rowHeight, height } = layout;
  context.fillStyle = roll.keyWhite;
  context.fillRect(0, ruler, keyboard, height - ruler);
  const { lowKey, highKey } = layout;
  context.fillStyle = roll.keyBlack;
  for (let key = lowKey; key <= highKey; key += 1) {
    if (isBlack(key)) context.fillRect(0, yOf(layout, key), keyboard * 0.62, rowHeight);
  }
  context.fillStyle = roll.keyLine;
  for (let key = lowKey; key <= highKey; key += 1) {
    // A line between two white keys that touch (E-F and B-C), and under every C.
    const pitchClass = (key + 21) % 12;
    if (pitchClass === 0 || pitchClass === 5) {
      context.fillRect(0, Math.round(yOf(layout, key) + rowHeight) - 0.5, keyboard, 1);
    }
  }
  if (rowHeight >= 5) {
    context.font = `${Math.min(10, Math.max(7, rowHeight + 1))}px Geist, system-ui, sans-serif`;
    context.textBaseline = "middle";
    context.fillStyle = roll.keyLabel;
    for (let key = 3; key <= highKey; key += 12) {
      if (key >= lowKey) context.fillText(noteName(key + 21), keyboard - 22, yOf(layout, key) + rowHeight / 2 + 0.5);
    }
  }
  context.fillStyle = grays.ink;
  context.fillRect(keyboard - 1, ruler, 1, height - ruler);
}

// ---------------------------------------------------------------------- the upper canvas

export interface OverlayScene {
  notes: RollNotes;
  colourBy: ColourBy;
  handFilter: HandFilter;
  /** Where the playhead is, in ms. `null` hides it (during the live transcription). */
  playheadMs: number | null;
  /**
   * Playback runs: the notes under the playhead are drawn as sounding (black). Their keys are lit
   * on the keyboard in any case, so a pause keeps showing what was pressed at that moment.
   */
  sounding: boolean;
  /** The keys of the selected notes, lit on the keyboard in the colour of the selection. */
  selectedKeys: ReadonlySet<number>;
  /** A band drag, in canvas pixels. */
  band: { x0: number; y0: number; x1: number; y1: number } | null;
}

export function paintOverlay(context: CanvasRenderingContext2D, layout: RollLayout, view: RollView, scene: OverlayScene): void {
  const { width, height, keyboard, ruler, rowHeight } = layout;
  const notes = scene.notes;

  const lit: { key: number; colour: string }[] = [];
  if (scene.playheadMs !== null) {
    const at = scene.playheadMs;
    const pxPerMs = view.pxPerSec / 1000;
    const gap = rowGap(rowHeight);
    const noteHeight = Math.max(1, rowHeight - gap);
    context.save();
    context.beginPath();
    context.rect(keyboard, ruler, width - keyboard, height - ruler);
    context.clip();
    notes.soundingAt(at, (slot) => {
      const key = notes.key[slot]!;
      if (key < layout.lowKey || key > layout.highKey) return;
      if (!shownBy(scene.handFilter, notes.hand[slot]!)) return;
      const colours = noteColours(notes.hand[slot]!, scene.colourBy);
      // The border of a sounding note is its colour: the hand's, or the notes' own.
      const colour = scene.colourBy === "hand" ? colours.border : colours.fill;
      lit.push({ key, colour });
      if (!scene.sounding) return;
      const on = notes.onMs[slot]!;
      const x = keyboard + (on - view.startMs) * pxPerMs;
      const w = Math.max(2, notes.lenMs[slot]! * pxPerMs - 1);
      const y = yOf(layout, key) + gap / 2;
      context.fillStyle = grays.ink;
      context.fillRect(x, y, w, noteHeight);
      context.strokeStyle = colour;
      context.lineWidth = 2;
      context.strokeRect(x + 1, y + 1, Math.max(0.5, w - 2), Math.max(0.5, noteHeight - 2));
      if (rowHeight >= 11) {
        const label = fittingNoteLabel(key + 21, w, noteHeight, 10);
        if (label) {
          context.font = LABEL_FONT;
          context.textBaseline = "middle";
          context.fillStyle = grays.white;
          context.fillText(label, x + 3, y + noteHeight / 2 + 0.5);
        }
      }
    });
    context.restore();
  }
  // The keys: the selected notes' in the colour of the selection, then the sounding ones (under the
  // playhead, playing or paused) in the colour of their notes, over them.
  const litKey = (key: number, colour: string) => {
    if (key < layout.lowKey || key > layout.highKey) return;
    context.fillStyle = colour;
    const black = isBlack(key);
    context.fillRect(0, yOf(layout, key) + 0.5, keyboard * (black ? 0.62 : 1) - 1, Math.max(1, rowHeight - 1));
  };
  for (const key of scene.selectedKeys) litKey(key, roll.selectedBorder);
  for (const { key, colour } of lit) litKey(key, colour);

  if (scene.band) {
    const { x0, y0, x1, y1 } = scene.band;
    context.fillStyle = roll.band;
    context.strokeStyle = roll.selectedBorder;
    context.lineWidth = 1;
    const x = Math.min(x0, x1);
    const y = Math.min(y0, y1);
    context.fillRect(x, y, Math.abs(x1 - x0), Math.abs(y1 - y0));
    context.strokeRect(x + 0.5, y + 0.5, Math.abs(x1 - x0), Math.abs(y1 - y0));
  }

  if (scene.playheadMs !== null) {
    const x = xOf(layout, view, scene.playheadMs);
    if (x >= keyboard - 1 && x <= width + 1) {
      context.fillStyle = roll.playhead;
      context.fillRect(Math.round(x) - 1, ruler, 2, height - ruler);
      // A handle in the ruler: the playhead is grabbed there.
      context.beginPath();
      context.moveTo(x - 6, 2);
      context.lineTo(x + 6, 2);
      context.lineTo(x + 6, ruler - 9);
      context.lineTo(x, ruler - 2);
      context.lineTo(x - 6, ruler - 9);
      context.closePath();
      context.fill();
    }
  }
}

/** The time under an x position, clamped to the piece. For the pointer. */
export function timeAtX(layout: RollLayout, view: RollView, x: number, durationMs: number): number {
  return Math.min(durationMs, Math.max(0, msAt(layout, view, x)));
}
