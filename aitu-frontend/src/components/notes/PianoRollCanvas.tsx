/**
 * The Notes tab's piano roll visualization: the vertical keyboard, one row per key, and the
 * rectangles on a time axis, on two canvases (plan section 9.5).
 *
 * **Why a canvas.** The old piano roll visualization is SVG, one element per note, and React
 * rebuilt the notes many times per second during playback. Here the notes are typed arrays
 * (`RollNotes`) painted directly, and React renders this component only when the page changes
 * something (the selection, a saved edit, a mode). Everything that moves on its own (the live
 * stream, the growing rectangles, the playhead) is painted from one animation loop, which runs only
 * while something moves and stops by itself.
 *
 * **Three modes.**
 * - `live`: a transcription is running. The notes come from the feed, the view follows the
 *   frontier (the part already transcribed is a little lighter), and nothing can be edited.
 * - `edit`: the saved notes, with the gestures below, and playback.
 * - `view`: the notes can be looked at, not changed (stale notes).
 *
 * **The gestures** (`edit`), each place with one job, as on the Audio tab:
 * - the **time ruler** at the top moves the playhead (press, or drag along it);
 * - **click** a rectangle to select it, **Command-click** to add it to the selection or take it
 *   out, **drag on empty space** to select every rectangle in the band;
 * - **drag a rectangle** to move the selection earlier or later (with **Shift**, also to another
 *   key), and **drag its left or right edge** to change where it starts or ends; every move snaps
 *   to whole time frames of 10 ms;
 * - **double-click on empty space** adds a rectangle of 250 ms on that key;
 * - **Command and the wheel** (or a pinch) zoom around the pointer; a sideways swipe, or Shift and
 *   the wheel, moves along the piece. In `live` and `view`, dragging the notes also moves along.
 */

import { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, type Ref } from "react";
import Box from "@mui/material/Box";
import { useElementSize } from "../../hooks/useElementSize";
import { semantic } from "../../ui";
import type { LiveFeed } from "../../notes/liveFeed";
import type { RollNotes } from "../../notes/rollNotes";
import {
  clampedKeyAt,
  clampRollView,
  widenKeys,
  DEFAULT_PX_PER_SEC,
  keyAt,
  msAt,
  pageRollTo,
  rollLayout,
  snapDelta,
  SNAP_MS,
  spanMs,
  wholeRollView,
  xOf,
  zoomRoll,
  type RollLayout,
  type RollView,
} from "../../notes/rollView";
import {
  paintBase,
  paintOverlay,
  prepareCanvas,
  REVEAL_MS,
  timeAtX,
  shownBy,
  type ColourBy,
  type DragPreview,
  type HandFilter,
} from "./rollPaint";

export type RollMode = "live" | "edit" | "view";

/** What the page can ask of the roll: the zoom buttons, and showing a time. */
export interface RollHandle {
  zoomBy: (factor: number) => void;
  showWhole: () => void;
  /** Move the view so `ms` is in it, if it is not already. */
  reveal: (ms: number) => void;
  /** Move the view by `ms` (a sideways swipe does this). */
  panBy: (ms: number) => void;
  /** Put `ms` in the middle of the view: going to one note. */
  center: (ms: number) => void;
  /** The view as it is now, for the checks. */
  view: () => RollView;
}

export interface PianoRollCanvasProps {
  notes: RollNotes;
  mode: RollMode;
  durationMs: number;
  /** The live stream, in `live` mode. */
  feed?: LiveFeed | null;
  selection: ReadonlySet<number>;
  colourBy?: ColourBy;
  /** Only one hand in full (the Hands tab's filter); the other is faint and cannot be picked. */
  handFilter?: HandFilter;
  /** Playback: the playhead at rest, and the live position while playing. */
  cursorMs: number;
  playing: boolean;
  position: () => number;
  /** `null` when the playhead cannot be moved (live, or no audio). */
  onSeek: ((ms: number) => void) | null;
  /** Keep the playhead (or the live frontier) in view. */
  follow: boolean;
  onFollowChange: (follow: boolean) => void;
  onSelect?: (ids: Set<number>) => void;
  onMove?: (ids: ReadonlySet<number>, dMs: number, dKey: number) => void;
  onResize?: (id: number, onMs: number, lenMs: number) => void;
  onAdd?: (key: number, onMs: number) => void;
  height?: number | string;
  ref?: Ref<RollHandle>;
  /** For the measurements (`/dev/roll-bench`): the time each painted frame took, in ms. */
  stats?: { paintMs: number[] };
}

