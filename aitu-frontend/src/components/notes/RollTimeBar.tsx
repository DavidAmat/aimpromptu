/**
 * The bar under the piano roll visualization, as in the MuScriptor examples.
 *
 * **While the piece is transcribed** it is the progress bar: it moves with the frontier the canvas
 * draws (smoothed between the chunks), says how far the transcription is in the piece ("1:50 /
 * 3:09"), how long it has taken, and about how long is left. At the end it says "done in 0:25".
 *
 * **Afterwards** it is the scrub bar of playback: the position in the piece, and a press or a drag
 * on it moves the playhead.
 *
 * Both are painted from an animation frame that writes into the bar directly, so neither the
 * stream nor playback renders React.
 */

import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { formatTime, formatTimeShort } from "../../audio/time";
import type { LiveFeed } from "../../notes/liveFeed";
import { semantic, timestampSx } from "../../ui";

export interface RollTimeBarProps {
  durationMs: number;
  /** The live transcription, or `null` for playback. */
  feed: LiveFeed | null;
  /** Words to show before the first chunk arrives (waiting, loading). */
  waiting?: string | null;
  cursorMs: number;
  playing: boolean;
  position: () => number;
  onSeek: ((ms: number) => void) | null;
}

function clockOf(seconds: number): string {
  return formatTimeShort(Math.round(seconds));
}

export function RollTimeBar({ durationMs, feed, waiting, cursorMs, playing, position, onSeek }: RollTimeBarProps) {
  const fillRef = useRef<HTMLDivElement | null>(null);
  const leftRef = useRef<HTMLSpanElement | null>(null);
  const rightRef = useRef<HTMLSpanElement | null>(null);
  const barRef = useRef<HTMLDivElement | null>(null);
  const dragging = useRef(false);

  useEffect(() => {
    let frame = 0;
    const paint = () => {
      frame = 0;
      const fill = fillRef.current;
      const left = leftRef.current;
      const right = rightRef.current;
      if (!fill || !left || !right) return;
      if (feed) {
        const now = performance.now();
        const total = Math.max(durationMs, feed.durationMs);
        const at = Math.min(total, feed.finished ? total : feed.shownMs);
        fill.style.width = `${total > 0 ? (at / total) * 100 : 0}%`;
        const elapsed = feed.elapsedSeconds(now);
        if (feed.finished) {
          left.textContent = `${clockOf(total / 1000)} / ${clockOf(total / 1000)}`;
          right.textContent = elapsed !== null ? `done in ${clockOf(elapsed)}` : "done";
        } else if (feed.received === 0) {
          left.textContent = waiting ?? "Starting…";
          right.textContent = elapsed !== null ? clockOf(elapsed) : "";
        } else {
          left.textContent = `${clockOf(at / 1000)} / ${clockOf(total / 1000)}`;
          const remaining = feed.progress.remainingMs(now);
          right.textContent = [
            `${feed.notes} notes`,
            elapsed !== null ? `${clockOf(elapsed)} elapsed` : null,
            remaining !== null ? `about ${Math.max(1, Math.round(remaining / 1000))} s left` : null,
          ]
            .filter(Boolean)
            .join(" · ");
        }
        if (!feed.finished) frame = requestAnimationFrame(paint);
        return;
      }
      const at = playing ? position() : cursorMs;
      fill.style.width = `${durationMs > 0 ? Math.min(100, (at / durationMs) * 100) : 0}%`;
      left.textContent = `${formatTime(at / 1000)} / ${formatTime(durationMs / 1000)}`;
      right.textContent = "";
      if (playing) frame = requestAnimationFrame(paint);
    };
    paint();
    const stop = feed?.subscribe(() => {
      if (!frame) frame = requestAnimationFrame(paint);
    });
    return () => {
      cancelAnimationFrame(frame);
      stop?.();
    };
  }, [feed, durationMs, waiting, cursorMs, playing, position]);

  const seekAt = (clientX: number) => {
    const bar = barRef.current;
    if (!bar || !onSeek) return;
    const bounds = bar.getBoundingClientRect();
    onSeek(Math.min(1, Math.max(0, (clientX - bounds.left) / Math.max(1, bounds.width))) * durationMs);
  };

  const seekable = !feed && onSeek !== null;
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2, px: 1.5, py: 1, bgcolor: semantic.roll.ruler, borderRadius: 1 }}>
      <Box
        ref={barRef}
        role={seekable ? "slider" : "progressbar"}
        aria-label={seekable ? "Position in the piece" : "Progress of the transcription"}
        onPointerDown={(event) => {
          if (!seekable || event.button !== 0) return;
          event.currentTarget.setPointerCapture(event.pointerId);
          dragging.current = true;
          seekAt(event.clientX);
        }}
        onPointerMove={(event) => {
          if (dragging.current) seekAt(event.clientX);
        }}
        onPointerUp={() => {
          dragging.current = false;
        }}
        onLostPointerCapture={() => {
          dragging.current = false;
        }}
        sx={{
          flexGrow: 1,
          height: 14,
          display: "flex",
          alignItems: "center",
          cursor: seekable ? "pointer" : "default",
          touchAction: "none",
        }}
      >
        <Box sx={{ position: "relative", width: "100%", height: 4, borderRadius: 2, bgcolor: semantic.roll.gridStrong }}>
          <Box
            ref={fillRef}
            sx={{
              position: "absolute",
              left: 0,
              top: 0,
              bottom: 0,
              width: 0,
              borderRadius: 2,
              bgcolor: feed ? semantic.status.success : semantic.roll.playhead,
            }}
          />
        </Box>
      </Box>
      <Typography
        component="span"
        ref={leftRef}
        data-bar="position"
        variant="body2"
        sx={{ ...timestampSx, color: semantic.roll.rulerText, minWidth: 130, textAlign: "right" }}
      />
      <Typography
        component="span"
        ref={rightRef}
        data-bar="details"
        variant="body2"
        sx={{ ...timestampSx, color: semantic.roll.rulerText, minWidth: 250 }}
      />
    </Box>
  );
}

export default RollTimeBar;
