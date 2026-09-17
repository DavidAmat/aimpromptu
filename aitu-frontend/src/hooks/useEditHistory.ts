/**
 * One object of edits, and the way back through every change made to it.
 *
 * A page that lets a reader make sixteen kinds of edit needs one gesture that takes the last one
 * back, not sixteen private ones in sixteen places. This holds the edits as a single value and
 * keeps the values they had before, so undo is going back to the previous one and redo is going
 * forward again.
 *
 * Three things it does that a plain `useState` does not:
 *
 * **A setter per field, with the identity of a constant.** `set.ottavas` is shaped exactly like a
 * `useState` setter and is the *same function* on every render. That matters more than it sounds:
 * the sheet is rebuilt whenever anything it draws from changes, so a setter that changed identity
 * would tear down and rebuild every note on every render of the page.
 *
 * **One press is one step.** A deletion that also clears a fingering sets two fields, and a reader
 * pressing undo means the deletion, not half of it. Every write made in one run of the browser's
 * event loop is gathered into a single step, so no call site has to say anything about grouping.
 *
 * **A step may carry a backend call.** Most edits live only on the page, but a hand swap is written
 * onto the recording, and taking it back means writing the old hands back. Such a step carries the
 * two calls, and the state only moves once the call has succeeded — a page that disagreed with the
 * recording would be worse than no undo at all.
 *
 * Everything below is a reducer over plain values, with no state held in a ref. That is on purpose:
 * this app compiles with the React Compiler, which reads a ref during render as a bug — and it is
 * right to, because a value read during render that React did not see change is a page that draws
 * something other than what it holds.
 */

import { useCallback, useMemo, useReducer, useState, type Dispatch, type SetStateAction } from "react";

/** How many steps are kept. Far more than anyone walks back, and small enough to cost nothing. */
const LIMIT = 100;

/**
 * Which run of the event loop we are in, as a number that only has to differ between runs.
 *
 * This is the whole of how one press becomes one step: two writes that report the same number
 * happened in the same run, so they are the same gesture. Module level rather than a ref, because
 * it is about the browser rather than about any one component, and because a ref could not be read
 * where it is needed without reading it during render.
 */
let gestureNow = 0;
let gestureEnding = false;
function gesture(): number {
  if (!gestureEnding) {
    gestureEnding = true;
    // As soon as the handler returns, the run is over and the next write starts a new step.
    queueMicrotask(() => {
      gestureNow += 1;
      gestureEnding = false;
    });
  }
  return gestureNow;
}

export interface StepEffects {
  /** Take the backend write back. Run before the state goes back. */
  undo: () => Promise<void>;
  /** Write it again. Run before the state goes forward. */
  redo: () => Promise<void>;
}

export interface HistoryStep<T> {
  label: string;
  before: T;
  after: T;
  /** Which run of the event loop made it, so writes from the same press join this step. */
  gesture: number;
  effects?: StepEffects;
}

export interface HistoryState<T> {
  present: T;
  past: HistoryStep<T>[];
  future: HistoryStep<T>[];
}

export type HistoryAction<T> =
  | { kind: "edit"; key: keyof T; label: string; value: SetStateAction<T[keyof T]>; gesture: number }
  | { kind: "stage"; label: string; effects: StepEffects; gesture: number }
  | { kind: "walk"; to: "undo" | "redo" }
  | { kind: "reset"; value: T | ((current: T) => T) };

/** Add to the step this gesture already opened, or open a new one. */
function record<T>(
  state: HistoryState<T>,
  step: {
    label: string;
    after: T;
    gesture: number;
    effects?: StepEffects;
    /** Take the label even when joining a step that is already open. `stage` does; a field does not. */
    rename?: boolean;
  },
): HistoryState<T> {
  const last = state.past[state.past.length - 1];
  if (last && last.gesture === step.gesture) {
    return {
      present: step.after,
      past: [
        ...state.past.slice(0, -1),
        {
          ...last,
          ...(step.rename ? { label: step.label } : {}),
          after: step.after,
          ...(step.effects ? { effects: step.effects } : {}),
        },
      ],
      future: [],
    };
  }
  return {
    present: step.after,
    past: [
      ...state.past,
      {
        label: step.label,
        before: state.present,
        after: step.after,
        gesture: step.gesture,
        ...(step.effects ? { effects: step.effects } : {}),
      },
    ].slice(-LIMIT),
    future: [],
  };
}

/**
 * The whole of the history, as one pure function of what it was and what happened.
 *
 * Exported so `npm run check:history` can drive it without a browser. The risky part of an undo is
 * not the two buttons, it is whether one press is one step and whether walking back lands exactly
 * where it started, and both of those are decided here.
 */
