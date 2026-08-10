/**
 * Which notes the reader has picked, and the three ways they pick them.
 *
 * Shared between the roll and the falling view because the *rules* are the same
 * even though the geometry is not — a band on the roll is time by pitch and on
 * the falling view it is pitch by time, so each page works out which notes a
 * rectangle covers and hands the ids here.
 *
 * The rules, which are the ones every list on a desktop has:
 *
 * * click a note — it becomes the whole selection
 * * ⌘-click (or Ctrl on Windows) — add it, or take it out if it was in
 * * drag a band over empty space — the notes under the band become the
 *   selection, or join it when ⌘ is held
 * * click empty space — nothing is selected
 */

import { useCallback, useMemo, useState } from "react";
import type { PlayedNote } from "../playback/playedNotes";

export function useNoteSelection(notes: PlayedNote[]) {
  const [ids, setIds] = useState<ReadonlySet<string>>(() => new Set());

  const clear = useCallback(() => setIds(new Set()), []);

  const pick = useCallback((id: string, additive: boolean) => {
    setIds((current) => {
      if (!additive) return new Set([id]);
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const pickMany = useCallback((picked: string[], additive: boolean) => {
    setIds((current) => (additive ? new Set([...current, ...picked]) : new Set(picked)));
  }, []);

  // Resolved against the current notes rather than stored as objects: a reload
  // after a delete replaces every note, and a selection holding stale copies
  // would keep drawing rectangles that no longer exist.
  const selected = useMemo(() => {
    if (ids.size === 0) return [] as PlayedNote[];
    return notes.filter((note) => ids.has(note.id));
  }, [ids, notes]);

  return { ids, selected, pick, pickMany, clear };
}

export default useNoteSelection;