/** A press this close to the left or the right edge of a rectangle grabs the edge. */
const EDGE_PX = 6;
/** How far the pointer must move, in pixels, before a press is a drag. */
const DRAG_PX = 3;
/** A rectangle this narrow can still be picked: the pointer may miss it by this much. */
const PICK_PX = 3;
/** Where the live frontier sits in the view while it is followed. */
const FOLLOW_AT = 0.66;
const FOLLOW_EASE = 0.09;
const MIN_LEN_MS = SNAP_MS;

type Gesture =
  | { kind: "scrub" }
  | { kind: "pan"; x: number; startMs: number }
  | { kind: "pressNote"; id: number; x: number; y: number; ms: number; key: number; ids: Set<number>; keep: boolean }
  | {
      kind: "move";
      ids: Set<number>;
      ms: number;
      key: number;
      /** The limits of the selection at the start, so the move stays inside the piece and keyboard. */
      minOn: number;
      maxEnd: number;
      minKey: number;
      maxKey: number;
      dMs: number;
      dKey: number;
    }
  | { kind: "resize"; id: number; edge: "start" | "end"; ms: number; on: number; end: number; newOn: number; newLen: number }
  | { kind: "pressEmpty"; x: number; y: number; additive: boolean }
  | { kind: "band"; x0: number; y0: number; x1: number; y1: number; additive: boolean; ids: Set<number> };

