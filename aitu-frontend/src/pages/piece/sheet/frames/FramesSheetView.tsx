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
 *   The cursor is dragged and dropped (implementation 04, Phase 1): the pointer shows `grab` over it, the line
 *   follows the pointer over the columns of any line (the page scrolls near the window's top and bottom edges, and
 *   stops keeping the cursor in view), and the recording moves there when it is let go, playing on if it played. A
 *   press on the cursor that does not move is a click (a notehead under it is picked as before).
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
 * - **Lyrics** (Phase 8): the engine draws each piece above the upper staff (`data-lyric`, its place in the sheet's
 *   lyrics; `data-part` when its frames cross a line break and its words are shared between the lines). While the
 *   music plays, the piece whose frames sound is black and bold; in Play mode the others are faint meanwhile. When
 *   the page gives `lyrics` (an editable sheet), a click on a piece picks it (⌘ or Shift adds it), and a piece of the
 *   pool dragged over the sheet shows where it would land: the frames of the other pieces in grey, its own in green,
 *   or red where it would cover another.
 * - **Lyrics blocks** (Phase 8A++, the user's request): a picked piece is a block with an outline and two handles.
 *   A drag of the block puts it anywhere (not on a frame); the side handle makes it narrower or wider and its words
 *   wrap again as the pointer moves; the corner handle makes the words larger or smaller. Its frames (when it
 *   sounds) are a bar in the strip above the staves, with an end at each side to drag. None of this changes the
 *   other: a block moved keeps its frames. While a piece is picked, the strip marks no stretch.
 *
 * Hooks for the browser checks: `data-frames-sheet` on the root (with `data-source`, `data-llm`, `data-working`),
 * `data-note="<frame>:<midi>"` on each notehead, `data-lit` on the lit ones, `data-selected` on the picked ones,
 * `data-frames-cursor` (with `data-ms`; `data-dragging` while it is dragged), `data-segment-state="working"` on the veil, `data-revealing` while a
 * segment appears, `data-pick-box` while a box is dragged, `data-range-band` on the marked stretch (one per line,
 * with `data-start` and `data-end`) and `data-range-strip` on the strip under the pointer; `data-lyric-lit` and
 * `data-lyric-picked` on the lyrics pieces, `data-lyric-landing` (`data-free`) while one is dragged;
 * `data-lyric-handle="width" | "scale"` on a picked block's handles, `data-lyric-frames` on its bar of frames (its
 * ends `data-lyric-handle="start" | "end"`), `data-lyric-preview` on the words wrapped while a side handle moves.
 */

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import Box from "@mui/material/Box";
import { keyframes } from "@mui/material/styles";
import type { FramesSheet, LyricFont } from "../../../../api";
import { palette, semantic } from "../../../../ui";
import { boxesOf, columnEdges, columnsOf, headsByColumn, msAtPoint, placeAt, steadyColumns } from "./geometry";
import { LYRIC_LEADING, LYRIC_MAX, LYRIC_MIN, familyOf, wrapWords } from "./lyricsText";

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
/** The cursor is caught this close to its line, in pixels. */
const CURSOR_PX = 6;
/** While the cursor is dragged, the page scrolls with the pointer this close to the window's top or bottom edge. */
const EDGE_PX = 56;
/** The fastest scroll at an edge, in pixels per frame. */
const EDGE_SPEED = 18;

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
/** The bar of a picked lyrics piece's frames: this far below the top of the strip, in staff spaces. */
const BAR_Y = 0.9;

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

/** A drawn lyrics block: its piece (`data-lyric`) and part (`data-part`, 0 for the first). */
function blockKey(element: Element): string {
  return `${element.getAttribute("data-lyric")}:${element.getAttribute("data-part") ?? 0}`;
}

/** The lyrics block under a point of the screen (a few pixels around its words), by its key. */
function lyricAt(root: ParentNode, x: number, y: number): string | null {
  for (const element of root.querySelectorAll("[data-lyric]")) {
    const box = element.getBoundingClientRect();
    if (x >= box.left - 3 && x <= box.right + 3 && y >= box.top - 3 && y <= box.bottom + 3) return blockKey(element);
  }
  return null;
}

/** What the page does with the lyrics pieces on the sheet (Phase 8). */
export interface LyricsOnSheet {
  /** The pieces picked, by their first frame. */
  picked: ReadonlySet<number>;
  onPick: (start: number, add: boolean) => void;
  /** A press off the picked pieces lets them go. */
  onUnpick: () => void;
  /**
   * A block put somewhere by hand: the frame of the column under its left edge, how far right of that column it
   * starts, and its last line's baseline below the top staff line (staff spaces).
   */
  onPlace: (start: number, place: { at: number; dx: number; dy: number }) => Promise<boolean>;
  /** A side handle let go: the width its words wrap to, in staff spaces. */
  onWidth: (start: number, width: number) => Promise<boolean>;
  /** A corner handle let go: the size of its words, and its width scaled with them (if it has one). */
  onScale: (start: number, size: number, width: number | null) => Promise<boolean>;
  /** The bar of its frames: when its words sound (`[start, end)`); refused (`false`) over another piece. */
  onFrames: (start: number, next: { start: number; end: number }) => Promise<boolean>;
  /** A piece of the pool is dragged: where it would land on a frame (its frames, free or over another). */
  landing: ((frame: number) => { start: number; end: number; free: boolean }) | null;
  onDropPool: (frame: number) => void;
}

