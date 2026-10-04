/**
 * The notes of the piano roll visualization, kept in typed arrays (plan section 9.5).
 *
 * The old piano roll visualization is one SVG element per note, rebuilt by React many times per
 * second during playback. Here a note is one index into a set of typed arrays (one array per field,
 * the same layout as the columns the backend sends), and the canvas reads those arrays directly.
 * Nothing in this module is React state: the live stream adds notes to it between two animation
 * frames, and an edit fills it again, without any component rendering.
 *
 * Two indexes are built on demand, after a change, for the canvas and the pointer:
 *
 * - **by onset**, so the painter finds the notes of the visible time range with one binary search
 *   instead of looking at every note;
 * - **by key**, one list per key sorted by onset, so a click finds the rectangle under the pointer,
 *   and the same-key rule finds the neighbours of a note, with one binary search in one short list.
 *
 * A note has a stable `id` (the backend's, or a negative one for a note added on the page and not
 * saved yet). Its place in the arrays (its "slot") changes when another note is removed, so only
 * the id is kept outside this module.
 */

export const KEY_COUNT = 88;

/** `hand` values: the same order as the backend's `hand` field (plan section 6.2). */
export const HAND_NONE = 0;
export const HAND_RIGHT = 1;
export const HAND_LEFT = 2;

/** Still sounding in the live stream: drawn from its onset up to the transcription frontier. */
export const FLAG_OPEN = 1;
/** Its hand came from the quick rule for an added note, not from the hand split or a person. */
export const FLAG_GUESSED = 2;

/** The columns of `GET /pieces/{uuid}/notes`, and of the live stream's messages. */
export interface NoteColumns {
  id: readonly number[];
  key: readonly number[];
  onMs: readonly number[];
  lenMs: readonly number[];
  /** One character per note: `r`, `l` or `-`. */
  hand?: string;
}

export function handCode(char: string | undefined): number {
  return char === "r" ? HAND_RIGHT : char === "l" ? HAND_LEFT : HAND_NONE;
}

export function handChar(code: number): "r" | "l" | "-" {
  return code === HAND_RIGHT ? "r" : code === HAND_LEFT ? "l" : "-";
}

export class RollNotes {
  /** How many notes are held. Slots `0 .. count - 1` of every array are in use. */
  count = 0;
  id = new Int32Array(0);
  key = new Uint8Array(0);
  onMs = new Float64Array(0);
  lenMs = new Float64Array(0);
  hand = new Uint8Array(0);
  flags = new Uint8Array(0);
  /**
   * When the note appeared, as `performance.now()`, for the short reveal of a new rectangle (it
   * grows from left to right). 0: drawn at once, at its full length.
   */
  spawn = new Float64Array(0);
  /** Goes up by one on every change. */
  version = 0;

  private slots = new Map<number, number>();
  private listeners = new Set<() => void>();
  private indexedVersion = -1;
  /** Every slot, sorted by onset then key. */
  private order = new Int32Array(0);
  /** One list of slots per key, sorted by onset. */
  private byKey: Int32Array[] = [];
  /** The slots of the notes still open in the live stream. */
  private openSlots: number[] = [];
  /** The longest note, in ms, so a range query knows how far back a note can start. */
  private longest = 0;
  private lowest = -1;
  private highest = -1;

  // ------------------------------------------------------------------ changes

  /** Call `listener` after every change. Returns the function that stops it. */
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Say that a batch of changes is complete: the indexes are rebuilt and the listeners called. */
  commit(): void {
    this.version += 1;
    for (const listener of this.listeners) listener();
  }

  clear(): void {
    this.count = 0;
    this.slots.clear();
    this.longest = 0;
  }

  private grow(needed: number): void {
    if (needed <= this.id.length) return;
    const size = Math.max(needed, Math.ceil(this.id.length * 1.5), 256);
    const copy = <A extends Int32Array | Uint8Array | Float64Array>(from: A, make: (n: number) => A): A => {
      const to = make(size);
      to.set(from.subarray(0, this.count));
      return to;
    };
    this.id = copy(this.id, (n) => new Int32Array(n));
    this.key = copy(this.key, (n) => new Uint8Array(n));
    this.onMs = copy(this.onMs, (n) => new Float64Array(n));
    this.lenMs = copy(this.lenMs, (n) => new Float64Array(n));
    this.hand = copy(this.hand, (n) => new Uint8Array(n));
    this.flags = copy(this.flags, (n) => new Uint8Array(n));
    this.spawn = copy(this.spawn, (n) => new Float64Array(n));
  }

