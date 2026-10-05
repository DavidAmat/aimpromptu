/**
 * Painting the Audio tab's waveform on a canvas: the peaks, the cuts, the selection, the playhead.
 *
 * The old waveform is one SVG element per bar, which is what made it slow. A canvas is one drawing
 * surface that is painted directly: the whole view costs one loop over the visible frames, a few
 * thousand at most, and nothing is kept in React between two paints.
 *
 * Pure functions of what to draw, so the components only decide *when* to paint.
 */

import type { Cut, FramePeaks } from "../../api";
import { formatTime, formatTimeShort } from "../../audio/time";
import type { FrameView } from "../../audio/frameView";
import { grays, semantic, ui } from "../../ui";

/**
 * The strip at the top of the main waveform where the time labels are. It is also where the
 * playhead is grabbed: pressing or dragging here moves it, and nowhere else does a single press.
 */
export const RULER = 26;

const FRAMES_PER_SECOND = 100;
/** Tick steps, in seconds; the first one at least {@link MIN_TICK_PX} wide is used. */
const TICK_STEPS = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
const MIN_TICK_PX = 90;
/** Below this many pixels per frame, frame borders are not drawn. */
const FRAME_GRID_PX = 8;

/** Size the canvas for the screen's pixel density, and give back a context in CSS pixels. */
export function prepare(canvas: HTMLCanvasElement, width: number, height: number): CanvasRenderingContext2D | null {
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

/**
 * The peaks between `top` and `top + height`, one column per pixel when a pixel holds several
 * frames, one bar per frame when a frame is several pixels wide.
 */
function paintPeaks(
  context: CanvasRenderingContext2D,
  peaks: FramePeaks,
  view: FrameView,
  width: number,
  top: number,
  height: number,
): void {
  const middle = top + height / 2;
  const scale = (height / 2) * 0.92 / 127;
  const span = view.end - view.start;
  const framesPerPixel = span / width;
  context.fillStyle = semantic.waveform.body;

  if (framesPerPixel >= 1) {
    for (let x = 0; x < width; x += 1) {
      const first = Math.floor(view.start + x * framesPerPixel);
      const last = Math.min(peaks.totalFrames, Math.ceil(view.start + (x + 1) * framesPerPixel));
      let low = 127;
      let high = -128;
      for (let frame = Math.max(0, first); frame < last; frame += 1) {
        const min = peaks.min[frame]!;
        const max = peaks.max[frame]!;
        if (min < low) low = min;
        if (max > high) high = max;
      }
      if (high < low) continue;
      const y = middle - high * scale;
      context.fillRect(x, y, 1, Math.max(1, (high - low) * scale));
    }
    return;
  }

  const pixelsPerFrame = width / span;
  const first = Math.max(0, Math.floor(view.start));
  const last = Math.min(peaks.totalFrames, Math.ceil(view.end));
  for (let frame = first; frame < last; frame += 1) {
    const x = (frame - view.start) * pixelsPerFrame;
    const high = peaks.max[frame]!;
    const low = peaks.min[frame]!;
    const y = middle - high * scale;
    context.fillRect(x, y, Math.max(1, pixelsPerFrame - (pixelsPerFrame > 3 ? 1 : 0)), Math.max(1, (high - low) * scale));
  }
}

/** A cut: shaded and crossed, so it reads as "deleted" and not as a selection. */
function paintCut(
  context: CanvasRenderingContext2D,
  left: number,
  right: number,
  top: number,
  height: number,
  label: string | null,
): void {
  const width = right - left;
  context.save();
  context.fillStyle = grays.slate;
  context.globalAlpha = 0.28;
  context.fillRect(left, top, width, height);
  context.beginPath();
  context.rect(left, top, width, height);
  context.clip();
  context.globalAlpha = 0.45;
  context.strokeStyle = grays.slate;
  context.lineWidth = 1;
  context.beginPath();
  for (let x = left - height; x < right; x += 9) {
    context.moveTo(x, top + height);
    context.lineTo(x + height, top);
  }
  context.stroke();
  context.restore();
  if (label && width > 70) {
    context.save();
    context.fillStyle = ui.text;
    context.font = "600 11px Geist, system-ui, sans-serif";
    context.textBaseline = "top";
    const text = context.measureText(label);
    context.fillStyle = grays.white;
    context.globalAlpha = 0.85;
    context.fillRect(left + 4, top + 4, text.width + 8, 16);
    context.globalAlpha = 1;
    context.fillStyle = ui.text;
    context.fillText(label, left + 8, top + 7);
    context.restore();
  }
}

/** The time labels along the top, and a faint line per frame when a frame is wide enough to see. */
function paintRuler(context: CanvasRenderingContext2D, view: FrameView, width: number, height: number): void {
  const span = view.end - view.start;
  const pixelsPerSecond = (width / span) * FRAMES_PER_SECOND;
  const step = TICK_STEPS.find((seconds) => seconds * pixelsPerSecond >= MIN_TICK_PX) ?? 600;
  const firstSecond = Math.ceil(view.start / FRAMES_PER_SECOND / step) * step;

  context.save();
  context.fillStyle = ui.bg;
  context.fillRect(0, 0, width, RULER);
  context.strokeStyle = ui.lineStrong;
  context.fillStyle = ui.text2;
  context.font = "11px Geist, system-ui, sans-serif";
  context.textBaseline = "middle";
  context.lineWidth = 1;
  context.beginPath();
  for (let seconds = firstSecond; seconds * FRAMES_PER_SECOND <= view.end; seconds += step) {
    const x = Math.round(((seconds * FRAMES_PER_SECOND - view.start) / span) * width) + 0.5;
    context.moveTo(x, RULER - 6);
    context.lineTo(x, RULER);
    context.fillText(step < 1 ? formatTime(seconds) : formatTimeShort(seconds), x + 3, RULER / 2 - 1);
  }
  context.moveTo(0, RULER + 0.5);
  context.lineTo(width, RULER + 0.5);
  context.stroke();

  const pixelsPerFrame = width / span;
  if (pixelsPerFrame >= FRAME_GRID_PX) {
    context.strokeStyle = ui.line;
    context.beginPath();
    for (let frame = Math.ceil(view.start); frame <= view.end; frame += 1) {
      const x = Math.round((frame - view.start) * pixelsPerFrame) + 0.5;
      context.moveTo(x, RULER + 1);
      context.lineTo(x, height);
    }
    context.stroke();
  }
  context.restore();
}

export interface WaveformScene {
  peaks: FramePeaks;
  cuts: readonly Cut[];
  selection: Cut | null;
  view: FrameView;
  /** The edge under the pointer or being dragged: drawn stronger, with its time beside it. */
  activeEdge?: "start" | "end" | null;
}

/** A small box of text, readable on the waveform and on a cut. */
function tag(context: CanvasRenderingContext2D, text: string, x: number, y: number, align: "left" | "right"): void {
  context.save();
  context.font = "600 11px Geist, system-ui, sans-serif";
  context.textBaseline = "top";
  const width = context.measureText(text).width + 10;
  const left = align === "left" ? x : x - width;
  context.fillStyle = semantic.waveform.selection;
  context.fillRect(left, y, width, 17);
  context.fillStyle = grays.white;
  context.fillText(text, left + 5, y + 3);
  context.restore();
}

/**
 * The selection: a tinted band, and at each edge a line with a grip in the middle.
 *
 * The grips say "this edge can be dragged" before the reader tries it. The edge under the pointer,
 * or the one being dragged, is drawn wider and carries its time, so a precise edge can be placed by
 * reading it rather than by guessing.
 */
function paintSelection(
  context: CanvasRenderingContext2D,
  selection: Cut,
  toX: (frame: number) => number,
  top: number,
  body: number,
  width: number,
  activeEdge: "start" | "end" | null,
): void {
  const left = toX(selection[0]);
  const right = toX(selection[1]);
  context.save();
  context.fillStyle = semantic.waveform.selection;
  context.globalAlpha = 0.18;
  context.fillRect(left, top, right - left, body);
  context.restore();

  const middle = top + body / 2;
  for (const edge of ["start", "end"] as const) {
    const x = Math.round(edge === "start" ? left : right);
    if (x < -8 || x > width + 8) continue;
    const active = activeEdge === edge;
    context.save();
    context.fillStyle = semantic.waveform.selection;
    context.globalAlpha = active ? 1 : 0.75;
    context.fillRect(x - (active ? 1.5 : 1), top, active ? 3 : 2, body);
    const gripWidth = active ? 12 : 9;
    const gripHeight = active ? 40 : 30;
    context.beginPath();
    context.roundRect(x - gripWidth / 2, middle - gripHeight / 2, gripWidth, gripHeight, 4);
    context.fill();
    context.globalAlpha = 1;
    context.strokeStyle = grays.white;
    context.lineWidth = 1;
    context.beginPath();
    for (const dy of [-5, 0, 5]) {
      context.moveTo(x - gripWidth / 2 + 3, middle + dy + 0.5);
      context.lineTo(x + gripWidth / 2 - 3, middle + dy + 0.5);
    }
    context.stroke();
    context.restore();
    if (active) {
      const seconds = selection[edge === "start" ? 0 : 1] / FRAMES_PER_SECOND;
      // The label sits inside the selection, so it never covers the part being reached for.
      tag(context, formatTime(seconds), edge === "start" ? x + 8 : x - 8, top + 6, edge === "start" ? "left" : "right");
    }
  }
}

/** The main waveform: ruler, peaks, cuts, selection. The playhead is on its own canvas. */
export function paintWaveform(
  canvas: HTMLCanvasElement,
  width: number,
  height: number,
  { peaks, cuts, selection, view, activeEdge = null }: WaveformScene,
): void {
  const context = prepare(canvas, width, height);
  if (!context || width <= 0) return;
  const span = view.end - view.start;
  const toX = (frame: number) => ((frame - view.start) / span) * width;
  const top = RULER + 1;
  const body = height - top;

  context.fillStyle = ui.bg;
  context.fillRect(0, top, width, body);
  paintRuler(context, view, width, height);

  context.strokeStyle = ui.lineStrong;
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(0, top + body / 2 + 0.5);
  context.lineTo(width, top + body / 2 + 0.5);
  context.stroke();

  paintPeaks(context, peaks, view, width, top, body);

  for (const [start, end] of cuts) {
    if (end <= view.start || start >= view.end) continue;
    const seconds = (end - start) / FRAMES_PER_SECOND;
    paintCut(context, toX(start), toX(end), top, body, `Cut · ${formatTime(seconds)}`);
  }

  if (selection) paintSelection(context, selection, toX, top, body, width, activeEdge);
}

/**
 * The playhead, on the canvas above the waveform: one line, repainted on every frame of playback,
 * with its handle in the time ruler, which is where it is grabbed.
 */
export function paintPlayhead(
  canvas: HTMLCanvasElement,
  width: number,
  height: number,
  view: FrameView,
  frame: number,
): void {
  const context = prepare(canvas, width, height);
  if (!context) return;
  if (frame < view.start || frame > view.end) return;
  const x = Math.round(((frame - view.start) / (view.end - view.start)) * width);
  context.fillStyle = semantic.waveform.cursor;
  context.fillRect(x - 1, 0, 2, height);
  context.beginPath();
  context.moveTo(x - 7, 2);
  context.lineTo(x + 7, 2);
  context.lineTo(x + 7, RULER - 10);
  context.lineTo(x, RULER - 2);
  context.lineTo(x - 7, RULER - 10);
  context.closePath();
  context.fill();
}

/** The overview: the whole audio, the cuts, and the part the main waveform shows. */
export function paintOverview(
  canvas: HTMLCanvasElement,
  width: number,
  height: number,
  { peaks, cuts, view }: Omit<WaveformScene, "selection">,
): void {
  const context = prepare(canvas, width, height);
  if (!context || width <= 0) return;
  const whole = { start: 0, end: peaks.totalFrames };
  context.fillStyle = ui.bg;
  context.fillRect(0, 0, width, height);
  paintPeaks(context, peaks, whole, width, 0, height);
  const toX = (frame: number) => (frame / peaks.totalFrames) * width;
  for (const [start, end] of cuts) paintCut(context, toX(start), toX(end), 0, height, null);

  const left = toX(view.start);
  const right = Math.max(left + 3, toX(view.end));
  context.save();
  context.fillStyle = semantic.waveform.selection;
  context.globalAlpha = 0.12;
  context.fillRect(left, 0, right - left, height);
  context.globalAlpha = 1;
  context.strokeStyle = semantic.waveform.selection;
  context.lineWidth = 2;
  context.strokeRect(left + 1, 1, right - left - 2, height - 2);
  context.restore();
}
