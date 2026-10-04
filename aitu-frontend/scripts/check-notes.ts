/**
 * The Notes tab's typed arrays, live feed and edits, checked without a browser (implementation 08,
 * Phase 7).
 *
 * The canvas trusts three things it cannot check on its own: that the arrays find the notes of a
 * time range and the note under the pointer, that the live stream's messages land in the arrays as
 * the backend meant them, and that an edit becomes the operations the backend applies to the same
 * notes (the same-key rule included). Each is checked here on small hand-made pieces.
 *
 *     npm run check:notes
 */

import type { PieceNotes } from "../src/api";
import { LiveFeed, type ChunkMessage } from "../src/notes/liveFeed";
import {
  addNote,
  anyHand,
  applyPrediction,
  baseOf,
  countChanges,
  deleteNotes,
  describeChanges,
  fillRoll,
  idsWithoutHand,
  mergeChanged,
  moveNotes,
  NO_OVERRIDES,
  nextTempId,
  noteOf,
  resizeNote,
  setHands,
  toOperations,
  type EditContext,
  type Overrides,
} from "../src/notes/noteEdits";
import { FLAG_OPEN, RollNotes } from "../src/notes/rollNotes";
import { clampedKeyAt, keyAt, rollLayout, widenKeys, yOf } from "../src/notes/rollView";

let failed = 0;
function check(label: string, ok: boolean, extra = ""): void {
  console.log(`${ok ? "  ok  " : "  FAIL"} ${label}${extra && !ok ? ` (${extra})` : ""}`);
  if (!ok) failed += 1;
}
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** A piece: two notes on key 40, one on 44, one long one on 30. */
const PIECE: PieceNotes = {
  revision: 3,
  handsRevision: 5,
  durationMs: 10_000,
  stale: false,
  id: [0, 1, 2, 3],
  key: [40, 40, 44, 30],
  onMs: [1000, 2000, 1500, 0],
  lenMs: [500, 500, 300, 8000],
  hand: "rrl-",
  guessed: [],
};

console.log("The typed arrays");
{
  const roll = new RollNotes();
  roll.load(PIECE);
  roll.commit();
  const found: number[] = [];
  roll.forEachIn(1400, 1600, 0, (slot) => found.push(roll.id[slot]!));
  check("a time range finds the notes that sound in it, the long one too", same(found.sort(), [0, 2, 3]), JSON.stringify(found));
  check("a click on a note finds it", roll.id[roll.hit(40, 1200)] === 0);
  check("a click just after a note, within the tolerance, still finds it", roll.id[roll.hit(40, 1520, 30)] === 0);
  check("a click between two notes of a key finds nothing", roll.hit(40, 1700) === -1);
  check("a click on another key finds nothing", roll.hit(41, 1200) === -1);
  check("a band finds the notes inside it", same(roll.idsInBand(40, 44, 1900, 2100).sort(), [1]));
  check("the keys of a key, in onset order", same(roll.idsOnKey(40), [0, 1]));
  check("the key range", same(roll.keyRange(), [30, 44]));
  roll.remove(0);
  roll.commit();
  check("after a removal, the last note takes its slot and is still found", roll.id[roll.hit(30, 5000)] === 3 && roll.count === 3);
  const sounding: number[] = [];
  roll.soundingAt(2100, (slot) => sounding.push(roll.id[slot]!));
  check("the notes sounding at a time", same(sounding.sort(), [1, 3]));
  const many = new RollNotes();
  for (let index = 0; index < 20_000; index += 1) many.upsert(index, index % 88, index * 10, 40);
  many.commit();
  let seen = 0;
  many.forEachIn(0, 0, 0, () => undefined); // builds the index
  const begin = performance.now();
  many.forEachIn(100_000, 101_000, 0, () => (seen += 1));
  const took = performance.now() - begin;
  // Onsets 99,960 to 101,000 ms: the first ends exactly at the start of the range.
  check("20,000 notes: a one-second range finds its 105 notes in under a millisecond", seen === 105 && took < 1, `seen ${seen}, ${took.toFixed(2)} ms`);
}

console.log("The rows");
{
  const layout = rollLayout(1000, 24 + 36 * 10, 20, 55);
  check("36 rows of 10 px", layout.rowHeight === 10);
  check("the highest key is at the top", yOf(layout, 55) === 24 && keyAt(layout, 25) === 55);
  check("the lowest key is at the bottom", keyAt(layout, 24 + 36 * 10 - 1) === 20);
  check("outside the rows there is no key", keyAt(layout, 10) === -1 && keyAt(layout, 1000) === -1);
  check("a drag below the rows stays on the lowest key", clampedKeyAt(layout, 5000) === 20);
  check("the keys grow to the notes with a margin", same(widenKeys(null, [30, 70]), [28, 72]));
  check("a narrow piece still shows 36 rows", same(widenKeys(null, [40, 42]), [24, 59]));
  check("the keys never shrink", same(widenKeys([10, 80], [40, 42]), [10, 80]));
  check("the keys stay on the keyboard", same(widenKeys(null, [0, 3]), [0, 35]));
}

