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
 * Hooks for the browser checks: `data-frames-sheet` on the root (with `data-source`, `data-llm`, `data-working`),
 * `data-note="<frame>:<midi>"` on each notehead, `data-lit` on the lit ones, `data-frames-cursor` (with
 * `data-ms`), `data-segment-state="working"` on the veil and `data-revealing` while a segment appears.
 */

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import Box from "@mui/material/Box";
import { keyframes } from "@mui/material/styles";
import type { FramesSheet } from "../../../../api";
import { semantic } from "../../../../ui";
import { boxesOf, columnEdges, columnsOf, headsByColumn, msAtPoint, placeAt, steadyColumns } from "./geometry";

/** The reveal of a segment takes about this long, whatever its number of columns. */
const REVEAL_MS = 1800;
const STEP_MIN_MS = 25;
const STEP_MAX_MS = 90;
/** The stroke of a staff line in the engine (Verovio's style, 13/180 of a staff space: `layout.STAFF_LINE_W`). */
const STAFF_LINE = 13 / 180;

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
}: {
  sheet: FramesSheet;
  playheadSeconds: number | null;
  /** The recording plays: keep the cursor's line in view. */
  follow: boolean;
  /** In the middle of the window (Play mode), not only in view. */
  centre?: boolean;
  onSeek?: (seconds: number) => void;
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
    // The segment that was at Sonnet (or waiting) and is decided now.
    const back = sheet.segments.find(
      (segment) =>
        (segment.state === "llm" || segment.state === "algorithm") &&
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

  const seek = (event: MouseEvent<HTMLDivElement>) => {
    const svg = overlay.current;
    const matrix = svg?.getScreenCTM();
    if (!svg || !matrix || !onSeek) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    const ms = msAtPoint(columns, sheet.systems, point.x, point.y);
    if (ms !== null) onSeek(ms / 1000);
  };

  return (
    <Box
      data-frames-sheet
      data-source={sheet.source}
      data-llm={sheet.llm.state}
      data-working={working.length > 0 ? "" : undefined}
      onClick={seek}
      sx={{
        position: "relative",
        backgroundColor: "#fff",
        borderRadius: 1,
        overflow: "hidden",
        cursor: onSeek ? "pointer" : "default",
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
    </Box>
  );
}

export default FramesSheetView;
