/**
 * The edits of the Notes tab, as changes on top of the saved notes (plan sections 6.4 and 9.5).
 *
 * The page loads the saved notes once (the **base**) and never changes them. Every edit is written
 * as an **override**: the note with that id as the page now has it. A note added on the page gets
 * a negative id until it is saved. A deleted note stays in the overrides with `deleted: true`, so
 * its place is known if it is put back.
 *
 * This makes three things cheap, whatever the length of the piece:
 *
 * - **Undo and redo.** One step of `useEditHistory` is one set of overrides, which holds only the
 *   notes that changed, not a copy of the piece.
 * - **Unsaved changes.** The page compares the overrides it has with the ones last saved.
 * - **Save.** The difference becomes the list of operations of `PATCH /pieces/{uuid}/notes`
 *   (`move`, `delete`, `restore`, `add`, `hand`), never the whole piece.
 *
 * **One key sounds one note at a time.** After an edit, on every key it touched, a note that runs
 * into the next onset of its key is shortened to that onset, as the backend does (Phase 5 report,
 * section 2.6). Two notes of one key that start at the same time are refused.
 *
 * Pure functions, so `npm run check:notes` checks them without a browser.
 */

import type { NotesOperation, PieceNotes } from "../api";
import { FLAG_GUESSED, handCode, type RollNotes } from "./rollNotes";

export type Hand = "r" | "l" | "-";

export interface Note {
  key: number;
  onMs: number;
  lenMs: number;
  hand: Hand;
  deleted?: boolean;
}

/** The saved notes as the page loaded them. */
export interface NotesBase {
  durationMs: number;
  notes: ReadonlyMap<number, Note>;
  /** The ids whose hand came from the quick rule. */
  guessed: ReadonlySet<number>;
}

/** The page's changes to the base, by id. A negative id is a note added on the page. */
export type Overrides = ReadonlyMap<number, Note>;
export const NO_OVERRIDES: Overrides = new Map();

/** The length of a rectangle added with a double-click. */
export const ADDED_LENGTH_MS = 250;
/** The shortest rectangle an edit can make: one time frame. */
export const MIN_LENGTH_MS = 10;
/** Two onsets of one key closer than this are the same onset (the backend's `SAME_ONSET_MS`). */
const SAME_ONSET_MS = 0.5;

export function baseOf(columns: PieceNotes): NotesBase {
  const notes = new Map<number, Note>();
  for (let index = 0; index < columns.id.length; index += 1) {
    const hand = columns.hand[index];
    notes.set(columns.id[index]!, {
      key: columns.key[index]!,
      onMs: columns.onMs[index]!,
      lenMs: columns.lenMs[index]!,
      hand: hand === "r" || hand === "l" ? hand : "-",
    });
  }
  return { durationMs: columns.durationMs, notes, guessed: new Set(columns.guessed) };
}

/** The note with this id as `over` has it (deleted or not), or `undefined` when there is none. */
export function noteOf(base: NotesBase, over: Overrides, id: number): Note | undefined {
  return over.get(id) ?? (id >= 0 ? base.notes.get(id) : undefined);
}

export function isLive(note: Note | undefined): note is Note {
  return note !== undefined && !note.deleted;
}

function sameSpan(a: Note, b: Note): boolean {
  return a.key === b.key && a.onMs === b.onMs && a.lenMs === b.lenMs;
}

/** Both absent or deleted, or both live with the same key, times and hand. */
export function sameNote(a: Note | undefined, b: Note | undefined): boolean {
  if (!isLive(a) || !isLive(b)) return isLive(a) === isLive(b);
  return sameSpan(a, b) && a.hand === b.hand;
}

/** How many live notes `base` with `over` has. */
export function liveCount(base: NotesBase, over: Overrides): number {
  let count = base.notes.size;
  for (const [id, note] of over) {
    const inBase = base.notes.has(id);
    if (inBase && note.deleted) count -= 1;
    else if (!inBase && !note.deleted) count += 1;
  }
  return count;
}

/** Put the live notes of `base` with `over` into the roll, then commit once. */
export function fillRoll(roll: RollNotes, base: NotesBase, over: Overrides): void {
  roll.clear();
  for (const [id, note] of base.notes) {
    if (over.has(id)) continue;
    roll.upsert(id, note.key, note.onMs, note.lenMs, handCode(note.hand), base.guessed.has(id) ? FLAG_GUESSED : 0);
  }
  for (const [id, note] of over) {
    if (note.deleted) continue;
    // A guessed hand stays marked only while nobody gave the note another hand.
    const guessed = base.guessed.has(id) && note.hand === base.notes.get(id)?.hand;
    roll.upsert(id, note.key, note.onMs, note.lenMs, handCode(note.hand), guessed ? FLAG_GUESSED : 0);
  }
  roll.commit();
}

