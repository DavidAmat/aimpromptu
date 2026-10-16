/**
 * The chart history of a public song as one line: its place each week, place 1 at the top and
 * place 100 at the bottom, over time (implementation 02, Phase 13, plan section 15.3, "Rankings").
 *
 * The line breaks where the song left the chart for more than three weeks, so a song that charted
 * again years later ("Billie Jean" in 1983 and in 2009) shows two runs, not one line across the
 * gap. The best place is marked with a dot. The numbers the line shows are also written beside it
 * (best place, weeks, first and last week) and in its label, so nothing depends on reading a curve.
 */

import { useCallback, useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { PublicChart } from "../../api";
import { monthYear } from "./shared";

/** The widest the line is drawn; narrower, it is drawn at the width it has, so its words keep their size. */
const MAX_WIDTH = 640;
const HEIGHT = 112;
const LEFT = 28;
const RIGHT = 8;
const TOP = 8;
const BOTTOM = 20;
const DAY = 86_400_000;

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 15, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>{value}</Typography>
    </Box>
  );
}

export function ChartHistory({ chart }: { chart: PublicChart }) {
  const [width, setWidth] = useState(MAX_WIDTH);
  const measured = useCallback((element: HTMLDivElement | null) => {
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.min(MAX_WIDTH, Math.max(200, Math.round(entry.contentRect.width)))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const WIDTH = width;
  const times = chart.history.map(([week]) => Date.parse(week));
  const start = times[0];
  const end = times[times.length - 1];
  const span = Math.max(end - start, 7 * DAY);
  const size = Math.max(100, ...chart.history.map(([, rank]) => rank));
  const x = (time: number) => LEFT + ((time - start) / span) * (WIDTH - LEFT - RIGHT);
  const y = (rank: number) => TOP + ((rank - 1) / (size - 1)) * (HEIGHT - TOP - BOTTOM);

  // One path, broken where the song was off the chart for more than three weeks.
  let path = "";
  chart.history.forEach(([, rank], index) => {
    const gap = index > 0 && times[index] - times[index - 1] > 21 * DAY;
    path += `${index === 0 || gap ? "M" : "L"}${x(times[index]).toFixed(1)},${y(rank).toFixed(1)}`;
  });
  const bestIndex = chart.history.findIndex(([, rank]) => rank === chart.best);
  const firstYear = Number(chart.first.slice(0, 4));
  const lastYear = Number(chart.last.slice(0, 4));
  const label = `Best place ${chart.best}, ${chart.weeks} weeks on the chart, from ${monthYear(chart.first)} to ${monthYear(chart.last)}`;

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" useFlexGap spacing={4} sx={{ flexWrap: "wrap", rowGap: 1 }}>
        <Fact label="Best place" value={String(chart.best)} />
        <Fact label="Weeks on the chart" value={String(chart.weeks)} />
        <Fact
          label="When"
          value={chart.first === chart.last ? monthYear(chart.first) : `${monthYear(chart.first)} – ${monthYear(chart.last)}`}
        />
      </Stack>
      <Box ref={measured} sx={{ width: "100%", maxWidth: MAX_WIDTH }}>
      <Box
        component="svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={label}
        data-testid="chart-history"
        sx={{ width: WIDTH, height: "auto", display: "block", color: "text.primary", overflow: "visible" }}
      >
        {[1, 50, 100].filter((rank) => rank <= size).map((rank) => (
          <g key={rank}>
            <line x1={LEFT} x2={WIDTH - RIGHT} y1={y(rank)} y2={y(rank)} stroke="currentColor" strokeOpacity={0.12} />
            <text x={LEFT - 6} y={y(rank) + 4} textAnchor="end" fontSize={11} fill="currentColor" fillOpacity={0.55}>
              {rank}
            </text>
          </g>
        ))}
        <path d={path} fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />
        {bestIndex >= 0 ? <circle cx={x(times[bestIndex])} cy={y(chart.best)} r={3.5} fill="currentColor" /> : null}
        <text x={LEFT} y={HEIGHT - 4} fontSize={11} fill="currentColor" fillOpacity={0.55}>
          {firstYear}
        </text>
        {lastYear !== firstYear ? (
          <text x={WIDTH - RIGHT} y={HEIGHT - 4} textAnchor="end" fontSize={11} fill="currentColor" fillOpacity={0.55}>
            {lastYear}
          </text>
        ) : null}
      </Box>
      </Box>
    </Stack>
  );
}

export default ChartHistory;