  /** Add a note, or change the note with this id. Returns its slot. Call {@link commit} after. */
  upsert(
    id: number,
    key: number,
    onMs: number,
    lenMs: number,
    hand = HAND_NONE,
    flags = 0,
    spawn = 0,
  ): number {
    let slot = this.slots.get(id);
    if (slot === undefined) {
      this.grow(this.count + 1);
      slot = this.count;
      this.count += 1;
      this.slots.set(id, slot);
      this.id[slot] = id;
    }
    this.key[slot] = key;
    this.onMs[slot] = onMs;
    this.lenMs[slot] = lenMs;
    this.hand[slot] = hand;
    this.flags[slot] = flags;
    this.spawn[slot] = spawn;
    if (lenMs > this.longest) this.longest = lenMs;
    return slot;
  }

  /** Remove the note with this id; the last note takes its slot. Call {@link commit} after. */
  remove(id: number): boolean {
    const slot = this.slots.get(id);
    if (slot === undefined) return false;
    const last = this.count - 1;
    if (slot !== last) {
      const moved = this.id[last]!;
      this.id[slot] = moved;
      this.key[slot] = this.key[last]!;
      this.onMs[slot] = this.onMs[last]!;
      this.lenMs[slot] = this.lenMs[last]!;
      this.hand[slot] = this.hand[last]!;
      this.flags[slot] = this.flags[last]!;
      this.spawn[slot] = this.spawn[last]!;
      this.slots.set(moved, slot);
    }
    this.slots.delete(id);
    this.count = last;
    return true;
  }

  /** Replace every note with the columns. Call {@link commit} after. */
  load(columns: NoteColumns, spawn = 0): void {
    this.clear();
    const n = columns.id.length;
    this.grow(n);
    for (let index = 0; index < n; index += 1) {
      this.upsert(
        columns.id[index]!,
        columns.key[index]!,
        columns.onMs[index]!,
        columns.lenMs[index]!,
        handCode(columns.hand?.[index]),
        0,
        spawn,
      );
    }
  }

  // ------------------------------------------------------------------ reading

  slotOf(id: number): number {
    return this.slots.get(id) ?? -1;
  }

  has(id: number): boolean {
    return this.slots.has(id);
  }

  /** Every id, in slot order. */
  ids(): number[] {
    return Array.from(this.id.subarray(0, this.count));
  }

  /** Where a note ends, in ms. An open note ends at `openUntilMs`. */
  endOf(slot: number, openUntilMs = 0): number {
    const on = this.onMs[slot]!;
    return (this.flags[slot]! & FLAG_OPEN) !== 0 ? Math.max(on, openUntilMs) : on + this.lenMs[slot]!;
  }

  private index(): void {
    if (this.indexedVersion === this.version && this.order.length === this.count) return;
    const count = this.count;
    const order = new Int32Array(count);
    for (let slot = 0; slot < count; slot += 1) order[slot] = slot;
    const on = this.onMs;
    const key = this.key;
    order.sort((a, b) => on[a]! - on[b]! || key[a]! - key[b]!);
    const buckets: number[][] = Array.from({ length: KEY_COUNT }, () => []);
    const open: number[] = [];
    let longest = 0;
    let lowest = KEY_COUNT;
    let highest = -1;
    for (let index = 0; index < count; index += 1) {
      const slot = order[index]!;
      const key = this.key[slot]!;
      buckets[key]?.push(slot);
      if (key < lowest) lowest = key;
      if (key > highest) highest = key;
      if ((this.flags[slot]! & FLAG_OPEN) !== 0) open.push(slot);
      else if (this.lenMs[slot]! > longest) longest = this.lenMs[slot]!;
    }
    this.order = order;
    this.byKey = buckets.map((bucket) => Int32Array.from(bucket));
    this.openSlots = open;
    this.longest = longest;
    this.lowest = highest < 0 ? -1 : lowest;
    this.highest = highest;
    this.indexedVersion = this.version;
  }