// ---------------------------------------------------------------------- the edits

export interface EditContext {
  base: NotesBase;
  over: Overrides;
  /** The ids of the live notes of a key, as the page draws them now (before this edit). */
  idsOnKey: (key: number) => Iterable<number>;
}

export interface EditResult {
  /** The new overrides; the same object when the edit changed nothing. */
  over: Overrides;
  /** Why the edit was refused, in words; `over` is then unchanged. */
  refused: string | null;
}

const unchanged = (context: EditContext, refused: string | null = null): EditResult => ({
  over: context.over,
  refused,
});

/**
 * Apply the same-key rule on the keys the `touched` notes are on now. A note that runs into the
 * next onset of its key is shortened to it, but only in a pair where one of the two notes was
 * touched, so overlaps already in an old piece stay as they are.
 */
function sameKeyRule(context: EditContext, next: Map<number, Note>, touched: ReadonlySet<number>): string | null {
  const keys = new Set<number>();
  for (const id of touched) {
    const note = noteOf(context.base, next, id);
    if (isLive(note)) keys.add(note.key);
  }
  for (const key of keys) {
    const ids = new Set<number>(context.idsOnKey(key));
    for (const id of touched) ids.add(id);
    const row: { id: number; note: Note }[] = [];
    for (const id of ids) {
      const note = noteOf(context.base, next, id);
      if (isLive(note) && note.key === key) row.push({ id, note });
    }
    row.sort((a, b) => a.note.onMs - b.note.onMs);
    for (let index = 0; index + 1 < row.length; index += 1) {
      const a = row[index]!;
      const b = row[index + 1]!;
      if (!touched.has(a.id) && !touched.has(b.id)) continue;
      if (Math.abs(a.note.onMs - b.note.onMs) < SAME_ONSET_MS) {
        return "Two notes of one key cannot start at the same time. Move it a little earlier or later.";
      }
      if (a.note.onMs + a.note.lenMs > b.note.onMs) {
        const shortened = { ...a.note, lenMs: b.note.onMs - a.note.onMs };
        next.set(a.id, shortened);
        a.note = shortened;
      }
    }
  }
  return null;
}

/** Move `ids` by `dMs` and `dKey`, kept inside the piece and the keyboard. */
export function moveNotes(context: EditContext, ids: Iterable<number>, dMs: number, dKey: number): EditResult {
  const { base, over } = context;
  const live: [number, Note][] = [];
  for (const id of ids) {
    const note = noteOf(base, over, id);
    if (isLive(note)) live.push([id, note]);
  }
  if (live.length === 0) return unchanged(context);
  let low = -Infinity;
  let high = Infinity;
  let lowKey = -Infinity;
  let highKey = Infinity;
  for (const [, note] of live) {
    low = Math.max(low, -note.onMs);
    high = Math.min(high, base.durationMs - (note.onMs + note.lenMs));
    lowKey = Math.max(lowKey, -note.key);
    highKey = Math.min(highKey, 87 - note.key);
  }
  const shift = Math.min(Math.max(dMs, low), Math.max(high, low));
  const keys = Math.min(Math.max(dKey, lowKey), highKey);
  if (shift === 0 && keys === 0) return unchanged(context);
  const next = new Map(over);
  const touched = new Set<number>();
  for (const [id, note] of live) {
    next.set(id, { ...note, onMs: note.onMs + shift, key: note.key + keys });
    touched.add(id);
  }
  const refused = sameKeyRule(context, next, touched);
  return refused ? unchanged(context, refused) : { over: next, refused: null };
}

/** Give one note a new onset and length (a drag of its left or right edge). */
export function resizeNote(context: EditContext, id: number, onMs: number, lenMs: number): EditResult {
  const note = noteOf(context.base, context.over, id);
  if (!isLive(note)) return unchanged(context);
  const on = Math.max(0, onMs);
  const length = Math.max(MIN_LENGTH_MS, Math.min(lenMs, context.base.durationMs - on));
  if (on === note.onMs && length === note.lenMs) return unchanged(context);
  const next = new Map(context.over);
  next.set(id, { ...note, onMs: on, lenMs: length });
  const refused = sameKeyRule(context, next, new Set([id]));
  return refused ? unchanged(context, refused) : { over: next, refused: null };
}

