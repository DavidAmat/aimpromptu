/**
 * The live transcription, between the progress stream and the canvas (plan sections 9.3 and 9.5).
 *
 * The backend sends a `chunk` message several times per 5-second chunk of audio. A fast GPU can
 * send many per second, and a page that reconnects receives every message of the job at once. If
 * each message were a React update, the page would render once per message. Instead the stream
 * puts each message in a queue ({@link LiveFeed.push}), and the canvas takes the whole queue once
 * per animation frame ({@link LiveFeed.drain}): the page paints at most once per screen refresh
 * however fast the notes arrive.
 *
 * The feed also keeps the **frontier**: how far into the piece the transcription has reached. The
 * chunks arrive in steps, so the frontier that is drawn moves smoothly toward the last reported
 * time instead of jumping, and the rectangles are drawn only up to it, so they grow from left to
 * right as the frontier passes, like the MuScriptor examples.
 */

import { FLAG_OPEN, HAND_NONE, type RollNotes } from "./rollNotes";

/** One `event: chunk` frame of `GET /matrix/progress/{jobId}` (Phase 4 report, section 2.3). */
export interface ChunkMessage {
  type: "chunk";
  /** Chunks finished so far, and chunks in the piece. */
  done: number;
  total: number;
  /** The furthest time the engine has reported, in ms of the piece. */
  upToMs: number;
  durationMs: number;
  /** Every rectangle still sounding: drawn up to the frontier until its end arrives. */
  open: { id: number[]; key: number[]; onMs: number[] };
  /** The rectangles that ended since the previous message. */
  closed: { id: number[]; key: number[]; onMs: number[]; lenMs: number[] };
}

export function isChunkMessage(value: unknown): value is ChunkMessage {
  if (typeof value !== "object" || value === null) return false;
  const message = value as Partial<ChunkMessage>;
  return message.type === "chunk" && typeof message.upToMs === "number" && !!message.closed && !!message.open;
}

/** How much of the remaining distance the drawn frontier covers on each frame. */
const FRONTIER_EASE = 0.14;
/** Weight of the latest chunk in the average time per chunk. */
const PACE_WEIGHT = 0.4;
/** Inside a chunk, the estimate never reaches the next chunk before its message arrives. */
const WITHIN_CHUNK_CAP = 0.95;
/** Before any chunk is measured, the estimate creeps toward the first chunk at this pace. */
const CREEP_MS = 3000;

/**
 * How far the transcription is, between two chunk messages.
 *
 * The chunks cover equal lengths of audio but not equal times on the GPU, so the pace is measured
 * here: an average of the time each chunk took, used to move the estimate forward inside the
 * current chunk and to say how long is left. The idea is the one of MuScriptor's own web page
 * (`web/src/progress.ts`).
 */
export class ProgressEstimator {
  private total = 0;
  private done = 0;
  private paceMs: number | null = null;
  private lastAt = 0;
  private started = false;

  reset(): void {
    this.total = 0;
    this.done = 0;
    this.paceMs = null;
    this.lastAt = 0;
    this.started = false;
  }

  /** A message said `done` of `total` chunks are finished, at time `now` (`performance.now()`). */
  anchor(done: number, total: number, now: number): void {
    this.total = total;
    if (this.started && done > this.done) {
      const perChunk = (now - this.lastAt) / (done - this.done);
      // Messages that arrive together (a page that reconnects) say nothing about the pace.
      if (perChunk > 5) {
        this.paceMs = this.paceMs === null ? perChunk : PACE_WEIGHT * perChunk + (1 - PACE_WEIGHT) * this.paceMs;
      }
    }
    if (!this.started || done > this.done) this.lastAt = now;
    this.done = Math.max(this.done, done);
    this.started = true;
  }

  /** 0 to 1, smoothed inside the current chunk. */
  fraction(now: number): number {
    if (!this.started || this.total <= 0) return 0;
    if (this.done >= this.total) return 1;
    const elapsed = now - this.lastAt;
    const within =
      this.paceMs !== null && this.paceMs > 0
        ? Math.min(elapsed / this.paceMs, WITHIN_CHUNK_CAP)
        : (1 - Math.exp(-elapsed / CREEP_MS)) * WITHIN_CHUNK_CAP;
    return Math.min((this.done + within) / this.total, 0.999);
  }

