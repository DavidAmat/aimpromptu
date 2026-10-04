/**
 * Which part of the audio the Audio tab shows: a window `[start, end)` of time frames.
 *
 * Zooming changes the width of the window, panning moves it. The frames are fractional here (a
 * window can start in the middle of a frame); only a selection and a cut snap to whole frames.
 */

export interface FrameView {
  start: number;
  end: number;
}

/** The narrowest window: half a second, so one frame is still several pixels wide on any screen. */
export const MIN_SPAN = 50;

/** Keep the window inside the audio and at least {@link MIN_SPAN} wide. */
export function clampView(view: FrameView, totalFrames: number, minSpan = MIN_SPAN): FrameView {
  const span = Math.min(totalFrames, Math.max(Math.min(minSpan, totalFrames), view.end - view.start));
  const start = Math.min(Math.max(0, view.start), totalFrames - span);
  return { start, end: start + span };
}

/** Zoom by `factor` (below 1 is in) around `anchor`, which stays under the pointer. */
export function zoomView(view: FrameView, factor: number, anchor: number, totalFrames: number): FrameView {
  const span = view.end - view.start;
  const next = Math.min(totalFrames, Math.max(MIN_SPAN, span * factor));
  const start = anchor - (anchor - view.start) * (next / span);
  return clampView({ start, end: start + next }, totalFrames);
}

/** Move the window by `frames`. */
export function panView(view: FrameView, frames: number, totalFrames: number): FrameView {
  return clampView({ start: view.start + frames, end: view.end + frames }, totalFrames);
}

/** The same width, with `frame` a little after its left edge: where playback continues. */
export function pageTo(view: FrameView, frame: number, totalFrames: number): FrameView {
  const span = view.end - view.start;
  const start = frame - span * 0.05;
  return clampView({ start, end: start + span }, totalFrames);
}

/** The whole audio. */
export function wholeView(totalFrames: number): FrameView {
  return { start: 0, end: totalFrames };
}