export function deleteNotes(context: EditContext, ids: Iterable<number>): EditResult {
  let next: Map<number, Note> | null = null;
  for (const id of ids) {
    const note = noteOf(context.base, context.over, id);
    if (!isLive(note)) continue;
    next ??= new Map(context.over);
    next.set(id, { ...note, deleted: true });
  }
  return next ? { over: next, refused: null } : unchanged(context);
}

/** The id for the next note added on the page: below every id used so far. */
export function nextTempId(over: Overrides, used: Iterable<number> = []): number {
  let lowest = 0;
  for (const id of over.keys()) lowest = Math.min(lowest, id);
  for (const id of used) lowest = Math.min(lowest, id);
  return lowest - 1;
}

/** Add a rectangle of `lenMs` on `key` at `onMs`, shortened to the next onset of its key. */
export function addNote(
  context: EditContext,
  tempId: number,
  key: number,
  onMs: number,
  lenMs = ADDED_LENGTH_MS,
): EditResult {
  const on = Math.max(0, Math.min(onMs, context.base.durationMs - MIN_LENGTH_MS));
  const length = Math.max(MIN_LENGTH_MS, Math.min(lenMs, context.base.durationMs - on));
  const next = new Map(context.over);
  next.set(tempId, { key, onMs: on, lenMs: length, hand: "-" });
  const refused = sameKeyRule(context, next, new Set([tempId]));
  return refused ? unchanged(context, refused) : { over: next, refused: null };
}

// ---------------------------------------------------------------------- hands

/** Give `ids` to one hand: the whole rectangle moves from one hand matrix to the other. */
export function setHands(context: EditContext, ids: Iterable<number>, hand: "r" | "l"): EditResult {
  let next: Map<number, Note> | null = null;
  for (const id of ids) {
    const note = noteOf(context.base, context.over, id);
    if (!isLive(note) || note.hand === hand) continue;
    next ??= new Map(context.over);
    next.set(id, { ...note, hand });
  }
  return next ? { over: next, refused: null } : unchanged(context);
}

/**
 * Lay the answer of **Predict hands** over the page's notes, as unsaved changes. The answer names
 * the notes by their backend id; `idMap` turns an added and saved note back into the page's id. A
 * note the split could not place (`-`) keeps the hand it has: there is nothing to save for it.
 */
export function applyPrediction(
  context: EditContext,
  answer: { id: readonly number[]; hand: string },
  idMap: ReadonlyMap<number, number>,
): EditResult {
  const pageId = new Map<number, number>();
  for (const [temp, real] of idMap) pageId.set(real, temp);
  let next: Map<number, Note> | null = null;
  for (let index = 0; index < answer.id.length; index += 1) {
    const hand = answer.hand[index];
    if (hand !== "r" && hand !== "l") continue;
    const id = pageId.get(answer.id[index]!) ?? answer.id[index]!;
    const note = noteOf(context.base, next ?? context.over, id);
    if (!isLive(note) || note.hand === hand) continue;
    next ??= new Map(context.over);
    next.set(id, { ...note, hand });
  }
  return next ? { over: next, refused: null } : unchanged(context);
}

/** The live notes with no hand, in onset order: the ones drawn red on the Hands tab. */
export function idsWithoutHand(base: NotesBase, over: Overrides): number[] {
  const found: { id: number; onMs: number }[] = [];
  for (const [id, note] of base.notes) {
    if (!over.has(id) && note.hand === "-") found.push({ id, onMs: note.onMs });
  }
  for (const [id, note] of over) {
    if (!note.deleted && note.hand === "-") found.push({ id, onMs: note.onMs });
  }
  return found.sort((a, b) => a.onMs - b.onMs).map((note) => note.id);
}

/** Whether any live note has a hand: the piano roll visualization can then colour by hand. */
export function anyHand(base: NotesBase, over: Overrides): boolean {
  for (const [id, note] of base.notes) if (!over.has(id) && note.hand !== "-") return true;
  for (const note of over.values()) if (!note.deleted && note.hand !== "-") return true;
  return false;
}

// ---------------------------------------------------------------------- unsaved and save

export interface ChangeCount {
  moved: number;
  deleted: number;
  added: number;
  hands: number;
}

/** What `present` changed against `saved`, note by note. */
export function countChanges(base: NotesBase, saved: Overrides, present: Overrides): ChangeCount {
  const count: ChangeCount = { moved: 0, deleted: 0, added: 0, hands: 0 };
  for (const id of new Set([...saved.keys(), ...present.keys()])) {
    const before = noteOf(base, saved, id);
    const after = noteOf(base, present, id);
    if (sameNote(before, after)) continue;
    if (!isLive(before)) count.added += 1;
    else if (!isLive(after)) count.deleted += 1;
    else {
      if (!sameSpan(before, after)) count.moved += 1;
      if (before.hand !== after.hand) count.hands += 1;
    }
  }
  return count;
}

