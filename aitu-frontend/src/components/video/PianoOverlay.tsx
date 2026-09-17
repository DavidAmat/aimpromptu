/**
 * The rendered piano overlay, drawn on the picture in its own pixels.
 *
 * One element per key, from the per-key borders of the calibration (V-38). It
 * is the same overlay everywhere it is needed — fitting the keyboard, marking
 * what is sounding, and looking at what the detector saw — because they are all
 * the same picture with the same keys on it.
 *
 * The keys are drawn inside the one rectangle the user placed (V-37): a group
 * translated to its top left corner and turned by its angle, so a border is
 * drawn where it was measured, along the rectangle's own top edge. A white key
 * runs from the top edge to the bottom of the rectangle, a black key to the
 * depth the finder measured.
 *
 * Hovering a key shows its name, so a wrong octave is obvious at a glance
 * (Task 2.1.3 of 04). No pitch here comes from a colour (V-10). A press on a
 * key is a press and nothing more: the two gestures that moved the grid are
 * gone with the grid.
 */

import type { MouseEvent as ReactMouseEvent } from "react";
import type { Calibration, PianoKey } from "../../api/frameExamples";
import { topEdgeU } from "../../video/overlayGeometry";
import { palette, surface } from "../../ui";
import { markColours, rectColours, type MarkState } from "./overlayColours";

const radians = (degrees: number) => degrees * (Math.PI / 180);
/** How wide the grab strip of a border is, in screen pixels. */
const BORDER_GRAB_SCREEN_PX = 7;

export interface PianoOverlayProps {
  calibration: Calibration;
  keys: PianoKey[];
  /** Picture pixels per screen pixel, so text and rules keep their size. */
  scale: number;
  /** What each key is marked as, by MIDI. Anything missing is released (V-19). */
  marks?: Record<number, MarkState>;
  /** A press on a key. */
  onKeyClick?: (key: PianoKey) => void;
  /** The keys picked out, by MIDI. */
  selectedMidis?: number[];
  hoveredMidi?: number | null;
  onHover?: (midi: number | null) => void;
  /** Black keys the finder placed through an occlusion: drawn dashed. */
  dashedMidis?: number[];
  /** Of those, the ones the pixels confirmed: drawn dotted. */
  dottedMidis?: number[];
  /** White key borders the user dragged by hand, by index: drawn in the user's colour. */
  correctedBorders?: number[];
  /**
   * Take one white key border and drag it along the top edge, told its index
   * and where it now is in u. Set only on the fitting step.
   */
  onBorderDrag?: (index: number, u: number) => void;
  /** Told when a border drag starts and ends, so the canvas stops panning. */
  onGesture?: (active: boolean) => void;
}

export function PianoOverlay({
  calibration,
  keys,
  scale,
  marks = {},
  onKeyClick,
  selectedMidis,
  hoveredMidi = null,
  onHover,
  dashedMidis,
  dottedMidis,
  correctedBorders,
  onBorderDrag,
  onGesture,
}: PianoOverlayProps) {
  const rect = calibration.pianoRect;
  const selected = new Set(selectedMidis ?? []);
  const dashed = new Set(dashedMidis ?? []);
  const dotted = new Set(dottedMidis ?? []);
  const corrected = new Set(correctedBorders ?? []);

  /** A border drag: the pointer's travel turned into a distance along the top edge. */
  const startBorder = (index: number) => (event: ReactMouseEvent) => {
    if (!onBorderDrag) return;
    event.stopPropagation();
    const a = radians(rect.angle);
    const origin = { x: event.clientX, y: event.clientY, u: calibration.whiteBorders[index] };
    onGesture?.(true);
    const move = (native: MouseEvent) => {
      const dx = (native.clientX - origin.x) * scale;
      const dy = (native.clientY - origin.y) * scale;
      onBorderDrag(index, origin.u + dx * Math.cos(a) + dy * Math.sin(a));
    };
    const stop = () => {
      onGesture?.(false);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
  };
  const whites = keys.filter((key) => key.kind === "white");
  const blacks = keys.filter((key) => key.kind === "black");

  const press = (key: PianoKey) => (event: ReactMouseEvent) => {
    if (!onKeyClick) return;
    event.stopPropagation();
    onKeyClick(key);
  };

  const draw = (key: PianoKey) => {
    const mark = marks[key.midi] ?? "released";
    const height = key.kind === "white" ? rect.height : calibration.blackDepth;
    const hovered = hoveredMidi === key.midi;
    const picked = selected.has(key.midi);
    // Back from picture x to a distance along the top edge, where it is drawn.
    const u0 = topEdgeU(calibration, key.left);
    const u1 = topEdgeU(calibration, key.right);
    return (
      <g key={key.midi}>
        <rect
          x={u0}
          y={0}
          width={Math.max(0.5, u1 - u0)}
          height={height}
          fill={picked ? palette.dark.Red : mark === "released" ? "transparent" : markColours[mark]}
          fillOpacity={picked ? 0.35 : mark === "released" ? 0 : 0.8}
          stroke={picked ? palette.dark.Red : hovered ? palette.dark.Lavender : surface.strongLine}
          strokeWidth={(picked ? 2.5 : hovered ? 2 : key.kind === "black" ? 0.8 : 0.6) * scale}
          strokeDasharray={
            dotted.has(key.midi)
              ? `${1.5 * scale} ${2 * scale}`
              : dashed.has(key.midi)
                ? `${4 * scale} ${3 * scale}`
                : undefined
          }
          // With nothing to press, a key lets the pointer through: on the fitting
          // step the one rectangle sits under the overlay and is dragged by its
          // body, and the border grab strips are the overlay's only gesture.
          style={{ cursor: onKeyClick ? "pointer" : "default", pointerEvents: onKeyClick ? undefined : "none" }}
          onMouseDown={press(key)}
          onMouseEnter={() => onHover?.(key.midi)}
          onMouseLeave={() => onHover?.(null)}
        >
          <title>{`${key.nameEn} · ${key.nameEs}`}</title>
        </rect>
        {hovered ? (
          <text
            x={(u0 + u1) / 2}
            y={height + 11 * scale}
            fill={surface.text}
            fontSize={10 * scale}
            textAnchor="middle"
            style={{ pointerEvents: "none", paintOrder: "stroke" }}
            stroke={surface.panel}
            strokeWidth={3 * scale}
          >
            {key.nameEn}
          </text>
        ) : null}
      </g>
    );
  };

  return (
    <g transform={`translate(${rect.x} ${rect.y}) rotate(${rect.angle})`}>
      {/* White keys first, then black ones on top: the same order a piano has. */}
      {whites.map(draw)}
      {blacks.map(draw)}
      {/* The white key borders, when they may be dragged: a grab strip down each,
          and the user's colour on the ones the user moved. */}
      {onBorderDrag
        ? calibration.whiteBorders.map((u, index) => (
            <g key={`border-${index}`}>
              {corrected.has(index) ? (
                <line
                  x1={u}
                  y1={0}
                  x2={u}
                  y2={rect.height}
                  stroke={rectColours.black}
                  strokeWidth={1.6 * scale}
                  style={{ pointerEvents: "none" }}
                />
              ) : null}
              <rect
                x={u - (BORDER_GRAB_SCREEN_PX * scale) / 2}
                y={0}
                width={BORDER_GRAB_SCREEN_PX * scale}
                height={rect.height}
                fill="transparent"
                style={{ cursor: "ew-resize" }}
                onMouseDown={startBorder(index)}
              >
                <title>drag this border along the top of the keys</title>
              </rect>
            </g>
          ))
        : null}
    </g>
  );
}

export default PianoOverlay;