console.log("The live feed");
{
  const roll = new RollNotes();
  const feed = new LiveFeed();
  const message = (patch: Partial<ChunkMessage>): ChunkMessage => ({
    type: "chunk",
    done: 0,
    total: 4,
    upToMs: 0,
    durationMs: 20_000,
    open: { id: [], key: [], onMs: [] },
    closed: { id: [], key: [], onMs: [], lenMs: [] },
    ...patch,
  });
  feed.push(message({ upToMs: 1200, open: { id: [7], key: [40], onMs: [1000] } }), 0);
  feed.push(message({ done: 1, upToMs: 5000, closed: { id: [7, 8], key: [40, 41], onMs: [1000, 3000], lenMs: [900, 400] }, open: { id: [9], key: [50], onMs: [4800] } }), 10);
  check("nothing is drawn before the animation frame", roll.count === 0 && feed.pending);
  const changed = feed.drain(roll, 100);
  check("one drain takes the whole queue", changed && !feed.pending && roll.count === 3);
  const seven = roll.slotOf(7);
  check("a note that was open gets its end, and no reveal", roll.lenMs[seven] === 900 && roll.flags[seven] === 0 && roll.spawn[seven] === 0);
  check("a note that arrives closed is revealed", roll.spawn[roll.slotOf(8)] === 100);
  check("a note still sounding is open", (roll.flags[roll.slotOf(9)]! & FLAG_OPEN) !== 0);
  check("the frontier target is the furthest time reported", feed.upToMs === 5000);
  check("the notes are counted once", feed.notes === 3, String(feed.notes));
  feed.finish();
  for (let frame = 0; frame < 200; frame += 1) feed.step(1000 + frame * 16);
  check("after the end, the frontier reaches the end of the piece", feed.shownMs === 20_000);
}

console.log("The edits");
const base = baseOf(PIECE);
const roll = new RollNotes();
const context = (over: Overrides): EditContext => {
  fillRoll(roll, base, over);
  return { base, over, idsOnKey: (key) => roll.idsOnKey(key) };
};
{
  const moved = moveNotes(context(NO_OVERRIDES), [0], 200, 0);
  check("a move changes the onset", noteOf(base, moved.over, 0)?.onMs === 1200 && moved.refused === null);
  const into = moveNotes(context(NO_OVERRIDES), [0], 800, 0);
  const zero = noteOf(base, into.over, 0)!;
  check("a move into the next note of its key shortens the moved note", zero.onMs === 1800 && zero.lenMs === 200, JSON.stringify(zero));
  const back = moveNotes(context(NO_OVERRIDES), [1], -800, 0);
  check("a move onto an earlier note of its key shortens that note", noteOf(base, back.over, 0)?.lenMs === 200);
  const clash = moveNotes(context(NO_OVERRIDES), [1], -1000, 0);
  check("two notes of one key at the same onset are refused", clash.refused !== null && clash.over === NO_OVERRIDES);
  const early = moveNotes(context(NO_OVERRIDES), [0, 2], -5000, 0);
  check("a move is stopped at the start of the piece, for the whole selection", noteOf(base, early.over, 0)?.onMs === 0 && noteOf(base, early.over, 2)?.onMs === 500);
  const late = moveNotes(context(NO_OVERRIDES), [3], 5000, 0);
  check("a move is stopped at the end of the piece", noteOf(base, late.over, 3)?.onMs === 2000);
  const up = moveNotes(context(NO_OVERRIDES), [2], 0, 3);
  check("a move with Shift changes the key", noteOf(base, up.over, 2)?.key === 47);
  const nothing = moveNotes(context(NO_OVERRIDES), [0], 0, 0);
  check("a move of nothing changes nothing (no undo step)", nothing.over === NO_OVERRIDES);
  const resized = resizeNote(context(NO_OVERRIDES), 0, 1000, 1500);
  check("a resize into the next note of its key stops at its onset", noteOf(base, resized.over, 0)?.lenMs === 1000);
  const tiny = resizeNote(context(NO_OVERRIDES), 0, 1000, 1);
  check("a resize keeps at least one time frame", noteOf(base, tiny.over, 0)?.lenMs === 10);
  const tempId = nextTempId(NO_OVERRIDES);
  const added = addNote(context(NO_OVERRIDES), tempId, 40, 1900);
  check("an added note is 250 ms, shortened to the next onset of its key", tempId === -1 && noteOf(base, added.over, -1)?.lenMs === 100);
  check("an added note inside a note of its key shortens that note", noteOf(base, addNote(context(NO_OVERRIDES), -1, 40, 1200).over, 0)?.lenMs === 200);
  const deleted = deleteNotes(context(NO_OVERRIDES), [2, 99]);
  check("a delete marks the note deleted", noteOf(base, deleted.over, 2)?.deleted === true);
}