/** "3 notes moved, 1 deleted", the words of the save bar; `null` when nothing is unsaved. */
export function describeChanges(count: ChangeCount): string | null {
  const parts: string[] = [];
  const notes = (n: number) => (n === 1 ? "1 note" : `${n} notes`);
  if (count.moved) parts.push(`${notes(count.moved)} moved`);
  if (count.deleted) parts.push(`${parts.length ? count.deleted : notes(count.deleted)} deleted`);
  if (count.added) parts.push(`${parts.length ? count.added : notes(count.added)} added`);
  if (count.hands) parts.push(`${parts.length ? count.hands : notes(count.hands)} with another hand`);
  return parts.length ? `Unsaved: ${parts.join(", ")}` : null;
}

/**
 * The operations that turn the saved notes into the page's notes.
 *
 * `idMap` gives the backend id of every note added on the page and already saved. A note put back
 * after its deletion was saved is a `restore`, followed by a `move` when it also moved.
 */
export function toOperations(
  base: NotesBase,
  saved: Overrides,
  present: Overrides,
  idMap: ReadonlyMap<number, number>,
): NotesOperation[] {
  const restore: number[] = [];
  const moves: NotesOperation[] = [];
  const remove: number[] = [];
  const adds: NotesOperation[] = [];
  const hands: Record<"r" | "l", number[]> = { r: [], l: [] };
  const ids = [...new Set([...saved.keys(), ...present.keys()])].sort((a, b) => a - b);
  for (const id of ids) {
    const before = noteOf(base, saved, id);
    const after = noteOf(base, present, id);
    if (sameNote(before, after)) continue;
    const real = id >= 0 ? id : idMap.get(id);
    if (real === undefined) {
      // Never saved: an add, or nothing when it was deleted again.
      if (isLive(after)) {
        adds.push({
          op: "add",
          tempId: id,
          key: after.key,
          onMs: after.onMs,
          lenMs: after.lenMs,
          ...(after.hand !== "-" ? { hand: after.hand } : {}),
        });
      }
      continue;
    }
    if (!isLive(after)) {
      if (isLive(before)) remove.push(real);
      continue;
    }
    if (!isLive(before)) restore.push(real);
    if (!before || !sameSpan(before, after)) {
      moves.push({
        op: "move",
        id: real,
        onMs: after.onMs,
        lenMs: after.lenMs,
        ...(!before || before.key !== after.key ? { key: after.key } : {}),
      });
    }
    // A note put back keeps the hand it had when it was deleted: only a different hand is sent.
    if (after.hand !== "-" && (!before || before.hand !== after.hand)) hands[after.hand].push(real);
  }
  const ops: NotesOperation[] = [];
  if (restore.length) ops.push({ op: "restore", ids: restore });
  ops.push(...moves);
  if (remove.length) ops.push({ op: "delete", ids: remove });
  ops.push(...adds);
  for (const hand of ["r", "l"] as const) if (hands[hand].length) ops.push({ op: "hand", ids: hands[hand], hand });
  return ops;
}

/**
 * The notes the backend changed beyond the operations (`changed` of the PATCH answer), laid over
 * `present`: a note the same-key rule shortened, a hand the quick rule gave. `null` when the page
 * already had every one of them as the backend has it.
 */
export function mergeChanged(
  base: NotesBase,
  present: Overrides,
  changed: { id: number[]; key: number[]; onMs: number[]; lenMs: number[]; hand: string } | undefined,
  idMap: ReadonlyMap<number, number>,
): Overrides | null {
  if (!changed || changed.id.length === 0) return null;
  const pageId = new Map<number, number>();
  for (const [temp, real] of idMap) pageId.set(real, temp);
  let next: Map<number, Note> | null = null;
  for (let index = 0; index < changed.id.length; index += 1) {
    const id = pageId.get(changed.id[index]!) ?? changed.id[index]!;
    const hand = changed.hand[index];
    const theirs: Note = {
      key: changed.key[index]!,
      onMs: changed.onMs[index]!,
      lenMs: changed.lenMs[index]!,
      hand: hand === "r" || hand === "l" ? hand : "-",
    };
    const ours = noteOf(base, next ?? present, id);
    if (sameNote(ours, theirs)) continue;
    next ??= new Map(present);
    next.set(id, theirs);
  }
  return next;
}
