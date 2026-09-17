/**
 * The one rectangle the user drags over the piano area (V-37).
 *
 * Resizable and rotatable, so it can take whatever shape the picture needs. It
 * moves by its body, resizes from its four edges and four corners, and turns
 * from one handle past its right end: dragging that handle sets the angle of
 * the top edge, about the top left corner, which is how the calibration
 * measures it.
 *
 * Everything is in picture pixels. `scale` is how many picture pixels one
 * screen pixel is worth right now, from the canvas, so a handle is the same
 * size on screen at every zoom and a drag stays under the pointer. A resize is
 * done in the rectangle's own frame: the pointer's travel is turned into a
 * distance along the top edge (u) and down the side (v) before it changes a
 * width or a height, so an edge of a turned rectangle still moves along itself.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
import type { PianoRect as Rect } from "../../api/frameExamples";
import { surface } from "../../ui";

export interface PianoRectProps {
  rect: Rect;
  onChange: (rect: Rect) => void;
  /** Told when a gesture starts and ends, so the canvas can stop panning. */
  onGesture: (active: boolean) => void;
  colour: string;
  /** Picture pixels per screen pixel — handles are sized in screen pixels. */
  scale: number;
  bounds: { width: number; height: number };
}

type Handle = "move" | "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw" | "rotate";

const HANDLE_SCREEN_PX = 9;
const ROTATE_REACH_SCREEN_PX = 26;
const MIN_SIZE = 8;

const radians = (degrees: number) => degrees * (Math.PI / 180);

export function PianoRect({ rect, onChange, onGesture, colour, scale, bounds }: PianoRectProps) {
  const size = HANDLE_SCREEN_PX * scale;
  const reach = ROTATE_REACH_SCREEN_PX * scale;

  const start = (handle: Handle) => (event: ReactMouseEvent) => {
    event.stopPropagation();
    const origin = { x: event.clientX, y: event.clientY, rect };
    onGesture(true);

    const move = (native: MouseEvent) => {
      const dx = (native.clientX - origin.x) * scale;
      const dy = (native.clientY - origin.y) * scale;
      onChange(clamp(applyDrag(origin.rect, handle, dx, dy), bounds));
    };
    const stop = () => {
      onGesture(false);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
  };

  // Handles are laid out in the rectangle's own frame, inside the turned group.
  const handles: { handle: Handle; u: number; v: number; cursor: string }[] = [
    { handle: "nw", u: 0, v: 0, cursor: "nwse-resize" },
    { handle: "n", u: rect.width / 2, v: 0, cursor: "ns-resize" },
    { handle: "ne", u: rect.width, v: 0, cursor: "nesw-resize" },
    { handle: "e", u: rect.width, v: rect.height / 2, cursor: "ew-resize" },
    { handle: "se", u: rect.width, v: rect.height, cursor: "nwse-resize" },
    { handle: "s", u: rect.width / 2, v: rect.height, cursor: "ns-resize" },
    { handle: "sw", u: 0, v: rect.height, cursor: "nesw-resize" },
    { handle: "w", u: 0, v: rect.height / 2, cursor: "ew-resize" },
  ];

  return (
    <g transform={`translate(${rect.x} ${rect.y}) rotate(${rect.angle})`}>
      <rect
        x={0}
        y={0}
        width={rect.width}
        height={rect.height}
        fill={colour}
        fillOpacity={0.1}
        stroke={colour}
        strokeWidth={1.5 * scale}
        style={{ cursor: "move" }}
        onMouseDown={start("move")}
      />
      {handles.map((spot) => (
        <rect
          key={spot.handle}
          x={spot.u - size / 2}
          y={spot.v - size / 2}
          width={size}
          height={size}
          fill={surface.panel}
          stroke={colour}
          strokeWidth={1.2 * scale}
          style={{ cursor: spot.cursor }}
          onMouseDown={start(spot.handle)}
        />
      ))}
      {/* The angle handle: past the right end of the top edge, on the edge's own line. */}
      <line
        x1={rect.width}
        y1={0}
        x2={rect.width + reach}
        y2={0}
        stroke={colour}
        strokeWidth={1.2 * scale}
        style={{ pointerEvents: "none" }}
      />
      <circle
        cx={rect.width + reach}
        cy={0}
        r={size / 2}
        fill={surface.panel}
        stroke={colour}
        strokeWidth={1.2 * scale}
        style={{ cursor: "grab" }}
        onMouseDown={start("rotate")}
      >
        <title>{`turn the rectangle · ${rect.angle.toFixed(1)}°`}</title>
      </circle>
    </g>
  );
}

/**
 * Apply a pointer travel of (dx, dy) picture pixels to the rectangle.
 *
 * A move is a move. A resize converts the travel into the rectangle's own frame
 * and changes the width, the height, or the origin along the edge that moved.
 * A turn sets the angle of the line from the top left corner to the pointer,
 * which starts on the top edge's own line past the right end.
 */
function applyDrag(rect: Rect, handle: Handle, dx: number, dy: number): Rect {
  if (handle === "move") return { ...rect, x: rect.x + dx, y: rect.y + dy };

  const a = radians(rect.angle);
  const cos = Math.cos(a);
  const sin = Math.sin(a);

  if (handle === "rotate") {
    const reachU = rect.width + 1; // the handle sits on the top edge's line
    const hx = rect.x + reachU * cos + dx;
    const hy = rect.y + reachU * sin + dy;
    const angle = (Math.atan2(hy - rect.y, hx - rect.x) * 180) / Math.PI;
    return { ...rect, angle: Math.max(-45, Math.min(45, angle)) };
  }

  // the travel in the rectangle's frame
  const du = dx * cos + dy * sin;
  const dv = -dx * sin + dy * cos;
  let { x, y, width, height } = rect;
  if (handle.includes("w")) {
    x += du * cos;
    y += du * sin;
    width -= du;
  }
  if (handle.includes("e")) width += du;
  if (handle.includes("n")) {
    x += -dv * sin;
    y += dv * cos;
    height -= dv;
  }
  if (handle.includes("s")) height += dv;
  return { x, y, width, height, angle: rect.angle };
}

/** Never let the rectangle turn inside out or leave the picture entirely. */
function clamp(rect: Rect, bounds: { width: number; height: number }): Rect {
  const width = Math.max(MIN_SIZE, rect.width);
  const height = Math.max(MIN_SIZE, rect.height);
  return {
    ...rect,
    width,
    height,
    x: Math.min(Math.max(rect.x, -width / 2), bounds.width - width / 2),
    y: Math.min(Math.max(rect.y, -height / 2), bounds.height - height / 2),
  };
}

export default PianoRect;
