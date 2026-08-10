/**
 * Taking notes off the recording, and putting them back.
 *
 * The call is one line; what this holds is the awkward part around it — the busy
 * flag while the write is in flight, the error if it fails, and the revision
 * counter that makes the view re-read afterwards.
 *
 * Re-reading is not optional and not a nicety. Removing a note changes the gap to
 * its neighbour, which changes that neighbour's printed figure, which changes the
 * hand split's input. Patching the note out of the local list would leave a view
 * that is right about the note it deleted and wrong about the ones around it.
 */

import { useCallback, useState } from "react";
import { matrixApi } from "../api";
import type { PlayedNote } from "../playback/playedNotes";

export function useNoteRemoval(audioUuid: string | null) {
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setRemoved = useCallback(
    async (notes: PlayedNote[], removed: boolean) => {
      if (!audioUuid || notes.length === 0) return false;
      setBusy(true);
      setError(null);
      try {
        await matrixApi.setRemoved(
          audioUuid,
          notes.map((note) => ({ midiNote: note.midiNote, start: note.startSeconds })),
          removed,
        );
        setRevision((current) => current + 1);
        return true;
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : removed
              ? "Those notes could not be taken off the recording."
              : "Those notes could not be put back.",
        );
        return false;
      } finally {
        setBusy(false);
      }
    },
    [audioUuid],
  );

  return { revision, busy, error, setRemoved, clearError: () => setError(null) };
}

export default useNoteRemoval;
