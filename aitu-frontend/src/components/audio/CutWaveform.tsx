/**
 * The Audio tab's waveform: a canvas over one window of the audio, and an overview of all of it.
 *
 * What the reader does on it (plan section 9.4). Each place has one job, so a press never does
 * something the reader did not aim at:
 *
 * - **The time ruler** (the strip with `0:15`, `0:30`, …) holds the playhead. A press there moves the
 *   playhead, and a drag there moves it along. A **double-click** anywhere also moves it.
 * - **In the waveform**, a drag selects a part. The selection snaps to whole time frames (10 ms), so
 *   a cut made from it always falls on a column border of the piano matrix notation.
 * - **The two edges** of the selection carry a grip. The pointer grabs an edge from
 *   {@link EDGE_PX} pixels on either side, and the edge then moves only left or right while the other
 *   one stays; its time is shown beside it. Dragging past the side of the view scrolls the view, so
 *   an edge can be placed precisely while zoomed in.
 * - **A single click** in the waveform clears the selection, or, inside a cut, selects the whole cut
 *   so Restore can put it back. Shift-click stretches the selection to the click.
 * - **Command and the mouse wheel** (or a trackpad pinch) zoom around the pointer. A sideways swipe,
 *   or Shift and the wheel, moves along the audio. The overview below shows the whole audio with the
 *   part on screen framed: drag the frame, or click anywhere to go there.
 *
 * Two canvases lie on top of each other. The lower one holds everything that changes when the
 * reader acts (the peaks, the cuts, the selection) and is painted only then. The upper one holds
 * the playhead alone, repainted on every animation frame while the audio plays, so playback
 * repaints one line and never the waveform, and never re-renders React.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import type { Cut, FramePeaks } from "../../api";
import { clampView, pageTo, panView, zoomView, type FrameView } from "../../audio/frameView";
import { useElementSize } from "../../hooks/useElementSize";
import { ui, useScheme } from "../../ui";
import { paintOverview, paintPlayhead, paintWaveform, RULER } from "./waveformPaint";

export interface CutWaveformProps {
  peaks: FramePeaks;
  cuts: readonly Cut[];
  selection: Cut | null;
  onSelectionChange: (selection: Cut | null) => void;
  /** A single click in the waveform (not the ruler) that was not a drag, and whether Shift was held. */
  onClickFrame: (frame: number, shift: boolean) => void;
  /** Move the playhead: a press or a drag in the ruler, or a double-click anywhere. */
  onSeek: (frame: number) => void;
  view: FrameView;
  onViewChange: (view: FrameView) => void;
  /** Where the playhead rests while nothing plays. */
  cursor: number;
  playing: boolean;
  /** The live position in frames, read on each animation frame while playing. */
  position: () => number;
  height?: number;
}

/** How far from a selection edge, in pixels on either side, a press grabs the edge. */
const EDGE_PX = 10;
/** How far the pointer must move, in pixels, before a press is a drag and not a click. */
const DRAG_PX = 4;
/** Two clicks closer than this, in ms, are one double-click. */
const DOUBLE_CLICK_MS = 500;
const OVERVIEW_HEIGHT = 44;

type Edge = "start" | "end";

type Gesture =
  | { kind: "pending"; x: number; frame: number; shift: boolean }
  | { kind: "select"; anchor: number }
  | { kind: "edge"; fixed: number }
  | { kind: "scrub" };

/** What the pointer is over while no button is pressed: it decides the pointer's shape. */
type Hover = "ruler" | Edge | null;