  /** The first position in `list` (slots sorted by onset) whose onset is `>= ms`. */
  private lowerBound(list: Int32Array, ms: number): number {
    let low = 0;
    let high = list.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.onMs[list[middle]!]! < ms) low = middle + 1;
      else high = middle;
    }
    return low;
  }

  /**
   * Call `visit` for every note that sounds inside `[fromMs, toMs]`, in onset order, and then for
   * the open notes. Only the notes of that range are looked at, whatever the length of the piece.
   */
  forEachIn(fromMs: number, toMs: number, openUntilMs: number, visit: (slot: number) => void): void {
    this.index();
    const order = this.order;
    for (let index = this.lowerBound(order, fromMs - this.longest); index < order.length; index += 1) {
      const slot = order[index]!;
      const on = this.onMs[slot]!;
      if (on > toMs) break;
      if ((this.flags[slot]! & FLAG_OPEN) !== 0) continue;
      if (on + this.lenMs[slot]! >= fromMs) visit(slot);
    }
    for (const slot of this.openSlots) {
      if (this.onMs[slot]! <= toMs && Math.max(this.onMs[slot]!, openUntilMs) >= fromMs) visit(slot);
    }
  }

  /**
   * The note of `key` under `ms`, or -1. `toleranceMs` widens every note on both sides, so a
   * rectangle a few pixels wide can still be picked. When two notes are close, the one whose body
   * holds `ms` wins, then the nearest.
   */
  hit(key: number, ms: number, toleranceMs = 0): number {
    this.index();
    const list = this.byKey[key];
    if (!list || list.length === 0) return -1;
    let best = -1;
    let bestDistance = Infinity;
    // Every candidate starts before `ms + tolerance`; walk back from there. The walk meets the
    // latest onset first, which wins a tie: it is the rectangle drawn on top.
    for (let index = this.lowerBound(list, ms + toleranceMs + 1e-9) - 1; index >= 0; index -= 1) {
      const slot = list[index]!;
      const on = this.onMs[slot]!;
      const end = this.endOf(slot);
      if (end + toleranceMs < ms) {
        // Notes of one key rarely overlap, so a note that ended before `ms` means the earlier
        // ones did too; the longest note bounds how far back an overlapping one could start.
        if (on + this.longest + toleranceMs < ms) break;
        continue;
      }
      const distance = ms < on ? on - ms : ms > end ? ms - end : 0;
      if (distance < bestDistance) {
        best = slot;
        bestDistance = distance;
      }
    }
    return best;
  }

  /** The ids of every note of `key`, in onset order. */
  idsOnKey(key: number): number[] {
    this.index();
    const list = this.byKey[key];
    return list ? Array.from(list, (slot) => this.id[slot]!) : [];
  }

  /** The ids of the notes with a key in `[lowKey, highKey]` that sound inside `[fromMs, toMs]`. */
  idsInBand(lowKey: number, highKey: number, fromMs: number, toMs: number): number[] {
    const found: number[] = [];
    this.forEachIn(fromMs, toMs, 0, (slot) => {
      const key = this.key[slot]!;
      if (key >= lowKey && key <= highKey) found.push(this.id[slot]!);
    });
    return found;
  }

  /** The slots of the notes sounding at `ms`: their onset is at or before it, their end after it. */
  soundingAt(ms: number, visit: (slot: number) => void): void {
    this.forEachIn(ms, ms, 0, (slot) => {
      if (this.onMs[slot]! <= ms && this.endOf(slot) > ms) visit(slot);
    });
  }

  /** The lowest and the highest key of any note, or `null` when there is none. */
  keyRange(): [number, number] | null {
    this.index();
    return this.highest < 0 ? null : [this.lowest, this.highest];
  }

  /** The time of the last note's end, in ms. */
  lastEnd(openUntilMs = 0): number {
    let last = 0;
    for (let slot = 0; slot < this.count; slot += 1) last = Math.max(last, this.endOf(slot, openUntilMs));
    return last;
  }
}
