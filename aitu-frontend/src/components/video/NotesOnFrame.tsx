/**
 * The notes that will be written, drawn back onto the frame they came from.
 *
 * Task 4.3.1. Before `events.json` is written, what will be written is shown on
 * the video player — and the honest way to show it is to put each note back
 * where its rectangle is at this moment. A note that sounds at `start` has its
 * tip on the upper line at `start`, so at time `t` its tip is
 * `(start - t) x scrollSpeed` pixels above the line and its last tip is
 * `(end - t) x scrollSpeed` above that. If the reading is right, every box lands
 * on a rectangle; if it is not, that is something you can look at rather than
 * something you have to imagine.
 *
 * **The picking is the one the Piano Roll already has**, through
 * `useNoteSelection`: click a note and it becomes the selection, ⌘-click adds or
 * takes out, drag a band over empty picture and everything under it is picked,
 * click empty picture and nothing is. No second way of picking notes was
 * invented for this screen.
 *
 * **Shift-drag on a key draws a note the reading missed.** The key is the one
 * under the pointer and the two rows are the two times, read with the same
 * arithmetic — which is the only gesture on this picture that is not a
 * selection, and it is the one Task 4.3.1 asks for by name.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
import type { Calibration, PianoKey } from "../../api/frameExamples";
import type { VideoNote } from "../../api/video";
import { place } from "../../video/notePlacement";
import { palette, semantic } from "../../ui";

export interface NotesOnFrameProps {
  notes: VideoNote[];
  keys: PianoKey[];
  calibration: Calibration;
  /** Seconds of the sampled frame on screen. */
  seconds: number;
  /** Measured pixels a second: what turns a time back into a row (V-05). */
  pxPerSecond: number;
  scale: number;
  selected: ReadonlySet<string>;
  /** Notes staged for removal: drawn struck through, never hidden (V-30). */
  removed: ReadonlySet<string>;
  onPick: (id: string, additive: boolean) => void;
  /** The band being dragged, in picture coordinates, or null. */
  band: { x0: number; y0: number; x1: number; y1: number } | null;
  /** The note being drawn by hand, in picture coordinates, or null. */
  drawing: { key: PianoKey; yTop: number; yBottom: number } | null;
}


export function NotesOnFrame({
  notes,
  keys,
  calibration,
  seconds,
  pxPerSecond,
  scale,
  selected,
  removed,
  onPick,
  band,
  drawing,
}: NotesOnFrameProps) {
  const placed = place(notes, keys, calibration, seconds, pxPerSecond);

  const press = (event: ReactMouseEvent, id: string) => {
    event.stopPropagation();
    onPick(id, event.metaKey || event.ctrlKey);
  };

  return (
    <g>
      {placed.map((one) => {
        const isSelected = selected.has(one.id);
        const isRemoved = removed.has(one.id);
        const y = Math.max(calibration.rollTop, one.yTop);
        const height = Math.max(1, Math.min(calibration.upperLine, one.yBottom) - y);
        return (
          <g key={one.id}>
            <rect
              x={one.key.left}
              y={y}
              width={Math.max(1, one.key.right - one.key.left)}
              height={height}
              fill={isRemoved ? palette.dark.Gray : semantic.rightHand.onset}
              fillOpacity={isSelected ? 0.34 : 0.14}
              stroke={isSelected ? palette.dark.Blue : semantic.rightHand.onset}
              strokeWidth={(isSelected ? 2.4 : 1.2) * scale}
              strokeDasharray={isRemoved ? `${4 * scale} ${3 * scale}` : undefined}
              onMouseDown={(event) => press(event, one.id)}
              style={{ cursor: "pointer" }}
            />
            {isRemoved ? (
              <line
                x1={one.key.left}
                x2={one.key.right}
                y1={y + height / 2}
                y2={y + height / 2}
                stroke={palette.dark.Red}
                strokeWidth={2 * scale}
                style={{ pointerEvents: "none" }}
              />
            ) : null}
          </g>
        );
      })}

      {band ? (
        <rect
          x={Math.min(band.x0, band.x1)}
          y={Math.min(band.y0, band.y1)}
          width={Math.abs(band.x1 - band.x0)}
          height={Math.abs(band.y1 - band.y0)}
          fill={palette.dark.Blue}
          fillOpacity={0.12}
          stroke={palette.dark.Blue}
          strokeWidth={1.2 * scale}
          style={{ pointerEvents: "none" }}
        />
      ) : null}

      {drawing ? (
        <rect
          x={drawing.key.left}
          y={Math.min(drawing.yTop, drawing.yBottom)}
          width={Math.max(1, drawing.key.right - drawing.key.left)}
          height={Math.max(1, Math.abs(drawing.yBottom - drawing.yTop))}
          fill={palette.dark.Green}
          fillOpacity={0.3}
          stroke={palette.dark.Green}
          strokeWidth={2 * scale}
          style={{ pointerEvents: "none" }}
        />
      ) : null}
    </g>
  );
}

export default NotesOnFrame;