export function historyReducer<T extends object>(state: HistoryState<T>, action: HistoryAction<T>): HistoryState<T> {
  switch (action.kind) {
    case "edit": {
      const current = state.present[action.key];
      const next =
        typeof action.value === "function"
          ? (action.value as (previous: T[keyof T]) => T[keyof T])(current)
          : action.value;
      // A chip pressed back to what it already was is not a step. Leaving this out would fill the
      // history with presses that changed nothing and make undo look broken.
      if (Object.is(next, current)) return state;
      return record(state, {
        label: action.label,
        after: { ...state.present, [action.key]: next },
        gesture: action.gesture,
      });
    }
    case "stage":
      // Opened even though nothing on the page has moved yet: the write to the recording is the
      // step, and the fields this gesture goes on to touch join it.
      return record(state, {
        label: action.label,
        after: state.present,
        gesture: action.gesture,
        effects: action.effects,
        rename: true,
      });
    case "walk": {
      const from = action.to === "undo" ? state.past : state.future;
      const step = from[from.length - 1];
      if (!step) return state;
      const rest = from.slice(0, -1);
      const onto = [...(action.to === "undo" ? state.future : state.past), step];
      return action.to === "undo"
        ? { present: step.before, past: rest, future: onto }
        : { present: step.after, past: onto, future: rest };
    }
    case "reset": {
      const value =
        typeof action.value === "function"
          ? (action.value as (current: T) => T)(state.present)
          : action.value;
      return { present: value, past: [], future: [] };
    }
  }
}

export interface EditHistory<T> {
  /** The edits as they are now. */
  state: T;
  /**
   * A `useState`-shaped setter per field, made once and the same on every render.
   *
   * Every call site writes exactly what it wrote before this hook existed —
   * `set.ottavas((current) => …)` — which is why none of them had to change.
   */
  set: { [K in keyof T]: Dispatch<SetStateAction<T[K]>> };
  /**
   * Name the step being built in this run, and give it the calls that take a backend write back
   * and put it again.
   *
   * Called *before* the setters it belongs to. Without it a step takes the name of the first field
   * written, which is right for an ordinary edit and wrong for one — a hand swap moves fingerings
   * and would otherwise be called "Fingering".
   */
  stage: (label: string, effects: StepEffects) => void;
  /**
   * Replace the edits and forget every step, in one go.
   *
   * For the moments where going back further would restore marks over notes that are not there any
   * more: the saved reading read back from the backend, a different piece, a passage placed into
   * the recording, an accepted re-record, and Remove all.
   */
  reset: (next: T | ((current: T) => T)) => void;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  canUndo: boolean;
  canRedo: boolean;
  /** What the next undo and the next redo are about, for the two buttons to say. */
  undoLabel: string | null;
  redoLabel: string | null;
  /** A step carrying a backend call is on its way. */
  busy: boolean;
  /** What went wrong the last time a step could not be taken back. Raw, so the page words it. */
  failure: unknown;
  clearFailure: () => void;
}

/**
 * @param initial what the edits are before anybody touches them
 * @param labels what to call a step that changes each field, one per field
 */
export function useEditHistory<T extends object>(
  initial: T,
  labels: Readonly<Record<keyof T, string>>,
): EditHistory<T> {
  const [history, dispatch] = useReducer(historyReducer<T>, {
    present: initial,
    past: [],
    future: [],
  });
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);

  // `dispatch` never changes, so neither do these. Built from the labels rather than on demand,
  // because a setter made lazily would have to be kept somewhere this hook could read during
  // render, and there is no such place that is safe.
  const set = useMemo(
    () =>
      Object.fromEntries(
        (Object.keys(labels) as (keyof T)[]).map((key) => [
          key,
          (value: SetStateAction<T[keyof T]>) =>
            dispatch({
              kind: "edit",
              key,
              label: labels[key],
              value,
              gesture: gesture(),
            }),
        ]),
      ) as { [K in keyof T]: Dispatch<SetStateAction<T[K]>> },
    [labels],
  );

  const stage = useCallback((label: string, effects: StepEffects) => {
    dispatch({ kind: "stage", label, effects, gesture: gesture() });
  }, []);

  const reset = useCallback((next: T | ((current: T) => T)) => {
    dispatch({ kind: "reset", value: next });
  }, []);

  /**
   * Walk one step, in either direction.
   *
   * The backend call goes first. If it fails, nothing is dispatched: the page is left saying
   * exactly what it said before, which is the truth, because nothing changed anywhere.
   */
  const walk = useCallback(
    async (to: "undo" | "redo") => {
      const stack = to === "undo" ? history.past : history.future;
      const step = stack[stack.length - 1];
      if (!step) return;
      const call = to === "undo" ? step.effects?.undo : step.effects?.redo;
      setFailure(null);
      if (!call) {
        dispatch({ kind: "walk", to });
        return;
      }
      setBusy(true);
      try {
        await call();
        dispatch({ kind: "walk", to });
      } catch (caught) {
        setFailure(caught);
      } finally {
        setBusy(false);
      }
    },
    [history.past, history.future],
  );

  const undo = useCallback(() => walk("undo"), [walk]);
  const redo = useCallback(() => walk("redo"), [walk]);
  const clearFailure = useCallback(() => setFailure(null), []);

  return {
    state: history.present,
    set,
    stage,
    reset,
    undo,
    redo,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
    undoLabel: history.past[history.past.length - 1]?.label ?? null,
    redoLabel: history.future[history.future.length - 1]?.label ?? null,
    busy,
    failure,
    clearFailure,
  };
}

export default useEditHistory;
