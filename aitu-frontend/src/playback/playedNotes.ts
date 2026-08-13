/**
 * The played notes, as the animated views want them.
 *
 * One conversion, from `GET /matrix/{id}/events` — the transcription in the
 * engine's own seconds — into a flat list with a keyboard row on it. There is no
 * grid in here and no figure: a rectangle on the roll is as long as the note was
 * actually held, and two notes a hair apart are drawn a hair apart.
 *
 * This replaces the old `matrixNotes.ts`, which walked a dense matrix looking for
 * `1` and `-1` cells. That matrix was built at a tempo and a resolution, so every
 * rectangle it produced had already been rounded to a beat subdivision before any
 * view saw it — which is exactly the rounding the wall-clock model removed.
 */

import type { RawEvents, RawNoteEvent } from "../api";

/** Lowest key of an 88-key piano; row 0. */
const LOWEST_MIDI = 21;
const HIGHEST_MIDI = 108;

export type PlayedHand = "single" | "left" | "right";

export interface PlayedNote {
  id: string;
  /** 0–87, the keyboard row `keyPositions` is indexed by. */
  row: number;
  midiNote: number;
  startSeconds: number;
  endSeconds: number;
  velocity: number;
  hand: PlayedHand;
  /** The pipeline discards this one as too short to have been played. */
  artifact: boolean;
  /** A reader has taken it off the recording. */
  removed: boolean;
  /** 12 or 24 when a note that far above was struck alongside it. */
  octaveBelow: number | null;
}

/**
 * Events in, notes out — dropping only what cannot be drawn.
 *
 * Notes outside the 88 keys are the one thing removed, because there is no row to
 * put them on. Artifacts are kept and flagged: the whole point of a view over the
 * raw events is being able to see what the rest of the system throws away, and a
 * filter you cannot see is a filter you cannot check.
 */
export function playedNotesOf(events: RawNoteEvent[]): PlayedNote[] {
  const notes: PlayedNote[] = [];

  events.forEach((event, index) => {
    if (event.midiNote < LOWEST_MIDI || event.midiNote > HIGHEST_MIDI) return;
    notes.push({
      // The index is part of the id because two strikes of one key can share a
      // start once rounded for display, and React needs them told apart.
      id: `${index}:${event.midiNote}`,
      row: event.midiNote - LOWEST_MIDI,
      midiNote: event.midiNote,
      startSeconds: event.start,
      endSeconds: Math.max(event.end, event.start + 0.01),
      velocity: event.velocity,
      hand: event.hand ?? "single",
      artifact: event.artifact,
      removed: event.removed,
      octaveBelow: event.octaveBelow,
    });
  });

  return notes.sort(
    (left, right) => left.startSeconds - right.startSeconds || left.row - right.row,
  );
}

/** Every key sounding at `seconds`, for the keyboard highlight. */
export function soundingRows(notes: PlayedNote[], seconds: number): Set<number> {
  const rows = new Set<number>();
  for (const note of notes) {
    if (note.startSeconds <= seconds && seconds < note.endSeconds) rows.add(note.row);
  }
  return rows;
}

/** How the loaded response describes itself, for the caption under a view. */
export function describeEvents(events: RawEvents | null): string {
  if (!events) return "";
  const kept = events.events.length - events.artifactCount;
  const phantoms = events.octavePhantomCount
    ? `, ${events.octavePhantomCount} of them an octave under a struck note`
    : "";
  return events.artifactCount
    ? `${kept} notes played · ${events.artifactCount} filtered as artifacts${phantoms}`
    : `${kept} notes played`;
}