console.log("Unsaved changes and save");
{
  let over = moveNotes(context(NO_OVERRIDES), [2], 100, 0).over;
  over = deleteNotes(context(over), [1]).over;
  over = addNote(context(over), -1, 60, 5000).over;
  const count = countChanges(base, NO_OVERRIDES, over);
  check("the changes are counted", same(count, { moved: 1, deleted: 1, added: 1, hands: 0 }));
  check("the save bar says them", describeChanges(count) === "Unsaved: 1 note moved, 1 deleted, 1 added", describeChanges(count) ?? "");
  const ops = toOperations(base, NO_OVERRIDES, over, new Map());
  check(
    "the operations: a move, a delete, an add",
    same(ops, [
      { op: "move", id: 2, onMs: 1600, lenMs: 300 },
      { op: "delete", ids: [1] },
      { op: "add", tempId: -1, key: 60, onMs: 5000, lenMs: 250 },
    ]),
    JSON.stringify(ops),
  );
  check("moving a note back where it was leaves nothing unsaved", describeChanges(countChanges(base, NO_OVERRIDES, moveNotes(context(moveNotes(context(NO_OVERRIDES), [2], 100, 0).over), [2], -100, 0).over)) === null);

  // Saved: the added note is now id 12 on the backend. Undo the delete and the add after the save.
  const idMap = new Map([[-1, 12]]);
  const saved = over;
  let undone = new Map(saved);
  undone.delete(1);
  undone.delete(-1);
  const after = toOperations(base, saved, undone, idMap);
  check(
    "undo after a save: the deleted note is restored, the added one deleted by its new id",
    same(after, [{ op: "restore", ids: [1] }, { op: "delete", ids: [12] }]),
    JSON.stringify(after),
  );
  undone = new Map(saved);
  undone.set(1, { key: 40, onMs: 2100, lenMs: 500, hand: "r" });
  const restoredMoved = toOperations(base, saved, undone, idMap);
  check(
    "a note restored at another place is a restore and a move",
    same(restoredMoved, [{ op: "restore", ids: [1] }, { op: "move", id: 1, onMs: 2100, lenMs: 500 }]),
    JSON.stringify(restoredMoved),
  );
  const handed = new Map(saved);
  handed.set(3, { key: 30, onMs: 0, lenMs: 8000, hand: "l" });
  check("a hand change is a hand operation", same(toOperations(base, saved, handed, idMap), [{ op: "hand", ids: [3], hand: "l" }]));
  const merged = mergeChanged(base, saved, { id: [12], key: [60], onMs: [5000], lenMs: [250], hand: "r" }, idMap);
  check("a hand the backend gave an added note is laid over the page's notes", merged !== null && noteOf(base, merged, -1)?.hand === "r");
  check("a note the backend has as the page has it changes nothing", mergeChanged(base, saved, { id: [12], key: [60], onMs: [5000], lenMs: [250], hand: "-" }, idMap) === null);
}

console.log("Hands");
{
  const toLeft = setHands(context(NO_OVERRIDES), [0, 1, 2], "l");
  check("To left hand gives the notes that hand, and leaves alone a note that has it", noteOf(base, toLeft.over, 0)?.hand === "l" && toLeft.over.size === 2);
  check("a hand change is counted as such", describeChanges(countChanges(base, NO_OVERRIDES, toLeft.over)) === "Unsaved: 2 notes with another hand");
  const predicted = applyPrediction(context(NO_OVERRIDES), { id: [0, 1, 2, 3], hand: "llr-" }, new Map());
  check("a prediction is laid over the notes, unsaved", noteOf(base, predicted.over, 0)?.hand === "l" && noteOf(base, predicted.over, 2)?.hand === "r");
  check("a note the split could not place keeps the hand it has", noteOf(base, predicted.over, 3)?.hand === "-");
  check("the operations of a prediction are two hand operations", same(toOperations(base, NO_OVERRIDES, predicted.over, new Map()), [{ op: "hand", ids: [2], hand: "r" }, { op: "hand", ids: [0, 1], hand: "l" }]));
  check("the notes without a hand", same(idsWithoutHand(base, predicted.over), [3]));
  const viaMap = applyPrediction(context(addNote(context(NO_OVERRIDES), -1, 60, 5000).over), { id: [12], hand: "r" }, new Map([[-1, 12]]));
  check("a prediction names an added and saved note by its backend id", noteOf(base, viaMap.over, -1)?.hand === "r");
  check("a piece with hands can be coloured by hand", anyHand(base, NO_OVERRIDES) && !anyHand(baseOf({ ...PIECE, hand: "----" }), NO_OVERRIDES));
}

console.log(failed === 0 ? "\nAll checks passed." : `\n${failed} check(s) failed.`);
process.exit(failed === 0 ? 0 : 1);