export function CutWaveform({
  peaks,
  cuts,
  selection,
  onSelectionChange,
  onClickFrame,
  onSeek,
  view,
  onViewChange,
  cursor,
  playing,
  position,
  height = 220,
}: CutWaveformProps) {
  const scheme = useScheme();
  const [boxRef, size] = useElementSize<HTMLDivElement>();
  const baseRef = useRef<HTMLCanvasElement | null>(null);
  const topRef = useRef<HTMLCanvasElement | null>(null);
  const overviewRef = useRef<HTMLCanvasElement | null>(null);
  const gestureRef = useRef<Gesture | null>(null);
  /**
   * The selection as it was before the first click of a possible double-click. The first click
   * clears the selection; when a second click makes it a double-click (move the playhead), the
   * selection comes back, because the reader only wanted to move the playhead.
   */
  const lastClickRef = useRef<{ time: number; selection: Cut | null } | null>(null);
  /** The selection while a drag is under way; handed to the page when the pointer is released. */
  const [dragged, setDragged] = useState<Cut | null>(null);
  const [hover, setHover] = useState<Hover>(null);
  const shown = dragged ?? selection;
  const width = size.width;
  const total = peaks.totalFrames;
  const activeEdge: Edge | null = hover === "start" || hover === "end" ? hover : null;

  // ------------------------------------------------------------------ painting

  useLayoutEffect(() => {
    if (baseRef.current && width > 0) {
      paintWaveform(baseRef.current, width, height, { peaks, cuts, selection: shown, view, activeEdge });
    }
  }, [width, height, peaks, cuts, shown, view, activeEdge, scheme]);

  useLayoutEffect(() => {
    if (overviewRef.current && width > 0) {
      paintOverview(overviewRef.current, width, OVERVIEW_HEIGHT, { peaks, cuts, view });
    }
  }, [width, peaks, cuts, view, scheme]);

  useEffect(() => {
    const canvas = topRef.current;
    if (!canvas || width <= 0) return;
    if (!playing) {
      paintPlayhead(canvas, width, height, view, cursor);
      return;
    }
    let previous = position();
    let frameId = requestAnimationFrame(function tick() {
      const at = position();
      paintPlayhead(canvas, width, height, view, at);
      // Follow the playhead: when it walks off the right edge, turn the page. Only on that crossing,
      // so a reader who moved the view elsewhere during playback is not pulled back at once.
      if (previous <= view.end && at > view.end) {
        onViewChange(pageTo(view, at, total));
        return;
      }
      previous = at;
      frameId = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frameId);
  }, [playing, cursor, view, width, height, position, onViewChange, total]);

  // ------------------------------------------------------------------ pointer

  const frameAt = useCallback(
    (clientX: number) => {
      const canvas = topRef.current;
      if (!canvas) return 0;
      const bounds = canvas.getBoundingClientRect();
      const fraction = (clientX - bounds.left) / Math.max(1, bounds.width);
      return Math.min(total, Math.max(0, view.start + fraction * (view.end - view.start)));
    },
    [view, total],
  );

  const inRuler = (clientY: number) => {
    const canvas = topRef.current;
    return canvas ? clientY - canvas.getBoundingClientRect().top < RULER : false;
  };

  /** The selection edge under the pointer, the nearer one when both are close. */
  const edgeUnder = (clientX: number): Edge | null => {
    if (!selection || !topRef.current) return null;
    const x = clientX - topRef.current.getBoundingClientRect().left;
    const toX = (frame: number) => ((frame - view.start) / (view.end - view.start)) * width;
    const toStart = Math.abs(x - toX(selection[0]));
    const toEnd = Math.abs(x - toX(selection[1]));
    if (Math.min(toStart, toEnd) > EDGE_PX) return null;
    return toStart < toEnd ? "start" : "end";
  };

  const range = (a: number, b: number): Cut => {
    const start = Math.round(Math.min(a, b));
    const end = Math.max(start + 1, Math.round(Math.max(a, b)));
    return [start, Math.min(total, end)];
  };

  /** The press is over: commit what it did. Also called when the release was never seen. */
  const finish = () => {
    const gesture = gestureRef.current;
    gestureRef.current = null;
    if (!gesture) return;
    if (gesture.kind === "pending") {
      const now = performance.now();
      const last = lastClickRef.current;
      if (!last || now - last.time > DOUBLE_CLICK_MS) {
        lastClickRef.current = { time: now, selection };
      }
      onClickFrame(gesture.frame, gesture.shift);
      return;
    }
    if (gesture.kind !== "scrub" && dragged) onSelectionChange(dragged);
    setDragged(null);
  };

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    // Control-click is the right click of a Mac: its menu takes the release, and a press that is
    // never released would leave the selection following the pointer.
    if (event.button !== 0 || event.ctrlKey) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const frame = frameAt(event.clientX);
    if (inRuler(event.clientY)) {
      gestureRef.current = { kind: "scrub" };
      onSeek(frame);
      return;
    }
    const edge = event.shiftKey ? null : edgeUnder(event.clientX);
    if (edge && selection) {
      gestureRef.current = { kind: "edge", fixed: edge === "start" ? selection[1] : selection[0] };
      setHover(edge);
      setDragged(selection);
      return;
    }
    gestureRef.current = { kind: "pending", x: event.clientX, frame, shift: event.shiftKey };
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const gesture = gestureRef.current;
    if (gesture && event.buttons === 0) {
      // The button is up but the release never reached the page: end the press here.
      finish();
      return;
    }
    if (!gesture) {
      setHover(inRuler(event.clientY) ? "ruler" : edgeUnder(event.clientX));
      return;
    }
    const frame = frameAt(event.clientX);
    if (gesture.kind === "scrub") {
      onSeek(frame);
      return;
    }
    if (gesture.kind === "pending") {
      if (Math.abs(event.clientX - gesture.x) < DRAG_PX) return;
      gestureRef.current = { kind: "select", anchor: gesture.frame };
      setDragged(range(gesture.frame, frame));
      return;
    }
    // Past the side of the view: scroll it, so the edge can travel beyond what is on screen.
    const bounds = event.currentTarget.getBoundingClientRect();
    const over = event.clientX < bounds.left ? event.clientX - bounds.left : Math.max(0, event.clientX - bounds.right);
    if (over !== 0) onViewChange(panView(view, over * ((view.end - view.start) / bounds.width) * 0.5, total));
    const anchor = gesture.kind === "select" ? gesture.anchor : gesture.fixed;
    if (gesture.kind === "edge") setHover(frame < anchor ? "start" : "end");
    setDragged(range(anchor, frame));
  };

  const onDoubleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (event.ctrlKey) return;
    const last = lastClickRef.current;
    lastClickRef.current = null;
    if (!inRuler(event.clientY) && last && performance.now() - last.time < DOUBLE_CLICK_MS * 2) {
      onSelectionChange(last.selection);
    }
    onSeek(frameAt(event.clientX));
  };

  // The wheel needs a listener that may call `preventDefault` (React's is passive), and zooming
  // must not also scroll the page.
  useEffect(() => {
    const canvas = topRef.current;
    if (!canvas) return;
    const onWheel = (event: WheelEvent) => {
      const bounds = canvas.getBoundingClientRect();
      const anchor = view.start + ((event.clientX - bounds.left) / bounds.width) * (view.end - view.start);
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        onViewChange(zoomView(view, Math.exp(event.deltaY * 0.002), anchor, total));
        return;
      }
      const sideways = event.shiftKey ? event.deltaY : event.deltaX;
      if (Math.abs(sideways) > Math.abs(event.shiftKey ? 0 : event.deltaY) && sideways !== 0) {
        event.preventDefault();
        const framesPerPixel = (view.end - view.start) / bounds.width;
        onViewChange(panView(view, sideways * framesPerPixel, total));
      }
      // A plain vertical wheel scrolls the page, as everywhere else.
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [view, total, onViewChange]);

  // ------------------------------------------------------------------ overview

  const overviewGrab = useRef<number | null>(null);

  const overviewFrame = (clientX: number) => {
    const canvas = overviewRef.current;
    if (!canvas) return 0;
    const bounds = canvas.getBoundingClientRect();
    return ((clientX - bounds.left) / Math.max(1, bounds.width)) * total;
  };

  const onOverviewDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const frame = overviewFrame(event.clientX);
    const span = view.end - view.start;
    if (frame >= view.start && frame <= view.end) {
      overviewGrab.current = frame - view.start;
    } else {
      overviewGrab.current = span / 2;
      onViewChange(clampView({ start: frame - span / 2, end: frame + span / 2 }, total));
    }
  };

  const onOverviewMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (overviewGrab.current === null) return;
    const span = view.end - view.start;
    const start = overviewFrame(event.clientX) - overviewGrab.current;
    onViewChange(clampView({ start, end: start + span }, total));
  };

  return (
    <Box ref={boxRef} sx={{ width: "100%", userSelect: "none" }}>
      <Box
        sx={{
          position: "relative",
          height,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          overflow: "hidden",
          bgcolor: ui.bg,
        }}
      >
        <canvas ref={baseRef} style={{ position: "absolute", inset: 0, width: "100%", height }} />
        <canvas
          ref={topRef}
          aria-label="Waveform of the audio. Drag to select, click to move the playhead."
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={finish}
          onLostPointerCapture={finish}
          onPointerLeave={() => {
            if (!gestureRef.current) setHover(null);
          }}
          onPointerCancel={() => {
            gestureRef.current = null;
            setDragged(null);
          }}
          onDoubleClick={onDoubleClick}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height,
            cursor: hover === "ruler" ? "pointer" : hover ? "ew-resize" : "text",
            touchAction: "none",
          }}
        />
      </Box>
      <Box
        sx={{
          mt: 1,
          height: OVERVIEW_HEIGHT,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          overflow: "hidden",
        }}
      >
        <canvas
          ref={overviewRef}
          aria-label="The whole audio. Drag the frame to move the view."
          onPointerDown={onOverviewDown}
          onPointerMove={onOverviewMove}
          onPointerUp={() => {
            overviewGrab.current = null;
          }}
          style={{ display: "block", width: "100%", height: OVERVIEW_HEIGHT, cursor: "grab", touchAction: "none" }}
        />
      </Box>
    </Box>
  );
}

export default CutWaveform;
