/**
 * The matrix as a spreadsheet: 88 key columns, one row per time frame.
 *
 * Reading it: a **filled circle** is a struck note, a **pale circle** is that
 * same note still being held, and a vertical line joins them — so one note
 * reads as a solid head with a pale tail running down the page. Scrolling down
 * is moving forward in time.
 *
 * Rendered from the **dense** form, which the backend produces. The frontend
 * does no sparse-to-dense work of its own.
 *
 * Long pieces are simply tall. Rows outside the viewport are not drawn
 * (a windowed range plus a spacer above and below), which keeps a
 * ten-thousand-frame piece scrolling smoothly without changing how it looks.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { KeyLabel } from "../../api";
import { formatTime } from "../../audio/time";
import { grays, handColors, semantic } from "../../ui";

/** Which hand a row of the piano belongs to, for colouring. */
export type GridHand = "single" | "left" | "right";

export interface MatrixGridProps {
  /** Dense grid, one row per frame, 88 values of 1 / -1 / 0 per row. */
  dense: number[][];
  /** The 88 key labels, in row order. */
  columnHeaders: KeyLabel[];
  /** Start time of each frame, in seconds. */
  rowTimestamps: number[];
  /** Seconds per frame — used for the `[start - end]` label. */
  timeStepSeconds: number;
  /**
   * Two-hands view: a second dense grid. When given, `dense` is the right hand
   * and this is the left, and the two are coloured differently.
   */
  denseLeft?: number[][] | null;
  /** Scroll this frame into view when it changes. */
  focusFrame?: number | null;
  /** Called when a cell is clicked — the hook Story 7.4's editing will use. */
  onCellClick?: (frame: number, row: number) => void;
  height?: number;
}

const COLUMN_WIDTH = 26;
const ROW_HEIGHT = 26;
const LABEL_WIDTH = 168;
const HEADER_HEIGHT = 62;
const CIRCLE_RADIUS = 7;
/** Rows drawn beyond the viewport, so scrolling never reveals a blank band. */
const OVERSCAN = 12;

/** Black keys get a darker column so the keyboard is readable at a glance. */
function isBlackKey(label: KeyLabel): boolean {
  return label.es.includes("#");
}