export function PianoRollCanvas({
  notes,
  mode,
  durationMs,
  feed = null,
  selection,
  colourBy = "none",
  handFilter = "both",
  cursorMs,
  playing,
  position,
  onSeek,
  follow,
  onFollowChange,
  onSelect,
  onMove,
  onResize,
  onAdd,
  height = "min(66vh, 720px)",
  ref,
  stats,
}: PianoRollCanvasProps) {
  const [boxRef, size] = useElementSize<HTMLDivElement>();
  const baseRef = useRef<HTMLCanvasElement | null>(null);
  const topRef = useRef<HTMLCanvasElement | null>(null);

  // Everything the animation loop and the pointer read, current as of the last render.
  const latest = useRef({ size, notes, mode, durationMs, feed, selection, colourBy, handFilter, cursorMs, playing, position, follow, stats });
  useLayoutEffect(() => {
    latest.current = { size, notes, mode, durationMs, feed, selection, colourBy, handFilter, cursorMs, playing, position, follow, stats };
  });

  /** The keys shown. They only grow while the page is open, so the rows never jump back. */
  const keysRef = useRef<[number, number] | null>(null);
  /** The layout now: the size of the box and the keys the notes use. */
  const layoutNow = useCallback((): RollLayout => {
    const { size: box, notes: held } = latest.current;
    const range = held.keyRange();
    const keys = widenKeys(keysRef.current, range);
    if (range) keysRef.current = keys;
    return rollLayout(box.width, box.height, keys[0], keys[1]);
  }, []);

  const viewRef = useRef<RollView>({ startMs: 0, pxPerSec: DEFAULT_PX_PER_SEC });
  const gestureRef = useRef<Gesture | null>(null);
  const loopRef = useRef({ frame: 0, inTick: false, base: true, top: true, revealUntil: 0, previousPlay: 0 });
  const [hover, setHover] = useState<"ruler" | "edge" | "note" | null>(null);

  // ------------------------------------------------------------------ the loop

  const tick = useCallback((now: number) => {
    const loop = loopRef.current;
    loop.frame = 0;
    // A change made during this frame (the feed's notes land in the store) must not ask for a
    // second frame: this one asks for the next, once, at its end.
    loop.inTick = true;
    const state = latest.current;
    const layout = layoutNow();
    const base = baseRef.current;
    const top = topRef.current;
    if (!base || !top || layout.width <= 0 || layout.height <= 0) {
      loop.inTick = false;
      return;
    }
    const began = performance.now();
    let more = false;
    let view = viewRef.current;

    // The live stream: take the queue, move the frontier, follow it.
    const live = state.mode === "live" ? state.feed : null;
    if (live) {
      if (live.drain(state.notes, now)) {
        loop.base = true;
        loop.revealUntil = now + REVEAL_MS;
      }
      if (live.step(now)) {
        more = true;
        loop.base = true;
      }
      if (state.follow) {
        const span = spanMs(layout, view);
        const target = Math.max(0, live.shownMs - span * FOLLOW_AT);
        const next = view.startMs + (target - view.startMs) * FOLLOW_EASE;
        if (Math.abs(next - view.startMs) > 0.5) {
          view = clampRollView({ ...view, startMs: Math.abs(target - next) < 1 ? target : next }, layout, Math.max(state.durationMs, live.durationMs));
          viewRef.current = view;
          loop.base = true;
          more = true;
        }
      }
    }
    if (now < loop.revealUntil) {
      loop.base = true;
      more = true;
    }

    // Playback: the playhead moves; turn the page when it walks off the right edge.
    let playhead: number | null = state.mode === "live" ? null : state.cursorMs;
    if (state.playing && state.mode !== "live") {
      playhead = state.position();
      const right = view.startMs + spanMs(layout, view);
      // Also when playback starts outside the view (the live view ends at the end of the piece).
      const outside = playhead < view.startMs || playhead > right;
      if (state.follow && (outside || (loop.previousPlay <= right && playhead > right))) {
        view = pageRollTo(view, playhead, layout, state.durationMs);
        viewRef.current = view;
        loop.base = true;
      }
      loop.previousPlay = playhead;
      loop.top = true;
      more = true;
    }

    const gesture = gestureRef.current;
    if (loop.base) {
      const context = prepareCanvas(base, layout.width, layout.height);
      if (context) {
        const frontier = live ? live.shownMs : null;
        paintBase(context, layout, view, {
          notes: state.notes,
          durationMs: Math.max(state.durationMs, live?.durationMs ?? 0),
          selection: state.selection,
          colourBy: state.colourBy,
          handFilter: state.handFilter,
          preview: previewOf(gesture),
          frontierMs: frontier,
          openUntilMs: live ? Math.min(live.shownMs, live.upToMs) : 0,
          now,
          banded: gesture?.kind === "band" ? gesture.ids : null,
        });
      }
      loop.base = false;
      loop.top = true;
      // For the checks in a headless browser: where the notes are drawn.
      base.dataset.viewStart = String(view.startMs);
      base.dataset.pxPerSec = String(view.pxPerSec);
      base.dataset.keys = `${layout.lowKey},${layout.highKey}`;
    }
    if (loop.top) {
      const context = prepareCanvas(top, layout.width, layout.height);
      if (context) {
        paintOverlay(context, layout, view, {
          notes: state.notes,
          colourBy: state.colourBy,
          handFilter: state.handFilter,
          playheadMs: playhead,
          sounding: state.playing,
          selectedKeys: selectedKeysOf(state.notes, gesture?.kind === "band" ? gesture.ids : state.selection),
          band: gesture?.kind === "band" ? gesture : null,
        });
      }
      loop.top = false;
    }
    state.stats?.paintMs.push(performance.now() - began);
    loop.inTick = false;
    if (more || loop.base || loop.top) loop.frame = requestAnimationFrame(tick);
  }, [layoutNow]);

  /** Paint on the next animation frame: the lower canvas, the upper one, or both. */
  const schedule = useCallback(
    (what: { base?: boolean; top?: boolean } = { base: true }) => {
      const loop = loopRef.current;
      if (what.base) loop.base = true;
      if (what.top) loop.top = true;
      if (!loop.frame && !loop.inTick) loop.frame = requestAnimationFrame(tick);
    },
    [tick],
  );

  useEffect(
    () => () => {
      // The id must go too: a remount (React's development mode does one) schedules again.
      cancelAnimationFrame(loopRef.current.frame);
      loopRef.current.frame = 0;
    },
    [],
  );
  useEffect(() => notes.subscribe(() => schedule()), [notes, schedule]);
  useEffect(() => (feed ? feed.subscribe(() => schedule()) : undefined), [feed, schedule]);
  useEffect(() => {
    schedule({ base: true, top: true });
  }, [schedule, size.width, size.height, selection, colourBy, handFilter, mode, durationMs, follow]);
  useEffect(() => {
    loopRef.current.previousPlay = cursorMs;
    schedule({ top: true });
  }, [schedule, cursorMs, playing]);

  // The first view of a piece: its first minute, or all of it when shorter.
  const placedFor = useRef<number | null>(null);
  useLayoutEffect(() => {
    if (size.width <= 0 || placedFor.current === durationMs) return;
    placedFor.current = durationMs;
    const layout = layoutNow();
    const whole = wholeRollView(layout, durationMs);
    viewRef.current = clampRollView(
      { startMs: 0, pxPerSec: Math.max(whole.pxPerSec, DEFAULT_PX_PER_SEC) },
      layout,
      durationMs,
    );
    schedule();
  });

  const setView = useCallback(
    (next: RollView) => {
      viewRef.current = clampRollView(next, layoutNow(), latest.current.durationMs);
      schedule({ base: true, top: true });
    },
    [schedule, layoutNow],
  );

  useImperativeHandle(
    ref,
    () => ({
      zoomBy: (factor: number) => {
        const view = viewRef.current;
        const state = latest.current;
        const span = spanMs(layoutNow(), view);
        const inView = (ms: number) => ms >= view.startMs && ms <= view.startMs + span;
        const anchor = inView(state.cursorMs) ? state.cursorMs : view.startMs + span / 2;
        setView(zoomRoll(view, factor, anchor, layoutNow(), state.durationMs));
      },
      showWhole: () => setView(wholeRollView(layoutNow(), latest.current.durationMs)),
      reveal: (ms: number) => {
        const view = viewRef.current;
        const span = spanMs(layoutNow(), view);
        if (ms < view.startMs || ms > view.startMs + span) {
          setView(pageRollTo(view, ms, layoutNow(), latest.current.durationMs));
        }
      },
      panBy: (ms: number) => setView({ ...viewRef.current, startMs: viewRef.current.startMs + ms }),
      center: (ms: number) =>
        setView({ ...viewRef.current, startMs: ms - spanMs(layoutNow(), viewRef.current) / 2 }),
      view: () => viewRef.current,
    }),
    [setView, layoutNow],
  );

  // ------------------------------------------------------------------ the pointer

  const local = (event: { clientX: number; clientY: number }) => {
    const bounds = topRef.current?.getBoundingClientRect();
    return bounds ? { x: event.clientX - bounds.left, y: event.clientY - bounds.top } : { x: 0, y: 0 };
  };

  /** The rectangle under a point, and which part of it: an edge or its body. */
  const noteAt = (x: number, y: number): { slot: number; part: "start" | "end" | "body" } | null => {
    const view = viewRef.current;
    const layout = layoutNow();
    const key = keyAt(layout, y);
    if (key < 0 || x < layout.keyboard) return null;
    const ms = msAt(layout, view, x);
    const slot = notes.hit(key, ms, (PICK_PX * 1000) / view.pxPerSec);
    if (slot < 0 || !shownBy(handFilter, notes.hand[slot]!)) return null;
    const left = xOf(layout, view, notes.onMs[slot]!);
    const right = xOf(layout, view, notes.endOf(slot));
    const width = right - left;
    if (width >= EDGE_PX * 2.5) {
      if (x - left <= EDGE_PX) return { slot, part: "start" };
      if (right - x <= EDGE_PX) return { slot, part: "end" };
    }
    return { slot, part: "body" };
  };

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    // Control-click is the right click of a Mac: its menu takes the release.
    if (event.button !== 0 || event.ctrlKey) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const { x, y } = local(event);
    const view = viewRef.current;
    const layout = layoutNow();
    if (y < layout.ruler) {
      if (onSeek) {
        gestureRef.current = { kind: "scrub" };
        onSeek(timeAtX(layout, view, x, durationMs));
      }
      return;
    }
    if (x < layout.keyboard) return;
    if (mode !== "edit") {
      gestureRef.current = { kind: "pan", x, startMs: view.startMs };
      return;
    }
    const hit = noteAt(x, y);
    if (!hit) {
      gestureRef.current = { kind: "pressEmpty", x, y, additive: event.metaKey || event.shiftKey };
      return;
    }
    const id = notes.id[hit.slot]!;
    if (hit.part !== "body") {
      if (!selection.has(id)) onSelect?.(new Set([id]));
      const on = notes.onMs[hit.slot]!;
      const end = notes.endOf(hit.slot);
      gestureRef.current = {
        kind: "resize",
        id,
        edge: hit.part,
        ms: msAt(layout, view, x),
        on,
        end,
        newOn: on,
        newLen: end - on,
      };
      return;
    }
    let ids: Set<number>;
    let keep = true;
    if (event.metaKey) {
      ids = new Set(selection);
      if (ids.has(id)) ids.delete(id);
      else ids.add(id);
      onSelect?.(ids);
      if (!ids.has(id)) return;
    } else if (selection.has(id)) {
      ids = new Set(selection);
      // A plain click on a note of a larger selection selects it alone, unless it becomes a drag.
      keep = selection.size === 1;
    } else {
      ids = new Set([id]);
      onSelect?.(ids);
    }
    gestureRef.current = {
      kind: "pressNote",
      id,
      x,
      y,
      ms: msAt(layout, view, x),
      key: notes.key[hit.slot]!,
      ids,
      keep,
    };
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const gesture = gestureRef.current;
    const { x, y } = local(event);
    const view = viewRef.current;
    const layout = layoutNow();
    if (gesture && event.buttons === 0) {
      finish();
      return;
    }
    if (!gesture) {
      if (y < layout.ruler) setHover(onSeek ? "ruler" : null);
      else if (mode === "edit") {
        const hit = noteAt(x, y);
        setHover(hit ? (hit.part === "body" ? "note" : "edge") : null);
      } else setHover(null);
      return;
    }
    const ms = msAt(layout, view, x);
    switch (gesture.kind) {
      case "scrub":
        onSeek?.(timeAtX(layout, view, x, durationMs));
        return;
      case "pan":
        if (follow) onFollowChange(false);
        setView({ ...view, startMs: gesture.startMs - ((x - gesture.x) * 1000) / view.pxPerSec });
        return;
      case "pressNote": {
        if (Math.hypot(x - gesture.x, y - gesture.y) < DRAG_PX) return;
        let minOn = Infinity;
        let maxEnd = 0;
        let minKey = 87;
        let maxKey = 0;
        for (const id of gesture.ids) {
          const slot = notes.slotOf(id);
          if (slot < 0) continue;
          minOn = Math.min(minOn, notes.onMs[slot]!);
          maxEnd = Math.max(maxEnd, notes.endOf(slot));
          minKey = Math.min(minKey, notes.key[slot]!);
          maxKey = Math.max(maxKey, notes.key[slot]!);
        }
        gestureRef.current = {
          kind: "move",
          ids: gesture.ids,
          ms: gesture.ms,
          key: gesture.key,
          minOn,
          maxEnd,
          minKey,
          maxKey,
          dMs: 0,
          dKey: 0,
        };
        onPointerMove(event);
        return;
      }
      case "move": {
        scrollAtSide(x);
        const dMs = Math.min(durationMs - gesture.maxEnd, Math.max(-gesture.minOn, snapDelta(ms - gesture.ms)));
        const dKey = event.shiftKey
          ? Math.min(layout.highKey - gesture.maxKey, Math.max(layout.lowKey - gesture.minKey, clampedKeyAt(layout, y) - gesture.key))
          : 0;
        if (dMs !== gesture.dMs || dKey !== gesture.dKey) {
          gestureRef.current = { ...gesture, dMs, dKey };
          schedule();
        }
        return;
      }
      case "resize": {
        scrollAtSide(x);
        const delta = snapDelta(ms - gesture.ms);
        let newOn = gesture.on;
        let newEnd = gesture.end;
        if (gesture.edge === "start") newOn = Math.min(gesture.end - MIN_LEN_MS, Math.max(0, gesture.on + delta));
        else newEnd = Math.max(gesture.on + MIN_LEN_MS, Math.min(durationMs, gesture.end + delta));
        if (newOn !== gesture.newOn || newEnd - newOn !== gesture.newLen) {
          gestureRef.current = { ...gesture, newOn, newLen: newEnd - newOn };
          schedule();
        }
        return;
      }
      case "pressEmpty":
        if (Math.hypot(x - gesture.x, y - gesture.y) < DRAG_PX) return;
        gestureRef.current = { kind: "band", x0: gesture.x, y0: gesture.y, x1: x, y1: y, additive: gesture.additive, ids: new Set() };
        onPointerMove(event);
        return;
      case "band": {
        const x1 = Math.max(layout.keyboard, Math.min(layout.width, x));
        const y1 = Math.max(layout.ruler, Math.min(layout.height, y));
        const low = clampedKeyAt(layout, Math.max(gesture.y0, y1));
        const high = clampedKeyAt(layout, Math.min(gesture.y0, y1));
        const from = msAt(layout, view, Math.min(gesture.x0, x1));
        const to = msAt(layout, view, Math.max(gesture.x0, x1));
        const ids = new Set(
          notes.idsInBand(low, high, from, to).filter((id) => shownBy(handFilter, notes.hand[notes.slotOf(id)]!)),
        );
        if (gesture.additive) for (const id of selection) ids.add(id);
        gestureRef.current = { ...gesture, x1, y1, ids };
        schedule({ base: true, top: true });
        return;
      }
    }
  };

  /** A drag past the side of the notes scrolls the view, so a note can travel beyond the screen. */
  const scrollAtSide = (x: number) => {
    const view = viewRef.current;
    const layout = layoutNow();
    const over = x < layout.keyboard ? x - layout.keyboard : Math.max(0, x - layout.width);
    if (over !== 0) setView({ ...view, startMs: view.startMs + ((over * 1000) / view.pxPerSec) * 0.5 });
  };

  /** The press is over: commit what it did. */
  function finish() {
    const gesture = gestureRef.current;
    gestureRef.current = null;
    if (!gesture) return;
    switch (gesture.kind) {
      case "pressNote":
        if (!gesture.keep) onSelect?.(new Set([gesture.id]));
        break;
      case "move":
        if (gesture.dMs !== 0 || gesture.dKey !== 0) onMove?.(gesture.ids, gesture.dMs, gesture.dKey);
        break;
      case "resize":
        if (gesture.newOn !== gesture.on || gesture.newLen !== gesture.end - gesture.on) {
          onResize?.(gesture.id, gesture.newOn, gesture.newLen);
        }
        break;
      case "pressEmpty":
        if (!gesture.additive) onSelect?.(new Set());
        break;
      case "band":
        onSelect?.(gesture.ids);
        break;
      default:
        break;
    }
    schedule({ base: true, top: true });
  }

  const onDoubleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (mode !== "edit" || !onAdd || event.ctrlKey) return;
    const { x, y } = local(event);
    const layout = layoutNow();
    if (y < layout.ruler || x < layout.keyboard) return;
    if (noteAt(x, y)) return;
    const key = keyAt(layout, y);
    if (key < 0) return;
    const ms = Math.round(msAt(layout, viewRef.current, x) / SNAP_MS) * SNAP_MS;
    onAdd(key, Math.max(0, Math.min(durationMs - MIN_LEN_MS, ms)));
  };

  // The wheel needs a listener that may call `preventDefault` (React's is passive).
  useEffect(() => {
    const canvas = topRef.current;
    if (!canvas) return;
    const onWheel = (event: WheelEvent) => {
      const state = latest.current;
      const bounds = canvas.getBoundingClientRect();
      const view = viewRef.current;
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        const anchor = msAt(layoutNow(), view, event.clientX - bounds.left);
        setView(zoomRoll(view, Math.exp(-event.deltaY * 0.002), anchor, layoutNow(), state.durationMs));
        return;
      }
      const sideways = event.shiftKey ? event.deltaY : event.deltaX;
      if (Math.abs(sideways) > Math.abs(event.shiftKey ? 0 : event.deltaY) && sideways !== 0) {
        event.preventDefault();
        if (state.follow) onFollowChange(false);
        setView({ ...view, startMs: view.startMs + (sideways * 1000) / view.pxPerSec });
      }
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [setView, onFollowChange, layoutNow]);

  const cursor =
    hover === "ruler"
      ? "pointer"
      : hover === "edge"
        ? "ew-resize"
        : hover === "note"
          ? "grab"
          : mode === "edit"
            ? "crosshair"
            : "grab";

  return (
    <Box
      ref={boxRef}
      sx={{
        position: "relative",
        width: "100%",
        height,
        minHeight: 420,
        borderRadius: 1,
        overflow: "hidden",
        userSelect: "none",
        bgcolor: semantic.roll.background,
      }}
    >
      <canvas ref={baseRef} data-roll="base" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      <canvas
        ref={topRef}
        data-roll="top"
        aria-label="Piano roll visualization of the notes"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={finish}
        onLostPointerCapture={finish}
        onPointerLeave={() => {
          if (!gestureRef.current) setHover(null);
        }}
        onPointerCancel={() => {
          gestureRef.current = null;
          schedule({ base: true, top: true });
        }}
        onDoubleClick={onDoubleClick}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", cursor, touchAction: "none" }}
      />
    </Box>
  );
}

