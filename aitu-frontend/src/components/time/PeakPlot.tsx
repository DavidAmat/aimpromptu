/**
 * The distribution of gaps between notes, with the piles drawn as clickable bands.
 *
 * This is the one picture the whole app now turns on. Every gap between two consecutive notes of a
 * hand is measured from the recording, and the piles are where the playing keeps landing. One of
 * them is the beat; the reader is the one who says which.
 *
 * The app deliberately does not choose. A beat and twice that beat explain the same gaps equally
 * well, so the question cannot be settled from the timings alone. What the picture can do is make
 * the answer obvious: a pile holding half the notes of a piece is hard to mistake.
 */

import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { surface, semantic } from "../../ui/palette";
import { FIGURE_LABELS, type LabelledPeak, type Peak } from "../../api";

export interface PeakPlotProps {
  peaks: Peak[];
  /** Present once a figure has been named, so each pile can show what it became. */
  labelled?: LabelledPeak[];
  /** The pile currently chosen, by its centre in milliseconds. */
  selectedMs?: number | null;
  onSelect?: (peak: Peak) => void;
  height?: number;
}

const AXIS_TICKS_MS = [0, 100, 200, 300, 400, 500, 600, 800, 1000, 1200];
const MAX_MS = 1200;
const PAD_LEFT = 8;
const PAD_RIGHT = 8;
const AXIS_HEIGHT = 34;
const BAR_WIDTH = 26;
/** One label is two lines: the gap, and its share with the figure it became. */
const LABEL_ROW_HEIGHT = 34;
/** Roughly how wide one character is at the sizes below, in the SVG's own units. */
const CHARACTER_WIDTH = 7.4;
const LABEL_GAP = 14;

