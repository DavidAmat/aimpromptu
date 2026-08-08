/**
 * The waveform itself: min/max peaks from the backend, drawn as one SVG path
 * per bucket, plus the selection shading and the playback cursor.
 *
 * Split out from the range selector so the piano roll (Story 8.2) can reuse it
 * as a watermark without dragging the interaction logic along.
 */

import Box from "@mui/material/Box";
import type { WaveformPeaks } from "../../api";
import { semantic, surface } from "../../ui";

export interface WaveformViewProps {
  peaks: WaveformPeaks;
  height?: number;
  /** Shaded selection, in seconds. Omit for no selection. */
  selection?: { startSeconds: number; endSeconds: number };
  /** Playback cursor position in seconds. */
  cursorSeconds?: number | null;
  /** Renders faint, for use behind other content. */
  watermark?: boolean;
}

export function WaveformView({
  peaks,
  height = 120,
  selection,
  cursorSeconds,
  watermark = false,
}: WaveformViewProps) {
  const duration = peaks.durationSeconds || 1;
  const middle = height / 2;
  const scale = (height / 2) * 0.95;
  const bucketWidth = 100 / Math.max(1, peaks.points);

  const toX = (seconds: number) => (seconds / duration) * 100;

  return (
    <Box sx={{ width: "100%", opacity: watermark ? 0.25 : 1 }}>
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        width="100%"
        height={height}
        role="img"
        aria-label="Audio waveform"
        style={{ display: "block" }}
      >
        {selection ? (
          <rect
            x={toX(selection.startSeconds)}
            y={0}
            width={Math.max(0, toX(selection.endSeconds) - toX(selection.startSeconds))}
            height={height}
            fill={semantic.waveform.selection}
            opacity={0.22}
          />
        ) : null}

        <line x1="0" y1={middle} x2="100" y2={middle} stroke={surface.strongLine} strokeWidth="0.4" />

        {peaks.max.map((high, index) => {
          const low = peaks.min[index] ?? 0;
          const top = middle - high * scale;
          const bottom = middle - low * scale;
          return (
            <rect
              key={index}
              x={index * bucketWidth}
              y={Math.min(top, bottom)}
              width={bucketWidth}
              height={Math.max(0.6, Math.abs(bottom - top))}
              fill={semantic.waveform.body}
            />
          );
        })}

        {cursorSeconds !== null && cursorSeconds !== undefined ? (
          <line
            x1={toX(cursorSeconds)}
            y1={0}
            x2={toX(cursorSeconds)}
            y2={height}
            stroke={semantic.waveform.cursor}
            strokeWidth="0.5"
          />
        ) : null}
      </svg>
    </Box>
  );
}

export default WaveformView;
