/**
 * `/dev/roll-bench`: the two performance targets of the Notes tab, measured on synthetic notes
 * (implementation 08, plan section 9.5, Phase 7 Story 7.5). Development builds only.
 *
 * The real canvas (`PianoRollCanvas`) is driven by a scenario, and the page records the time
 * between two animation frames and the time each painted frame took. `scripts/bench-roll.mjs`
 * opens it in a headless Chromium and reads the result from `window.__rollBench`.
 *
 * - `?scenario=play`: 10,000 rectangles, playback followed at the default zoom (the playhead and the
 *   sounding notes on every frame, a page turn now and then).
 * - `?scenario=scroll`: 10,000 rectangles, the view moved on every frame (the notes of the view
 *   painted again on every frame).
 * - `?scenario=whole`: 10,000 rectangles, all of them in view, the view moved on every frame (every
 *   rectangle painted on every frame: the worst case).
 * - `?scenario=live`: a live transcription arriving at 100 chunk messages per second (`&rate=`),
 *   each parsed from JSON as the stream delivers it, 10 rectangles per message.
 * - `?scenario=idle`: the live view with no message at all, as a baseline of the browser itself.
 */

import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import PianoRollCanvas, { type RollHandle } from "../../components/notes/PianoRollCanvas";
import { LiveFeed, type ChunkMessage } from "../../notes/liveFeed";
import { RollNotes } from "../../notes/rollNotes";

type Scenario = "play" | "scroll" | "whole" | "live" | "idle";

const DURATION_MS = 200_000;
const RUN_MS = 6000;
const NO_SELECTION: ReadonlySet<number> = new Set();

/** A deterministic pseudo-random sequence, so every run draws the same notes. */
function random(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1_103_515_245 + 12_345) % 2_147_483_648;
    return state / 2_147_483_648;
  };
}

/** `count` notes spread over the piece, like a dense piano piece: 10,000 in 200 s is 50 per second. */
function synthetic(count: number): { id: number[]; key: number[]; onMs: number[]; lenMs: number[] } {
  const next = random(7);
  const columns = { id: [] as number[], key: [] as number[], onMs: [] as number[], lenMs: [] as number[] };
  for (let index = 0; index < count; index += 1) {
    columns.id.push(index);
    columns.key.push(15 + Math.floor(next() * 60));
    columns.onMs.push(Math.round((index / count) * (DURATION_MS - 2000)));
    columns.lenMs.push(60 + Math.round(next() * 900));
  }
  return columns;
}

function summary(values: number[]): { count: number; median: number; p95: number; max: number } {
  const sorted = [...values].sort((a, b) => a - b);
  const at = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] ?? 0;
  const round = (value: number) => Math.round(value * 100) / 100;
  return { count: values.length, median: round(at(0.5)), p95: round(at(0.95)), max: round(sorted[sorted.length - 1] ?? 0) };
}

declare global {
  interface Window {
    __rollBench?: unknown;
  }
}

