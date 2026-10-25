/**
 * The new piano sheet on the page (implementation 03, Phase 5): the SVG the backend draws, and over it, in the same
 * staff-space units, what moves.
 *
 * - **The segment at Sonnet** (plan section 3.6) is covered by a pale, slowly breathing veil: the notes under it
 *   read grey. No text: the look alone says that it is changing.
 * - **A segment that comes back** appears column by column, like a text an LLM writes word by word: blank staves
 *   over it, then the notes, left to right, in about two seconds.
 * - **The cursor** follows the recording (the research viewer's arithmetic, `geometry.ts`): a line between two
 *   columns by their times, the noteheads of the column it is in lit, and a click on the sheet moves the
 *   recording there. While it plays, the page keeps the line of the cursor in view (in the middle in Play mode).
 *
 * - **Notes can be picked** (Phase 6, when the page gives `onPick`): a click on a notehead picks it (and moves the
 *   recording there), ⌘ or Shift adds it to the notes already picked, and a box dragged across the staves picks
 *   every notehead in it. A click off the notes drops the pick and moves the recording, as before. A head is found
 *   within a few pixels of the click: a notehead is about 8 pixels wide.
 * - **A stretch can be marked** (Phase 7, when the page gives `onRange`), as in the old sheet: in the strip above the
 *   upper staff of a line (it shows faintly under the pointer), a click marks one column, a drag marks every column
 *   it crosses (on to the next lines too), and Shift-click extends the stretch marked. The stretch is a lavender
 *   band over the staves in scope (both, or the one hand's staff of **Both / Right / Left**).
 *
 * Hooks for the browser checks: `data-frames-sheet` on the root (with `data-source`, `data-llm`, `data-working`),
 * `data-note="<frame>:<midi>"` on each notehead, `data-lit` on the lit ones, `data-selected` on the picked ones,
 * `data-frames-cursor` (with `data-ms`), `data-segment-state="working"` on the veil, `data-revealing` while a
 * segment appears, `data-pick-box` while a box is dragged, `data-range-band` on the marked stretch (one per line,
 * with `data-start` and `data-end`) and `data-range-strip` on the strip under the pointer.
 */

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import Box from "@mui/material/Box";
import { keyframes } from "@mui/material/styles";
import type { FramesSheet } from "../../../../api";
import { palette, semantic } from "../../../../ui";
import { boxesOf, columnEdges, columnsOf, headsByColumn, msAtPoint, placeAt, steadyColumns } from "./geometry";

/** The reveal of a segment takes about this long, whatever its number of columns. */
const REVEAL_MS = 1800;
const STEP_MIN_MS = 25;
const STEP_MAX_MS = 90;
/** The stroke of a staff line in the engine (Verovio's style, 13/180 of a staff space: `layout.STAFF_LINE_W`). */
const STAFF_LINE = 13 / 180;
/** A click this close to a notehead picks it, in pixels. */
const PICK_PX = 6;
/** A press that moves farther than this drags a box, in pixels. */
const DRAG_PX = 5;

/** How a pick joins the notes already picked: `only` replaces them, `add` adds (or takes away) the ones named. */
export type PickHow = "only" | "add";

/** A marked stretch of frames (`end` excluded), and the staff it is about. */
export interface MarkedRange {
  start: number;
  end: number;
}
export type RangeScope = "both" | "right" | "left";

/** The strip above the upper staff where a stretch is marked: from this far above its top line, in staff spaces. */
const STRIP_SPACES = 3.5;
/** The band of a stretch reaches this far beyond the staff lines it covers, in staff spaces. */
const BAND_PAD = 1.5;

/** The refs a notehead names (merged unisons name several). */
function refsOf(element: Element): string[] {
  return (element.getAttribute("data-note") ?? "").split(" ").filter(Boolean);
}

/** The notehead nearest a point of the screen, within `PICK_PX`. */
function headAt(root: ParentNode, x: number, y: number): Element | null {
  let best: Element | null = null;
  let distance = PICK_PX;
  for (const element of root.querySelectorAll("[data-note]")) {
    const box = element.getBoundingClientRect();
    const dx = Math.max(box.left - x, 0, x - box.right);
    const dy = Math.max(box.top - y, 0, y - box.bottom);
    const d = Math.hypot(dx, dy);
    if (d <= distance) {
      distance = d;
      best = element;
    }
  }
  return best;
}

