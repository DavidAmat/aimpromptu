/**
 * The arithmetic of the new sheet on the page (implementation 03, Phase 5), from the cursor map the backend sends:
 * one row per drawn column (its system, its x in staff spaces, its time) and one box per system. It follows the
 * research viewer (`viewer/index.html` of the research folder), which the plan names as the reference.
 */

import type { SheetColumn, SheetSegment, SheetSystem } from "../../../../api";

/** Room before the first column of a line, for its accidentals and grace notes, in staff spaces. */
const LEAD = 2.5;

/** The columns with a time that never goes back (two columns of one chord played unevenly can share a frame). */
export function steadyColumns(columns: readonly SheetColumn[]): SheetColumn[] {
  let last = -Infinity;
  return columns.map((column) => {
    last = Math.max(last, column.ms);
    return { ...column, ms: last };
  });
}

/** Where the cursor is at `ms`: its x and system, and the column it is in (`-1` before the first one). */
export function placeAt(
  columns: readonly SheetColumn[],
  systems: readonly SheetSystem[],
  ms: number,
): { x: number; system: number; column: number } | null {
  if (columns.length === 0) return null;
  if (ms <= columns[0].ms) return { x: columns[0].x, system: columns[0].system, column: ms < columns[0].ms ? -1 : 0 };
  let lo = 0;
  let hi = columns.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (columns[mid].ms <= ms) lo = mid;
    else hi = mid - 1;
  }
  const a = columns[lo];
  const b = columns[lo + 1];
  if (!b) return { x: a.x, system: a.system, column: lo };
  const ratio = b.ms > a.ms ? (ms - a.ms) / (b.ms - a.ms) : 0;
  // To the end of the line when the next column is on the next one.
  const xb = b.system === a.system ? b.x : (systems[a.system]?.right ?? a.x);
  return { x: a.x + ratio * (xb - a.x), system: a.system, column: lo };
}

/** The left and right edge of each column on its line: half way to its neighbours, the line's end after the last. */
export function columnEdges(columns: readonly SheetColumn[], systems: readonly SheetSystem[]): [number, number][] {
  return columns.map((column, i) => {
    const before = columns[i - 1];
    const after = columns[i + 1];
    const left = before && before.system === column.system ? (before.x + column.x) / 2 : column.x - LEAD;
    const right =
      after && after.system === column.system ? (column.x + after.x) / 2 : (systems[column.system]?.right ?? column.x + LEAD);
    return [left, right];
  });
}

/** One box of a segment on one line, in staff spaces. */
export interface Box {
  system: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

/** The boxes of the columns `from` to `to` (indices, `to` excluded) on their lines. */
export function boxesOf(
  from: number,
  to: number,
  columns: readonly SheetColumn[],
  edges: readonly [number, number][],
  systems: readonly SheetSystem[],
): Box[] {
  const out: Box[] = [];
  for (let i = from; i < to; i += 1) {
    const system = systems[columns[i].system];
    if (!system) continue;
    const [left, right] = edges[i];
    const last = out[out.length - 1];
    if (last && last.system === columns[i].system) {
      last.width = right - last.x;
    } else {
      out.push({ system: columns[i].system, x: left, y: system.top - 1, width: right - left, height: system.bottom - system.top + 2 });
    }
  }
  return out;
}

/** The indices of the columns of a segment or a marked stretch: `[first, end)`. */
export function columnsOf(
  segment: Pick<SheetSegment, "start" | "end">,
  columns: readonly SheetColumn[],
): [number, number] {
  let first = columns.findIndex((column) => column.frame >= segment.start);
  if (first < 0) first = columns.length;
  let end = columns.findIndex((column) => column.frame >= segment.end);
  if (end < 0) end = columns.length;
  return [first, end];
}

/** The time under a point of the sheet (staff spaces), as the viewer's click: on the nearest line, between columns. */
export function msAtPoint(
  columns: readonly SheetColumn[],
  systems: readonly SheetSystem[],
  x: number,
  y: number,
): number | null {
  if (columns.length === 0 || systems.length === 0) return null;
  let line = systems.findIndex((system) => y >= system.top - 2 && y <= system.bottom + 2);
  if (line < 0) {
    line = 0;
    let best = Infinity;
    systems.forEach((system, i) => {
      const distance = Math.abs((system.top + system.bottom) / 2 - y);
      if (distance < best) {
        best = distance;
        line = i;
      }
    });
  }
  const on = columns.map((_, i) => i).filter((i) => columns[i].system === line);
  if (on.length === 0) return null;
  let ms = columns[on[0]].ms;
  for (const i of on) {
    const a = columns[i];
    const b = columns[i + 1];
    if (x < a.x) break;
    if (!b) return a.ms;
    const xb = b.system === line ? b.x : systems[line].right;
    if (x <= xb) return a.ms + ((b.ms - a.ms) * (x - a.x)) / Math.max(1e-6, xb - a.x);
    ms = b.ms;
  }
  return ms;
}

/**
 * The noteheads of each column. A head carries `data-note="<frame>:<midi>"` (several when it stands for merged
 * unisons); a column holds the frames from its own time to the next column's (a chord played unevenly spans one
 * or two frames). A grace note lights with the column before its note: it sounds just before it.
 */
export function headsByColumn(root: ParentNode, columns: readonly SheetColumn[], frameMs = 40): Element[][] {
  const byFrame = new Map<number, Element[]>();
  for (const element of root.querySelectorAll("[data-note]")) {
    for (const ref of (element.getAttribute("data-note") ?? "").split(" ")) {
      const frame = Number(ref.split(":")[0]);
      if (!Number.isFinite(frame)) continue;
      const list = byFrame.get(frame);
      if (list) list.push(element);
      else byFrame.set(frame, [element]);
    }
  }
  const frames = [...byFrame.keys()].sort((a, b) => a - b);
  let k = 0;
  return columns.map((column, i) => {
    const lo = Math.round(column.ms / frameMs);
    const hi = i + 1 < columns.length ? Math.round(columns[i + 1].ms / frameMs) : Infinity;
    const out: Element[] = [];
    while (k < frames.length && frames[k] < lo) k += 1;
    for (let j = k; j < frames.length && frames[j] < Math.max(hi, lo + 1); j += 1) out.push(...(byFrame.get(frames[j]) ?? []));
    return out;
  });
}