export function MatrixGrid({
  dense,
  columnHeaders,
  rowTimestamps,
  timeStepSeconds,
  denseLeft,
  focusFrame,
  onCellClick,
  height = 620,
}: MatrixGridProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const frameCount = dense.length;
  const twoHands = Boolean(denseLeft);

  // Only the visible slice is rendered; spacers stand in for the rest.
  const first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const last = Math.min(
    frameCount,
    Math.ceil((scrollTop + height) / ROW_HEIGHT) + OVERSCAN,
  );
  const visible = useMemo(
    () => Array.from({ length: Math.max(0, last - first) }, (_, index) => first + index),
    [first, last],
  );

  const onScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  useEffect(() => {
    if (focusFrame === null || focusFrame === undefined) return;
    const element = scrollRef.current;
    if (!element) return;
    // Put the target a third of the way down, not flush at the top edge.
    element.scrollTo({ top: Math.max(0, focusFrame * ROW_HEIGHT - height / 3), behavior: "smooth" });
  }, [focusFrame, height]);

  const gridWidth = columnHeaders.length * COLUMN_WIDTH;

  /** Colour for a cell, given its value and which hand it came from. */
  const cellColor = (value: number, hand: GridHand): string => {
    const colors = handColors(hand);
    return value === 1 ? colors.onset : colors.sustain;
  };

  const renderRow = (frame: number) => {
    const cells: React.ReactNode[] = [];

    const draw = (grid: number[][], hand: GridHand) => {
      const row = grid[frame];
      if (!row) return;
      for (let key = 0; key < row.length; key += 1) {
        const value = row[key];
        if (value === 0) continue;

        const x = key * COLUMN_WIDTH + COLUMN_WIDTH / 2;
        const color = cellColor(value, hand);
        // A tail connects to the cell above whenever this one is a sustain.
        const continues = value === -1 && (grid[frame - 1]?.[key] ?? 0) !== 0;

        cells.push(
          <g key={`${hand}-${key}`}>
            {continues ? (
              <line
                x1={x}
                y1={0}
                x2={x}
                y2={ROW_HEIGHT / 2 - CIRCLE_RADIUS}
                stroke={handColors(hand).sustain}
                strokeWidth={2}
              />
            ) : null}
            {/* A note that carries on drops a line towards the next row. */}
            {(grid[frame + 1]?.[key] ?? 0) === -1 ? (
              <line
                x1={x}
                y1={ROW_HEIGHT / 2 + CIRCLE_RADIUS}
                x2={x}
                y2={ROW_HEIGHT}
                stroke={handColors(hand).sustain}
                strokeWidth={2}
              />
            ) : null}
            <circle
              cx={x}
              cy={ROW_HEIGHT / 2}
              r={CIRCLE_RADIUS}
              fill={color}
              stroke={value === 1 ? "none" : grays.slate}
              strokeWidth={0.5}
              style={onCellClick ? { cursor: "pointer" } : undefined}
              onClick={onCellClick ? () => onCellClick(frame, key) : undefined}
            />
          </g>,
        );
      }
    };

    if (twoHands && denseLeft) {
      draw(denseLeft, "left");
      draw(dense, "right");
    } else {
      draw(dense, "single");
    }

    return cells;
  };

  const start = rowTimestamps[0] ?? 0;

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
      {/* Frozen header: the key names stay put while time scrolls past. */}
      <Box sx={{ display: "flex", borderBottom: 1, borderColor: "divider" }}>
        <Box
          sx={{
            width: LABEL_WIDTH,
            flexShrink: 0,
            height: HEADER_HEIGHT,
            display: "flex",
            alignItems: "flex-end",
            px: 1,
            pb: 0.5,
            borderRight: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
          }}
        >
          <Typography variant="caption" color="text.secondary">
            frame [start – end]
          </Typography>
        </Box>
        <Box
          id="matrix-header-scroll"
          sx={{ overflow: "hidden", flexGrow: 1, backgroundColor: "background.paper" }}
        >
          <svg width={gridWidth} height={HEADER_HEIGHT} style={{ display: "block" }}>
            {columnHeaders.map((label, key) => {
              const x = key * COLUMN_WIDTH + COLUMN_WIDTH / 2;
              return (
                <g key={label.row}>
                  {isBlackKey(label) ? (
                    <rect
                      x={key * COLUMN_WIDTH}
                      y={0}
                      width={COLUMN_WIDTH}
                      height={HEADER_HEIGHT}
                      fill={grays.charcoal}
                    />
                  ) : null}
                  {/* Spanish name, rotated so the columns can stay narrow. */}
                  <text
                    x={x}
                    y={HEADER_HEIGHT - 20}
                    fill={grays.silver}
                    fontSize={9}
                    textAnchor="start"
                    transform={`rotate(-90 ${x} ${HEADER_HEIGHT - 20})`}
                  >
                    {label.es}
                  </text>
                  <text
                    x={x}
                    y={HEADER_HEIGHT - 5}
                    fill={grays.paper}
                    fontSize={9}
                    textAnchor="middle"
                  >
                    {label.en}
                  </text>
                </g>
              );
            })}
          </svg>
        </Box>
      </Box>

      <Box
        ref={scrollRef}
        onScroll={onScroll}
        sx={{ display: "flex", height, overflow: "auto", position: "relative" }}
      >
        {/* Row labels, pinned to the left while the keys scroll sideways. */}
        <Box
          sx={{
            width: LABEL_WIDTH,
            flexShrink: 0,
            position: "sticky",
            left: 0,
            zIndex: 2,
            borderRight: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
          }}
        >
          <Box sx={{ height: first * ROW_HEIGHT }} />
          {visible.map((frame) => {
            const from = rowTimestamps[frame] ?? start + frame * timeStepSeconds;
            return (
              <Box
                key={frame}
                sx={{
                  height: ROW_HEIGHT,
                  display: "flex",
                  alignItems: "center",
                  px: 1,
                  borderBottom: "1px solid",
                  borderColor: grays.charcoal,
                }}
              >
                <Typography
                  variant="caption"
                  sx={{ fontFamily: "monospace", fontSize: 11, color: grays.silver }}
                >
                  f: {frame} [{formatTime(from)} – {formatTime(from + timeStepSeconds)}]
                </Typography>
              </Box>
            );
          })}
          <Box sx={{ height: Math.max(0, (frameCount - last) * ROW_HEIGHT) }} />
        </Box>

        <Box sx={{ position: "relative" }}>
          <Box sx={{ height: first * ROW_HEIGHT }} />
          {visible.map((frame) => (
            <svg
              key={frame}
              width={gridWidth}
              height={ROW_HEIGHT}
              style={{ display: "block" }}
              role="row"
              aria-rowindex={frame + 1}
            >
              {/* Column separators and black-key shading. */}
              {columnHeaders.map((label, key) => (
                <g key={label.row}>
                  {isBlackKey(label) ? (
                    <rect
                      x={key * COLUMN_WIDTH}
                      y={0}
                      width={COLUMN_WIDTH}
                      height={ROW_HEIGHT}
                      fill={grays.charcoal}
                      opacity={0.5}
                    />
                  ) : null}
                  <line
                    x1={key * COLUMN_WIDTH}
                    y1={0}
                    x2={key * COLUMN_WIDTH}
                    y2={ROW_HEIGHT}
                    stroke={grays.charcoal}
                    strokeWidth={0.5}
                  />
                </g>
              ))}
              <line
                x1={0}
                y1={ROW_HEIGHT - 0.5}
                x2={gridWidth}
                y2={ROW_HEIGHT - 0.5}
                stroke={grays.charcoal}
                strokeWidth={1}
              />
              {renderRow(frame)}
            </svg>
          ))}
          <Box sx={{ height: Math.max(0, (frameCount - last) * ROW_HEIGHT) }} />
        </Box>
      </Box>

      <Box
        sx={{
          display: "flex",
          gap: 2,
          px: 1.5,
          py: 0.75,
          borderTop: 1,
          borderColor: "divider",
          flexWrap: "wrap",
        }}
      >
        <Legend color={twoHands ? semantic.rightHand.onset : semantic.matrixOneHand.onset}
          label={twoHands ? "right hand — struck" : "struck"} />
        <Legend color={twoHands ? semantic.rightHand.sustain : semantic.matrixOneHand.sustain}
          label={twoHands ? "right hand — held" : "held"} />
        {twoHands ? (
          <>
            <Legend color={semantic.leftHand.onset} label="left hand — struck" />
            <Legend color={semantic.leftHand.sustain} label="left hand — held" />
          </>
        ) : null}
        <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
          {frameCount} frame{frameCount === 1 ? "" : "s"}
        </Typography>
      </Box>
    </Box>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      <Box sx={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: color }} />
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

export default MatrixGrid;