  /** The time left, in ms, or `null` while the pace is not known yet. */
  remainingMs(now: number): number | null {
    if (!this.started) return null;
    if (this.done >= this.total) return 0;
    if (this.paceMs === null) return null;
    return Math.max(0, this.paceMs * (this.total - this.done) - (now - this.lastAt));
  }
}

export class LiveFeed {
  readonly progress = new ProgressEstimator();
  /** The length of the piece, in ms, from the first message. */
  durationMs = 0;
  /** The furthest time the engine reported. */
  upToMs = 0;
  /** The frontier as drawn: it moves toward the target on each frame. */
  shownMs = 0;
  /** The `done` frame arrived: the frontier goes to the end and stays there. */
  finished = false;
  /** Messages received, for the page and the measurements. */
  received = 0;
  /** Notes received (each closed rectangle once). */
  notes = 0;

  private queue: ChunkMessage[] = [];
  private listeners = new Set<() => void>();
  /** The backend's clock (seconds) of the first and of the latest progress frame, for the time taken. */
  private firstStamp: number | null = null;
  private lastStamp: number | null = null;
  private lastStampAt = 0;

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private wake(): void {
    for (const listener of this.listeners) listener();
  }

  reset(): void {
    this.progress.reset();
    this.durationMs = 0;
    this.upToMs = 0;
    this.shownMs = 0;
    this.finished = false;
    this.received = 0;
    this.notes = 0;
    this.queue = [];
    this.firstStamp = null;
    this.lastStamp = null;
    this.wake();
  }

  /** A `chunk` message arrived. Nothing is drawn until the next animation frame. */
  push(message: ChunkMessage, now = performance.now()): void {
    this.queue.push(message);
    this.received += 1;
    if (message.durationMs > 0) this.durationMs = message.durationMs;
    this.progress.anchor(message.done, message.total, now);
    this.wake();
  }

  /** A progress frame arrived, with the backend's own clock in seconds: it measures the time taken. */
  stamp(seconds: number, now = performance.now()): void {
    if (this.firstStamp === null) this.firstStamp = seconds;
    this.lastStamp = seconds;
    this.lastStampAt = now;
  }

  /** The `done` frame arrived. */
  finish(): void {
    this.finished = true;
    this.wake();
  }

  /**
   * The time the transcription has taken so far, in seconds: from the backend's own clock, so a
   * page that connects late (or from another machine, with another clock) says the same.
   */
  elapsedSeconds(now = performance.now()): number | null {
    if (this.firstStamp === null || this.lastStamp === null) return null;
    const running = this.finished ? 0 : (now - this.lastStampAt) / 1000;
    return this.lastStamp - this.firstStamp + running;
  }

  /** Something is waiting in the queue. */
  get pending(): boolean {
    return this.queue.length > 0;
  }

  /**
   * Put every queued message into `roll`, then commit once. A rectangle that arrives already
   * closed is revealed from `now`; one that was open is only given its end.
   */
  drain(roll: RollNotes, now: number): boolean {
    if (this.queue.length === 0) return false;
    for (const message of this.queue) {
      const closed = message.closed;
      for (let index = 0; index < closed.id.length; index += 1) {
        const id = closed.id[index]!;
        const slot = roll.slotOf(id);
        const wasOpen = slot >= 0 && (roll.flags[slot]! & FLAG_OPEN) !== 0;
        if (slot < 0) this.notes += 1;
        roll.upsert(id, closed.key[index]!, closed.onMs[index]!, closed.lenMs[index]!, HAND_NONE, 0, wasOpen ? 0 : now);
      }
      const open = message.open;
      for (let index = 0; index < open.id.length; index += 1) {
        const id = open.id[index]!;
        if (roll.has(id)) continue;
        this.notes += 1;
        roll.upsert(id, open.key[index]!, open.onMs[index]!, 0, HAND_NONE, FLAG_OPEN, 0);
      }
      this.upToMs = Math.max(this.upToMs, message.upToMs);
    }
    this.queue = [];
    roll.commit();
    return true;
  }

  /** Move the drawn frontier one frame toward its target. `true` while it still moves. */
  step(now: number): boolean {
    const target = this.finished
      ? Math.max(this.durationMs, this.upToMs)
      : Math.max(this.upToMs, this.progress.fraction(now) * this.durationMs);
    const gap = target - this.shownMs;
    if (Math.abs(gap) < 2) {
      this.shownMs = target;
      return !this.finished;
    }
    this.shownMs += gap * FRONTIER_EASE;
    return true;
  }
}
