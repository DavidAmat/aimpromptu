/** Convert dense frame rows into note runs shared by every animated view. */

export type PlaybackHand = "single" | "left" | "right";

export interface MatrixPlaybackNote {
  id: string;
  key: number;
  startFrame: number;
  endFrame: number;
  startSeconds: number;
  endSeconds: number;
  hand: PlaybackHand;
}

function notesForGrid(
  dense: number[][],
  timeStepSeconds: number,
  hand: PlaybackHand,
): MatrixPlaybackNote[] {
  const notes: MatrixPlaybackNote[] = [];
  const keyCount = dense[0]?.length ?? 88;

  for (let key = 0; key < keyCount; key += 1) {
    for (let frame = 0; frame < dense.length; frame += 1) {
      if (dense[frame]?.[key] !== 1) continue;
      let endFrame = frame + 1;
      while (endFrame < dense.length && dense[endFrame]?.[key] === -1) endFrame += 1;
      notes.push({
        id: `${hand}:${key}:${frame}`,
        key,
        startFrame: frame,
        endFrame,
        startSeconds: frame * timeStepSeconds,
        endSeconds: endFrame * timeStepSeconds,
        hand,
      });
    }
  }
  return notes.sort((left, right) => left.startSeconds - right.startSeconds || left.key - right.key);
}

export function extractMatrixNotes(
  denseRightOrSingle: number[][],
  denseLeft: number[][] | null | undefined,
  timeStepSeconds: number,
): MatrixPlaybackNote[] {
  if (!denseLeft) return notesForGrid(denseRightOrSingle, timeStepSeconds, "single");
  return [
    ...notesForGrid(denseLeft, timeStepSeconds, "left"),
    ...notesForGrid(denseRightOrSingle, timeStepSeconds, "right"),
  ].sort((left, right) => left.startSeconds - right.startSeconds || left.key - right.key);
}

export function soundingKeys(notes: MatrixPlaybackNote[], seconds: number): Set<number> {
  return new Set(
    notes
      .filter((note) => note.startSeconds <= seconds && seconds < note.endSeconds)
      .map((note) => note.key),
  );
}