/** The keys of the selected notes, kept until the selection or the notes change. */
let keysCache: { selection: ReadonlySet<number> | null; version: number; notes: RollNotes | null; keys: Set<number> } = {
  selection: null,
  version: -1,
  notes: null,
  keys: new Set(),
};
function selectedKeysOf(notes: RollNotes, selection: ReadonlySet<number>): ReadonlySet<number> {
  if (keysCache.selection === selection && keysCache.notes === notes && keysCache.version === notes.version) return keysCache.keys;
  const keys = new Set<number>();
  for (const id of selection) {
    const slot = notes.slotOf(id);
    if (slot >= 0) keys.add(notes.key[slot]!);
  }
  keysCache = { selection, version: notes.version, notes, keys };
  return keys;
}

/** The drag being made, as the painter draws it. */
function previewOf(gesture: Gesture | null): DragPreview | null {
  if (gesture?.kind === "move") return { kind: "move", ids: gesture.ids, dMs: gesture.dMs, dKey: gesture.dKey };
  if (gesture?.kind === "resize") return { kind: "resize", id: gesture.id, onMs: gesture.newOn, lenMs: gesture.newLen };
  return null;
}

/** For the painter's layout type, re-exported so pages do not import two modules. */
export type { RollLayout };

export default PianoRollCanvas;
