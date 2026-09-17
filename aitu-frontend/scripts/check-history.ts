/**
 * Does undo take back exactly one press, and land exactly where it started?
 *
 * The two buttons and the keyboard are the easy half of an undo. The half that goes wrong is the
 * bookkeeping: whether a press that changes four things is one step or four, whether going back and
 * forward lands on the same values, and whether a press that changed nothing quietly fills the
 * history with steps that appear to do nothing when a reader walks them.
 *
 * None of that needs a browser — `historyReducer` is a pure function of what the history was and
 * what happened — so it is checked here rather than by clicking, the same way the overlay geometry
 * is checked against its fixture rather than by eye.
 *
 *     npm run check:history
 */

import {
  historyReducer,
  type HistoryAction,
  type HistoryState,
} from "../src/hooks/useEditHistory";

/** A stand-in for the page's edits: two fields is enough to show a press touching several. */
interface Edits {
  fingers: Record<string, number>;
  hidden: string[];
  scale: number;
}

const NOTHING: Edits = { fingers: {}, hidden: [], scale: 1 };

const LABELS: Record<keyof Edits, string> = {
  fingers: "Fingering",
  hidden: "Notes off the page",
  scale: "Mark size",
};

function start(): HistoryState<Edits> {
  return { present: NOTHING, past: [], future: [] };
}

/** One write to one field, as the hook's setters make it. */
function edit<K extends keyof Edits>(
  key: K,
  value: Edits[K] | ((previous: Edits[K]) => Edits[K]),
  gesture: number,
): HistoryAction<Edits> {
  return {
    kind: "edit",
    key,
    label: LABELS[key],
    value: value as HistoryAction<Edits> extends { value: infer V } ? V : never,
    gesture,
  } as HistoryAction<Edits>;
}

function run(
  state: HistoryState<Edits>,
  ...actions: HistoryAction<Edits>[]
): HistoryState<Edits> {
  return actions.reduce(historyReducer<Edits>, state);
}

let failed = 0;

function check(what: string, passed: boolean, detail = ""): void {
  if (passed) {
    console.log(`  ✓ ${what}${detail ? ` — ${detail}` : ""}`);
    return;
  }
  failed += 1;
  console.error(`  ✗ ${what}${detail ? ` — ${detail}` : ""}`);
}

function same(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

console.log("\nOne press is one step");
{
  // A note taken off the page also clears its fingering: two fields, one gesture, one undo.
  const after = run(
    start(),
    edit("fingers", { "right:8:40": 3 }, 1),
    edit("hidden", ["8:40"], 1),
  );
  check("two fields written in one run make one step", after.past.length === 1, `${after.past.length}`);
  check("the step is named after the first field written", after.past[0]!.label === "Fingering");

  const back = run(after, { kind: "walk", to: "undo" });
  check("one undo takes both fields back", same(back.present, NOTHING));
  check("and there is nothing left to undo", back.past.length === 0);

  const forward = run(back, { kind: "walk", to: "redo" });
  check("redo puts both back", same(forward.present, after.present));
}

console.log("\nTwo presses are two steps");
{
  const after = run(
    start(),
    edit("scale", 1.2, 1),
    edit("scale", 1.4, 2),
    edit("scale", 1.6, 3),
  );
  check("three runs make three steps", after.past.length === 3, `${after.past.length}`);
  const back = run(
    after,
    { kind: "walk", to: "undo" },
    { kind: "walk", to: "undo" },
  );
  check("walking back twice lands on the first press", back.present.scale === 1.2, `${back.present.scale}`);
  check("and two are waiting to be put back", back.future.length === 2);
}

console.log("\nA press that changed nothing is not a step");
{
  const after = run(start(), edit("scale", 1, 1));
  check("setting a field to what it already held adds no step", after.past.length === 0);

  // The updater form has to be read before it can be compared, which is where this would be missed.
  const twice = run(
    run(start(), edit("hidden", ["8:40"], 1)),
    edit("scale", (previous) => previous, 2),
  );
  check("an updater that returns the same value adds no step", twice.past.length === 1);
}

console.log("\nA new edit drops what was waiting to be put back");
{
  const walked = run(
    run(start(), edit("scale", 1.2, 1), edit("scale", 1.4, 2)),
    { kind: "walk", to: "undo" },
  );
  check("one step is waiting after an undo", walked.future.length === 1);
  const edited = run(walked, edit("hidden", ["0:21"], 3));
  check("editing after an undo drops it", edited.future.length === 0);
}

console.log("\nA step that also wrote to the recording");
{
  const effects = { undo: async () => {}, redo: async () => {} };
  // `stage` is called first and names the step, then the fields the move drags along join it.
  const after = run(
    start(),
    { kind: "stage", label: "Hand", effects, gesture: 1 },
    edit("fingers", { "left:8:40": 2 }, 1),
  );
  check("staging and the fields it drags along are one step", after.past.length === 1);
  check("the staged name wins over the field's", after.past[0]!.label === "Hand");
  check("the step carries the calls that take the write back", after.past[0]!.effects === effects);

  // A move that changed nothing on the page is still a step, because the recording changed.
  const alone = run(start(), { kind: "stage", label: "Hand", effects, gesture: 1 });
  check("a move with no page edit under it is still a step", alone.past.length === 1);
}

console.log("\nStarting again forgets everything");
{
  const after = run(
    run(start(), edit("scale", 1.2, 1), edit("hidden", ["8:40"], 2)),
    { kind: "reset", value: NOTHING },
  );
  check("reset empties both stacks", after.past.length === 0 && after.future.length === 0);
  check("and puts the edits back to what it was given", same(after.present, NOTHING));
}

console.log("\nWalking past the end does nothing");
{
  const empty = run(start(), { kind: "walk", to: "undo" }, { kind: "walk", to: "redo" });
  check("undo and redo on an empty history leave it alone", same(empty, start()));
}

console.log(
  failed === 0 ? "\nEvery check passed.\n" : `\n${failed} check${failed === 1 ? "" : "s"} failed.\n`,
);
process.exit(failed === 0 ? 0 : 1);