export function PeakPlot({
  peaks,
  labelled,
  selectedMs = null,
  onSelect,
  height = 240,
}: PeakPlotProps) {
  if (!peaks.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No rhythm to read here yet. This piece has too few notes for the gaps
        between them to form anything.
      </Typography>
    );
  }

  const tallest = Math.max(...peaks.map((peak) => peak.share));
  const plotHeight = height - AXIS_HEIGHT;
  const nameOf = (peak: Peak) =>
    labelled?.find((entry) => entry.peak.centreMs === peak.centreMs)?.name;

  // Piles a fast piece produces sit close together — 60, 120 and 160 ms are only a few pixels
  // apart — so a label centred over each one runs into its neighbours and none of them can be
  // read. Labels that would collide are stacked instead, and the bars start below whatever depth
  // that takes.
  const rows = labelRows(peaks, (peak) => labelWidth(peak, nameOf(peak)));
  const bandHeight = (Math.max(...rows) + 1) * LABEL_ROW_HEIGHT;

  return (
    <Box>
      <Box
        component="svg"
        viewBox={`0 0 1000 ${height}`}
        sx={{ width: "100%", height, display: "block", userSelect: "none" }}
        role="group"
        aria-label="Gaps between notes"
      >
        {AXIS_TICKS_MS.map((tick) => {
          const x = xFor(tick);
          return (
            <g key={tick}>
              <line
                x1={x}
                x2={x}
                y1={0}
                y2={plotHeight}
                stroke={surface.line}
                strokeWidth={1}
              />
              <text
                x={x}
                y={plotHeight + 20}
                textAnchor="middle"
                fontSize={12}
                fill={surface.mutedText}
              >
                {tick}
              </text>
            </g>
          );
        })}
        <text
          x={xFor(MAX_MS)}
          y={plotHeight + 34}
          textAnchor="end"
          fontSize={11}
          fill={surface.mutedText}
        >
          milliseconds between one note and the next
        </text>
        <line
          x1={PAD_LEFT}
          x2={1000 - PAD_RIGHT}
          y1={plotHeight}
          y2={plotHeight}
          stroke={surface.strongLine}
          strokeWidth={1.5}
        />

        {peaks.map((peak, index) => {
          const selected =
            selectedMs !== null && Math.abs(peak.centreMs - selectedMs) < 0.5;
          // A fixed-width bar on the centre, not a block as wide as the pile. The width of a pile
          // says how loosely the playing landed, which is a different question from how often, and
          // drawing it as width makes a common gap look like a rare wide one.
          const centre = xFor(peak.centreMs);
          const left = centre - BAR_WIDTH / 2;
          const right = centre + BAR_WIDTH / 2;
          const barHeight = Math.max(
            6,
            (peak.share / tallest) * (plotHeight - bandHeight - 8),
          );
          const top = plotHeight - barHeight;
          const name = nameOf(peak);
          const labelTop = rows[index]! * LABEL_ROW_HEIGHT;
          return (
            <g
              key={peak.centreMs}
              onClick={() => onSelect?.(peak)}
              style={{ cursor: onSelect ? "pointer" : "default" }}
              role={onSelect ? "button" : undefined}
              aria-label={`${Math.round(peak.centreMs)} milliseconds, ${Math.round(peak.share * 100)} per cent of the notes`}
            >
              <rect
                x={centre - 26}
                width={52}
                y={0}
                height={plotHeight}
                fill="transparent"
              />
              <rect
                x={left}
                width={BAR_WIDTH}
                y={top}
                height={barHeight}
                rx={3}
                fill={
                  selected
                    ? semantic.rightHand.onset
                    : semantic.rightHand.sustain
                }
                stroke={selected ? semantic.rightHand.onset : surface.line}
                strokeWidth={selected ? 2 : 1}
              />
              <line
                x1={(left + right) / 2}
                x2={(left + right) / 2}
                y1={labelTop + LABEL_ROW_HEIGHT - 6}
                y2={top}
                stroke={surface.line}
                strokeWidth={1}
              />
              <text
                x={(left + right) / 2}
                y={labelTop + 13}
                textAnchor="middle"
                fontSize={14}
                fontWeight={selected ? 700 : 500}
                fill={surface.text}
              >
                {Math.round(peak.centreMs)} ms
              </text>
              <text
                x={(left + right) / 2}
                y={labelTop + 27}
                textAnchor="middle"
                fontSize={12}
                fill={surface.mutedText}
              >
                {Math.round(peak.share * 100)}% {name ? `· ${name}` : ""}
              </text>
            </g>
          );
        })}
      </Box>

      <Stack
        direction="row"
        spacing={2}
        sx={{ flexWrap: "wrap", rowGap: 0.5, mt: 1 }}
      >
        {peaks.map((peak) => {
          const entry = labelled?.find(
            (item) => item.peak.centreMs === peak.centreMs,
          );
          return (
            <Typography
              key={peak.centreMs}
              variant="caption"
              color="text.secondary"
            >
              <strong>{Math.round(peak.centreMs)} ms</strong> · {peak.count}{" "}
              notes
              {entry
                ? ` · ${entry.tresilloOf ? entry.name : FIGURE_LABELS[entry.figure]} (${entry.percentOff.toFixed(0)}% off)`
                : ""}
            </Typography>
          );
        })}
      </Stack>
    </Box>
  );
}

/**
 * Which row each label goes on, so no two overlap.
 *
 * Left to right, each label takes the topmost row whose last label it clears. Two piles far apart
 * both stay on the top row; a cluster fans downwards. Nothing is hidden — a label a reader cannot
 * find is worse than a tall plot.
 */
function labelRows(peaks: Peak[], widthOf: (peak: Peak) => number): number[] {
  const lastRight: number[] = [];
  return peaks.map((peak) => {
    const half = widthOf(peak) / 2;
    const centre = xFor(peak.centreMs);
    let row = 0;
    while ((lastRight[row] ?? -Infinity) > centre - half) row += 1;
    lastRight[row] = centre + half + LABEL_GAP;
    return row;
  });
}

function labelWidth(peak: Peak, name?: string): number {
  const top = `${Math.round(peak.centreMs)} ms`;
  const bottom = `${Math.round(peak.share * 100)}%${name ? ` · ${name}` : ""}`;
  return Math.max(top.length, bottom.length) * CHARACTER_WIDTH;
}

function xFor(ms: number): number {
  const usable = 1000 - PAD_LEFT - PAD_RIGHT;
  return PAD_LEFT + (Math.min(ms, MAX_MS) / MAX_MS) * usable;
}

export default PeakPlot;
