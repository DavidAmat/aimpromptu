/**
 * The offset line, dragged up and down the picture with the mouse.
 *
 * The upper line and the offset line together describe one window of time: a
 * rectangle tip inside it is an onset, and how far apart they are is how far the
 * rectangles fall in one time frame. On a screenshot there is no measured scroll
 * speed, so the distance is the user's to choose — and choosing it is dragging
 * the line, not typing a number into a field. On a video it is not free at all:
 * it is the measured scroll speed times the sampling granularity (V-25).
 *
 * The band between the two lines is shaded, because the window is the thing being
 * judged and it should be the thing you see.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
import { palette, surface } from "../../ui";

export interface OffsetLineProps {
  upperLine: number;
  /** How far the offset line sits above the upper line, in picture pixels. */
  offsetPx: number;
  imageWidth: number;
  whiteWidth: number;
  /** Picture pixels per screen pixel. */
  scale: number;
  onChange: (offsetPx: number) => void;
  /** Told when the drag starts and ends, so the canvas stops panning. */
  onGesture?: (active: boolean) => void;
}

/** How tall the grab strip is, in screen pixels: the line is one pixel, the grab is not. */
const GRAB_SCREEN_PX = 11;

export function OffsetLine({
  upperLine,
  offsetPx,
  imageWidth,
  whiteWidth,
  scale,
  onChange,
  onGesture,
}: OffsetLineProps) {
  const y = upperLine - offsetPx;
  const grab = GRAB_SCREEN_PX * scale;

  const start = (event: ReactMouseEvent) => {
    event.stopPropagation();
    const origin = { y: event.clientY, offset: offsetPx };
    onGesture?.(true);
    const move = (native: MouseEvent) => {
      // Dragging up is a bigger window: y grows downward and the offset does not.
      onChange(Math.max(2, origin.offset - (native.clientY - origin.y) * scale));
    };
    const stop = () => {
      onGesture?.(false);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
  };

  return (
    <g>
      <rect
        x={0}
        y={y}
        width={imageWidth}
        height={offsetPx}
        fill={palette.dark.Yellow}
        fillOpacity={0.14}
        style={{ pointerEvents: "none" }}
      />
      <line
        x1={0}
        x2={imageWidth}
        y1={upperLine}
        y2={upperLine}
        stroke={palette.dark.Red}
        strokeWidth={1.4 * scale}
        style={{ pointerEvents: "none" }}
      />
      {/* The grab strip is wider than the line it draws, or it could not be caught. */}
      <rect
        x={0}
        y={y - grab / 2}
        width={imageWidth}
        height={grab}
        fill="transparent"
        style={{ cursor: "ns-resize" }}
        onMouseDown={start}
      >
        <title>Drag to set how far the rectangles fall in one time frame</title>
      </rect>
      <line
        x1={0}
        x2={imageWidth}
        y1={y}
        y2={y}
        stroke={palette.dark.Yellow}
        strokeWidth={1.6 * scale}
        style={{ pointerEvents: "none" }}
      />
      <text
        x={6 * scale}
        y={y - 5 * scale}
        fill={palette.dark.Yellow}
        fontSize={11 * scale}
        stroke={surface.text}
        strokeWidth={2.5 * scale}
        style={{ paintOrder: "stroke", pointerEvents: "none" }}
      >
        {offsetPx.toFixed(0)} px · {(offsetPx / whiteWidth).toFixed(2)} white keys
      </text>
    </g>
  );
}

export default OffsetLine;