export function RollBenchPage() {
  const params = new URLSearchParams(window.location.search);
  const scenario = (params.get("scenario") ?? "play") as Scenario;
  const count = Number(params.get("notes") ?? 10_000);
  const rate = Number(params.get("rate") ?? 100);
  const [roll] = useState(() => {
    const notes = new RollNotes();
    if (scenario !== "live") {
      notes.load(synthetic(count));
      notes.commit();
    }
    return notes;
  });
  const [feed] = useState(() => new LiveFeed());
  const [stats] = useState(() => ({ paintMs: [] as number[] }));
  const [playing, setPlaying] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [result, setResult] = useState<string>("running…");
  const handle = useRef<RollHandle | null>(null);

  useEffect(() => {
    window.__rollBench = undefined;
    const intervals: number[] = [];
    const longTasks: number[] = [];
    let observer: PerformanceObserver | null = null;
    try {
      observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) longTasks.push(entry.duration);
      });
      observer.observe({ type: "longtask", buffered: false });
    } catch {
      observer = null;
    }
    let frame = 0;
    let last = 0;
    let stop = false;
    let timer = 0;
    let sent = 0;
    const begin = window.setTimeout(() => {
      const t0 = performance.now();
      if (scenario === "play") {
        setStartedAt(t0);
        setPlaying(true);
      }
      if (scenario === "whole") handle.current?.showWhole();
      if (scenario === "live") {
        // 100 messages per second; each carries 10 closed rectangles and advances 200 ms of piece.
        const next = random(11);
        let id = 0;
        // A browser runs a timer at most every few ms, so each tick of 20 ms sends its share.
        const perTick = rate / 50;
        let owed = 0;
        const sendOne = () => {
          const upToMs = Math.min(DURATION_MS, (sent + 1) * 200);
          const closed = { id: [] as number[], key: [] as number[], onMs: [] as number[], lenMs: [] as number[] };
          for (let index = 0; index < 10; index += 1) {
            closed.id.push(id);
            closed.key.push(15 + Math.floor(next() * 60));
            closed.onMs.push(Math.max(0, upToMs - 200 + index * 20));
            closed.lenMs.push(60 + Math.round(next() * 400));
            id += 1;
          }
          const message: ChunkMessage = {
            type: "chunk",
            done: Math.floor(upToMs / 5000),
            total: DURATION_MS / 5000,
            upToMs,
            durationMs: DURATION_MS,
            open: { id: [id], key: [40], onMs: [upToMs - 50] },
            closed,
          };
          // As the stream delivers it: a string, parsed on arrival.
          feed.push(JSON.parse(JSON.stringify(message)) as ChunkMessage);
          sent += 1;
        };
        timer = window.setInterval(() => {
          owed += perTick;
          for (; owed >= 1; owed -= 1) sendOne();
        }, 20);
      }
      const tick = (now: number) => {
        if (last) intervals.push(now - last);
        last = now;
        if (scenario === "scroll" || scenario === "whole") handle.current?.panBy(scenario === "whole" ? 40 : 25);
        if (now - t0 < RUN_MS && !stop) {
          frame = requestAnimationFrame(tick);
          return;
        }
        window.clearInterval(timer);
        setPlaying(false);
        const refresh = summary(intervals).median;
        const report = {
          scenario,
          notes: scenario === "live" ? feed.notes : count,
          messages: scenario === "live" ? sent : undefined,
          messagesPerSecond: scenario === "live" ? Math.round((sent / RUN_MS) * 1000) : undefined,
          frameInterval: summary(intervals),
          fps: Math.round((intervals.length / RUN_MS) * 1000 * 10) / 10,
          // A frame is dropped when the gap is more than one and a half refreshes.
          dropped: intervals.filter((gap) => gap > refresh * 1.5).length,
          paintMs: summary(stats.paintMs),
          longTasks: longTasks.length,
          longestTaskMs: Math.round(Math.max(0, ...longTasks)),
        };
        window.__rollBench = report;
        setResult(JSON.stringify(report, null, 1));
      };
      frame = requestAnimationFrame(tick);
    }, 800);
    return () => {
      stop = true;
      window.clearTimeout(begin);
      window.clearInterval(timer);
      cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [scenario, count, rate, feed, stats]);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h3" sx={{ mb: 1 }}>{`Roll bench: ${scenario}`}</Typography>
      <PianoRollCanvas
        ref={handle}
        notes={roll}
        mode={scenario === "live" || scenario === "idle" ? "live" : "edit"}
        feed={scenario === "live" || scenario === "idle" ? feed : null}
        durationMs={DURATION_MS}
        selection={NO_SELECTION}
        cursorMs={0}
        playing={playing}
        position={() => (playing ? performance.now() - startedAt : 0)}
        onSeek={null}
        follow
        onFollowChange={() => undefined}
        stats={stats}
        height={640}
      />
      <Typography component="pre" data-bench-result sx={{ mt: 1, fontSize: 12 }}>
        {result}
      </Typography>
    </Box>
  );
}

export default RollBenchPage;
