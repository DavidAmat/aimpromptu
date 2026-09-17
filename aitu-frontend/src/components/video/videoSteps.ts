/**
 * What is done on one video, in the order the work happens.
 *
 * Its own module because a file that exports a component may not also export a
 * function: Vite's fast refresh stops working for it, and the lint says so.
 */

import type { VideoSummary } from "../../api/video";

export interface VideoStep {
  label: string;
  done: boolean;
}

/**
 * The six steps, always all six and always in order, so the chips say what is
 * missing as plainly as what is done: download it, sample its frames, fit the
 * piano on one of them, measure how fast the roll falls, read every frame of it,
 * and stitch the whole thing into the notes of the piece.
 */
export function steps(video: VideoSummary): VideoStep[] {
  const speed = video.measurement?.scrollSpeed;
  return [
    { label: "downloaded", done: true },
    {
      label: video.metadata.frameCount
        ? `${video.metadata.frameCount} frames at ${video.metadata.sampleMs} ms`
        : "not sampled",
      done: video.metadata.frameCount > 0,
    },
    {
      label: video.calibration ? "piano fitted" : "no piano yet",
      done: video.calibration !== null,
    },
    {
      label: speed?.stable
        ? `${speed.pxPerSecond.toFixed(1)} px/s`
        : speed
          ? "speed not stable"
          : "not measured",
      done: Boolean(speed?.stable),
    },
    {
      label: video.detected ? `${video.detectedFrames} frames read` : "not read",
      done: video.detected,
    },
    {
      label: video.noteCount ? `${video.noteCount} notes` : "no notes yet",
      done: video.noteCount > 0,
    },
  ];
}
