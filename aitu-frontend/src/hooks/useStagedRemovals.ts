/**
 * Notes waiting to be taken off the recording, and the one press that commits them.
 *
 * Deleting used to write straight through. That was wrong for the same reason the
 * sheet stages its edits: taking a note off changes the gap to its neighbour, and
 * therefore that neighbour's printed figure, so it is a decision about the piece
 * and a decision should be reviewable before it lands. Now a delete only marks
 * the note, the view draws it as struck through, and **Save** on the floating bar
 * writes the lot.
 *
 * Staging is keyed by pitch and start second, not by the note's list index. A save
 * re-reads the recording, and an index would point at a different note afterwards.
 *
 * A pending entry can point either way — `true` to take a note off, `false` to put
 * one back — so undoing a staged delete is the same mechanism as staging one, and
 * staging then unstaging leaves nothing behind.
 */

import { useCallback, useMemo, useState } from "react";
import { matrixApi } from "../api";
import type { PlayedNote } from "../playback/playedNotes";

/** The note's identity in the recording, stable across a re-read. */
export function noteKeyOf(note: PlayedNote): string {
  return `${note.midiNote}@${note.startSeconds.toFixed(4)}`;
}

export function useStagedRemovals(audioUuid: string | null) {
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState<ReadonlyMap<string, boolean>>(() => new Map());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stage = useCallback((notes: PlayedNote[], removed: boolean) => {
    if (notes.length === 0) return;
    setPending((current) => {
      const next = new Map(current);
      for (const note of notes) {
        const key = noteKeyOf(note);
        // Back to where it started is not a change at all. Dropping the entry
        // keeps the bar's count honest and lets the bar disappear.
        if (note.removed === removed) next.delete(key);
        else next.set(key, removed);
      }
      return next;
    });
    setError(null);
  }, []);

  const discard = useCallback(() => {
    setPending(new Map());
    setError(null);
  }, []);

  /** What the view should draw: the pending decision if there is one, else the stored one. */
  const isRemoved = useCallback(
    (note: PlayedNote) => pending.get(noteKeyOf(note)) ?? note.removed,
    [pending],
  );
  const isStaged = useCallback(
    (note: PlayedNote) => pending.has(noteKeyOf(note)),
    [pending],
  );

  const counts = useMemo(() => {
    let removing = 0;
    let restoring = 0;
    for (const removed of pending.values()) {
      if (removed) removing += 1;
      else restoring += 1;
    }
    return { removing, restoring, total: pending.size };
  }, [pending]);

  /**
   * Write every staged decision, in two calls at most.
   *
   * The notes are looked up in the list this was staged against rather than kept
   * as objects, so a stale copy can never be sent. Both directions are attempted
   * before anything is cleared: a half-applied save that silently forgot the rest
   * would be the worst outcome here.
   */
  const save = useCallback(
    async (notes: PlayedNote[]) => {
      if (!audioUuid || pending.size === 0) return false;
      const byKey = new Map(notes.map((note) => [noteKeyOf(note), note]));
      const removing: PlayedNote[] = [];
      const restoring: PlayedNote[] = [];
      for (const [key, removed] of pending) {
        const note = byKey.get(key);
        if (!note) continue;
        (removed ? removing : restoring).push(note);
      }

      setSaving(true);
      setError(null);
      try {
        for (const [group, removed] of [
          [removing, true],
          [restoring, false],
        ] as const) {
          if (group.length === 0) continue;
          await matrixApi.setRemoved(
            audioUuid,
            group.map((note) => ({ midiNote: note.midiNote, start: note.startSeconds })),
            removed,
          );
        }
        setPending(new Map());
        setRevision((current) => current + 1);
        return true;
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Those changes could not be saved.",
        );
        return false;
      } finally {
        setSaving(false);
      }
    },
    [audioUuid, pending],
  );

  return { revision, pending, counts, saving, error, stage, discard, save, isRemoved, isStaged };
}

export default useStagedRemovals;
