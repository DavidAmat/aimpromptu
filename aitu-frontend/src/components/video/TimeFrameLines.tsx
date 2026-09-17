/**
 * The upper line, and one offset line per time frame above it (Task 3.4.2).
 *
 * The upper line and the line above it describe one window of time: a rectangle
 * tip inside it is an onset in that sampled frame. On a screenshot the distance
 * between them is the user's to drag, because there is no measured speed. **On a
 * video it is not a free parameter at all**: it is the measured scroll speed
 * times the sampling granularity and nothing else (V-25).
 *
 * So this draws that spacing instead of offering it. Several lines, not one,
 * because what the user wants to see on a real frame is which rectangles will
 * land in which sampled frame — the first band is the next frame, the second is
 * the one after it, and so on up the roll.
 */

import { palette, surface } from "../../ui";

export interface TimeFrameLinesProps {
  upperLine: number;
  /** How far the roll falls in one sampled frame, in picture pixels. */
  offsetPx: number;
  imageWidth: number;
  /** How many time frames to draw above the upper line. */
  count?: number;
  /** Nothing above this row is music (V-28). Drawn when it is not zero. */
  rollTop?: number;
  /** Where the strike light makes the picture unreadable (V-08, V-24). */
  guardBand?: number;
  /** Picture pixels per screen pixel, so a stroke keeps its size on screen. */
  scale: number;
}

export function TimeFrameLines({
  upperLine,
  offsetPx,
  imageWidth,
  count = 6,
  rollTop = 0,
  guardBand = 0,
  scale,
}: TimeFrameLinesProps) {
  const bands = offsetPx > 0 ? Array.from({ length: count }, (_, i) => i) : [];

  return (
    <g>
      {/* The halo guard band: inside it the tip is extrapolated, not read
          (V-08), so it is shown as a region and not as a line. */}
      {guardBand > 0 ? (
        <rect
          x={0}
          y={upperLine - guardBand}
          width={imageWidth}
          height={guardBand}
          fill={palette.dark.Red}
          fillOpacity={0.1}
          style={{ pointerEvents: "none" }}
        />
      ) : null}

      {bands.map((band) => (
        <g key={band}>
          <rect
            x={0}
            y={upperLine - offsetPx * (band + 1)}
            width={imageWidth}
            height={offsetPx}
            fill={palette.dark.Yellow}
            fillOpacity={band % 2 === 0 ? 0.13 : 0.05}
            style={{ pointerEvents: "none" }}
          />
          <line
            x1={0}
            x2={imageWidth}
            y1={upperLine - offsetPx * (band + 1)}
            y2={upperLine - offsetPx * (band + 1)}
            stroke={palette.dark.Yellow}
            strokeWidth={(band === 0 ? 1.4 : 0.8) * scale}
            style={{ pointerEvents: "none" }}
          />
        </g>
      ))}

      {rollTop > 0 ? (
        <line
          x1={0}
          x2={imageWidth}
          y1={rollTop}
          y2={rollTop}
          stroke={palette.dark.Blue}
          strokeWidth={1.2 * scale}
          strokeDasharray={`${5 * scale} ${4 * scale}`}
          style={{ pointerEvents: "none" }}
        />
      ) : null}

      <line
        x1={0}
        x2={imageWidth}
        y1={upperLine}
        y2={upperLine}
        stroke={palette.dark.Red}
        strokeWidth={1.5 * scale}
        style={{ pointerEvents: "none" }}
      />

      {offsetPx > 0 ? (
        <text
          x={6 * scale}
          y={upperLine - offsetPx - 5 * scale}
          fill={palette.dark.Yellow}
          fontSize={11 * scale}
          stroke={surface.text}
          strokeWidth={2.5 * scale}
          style={{ paintOrder: "stroke", pointerEvents: "none" }}
        >
          one sampled frame = {offsetPx.toFixed(1)} px
        </text>
      ) : null}
    </g>
  );
}

export default TimeFrameLines;
