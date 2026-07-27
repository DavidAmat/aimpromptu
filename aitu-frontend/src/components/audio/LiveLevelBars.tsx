/**
 * SoundCloud-style level meter: one bar per sampled window, tall = loud.
 *
 * Purely visual feedback while recording. Drawn as SVG rects rather than a
 * canvas — under a hundred bars, and it keeps the palette in CSS terms.
 */

import Box from "@mui/material/Box";
import { LEVEL_HISTORY } from "../../audio/useRecorder";
import { grays, semantic } from "../../ui";

export interface LiveLevelBarsProps {
  /** Levels in 0..1, oldest first. */
  levels: number[];
  /** Dims the meter when not recording. */
  active?: boolean;
  height?: number;
}

export function LiveLevelBars({ levels, active = true, height = 72 }: LiveLevelBarsProps) {
  const slots = LEVEL_HISTORY;
  const barWidth = 100 / slots;
  // Right-align the history so new bars appear at the leading edge.
  const offset = slots - levels.length;

  return (
    <Box
      sx={{
        width: "100%",
        height,
        borderRadius: 1,
        border: 1,
        borderColor: "divider",
        opacity: active ? 1 : 0.45,
        transition: "opacity 150ms",
        overflow: "hidden",
      }}
    >
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        width="100%"
        height={height}
        role="img"
        aria-label="Microphone level"
      >
        <line
          x1="0"
          y1={height / 2}
          x2="100"
          y2={height / 2}
          stroke={grays.slate}
          strokeWidth="0.5"
        />
        {levels.map((level, index) => {
          const barHeight = Math.max(1, level * (height - 4));
          return (
            <rect
              key={index}
              x={(offset + index) * barWidth + barWidth * 0.15}
              y={(height - barHeight) / 2}
              width={barWidth * 0.7}
              height={barHeight}
              rx={barWidth * 0.3}
              fill={level > 0.85 ? semantic.status.warning : semantic.waveform.body}
            />
          );
        })}
      </svg>
    </Box>
  );
}

export default LiveLevelBars;