/** A stretch being dragged in the strip: the column indices where it began and where the pointer is. */
interface RangeDrag {
  from: number;
  to: number;
  extend: boolean;
}

interface Drag {
  /** The top left of the sheet on screen when the press began: the box is drawn from it. */
  left: number;
  top: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  add: boolean;
  moved: boolean;
}

const breathe = keyframes`
  from { opacity: 0.55; }
  to { opacity: 0.72; }
`;

interface Reveal {
  /** The columns of the segment that appears: `[from, to)`. */
  from: number;
  to: number;
  /** Columns shown so far, from `from`. */
  shown: number;
}

export function FramesSheetView({
  sheet,
  playheadSeconds,
  follow,
  centre = false,
  onSeek,
  selected,
  onPick,
  range = null,
  rangeScope = "both",
  onRange,
}: {
  sheet: FramesSheet;
  playheadSeconds: number | null;
  /** The recording plays: keep the cursor's line in view. */
  follow: boolean;
  /** In the middle of the window (Play mode), not only in view. */
  centre?: boolean;
  onSeek?: (seconds: number) => void;
  /** The notes picked, by ref (`"<frame>:<midi>"`). */
  selected?: ReadonlySet<string>;
  /** Notes can be picked: called with the refs of a click or of a box; `[]` with `only` drops the pick. */
  onPick?: (refs: string[], how: PickHow) => void;
  /** The stretch marked, and the staff it is about. */
  range?: MarkedRange | null;
  rangeScope?: RangeScope;
  /** A stretch can be marked: called with its frames when a click or a drag in the strip ends. */
  onRange?: (range: MarkedRange) => void;
}) {
  const host = useRef<HTMLDivElement | null>(null);
  const overlay = useRef<SVGSVGElement | null>(null);
  const cursor = useRef<SVGLineElement | null>(null);
  const columns = useMemo(() => steadyColumns(sheet.columns), [sheet.columns]);
  const edges = useMemo(() => columnEdges(columns, sheet.systems), [columns, sheet.systems]);
  /** The noteheads of each column of the drawing on the page (`data-note`). */
  const heads = useRef<Element[][]>([]);

  // The drawing itself, put in as the backend wrote it; it scales to the page's width.
  useLayoutEffect(() => {
    const element = host.current;
    if (!element) return;
    element.innerHTML = sheet.svg;
    const svg = element.querySelector("svg");
    if (svg) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      svg.style.display = "block";
      svg.style.width = "100%";
      svg.style.height = "auto";
    }
    heads.current = headsByColumn(element, columns);
  }, [sheet.svg, columns]);

  // ------------------------------------------------------------------ segments: at Sonnet, and coming back

  const working = useMemo(
    () =>
      sheet.segments
        .filter((segment) => segment.state === "working")
        .flatMap((segment) => {
          const [from, to] = columnsOf(segment, columns);
          return boxesOf(from, to, columns, edges, sheet.systems);
        }),
    [sheet.segments, columns, edges, sheet.systems],
  );

  const [reveal, setReveal] = useState<Reveal | null>(null);
  // Compared during render, so the new drawing never shows for one frame before its segment is covered.
  const [seen, setSeen] = useState(sheet.segments);
  if (seen !== sheet.segments) {
    setSeen(sheet.segments);
    const earlier = new Map(seen.map((segment) => [segment.start, segment.state]));
    const wasWorking = seen.find((segment) => segment.state === "working");
    const decided = (segment: (typeof sheet.segments)[number]) => segment.state === "llm" || segment.state === "algorithm";
    // The segment that was at Sonnet (or waiting) and is decided now: the same stretch first (a stretch the AI wrote
    // again with the user's words, Phase 7, ends where it ended), else a window with the same start.
    const back =
      sheet.segments.find(
        (segment) => decided(segment) && wasWorking && segment.start === wasWorking.start && segment.end === wasWorking.end,
      ) ??
      sheet.segments.find(
        (segment) =>
          decided(segment) &&
          (earlier.get(segment.start) === "working" || earlier.get(segment.start) === "waiting"),
      );
    if (back) {
      const [from, to] = columnsOf(back, columns);
      if (to > from) setReveal({ from, to, shown: 0 });
    }
  }

  useEffect(() => {
    if (!reveal || reveal.shown >= reveal.to - reveal.from) return;
    const count = reveal.to - reveal.from;
    const step = Math.min(STEP_MAX_MS, Math.max(STEP_MIN_MS, REVEAL_MS / count));
    const timer = window.setTimeout(
      () => setReveal((current) => (current ? { ...current, shown: current.shown + 1 } : null)),
      step,
    );
    return () => window.clearTimeout(timer);
  }, [reveal]);

  const hidden = reveal && reveal.shown < reveal.to - reveal.from ? boxesOf(reveal.from + reveal.shown, reveal.to, columns, edges, sheet.systems) : [];

  // ------------------------------------------------------------------ the cursor and the lit notes

  const place = playheadSeconds === null ? null : placeAt(columns, sheet.systems, playheadSeconds * 1000);
  const lit = place ? place.column : -1;
  useEffect(() => {
    const now = heads.current[lit] ?? [];
    for (const element of now) element.setAttribute("data-lit", "");
    return () => {
      for (const element of now) element.removeAttribute("data-lit");
    };
  }, [lit, sheet.svg]);

  // The picked noteheads, marked on the drawing (a new drawing after an edit is marked again).
  useEffect(() => {
    const element = host.current;
    if (!element || !selected || selected.size === 0) return;
    const marked: Element[] = [];
    for (const head of element.querySelectorAll("[data-note]")) {
      if (refsOf(head).some((ref) => selected.has(ref))) {
        head.setAttribute("data-selected", "");
        marked.push(head);
      }
    }
    return () => {
      for (const head of marked) head.removeAttribute("data-selected");
    };
  }, [selected, sheet.svg]);

  const line = place ? sheet.systems[place.system] : null;
  const lastLine = useRef<number | null>(null);
  useEffect(() => {
    const system = place?.system ?? null;
    if (system === lastLine.current) return;
    lastLine.current = system;
    // Only while it plays, and only when the music moves to another line: scrolling on every tick fights the reader.
    if (follow && system !== null) {
      cursor.current?.scrollIntoView?.(
        centre ? { block: "center", inline: "nearest", behavior: "smooth" } : { block: "nearest", inline: "nearest" },
      );
    }
  }, [place?.system, follow, centre]);

  const seekTo = (clientX: number, clientY: number) => {
    const svg = overlay.current;
    const matrix = svg?.getScreenCTM();
    if (!svg || !matrix || !onSeek) return;
    const point = new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse());
    const ms = msAtPoint(columns, sheet.systems, point.x, point.y);
    if (ms !== null) onSeek(ms / 1000);
  };

  // ------------------------------------------------------------------ marking a stretch (Phase 7)

  /** A point of the screen in the sheet's units (staff spaces). */
  const toSheet = (clientX: number, clientY: number) => {
    const matrix = overlay.current?.getScreenCTM();
    return matrix ? new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse()) : null;
  };
  /** The line whose strip (above its upper staff) holds the point, or `-1`. */
  const stripAt = (x: number, y: number) =>
    sheet.systems.findIndex((system, i) => {
      const above = Math.min(system.staff_top - STRIP_SPACES, system.top - 0.5);
      const floor = i > 0 ? Math.max(above, sheet.systems[i - 1].bottom + 0.2) : above;
      return y >= floor && y <= system.staff_top - 0.3 && x >= system.left - 1 && x <= system.right + 1;
    });
  /** The column under `x` on a line (the nearest one of that line). */
  const columnAt = (system: number, x: number) => {
    let best = -1;
    let distance = Infinity;
    columns.forEach((column, i) => {
      if (column.system !== system) return;
      const [left, right] = edges[i];
      const d = x < left ? left - x : x > right ? x - right : 0;
      if (d < distance) {
        distance = d;
        best = i;
      }
    });
    return best;
  };
  /** The line nearest a point (for a drag that leaves the strip). */
  const lineAt = (y: number) => {
    let best = 0;
    let distance = Infinity;
    sheet.systems.forEach((system, i) => {
      const d = y < system.top ? system.top - y : y > system.bottom ? y - system.bottom : 0;
      if (d < distance) {
        distance = d;
        best = i;
      }
    });
    return best;
  };
  const framesOf = (from: number, to: number): MarkedRange => {
    const [a, b] = from <= to ? [from, to] : [to, from];
    const next = columns[b + 1];
    return { start: columns[a].frame, end: next ? next.frame : columns[b].frame + 1 };
  };
  const [rangeDrag, setRangeDrag] = useState<RangeDrag | null>(null);
  const [strip, setStrip] = useState(-1);
  const marking = rangeDrag ? framesOf(rangeDrag.from, rangeDrag.to) : null;
  const shown = marking ?? range;
  const bands = useMemo(() => {
    if (!shown) return [];
    const [from, to] = columnsOf(shown, columns);
    return boxesOf(from, to, columns, edges, sheet.systems).map((box) => {
      const system = sheet.systems[box.system];
      const top =
        rangeScope === "left" ? system.staff_bottom - 4 - BAND_PAD : system.staff_top - BAND_PAD;
      const bottom = rangeScope === "right" ? system.staff_top + 4 + BAND_PAD : system.staff_bottom + BAND_PAD;
      return { ...box, y: top, height: bottom - top, stripY: system.staff_top - STRIP_SPACES };
    });
  }, [shown, rangeScope, columns, edges, sheet.systems]);

  // ------------------------------------------------------------------ picking notes

  const [drag, setDrag] = useState<Drag | null>(null);
  const dragged = useRef(false);

  const click = (event: MouseEvent<HTMLDivElement>) => {
    if (dragged.current) {
      dragged.current = false;
      return;
    }
    const add = event.metaKey || event.ctrlKey || event.shiftKey;
    const head = onPick && host.current ? headAt(host.current, event.clientX, event.clientY) : null;
    if (head && onPick) {
      onPick(refsOf(head), add ? "add" : "only");
      // The recording goes to the note, so that what is heard is what was picked.
      const frame = Number(refsOf(head)[0]?.split(":")[0]);
      if (!add && onSeek && Number.isFinite(frame)) onSeek((frame * 40) / 1000);
      return;
    }
    if (onPick && !add) onPick([], "only");
    seekTo(event.clientX, event.clientY);
  };

  const press = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    if (onRange && host.current && !headAt(host.current, event.clientX, event.clientY)) {
      const point = toSheet(event.clientX, event.clientY);
      const line = point ? stripAt(point.x, point.y) : -1;
      if (point && line >= 0) {
        const at = columnAt(line, point.x);
        if (at >= 0) {
          event.currentTarget.setPointerCapture(event.pointerId);
          const from = event.shiftKey && range ? columnsOf(range, columns)[0] : at;
          setRangeDrag({ from, to: at, extend: event.shiftKey });
          return;
        }
      }
    }
    if (!onPick) return;
    const add = event.metaKey || event.ctrlKey || event.shiftKey;
    const { left, top } = event.currentTarget.getBoundingClientRect();
    const [x, y] = [event.clientX, event.clientY];
    setDrag({ left, top, x0: x, y0: y, x1: x, y1: y, add, moved: false });
  };
  const pull = (event: PointerEvent<HTMLDivElement>) => {
    if (onRange) {
      const point = toSheet(event.clientX, event.clientY);
      if (rangeDrag && point) {
        const at = columnAt(lineAt(point.y), point.x);
        if (at >= 0 && at !== rangeDrag.to) setRangeDrag({ ...rangeDrag, to: at });
        return;
      }
      const line = point && host.current && !headAt(host.current, event.clientX, event.clientY) ? stripAt(point.x, point.y) : -1;
      if (line !== strip) setStrip(line);
    }
    if (!drag) return;
    const moved = drag.moved || Math.hypot(event.clientX - drag.x0, event.clientY - drag.y0) > DRAG_PX;
    if (moved && !drag.moved) event.currentTarget.setPointerCapture(event.pointerId);
    setDrag({ ...drag, x1: event.clientX, y1: event.clientY, moved });
  };
  const release = () => {
    if (rangeDrag) {
      setRangeDrag(null);
      dragged.current = true;
      onRange?.(framesOf(rangeDrag.from, rangeDrag.to));
      return;
    }
    if (!drag) return;
    setDrag(null);
    if (!drag.moved || !onPick || !host.current) return;
    dragged.current = true;
    const [left, right] = [Math.min(drag.x0, drag.x1), Math.max(drag.x0, drag.x1)];
    const [top, bottom] = [Math.min(drag.y0, drag.y1), Math.max(drag.y0, drag.y1)];
    const refs: string[] = [];
    for (const head of host.current.querySelectorAll("[data-note]")) {
      const box = head.getBoundingClientRect();
      const x = (box.left + box.right) / 2;
      const y = (box.top + box.bottom) / 2;
      if (x >= left && x <= right && y >= top && y <= bottom) refs.push(...refsOf(head));
    }
    onPick(refs, drag.add ? "add" : "only");
  };
  const band = drag?.moved
    ? {
        left: Math.min(drag.x0, drag.x1) - drag.left,
        top: Math.min(drag.y0, drag.y1) - drag.top,
        width: Math.abs(drag.x1 - drag.x0),
        height: Math.abs(drag.y1 - drag.y0),
      }
    : null;

  return (
    <Box
      data-frames-sheet
      data-source={sheet.source}
      data-llm={sheet.llm.state}
      data-working={working.length > 0 ? "" : undefined}
      onClick={click}
      onPointerDown={press}
      onPointerMove={pull}
      onPointerUp={release}
      onPointerCancel={() => {
        setDrag(null);
        setRangeDrag(null);
      }}
      onPointerLeave={() => setStrip(-1)}
      sx={{
        position: "relative",
        backgroundColor: "#fff",
        borderRadius: 1,
        overflow: "hidden",
        cursor: strip >= 0 || rangeDrag ? "col-resize" : onSeek || onPick ? "pointer" : "default",
        userSelect: "none",
        touchAction: onPick ? "pan-y" : undefined,
        "& [data-selected]": { fill: palette.dark.Lavender },
        "& [data-lit]": { fill: semantic.pressedKey },
        "& [data-segment-state='working']": { animation: `${breathe} 1.6s ease-in-out infinite alternate` },
      }}
    >
      <div ref={host} />
      <svg
        ref={overlay}
        viewBox={`0 0 ${sheet.width} ${sheet.height}`}
        preserveAspectRatio="xMinYMin meet"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
      >
        {working.map((box) => (
          <rect
            key={`w${box.system}:${box.x}`}
            data-segment-state="working"
            x={box.x}
            y={box.y}
            width={box.width}
            height={box.height}
            fill="#fff"
          />
        ))}
        {hidden.map((box) => {
          const system = sheet.systems[box.system];
          const ys = system
            ? [0, 1, 2, 3, 4].flatMap((i) => [system.staff_top + i, system.staff_bottom - 4 + i])
            : [];
          return (
            <g key={`r${box.system}`} data-revealing>
              <rect x={box.x} y={box.y} width={box.width} height={box.height} fill="#fff" />
              {ys.map((y) => (
                <line key={y} x1={box.x} x2={box.x + box.width} y1={y} y2={y} stroke="#000" strokeWidth={STAFF_LINE} />
              ))}
            </g>
          );
        })}
        {strip >= 0 && !rangeDrag && sheet.systems[strip] ? (
          <rect
            data-range-strip
            x={sheet.systems[strip].left}
            y={sheet.systems[strip].staff_top - STRIP_SPACES}
            width={sheet.systems[strip].right - sheet.systems[strip].left}
            height={STRIP_SPACES - 0.3}
            fill={palette.dark.Lavender}
            opacity={0.07}
          />
        ) : null}
        {bands.map((band) => (
          <g key={`b${band.system}:${band.x}`}>
            <rect
              data-range-band
              data-start={shown?.start}
              data-end={shown?.end}
              x={band.x}
              y={band.y}
              width={band.width}
              height={band.height}
              fill={palette.dark.Lavender}
              opacity={0.12}
            />
            <rect
              x={band.x}
              y={band.stripY}
              width={band.width}
              height={0.7}
              fill={palette.dark.Lavender}
              opacity={0.55}
            />
          </g>
        ))}
        {place && line ? (
          <line
            ref={cursor}
            data-frames-cursor
            data-ms={Math.round((playheadSeconds ?? 0) * 1000)}
            x1={place.x}
            x2={place.x}
            y1={line.staff_top - 1.5}
            y2={line.staff_bottom + 1.5}
            stroke={semantic.pressedKey}
            strokeWidth={0.28}
            strokeLinecap="round"
            opacity={0.85}
          />
        ) : null}
      </svg>
      {band ? (
        <Box
          data-pick-box
          sx={{
            position: "absolute",
            left: band.left,
            top: band.top,
            width: band.width,
            height: band.height,
            border: `1px solid ${palette.dark.Lavender}`,
            backgroundColor: "rgba(129, 110, 255, 0.08)",
            pointerEvents: "none",
          }}
        />
      ) : null}
    </Box>
  );
}

export default FramesSheetView;