/** A drawn lyrics block, in sheet units, measured when the drawing goes in. */
interface LyricBlock {
  index: number;
  part: number;
  /** Its ink. */
  x: number;
  y: number;
  width: number;
  height: number;
  /** Where its lines start, its last line's baseline, its size and the width its words wrap to. */
  left: number;
  base: number;
  size: number;
  wrap: number | null;
  font: LyricFont;
  bold: boolean;
  italic: boolean;
  /** Its words as drawn (the lines joined by spaces). */
  words: string;
}

/** What a drag of a lyrics block does: moves it, sets its width, scales its words, or moves an end of its frames. */
type LyricDragMode = "move" | "width" | "scale" | "start" | "end";

/** A lyrics block being dragged on the sheet: the press and the pointer now, in sheet units. */
interface LyricDrag {
  key: string;
  mode: LyricDragMode;
  x0: number;
  y0: number;
  x: number;
  y: number;
  moved: boolean;
  /** Its frames now, while an end of the bar is dragged. */
  nextStart: number;
  nextEnd: number;
}

/** The font of a drawn lyrics block, from its family. */
function fontOf(family: string): LyricFont {
  const name = family.toLowerCase();
  return name.startsWith("geist") ? "geist" : name.startsWith("montserrat") ? "montserrat" : "lora";
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

/** The window over a take (Record in Sheet): the old sheet's blue, and the grip it is dragged by, in staff spaces. */
const WINDOW_COLOUR = "#2563eb";
const WINDOW_GRIP = { width: 3, height: 0.9 } as const;
/** The window's edge before a column: room for an accidental of its notes, in staff spaces. */
const WINDOW_LEAD = 1.6;

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
  lyrics,
  playing = false,
  frameWindow = null,
  onWindowMove,
  keepClear = 0,
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
  /** The lyrics pieces can be picked and dragged (the Lyrics tab), and pieces of the pool dropped. */
  lyrics?: LyricsOnSheet;
  /** The recording plays: the lyrics piece that sounds is lit (and in Play mode, `centre`, the others faint). */
  playing?: boolean;
  /** The window over a take (Record in Sheet, Phase 8B): the frames of the take that go into the song. */
  frameWindow?: MarkedRange | null;
  /** The window is dragged by its grip: its first frame now, and `done` when it is let go. */
  onWindowMove?: (start: number, done: boolean) => void;
  /** Pixels at the top of the window covered by the page's header: the cursor is kept in view below them. */
  keepClear?: number;
}) {
  const host = useRef<HTMLDivElement | null>(null);
  const overlay = useRef<SVGSVGElement | null>(null);
  const cursor = useRef<SVGLineElement | null>(null);
  const columns = useMemo(() => steadyColumns(sheet.columns), [sheet.columns]);
  const edges = useMemo(() => columnEdges(columns, sheet.systems), [columns, sheet.systems]);
  /** The noteheads of each column of the drawing on the page (`data-note`). */
  const heads = useRef<Element[][]>([]);

  /** The lyrics blocks of the drawing, in sheet units, by key (`"<data-lyric>:<part>"`). */
  const [lyricBlocks, setLyricBlocks] = useState<{ svg: string; boxes: Record<string, LyricBlock> }>({ svg: "", boxes: {} });

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
    const boxes: Record<string, LyricBlock> = {};
    for (const text of element.querySelectorAll<SVGTextElement>("[data-lyric]")) {
      const box = text.getBBox();
      const spans = [...text.querySelectorAll("tspan")];
      const wrap = text.getAttribute("data-width");
      boxes[blockKey(text)] = {
        index: Number(text.getAttribute("data-lyric")),
        part: Number(text.getAttribute("data-part") ?? 0),
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        left: Number(spans[0]?.getAttribute("x") ?? box.x),
        base: Number(text.getAttribute("data-base") ?? box.y + box.height),
        size: Number(text.getAttribute("font-size") ?? 1.4),
        wrap: wrap === null ? null : Number(wrap),
        font: fontOf(text.getAttribute("font-family") ?? ""),
        bold: text.getAttribute("font-weight") === "700",
        italic: text.getAttribute("font-style") === "italic",
        words: spans.map((span) => span.textContent ?? "").join(" "),
      };
    }
    setLyricBlocks({ svg: sheet.svg, boxes });
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

  /** The cursor being dragged: the time under the pointer, and whether it moved yet (a press alone is a click). */
  const [cursorDrag, setCursorDrag] = useState<{ ms: number; moved: boolean; x0: number; y0: number } | null>(null);
  const [overCursor, setOverCursor] = useState(false);
  const cursorMs = cursorDrag?.moved ? cursorDrag.ms : playheadSeconds === null ? null : playheadSeconds * 1000;
  const place = cursorMs === null ? null : placeAt(columns, sheet.systems, cursorMs);
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

  // The lyrics piece that sounds, lit while the music plays; the picked pieces marked.
  const sounding = playing && playheadSeconds !== null ? Math.floor((playheadSeconds * 1000) / 40) : null;
  const litLyric = sounding === null ? -1 : sheet.lyrics.findIndex((one) => one.start <= sounding && sounding < one.end);
  useEffect(() => {
    const elements = [...(host.current?.querySelectorAll(`[data-lyric="${litLyric}"]`) ?? [])];
    for (const element of elements) element.setAttribute("data-lyric-lit", "");
    return () => {
      for (const element of elements) element.removeAttribute("data-lyric-lit");
    };
  }, [litLyric, sheet.svg]);
  const pickedLyrics = lyrics?.picked;
  useEffect(() => {
    const element = host.current;
    if (!element || !pickedLyrics || pickedLyrics.size === 0) return;
    const marked: Element[] = [];
    for (const text of element.querySelectorAll("[data-lyric]")) {
      if (pickedLyrics.has(Number(text.getAttribute("data-start")))) {
        text.setAttribute("data-lyric-picked", "");
        marked.push(text);
      }
    }
    return () => {
      for (const text of marked) text.removeAttribute("data-lyric-picked");
    };
  }, [pickedLyrics, sheet.svg]);

  const line = place ? sheet.systems[place.system] : null;
  const draggingCursor = cursorDrag?.moved === true;
  const lastLine = useRef<number | null>(null);
  useEffect(() => {
    const system = place?.system ?? null;
    if (system === lastLine.current) return;
    lastLine.current = system;
    // Only while it plays, and only when the music moves to another line: scrolling on every tick fights the reader.
    // Never while the cursor is dragged: the reader moves the page then.
    if (follow && !draggingCursor && system !== null) {
      cursor.current?.scrollIntoView?.(
        centre ? { block: "center", inline: "nearest", behavior: "smooth" } : { block: "nearest", inline: "nearest" },
      );
    }
  }, [place?.system, follow, centre, draggingCursor]);

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
  // ------------------------------------------------------------------ dragging the cursor (implementation 04, Phase 1)

  /** The cursor's line is under a point of the screen (within a few pixels of it). */
  const onCursor = (clientX: number, clientY: number) => {
    const matrix = overlay.current?.getScreenCTM();
    if (!onSeek || !place || !line || !matrix || matrix.a <= 0) return false;
    const point = new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse());
    const reach = CURSOR_PX / matrix.a;
    return (
      Math.abs(point.x - place.x) <= reach &&
      point.y >= line.staff_top - 1.5 - reach &&
      point.y <= line.staff_bottom + 1.5 + reach
    );
  };
  /** The time under a point of the screen, for the cursor dragged (as a click moves the recording). */
  const msAtScreen = (clientX: number, clientY: number) => {
    const point = toSheet(clientX, clientY);
    return point ? msAtPoint(columns, sheet.systems, point.x, point.y) : null;
  };
  // Near the window's top (below the page's header) or bottom edge, the page scrolls while the cursor is dragged,
  // and the cursor follows the pointer over what comes into view.
  const pointer = useRef<{ x: number; y: number } | null>(null);
  useEffect(() => {
    if (!draggingCursor) return;
    let frame = 0;
    const tick = () => {
      const at = pointer.current;
      if (at) {
        const top = keepClear + EDGE_PX - at.y;
        const bottom = at.y - (window.innerHeight - EDGE_PX);
        const by = top > 0 ? -top : bottom > 0 ? bottom : 0;
        if (by !== 0 && overlay.current) {
          window.scrollBy(0, Math.max(-EDGE_SPEED, Math.min(EDGE_SPEED, Math.round(by / 3))));
          // The sheet moved under the pointer: the time under it now.
          const matrix = overlay.current.getScreenCTM();
          const point = matrix ? new DOMPoint(at.x, at.y).matrixTransform(matrix.inverse()) : null;
          const ms = point ? msAtPoint(columns, sheet.systems, point.x, point.y) : null;
          if (ms !== null) setCursorDrag((now) => (now && now.ms !== ms ? { ...now, ms } : now));
        }
      }
      frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [draggingCursor, keepClear, columns, sheet.systems]);

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
  /** The frame under a point of the sheet (between columns by time, as a click moves the recording). */
  const frameAt = (x: number, y: number) => {
    const ms = msAtPoint(columns, sheet.systems, x, y);
    return ms === null ? null : Math.max(0, Math.round(ms / 40));
  };
  /** Where a frame is drawn: its x and line (the cursor's rule). */
  const placeOf = (frame: number) => placeAt(columns, sheet.systems, frame * 40);

  // ------------------------------------------------------------------ lyrics pieces and blocks (Phase 8, 8A++)

  const [lyricDrag, setLyricDrag] = useState<LyricDrag | null>(null);
  /** A drag let go: its preview stays until the new drawing comes (or the edit is refused). */
  const [settle, setSettle] = useState<{ svg: string; drag: LyricDrag } | null>(null);
  const [poolLanding, setPoolLanding] = useState<{ start: number; end: number; free: boolean } | null>(null);
  const [hoverHandle, setHoverHandle] = useState<LyricDragMode | null>(null);
  const blocks = lyricBlocks.svg === sheet.svg ? lyricBlocks.boxes : {};
  const startOf = (block: LyricBlock) => sheet.lyrics[block.index]?.start ?? -1;
  /** The blocks of the picked pieces (every part of each). */
  const pickedBlocks = lyrics ? Object.entries(blocks).filter(([, block]) => lyrics.picked.has(startOf(block))) : [];
  /** One piece picked: its frames are a bar in the strip. */
  const onePicked = lyrics && lyrics.picked.size === 1 ? sheet.lyrics.findIndex((one) => lyrics.picked.has(one.start)) : -1;
  /** The drag that shows now: the one under the pointer, or the one let go until the new drawing. */
  const active = lyricDrag?.moved ? lyricDrag : settle && settle.svg === sheet.svg ? settle.drag : null;
  const activeBlock = active ? (blocks[active.key] ?? null) : null;
  /** The frames a dragged piece would cover, free or over another piece. */
  const busyOver = (start: number, end: number, except: number) =>
    sheet.lyrics.some((one, k) => k !== except && one.start < end && one.end > start);
  /** The frames of the bar now: dragged, or the picked piece's own. */
  const barFrames =
    onePicked < 0
      ? null
      : active && (active.mode === "start" || active.mode === "end")
        ? { start: active.nextStart, end: active.nextEnd }
        : { start: sheet.lyrics[onePicked]!.start, end: sheet.lyrics[onePicked]!.end };
  /** Boxes of frames `[start, end)` in the strip, one per line (a thin one where no column falls inside). */
  const stripBoxes = (start: number, end: number) => {
    const [from, to] = columnsOf({ start, end }, columns);
    const boxes = to > from ? boxesOf(from, to, columns, edges, sheet.systems) : [];
    if (boxes.length === 0) {
      const at = placeOf(start);
      if (!at) return [];
      return [{ system: at.system, x: at.x - 0.4, width: 0.8, y: sheet.systems[at.system].staff_top - STRIP_SPACES }];
    }
    return boxes.map((box) => ({ system: box.system, x: box.x, width: box.width, y: sheet.systems[box.system].staff_top - STRIP_SPACES }));
  };
  /** Shades of the frames of lyrics pieces on the strip, while frames are dragged: `[start, end)` and its colour. */
  const lyricShades = (() => {
    const out: { start: number; end: number; fill: string; landing: boolean; free?: boolean }[] = [];
    const framing = active && (active.mode === "start" || active.mode === "end") && onePicked >= 0;
    if (!framing && !poolLanding) return out;
    sheet.lyrics.forEach((one, k) => {
      if (framing && k === onePicked) return;
      out.push({ start: one.start, end: one.end, fill: "#9e9e9e", landing: false });
    });
    const target =
      framing && barFrames ? { ...barFrames, free: !busyOver(barFrames.start, barFrames.end, onePicked) } : poolLanding;
    if (target) out.push({ ...target, fill: target.free ? "#2e7d32" : "#c62828", landing: true });
    return out;
  })();
  const shadeBoxes = lyricShades.flatMap((shade) => stripBoxes(shade.start, shade.end).map((box) => ({ ...shade, ...box })));
  const bar = barFrames ? stripBoxes(barFrames.start, barFrames.end) : [];

  /** The handles of a picked block: its width at the middle of its right side, its size at its lower right corner. */
  const handlesOf = (block: LyricBlock) => {
    const right = Math.max(block.x + block.width, block.left + (block.wrap ?? 0)) + 0.35;
    return { width: { x: right, y: block.y + block.height / 2 }, scale: { x: right, y: block.y + block.height + 0.3 } };
  };
  const near = (point: { x: number; y: number }, at: { x: number; y: number }) =>
    Math.abs(point.x - at.x) <= 0.7 && Math.abs(point.y - at.y) <= 0.7;
  /** A handle of the picked blocks or of the bar under a point of the sheet. */
  const handleAt = (point: { x: number; y: number }): { key: string; mode: LyricDragMode } | null => {
    for (const [key, block] of pickedBlocks) {
      const handles = handlesOf(block);
      if (near(point, handles.scale)) return { key, mode: "scale" };
      if (near(point, handles.width)) return { key, mode: "width" };
    }
    if (onePicked >= 0 && bar.length > 0) {
      const key = Object.keys(blocks).find((one) => blocks[one]!.index === onePicked);
      const first = bar[0]!;
      const last = bar[bar.length - 1]!;
      const y = first.y + BAR_Y + 0.4;
      if (key && Math.abs(point.x - first.x) <= 0.6 && Math.abs(point.y - y) <= 0.9) return { key, mode: "start" };
      const lastY = last.y + BAR_Y + 0.4;
      if (key && Math.abs(point.x - (last.x + last.width)) <= 0.6 && Math.abs(point.y - lastY) <= 0.9) return { key, mode: "end" };
    }
    return null;
  };
  /** The scale of the words while a corner handle is dragged (their size kept within its limits). */
  const scaleOf = (drag: LyricDrag, block: LyricBlock) => {
    const was = Math.max(0.5, block.x + block.width - block.left);
    const ratio = Math.max(0.1, (drag.x - block.left) / was);
    return Math.min(LYRIC_MAX, Math.max(LYRIC_MIN, block.size * ratio)) / block.size;
  };
  /** The width a side handle sets, in staff spaces. */
  const widthOf = (drag: LyricDrag, block: LyricBlock) => Math.max(2, Math.round((drag.x - block.left) * 10) / 10);
  /** Where a block moved to lands: its line (the one whose staves are under its baseline), the column under its left edge. */
  const placeFor = (left: number, base: number) => {
    let line = sheet.systems.findIndex((system) => base <= system.staff_bottom);
    if (line < 0) line = sheet.systems.length - 1;
    const inLine = columns.filter((column) => column.system === line);
    const column = inLine.filter((one) => one.x <= left).pop() ?? inLine[0];
    if (!column) return null;
    const round = (value: number) => Math.round(value * 100) / 100;
    return { at: column.frame, dx: round(left - column.x), dy: round(base - sheet.systems[line]!.staff_top) };
  };

  // The block under the pointer follows it: moved, or its words scaled from the start of its last line; while a side
  // handle moves, the words wrapped again are drawn over it (the block itself hidden).
  useEffect(() => {
    if (!active || !activeBlock || !host.current) return;
    const elements = [...host.current.querySelectorAll(`[data-lyric="${activeBlock.index}"]`)].filter(
      (element) => blockKey(element) === active.key,
    );
    let transform: string | null = null;
    if (active.mode === "move") transform = `translate(${active.x - active.x0} ${active.y - active.y0})`;
    if (active.mode === "scale") {
      const ratio = scaleOf(active, activeBlock);
      const { left, base } = activeBlock;
      transform = `translate(${left} ${base}) scale(${ratio}) translate(${-left} ${-base})`;
    }
    for (const element of elements) {
      if (transform) element.setAttribute("transform", transform);
      if (active.mode === "width") element.setAttribute("opacity", "0");
    }
    return () => {
      for (const element of elements) {
        element.removeAttribute("transform");
        element.removeAttribute("opacity");
      }
    };
  }, [active, activeBlock, sheet.svg]);
  const widthPreview = (() => {
    if (!active || active.mode !== "width" || !activeBlock) return null;
    const block = activeBlock;
    const piece = sheet.lyrics[block.index];
    const split = Object.values(blocks).filter((one) => one.index === block.index).length > 1;
    const width = widthOf(active, block);
    const lines = wrapWords(split || !piece ? block.words : piece.text, width, block.size, block.font, block.bold, block.italic);
    return { block, width, lines, top: block.base - (lines.length - 1) * block.size * LYRIC_LEADING };
  })();

  /** A drag of a lyrics block let go: what it changes, sent to the page. */
  const letGo = (drag: LyricDrag) => {
    const block = blocks[drag.key];
    if (!lyrics || !block) return;
    const start = startOf(block);
    let sent: Promise<boolean> | null = null;
    if (drag.mode === "move") {
      const place = placeFor(block.left + drag.x - drag.x0, block.base + drag.y - drag.y0);
      if (place) sent = lyrics.onPlace(start, place);
    } else if (drag.mode === "width") {
      sent = lyrics.onWidth(start, widthOf(drag, block));
    } else if (drag.mode === "scale") {
      const size = Math.round(block.size * scaleOf(drag, block) * 100) / 100;
      sent = lyrics.onScale(start, size, block.wrap === null ? null : Math.round((block.wrap * size * 10) / block.size) / 10);
    } else if (drag.nextStart !== start || drag.nextEnd !== sheet.lyrics[block.index]?.end) {
      sent = lyrics.onFrames(start, { start: drag.nextStart, end: drag.nextEnd });
    }
    if (!sent) return;
    setSettle({ svg: sheet.svg, drag });
    void sent.then((done) => {
      if (!done) setSettle(null);
    });
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

  // The window over a take (Record in Sheet): a band on each line it covers, and a grip on its first line.
  const [windowDrag, setWindowDrag] = useState<{ grab: number; start: number } | null>(null);
  const windowStart = frameWindow ? (windowDrag?.start ?? frameWindow.start) : null;
  const windowLength = frameWindow ? frameWindow.end - frameWindow.start : 0;
  const windowNow = windowStart === null ? null : { start: windowStart, end: windowStart + windowLength };
  const windowBoxes = useMemo(() => {
    if (windowStart === null || windowLength <= 0 || columns.length === 0) return [];
    // A frame is drawn before the first column at or after it: the notes from it on are inside the window (or after
    // it, for its end); past the last column, at the end of the last line.
    const edgeOf = (frame: number) => {
      const i = columns.findIndex((column) => column.frame >= frame);
      // Never further left than the room of the column's own accidentals: at the start of a line, the armadura.
      if (i >= 0) return { x: Math.max(edges[i]![0], columns[i]!.x - WINDOW_LEAD), system: columns[i]!.system };
      const last = columns[columns.length - 1]!;
      return { x: sheet.systems[last.system]?.right ?? last.x, system: last.system };
    };
    const a = edgeOf(windowStart);
    const b = edgeOf(windowStart + windowLength);
    if (!a || !b) return [];
    const out: { system: number; x: number; width: number; first: boolean; last: boolean }[] = [];
    for (let line = a.system; line <= b.system; line += 1) {
      const system = sheet.systems[line];
      if (!system) continue;
      const x0 = line === a.system ? a.x : system.left;
      const x1 = line === b.system ? b.x : system.right;
      if (x1 > x0) out.push({ system: line, x: x0, width: x1 - x0, first: line === a.system, last: line === b.system });
    }
    return out;
  }, [windowStart, windowLength, columns, edges, sheet.systems]);
  /** The grip of the window, in sheet units: in the middle of its first line's band, at the top. */
  const grip = windowBoxes[0] && onWindowMove
    ? {
        x: Math.max(windowBoxes[0].x + 0.4, windowBoxes[0].x + windowBoxes[0].width / 2 - WINDOW_GRIP.width / 2),
        // Above the ink of the line, clear of stems and beams.
        y: Math.max(0.1, (sheet.systems[windowBoxes[0].system]?.top ?? 0) - WINDOW_GRIP.height - 0.3),
      }
    : null;
  const onGrip = (point: { x: number; y: number }) =>
    grip !== null &&
    point.x >= grip.x - 0.4 &&
    point.x <= grip.x + WINDOW_GRIP.width + 0.4 &&
    point.y >= grip.y - 0.4 &&
    point.y <= grip.y + WINDOW_GRIP.height + 0.4;

  // ------------------------------------------------------------------ picking notes

  const [drag, setDrag] = useState<Drag | null>(null);
  const dragged = useRef(false);

  const click = (event: MouseEvent<HTMLDivElement>) => {
    if (dragged.current) {
      dragged.current = false;
      return;
    }
    if (lyrics && host.current && lyricAt(host.current, event.clientX, event.clientY) !== null) return;
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
    // The cursor, unless a lyrics block is under the pointer: a drag moves it; a press alone stays a click.
    if (onCursor(event.clientX, event.clientY) && !(lyrics && host.current && lyricAt(host.current, event.clientX, event.clientY))) {
      const ms = msAtScreen(event.clientX, event.clientY);
      if (ms !== null) {
        setCursorDrag({ ms, moved: false, x0: event.clientX, y0: event.clientY });
        return;
      }
    }
    if (frameWindow && onWindowMove) {
      const point = toSheet(event.clientX, event.clientY);
      const frame = point && onGrip(point) ? frameAt(point.x, point.y) : null;
      if (frame !== null) {
        event.currentTarget.setPointerCapture(event.pointerId);
        setWindowDrag({ grab: frame - frameWindow.start, start: frameWindow.start });
        dragged.current = true;
        return;
      }
    }
    if (lyrics && host.current) {
      const point = toSheet(event.clientX, event.clientY);
      const handle = point ? handleAt(point) : null;
      const key = handle?.key ?? lyricAt(host.current, event.clientX, event.clientY);
      const block = key ? blocks[key] : undefined;
      const piece = block ? sheet.lyrics[block.index] : undefined;
      if (point && key && piece) {
        event.currentTarget.setPointerCapture(event.pointerId);
        setSettle(null);
        setLyricDrag({
          key,
          mode: handle?.mode ?? "move",
          x0: point.x,
          y0: point.y,
          x: point.x,
          y: point.y,
          moved: false,
          nextStart: piece.start,
          nextEnd: piece.end,
        });
        return;
      }
      // A press off the picked pieces lets them go, and does nothing else: the strip marks no stretch meanwhile.
      if (lyrics.picked.size > 0) {
        dragged.current = true;
        lyrics.onUnpick();
        return;
      }
    }
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
    if (cursorDrag) {
      const moved = cursorDrag.moved || Math.hypot(event.clientX - cursorDrag.x0, event.clientY - cursorDrag.y0) > DRAG_PX;
      if (moved && !cursorDrag.moved) event.currentTarget.setPointerCapture(event.pointerId);
      pointer.current = { x: event.clientX, y: event.clientY };
      const ms = moved ? msAtScreen(event.clientX, event.clientY) : null;
      if (moved !== cursorDrag.moved || (ms !== null && ms !== cursorDrag.ms)) {
        setCursorDrag({ ...cursorDrag, moved, ms: ms ?? cursorDrag.ms });
      }
      return;
    }
    // The pointer says the cursor can be dragged.
    const over = !drag?.moved && !rangeDrag && !lyricDrag && !windowDrag && onCursor(event.clientX, event.clientY);
    if (over !== overCursor) setOverCursor(over);
    if (windowDrag && onWindowMove) {
      const point = toSheet(event.clientX, event.clientY);
      const frame = point ? frameAt(point.x, point.y) : null;
      if (frame === null) return;
      const start = Math.max(0, frame - windowDrag.grab);
      if (start !== windowDrag.start) {
        setWindowDrag({ ...windowDrag, start });
        onWindowMove(start, false);
      }
      return;
    }
    if (lyricDrag) {
      const point = toSheet(event.clientX, event.clientY);
      if (!point) return;
      const moved = lyricDrag.moved || Math.hypot(point.x - lyricDrag.x0, point.y - lyricDrag.y0) > 0.4;
      const next = { ...lyricDrag, moved, x: point.x, y: point.y };
      const piece = blocks[lyricDrag.key] ? sheet.lyrics[blocks[lyricDrag.key]!.index] : undefined;
      if (piece && (lyricDrag.mode === "start" || lyricDrag.mode === "end")) {
        const frame = frameAt(point.x, point.y);
        if (frame !== null && lyricDrag.mode === "start") next.nextStart = Math.min(frame, piece.end - 1);
        if (frame !== null && lyricDrag.mode === "end") next.nextEnd = Math.max(piece.start + 1, frame);
      }
      setLyricDrag(next);
      return;
    }
    if (lyrics && lyrics.picked.size > 0) {
      // A picked block: its handles say what a press there does; the strip stays off.
      const point = toSheet(event.clientX, event.clientY);
      const mode = point ? (handleAt(point)?.mode ?? null) : null;
      if (mode !== hoverHandle) setHoverHandle(mode);
      if (strip !== -1) setStrip(-1);
      return;
    }
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
  const release = (event: PointerEvent<HTMLDivElement>) => {
    if (cursorDrag) {
      setCursorDrag(null);
      pointer.current = null;
      // Not moved: the click that follows picks a notehead or moves the recording, as anywhere on the sheet.
      if (!cursorDrag.moved) return;
      dragged.current = true;
      onSeek?.(cursorDrag.ms / 1000);
      return;
    }
    if (windowDrag) {
      setWindowDrag(null);
      dragged.current = true;
      onWindowMove?.(windowDrag.start, true);
      return;
    }
    if (lyricDrag) {
      const drag = lyricDrag;
      setLyricDrag(null);
      dragged.current = true;
      const block = blocks[drag.key];
      if (!lyrics || !block) return;
      if (!drag.moved) {
        if (drag.mode === "move") lyrics.onPick(startOf(block), event.metaKey || event.ctrlKey || event.shiftKey);
        return;
      }
      letGo(drag);
      return;
    }
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
        setCursorDrag(null);
        setDrag(null);
        setRangeDrag(null);
        setLyricDrag(null);
        setWindowDrag(null);
      }}
      onPointerLeave={() => {
        setStrip(-1);
        setOverCursor(false);
        setHoverHandle(null);
      }}
      onDragOver={(event) => {
        if (!lyrics?.landing) return;
        event.preventDefault();
        const point = toSheet(event.clientX, event.clientY);
        const frame = point ? frameAt(point.x, point.y) : null;
        const next = frame === null ? null : lyrics.landing(frame);
        if (next?.start !== poolLanding?.start || next?.end !== poolLanding?.end || next?.free !== poolLanding?.free) {
          setPoolLanding(next);
        }
      }}
      onDragLeave={() => setPoolLanding(null)}
      onDrop={(event) => {
        if (!lyrics?.landing) return;
        event.preventDefault();
        setPoolLanding(null);
        const point = toSheet(event.clientX, event.clientY);
        const frame = point ? frameAt(point.x, point.y) : null;
        if (frame !== null) lyrics.onDropPool(frame);
      }}
      sx={{
        position: "relative",
        backgroundColor: "#fff",
        borderRadius: 1,
        overflow: "hidden",
        cursor:
          windowDrag || draggingCursor
            ? "grabbing"
            : hoverHandle === "scale" || lyricDrag?.mode === "scale"
            ? "nwse-resize"
            : hoverHandle || (lyricDrag && lyricDrag.mode !== "move")
              ? "ew-resize"
              : lyricDrag?.moved
                ? "grabbing"
                : overCursor && !cursorDrag
                  ? "grab"
                  : strip >= 0 || rangeDrag
                  ? "col-resize"
                  : onSeek || onPick
                    ? "pointer"
                    : "default",
        userSelect: "none",
        touchAction: onPick ? "pan-y" : undefined,
        "& [data-selected]": { fill: palette.dark.Lavender },
        "& [data-lit]": { fill: semantic.pressedKey },
        "& [data-segment-state='working']": { animation: `${breathe} 1.6s ease-in-out infinite alternate` },
        "& [data-lyric]": { cursor: lyrics ? "grab" : undefined, transition: "opacity 0.2s" },
        "& [data-lyric][data-lyric-lit]": { fill: "#000", fontWeight: 700 },
        ...(centre ? { "& [data-lyric]": { fill: "#000" } } : {}),
        ...(centre && playing ? { "& [data-lyric]:not([data-lyric-lit])": { opacity: 0.4 } } : {}),

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
        {windowBoxes.length > 0 && windowNow ? (
          <g data-frame-window data-start={windowNow.start} data-end={windowNow.end}>
            {windowBoxes.map((box) => {
              const system = sheet.systems[box.system]!;
              return (
                <g key={`fw${box.system}`}>
                  <rect x={box.x} y={system.top} width={box.width} height={system.bottom - system.top} fill={WINDOW_COLOUR} opacity={0.07} />
                  {box.first ? (
                    // From the grip down: the edge the window is dragged by.
                    <line
                      x1={box.x}
                      x2={box.x}
                      y1={Math.max(0.1, system.top - WINDOW_GRIP.height - 0.3)}
                      y2={system.bottom}
                      stroke={WINDOW_COLOUR}
                      strokeWidth={0.18}
                    />
                  ) : null}
                  {box.last ? (
                    <line x1={box.x + box.width} x2={box.x + box.width} y1={system.top} y2={system.bottom} stroke={WINDOW_COLOUR} strokeWidth={0.18} />
                  ) : null}
                </g>
              );
            })}
            {grip ? (
              <rect
                data-frame-window-grip
                x={grip.x}
                y={grip.y}
                width={WINDOW_GRIP.width}
                height={WINDOW_GRIP.height}
                rx={WINDOW_GRIP.height / 2}
                fill={WINDOW_COLOUR}
              >
                <title>Drag: the stretch of the take that goes into the song</title>
              </rect>
            ) : null}
          </g>
        ) : null}
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
        {shadeBoxes.map((shade) => (
          <rect
            key={`l${shade.system}:${shade.x}:${shade.start}`}
            {...(shade.landing ? { "data-lyric-landing": "", "data-free": shade.free ? "true" : "false" } : {})}
            x={shade.x}
            y={shade.y}
            width={shade.width}
            height={STRIP_SPACES - 0.3}
            fill={shade.fill}
            opacity={shade.landing ? 0.25 : 0.15}
          />
        ))}
        {bar.map((box, k) => (
          <g key={`f${box.system}:${box.x}`} data-lyric-frames={k === 0 ? "" : undefined}>
            <rect x={box.x} y={box.y + BAR_Y} width={box.width} height={0.8} fill={palette.dark.Lavender} opacity={0.35} rx={0.2} />
            {k === 0 ? (
              <rect data-lyric-handle="start" pointerEvents="all" x={box.x - 0.25} y={box.y + BAR_Y - 0.3} width={0.5} height={1.4} fill={palette.dark.Lavender} rx={0.15}>
                <title>Drag: when the words start to sound</title>
              </rect>
            ) : null}
            {k === bar.length - 1 ? (
              <rect
                data-lyric-handle="end" pointerEvents="all"
                x={box.x + box.width - 0.25}
                y={box.y + BAR_Y - 0.3}
                width={0.5}
                height={1.4}
                fill={palette.dark.Lavender}
                rx={0.15}
              >
                <title>Drag: when the words stop sounding</title>
              </rect>
            ) : null}
          </g>
        ))}
        {pickedBlocks.map(([key, block]) => {
          // The outline follows the drag: moved, scaled, or as wide as the words wrapped now.
          let { x, y, width: wide, height } = block;
          if (active?.key === key && active.mode === "move") {
            x += active.x - active.x0;
            y += active.y - active.y0;
          } else if (active?.key === key && active.mode === "scale") {
            const ratio = scaleOf(active, block);
            [x, y, wide, height] = [block.left + (x - block.left) * ratio, block.base + (y - block.base) * ratio, wide * ratio, height * ratio];
          } else if (active?.key === key && widthPreview) {
            const rows = widthPreview.lines.length;
            [wide, y, height] = [widthPreview.width, widthPreview.top - block.size * 0.85, rows * block.size * LYRIC_LEADING];
          }
          const right = Math.max(x + wide, block.wrap !== null && active?.key !== key ? block.left + block.wrap : 0);
          const handles = handlesOf({ ...block, x, y, width: right - x, height, wrap: null });
          return (
            <g key={`p${key}`}>
              <rect
                x={x - 0.3}
                y={y - 0.2}
                width={right - x + 0.6}
                height={height + 0.4}
                fill={palette.dark.Lavender}
                fillOpacity={0.08}
                stroke={palette.dark.Lavender}
                strokeWidth={0.08}
                rx={0.3}
              />
              <rect
                data-lyric-handle="width" pointerEvents="all"
                x={handles.width.x - 0.18}
                y={handles.width.y - 0.6}
                width={0.36}
                height={1.2}
                fill={palette.dark.Lavender}
                rx={0.12}
              >
                <title>Drag: narrower or wider (the words wrap)</title>
              </rect>
              <rect
                data-lyric-handle="scale" pointerEvents="all"
                x={handles.scale.x - 0.3}
                y={handles.scale.y - 0.3}
                width={0.6}
                height={0.6}
                fill="#fff"
                stroke={palette.dark.Lavender}
                strokeWidth={0.12}
                rx={0.1}
              >
                <title>Drag: larger or smaller words</title>
              </rect>
            </g>
          );
        })}
        {widthPreview ? (
          <text
            data-lyric-preview
            fontSize={widthPreview.block.size}
            fontFamily={familyOf(widthPreview.block.font)}
            fontWeight={widthPreview.block.bold ? 700 : 400}
            fontStyle={widthPreview.block.italic ? "italic" : "normal"}
            fill="#3a3a3a"
          >
            {widthPreview.lines.map((text, k) => (
              <tspan key={k} x={widthPreview.block.left} y={widthPreview.top + k * widthPreview.block.size * LYRIC_LEADING}>
                {text}
              </tspan>
            ))}
          </text>
        ) : null}
        {place && line ? (
          <line
            ref={cursor}
            data-frames-cursor
            data-ms={Math.round(cursorMs ?? 0)}
            data-dragging={draggingCursor ? "" : undefined}
            style={{ scrollMarginTop: keepClear + 8 }}
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
