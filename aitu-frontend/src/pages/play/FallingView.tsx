/**
 * **Notes Falling** as a view of Play mode (implementation 02, plan section 17, Q-4): the notes of
 * the part on show drop onto a keyboard and are swallowed at the moment they sound.
 *
 * Until Phase 11 it was a page of its own (`/projects/:id/notes-falling`) with its own transport, a
 * synthesised piano, a stretch to loop and the notes to take off. In Play mode it only plays: the
 * clock is the one of the sheet's recording (`PlayClock`), so switching between the sheet and this
 * view keeps the place in the music, and only the recording is heard (the app context: no sound is
 * made from the notes). Taking notes off stays on the Notes step.
 */

import { useMemo, useSyncExternalStore } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useElementSize } from "../../hooks/useElementSize";
import { usePlayedNotes } from "../../hooks/usePlayedNotes";
import { fittingNoteLabel } from "../../music/noteNames";
import { PIANO_WIDTH, pianoKeyByRow } from "../../piano/keyPositions";
import Piano from "../../piano/Piano";
import { soundingRows } from "../../playback/playedNotes";
import { labelFontSize, NOTE_LABEL_FAMILY, noteVisuals } from "../../playback/noteVisuals";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { grays, semantic } from "../../ui";
import type { PlayClock } from "./playQueue";

/** How far ahead the window shows, in seconds. */
const LEAD_SECONDS = 3;
/** Below this a rectangle is a sliver, so it is floored to stay visible. */
const MIN_NOTE_HEIGHT = 6;

export function FallingView({ part, clock }: { part: string; clock: PlayClock }) {
  const seconds = useSyncExternalStore(clock.subscribe, clock.get);
  const { artifact } = useWorkingArtifact();
  const working = useMemo(() => ({ frameMs: artifact.frameMs, audioUuid: part }), [artifact.frameMs, part]);
  const data = usePlayedNotes(working);
  const notes = useMemo(() => data.notes.filter((note) => !note.artifact && !note.removed), [data.notes]);
  const [sizeRef, size] = useElementSize<HTMLDivElement>();
  const width = size.width || 1;
  const height = size.height || 1;
  // Pixels per second of travel: the window is the whole plot.
  const velocity = height / LEAD_SECONDS;
  const pressed = useMemo(() => soundingRows(notes, seconds), [notes, seconds]);

  return (
    <Box
      data-play-falling
      sx={{ position: "fixed", inset: 0, display: "flex", flexDirection: "column", backgroundColor: grays.ink, zIndex: 1 }}
    >
      <Box ref={sizeRef} sx={{ flex: 1, minHeight: 0, position: "relative" }}>
        {data.loading ? (
          <Box sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
            <CircularProgress size={22} sx={{ color: grays.silver }} />
          </Box>
        ) : null}
        {data.error ? (
          <Typography sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", color: grays.silver }}>
            {data.error}
          </Typography>
        ) : null}
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
          {notes.map((note) => {
            const bottom = height - (note.startSeconds - seconds) * velocity;
            const noteHeight = Math.max(MIN_NOTE_HEIGHT, (note.endSeconds - note.startSeconds) * velocity);
            const top = bottom - noteHeight;
            if (bottom < 0 || top > height) return null;
            const key = pianoKeyByRow.get(note.row);
            if (!key) return null;
            const x = (key.x / PIANO_WIDTH) * width;
            const boxWidth = Math.max(4, (key.width / PIANO_WIDTH) * width - 2);
            const active = note.startSeconds <= seconds && seconds < note.endSeconds;
            const visuals = noteVisuals(
              { hand: note.hand, active, selected: false, ghost: false, staged: false },
              noteHeight,
              boxWidth,
            );
            const fontSize = labelFontSize(boxWidth);
            const label = fittingNoteLabel(note.midiNote, boxWidth, noteHeight, fontSize);
            return (
              <g key={note.id} data-note-id={note.id}>
                <rect
                  x={x + 1}
                  y={top}
                  width={boxWidth}
                  height={noteHeight}
                  rx={visuals.rx}
                  fill={visuals.fill}
                  stroke={visuals.stroke}
                  strokeWidth={visuals.strokeWidth}
                />
                {label ? (
                  <text
                    x={x + 1 + boxWidth / 2}
                    y={top + noteHeight / 2}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={fontSize}
                    fontFamily={NOTE_LABEL_FAMILY}
                    fontWeight={600}
                    fill={visuals.labelFill}
                  >
                    {label}
                  </text>
                ) : null}
              </g>
            );
          })}
          <line x1={0} x2={width} y1={height - 1.5} y2={height - 1.5} stroke={semantic.pressedKey} strokeWidth={3} />
        </svg>
      </Box>
      <Piano width="100%" height="auto" pressedKeys={pressed} ariaLabel="Piano receiving the falling notes" />
    </Box>
  );
}

export default FallingView;
