/** Scalable 88-key piano with reusable pressed-key SVG overlays. */

import type { CSSProperties } from "react";
import { PIANO_HEIGHT, PIANO_WIDTH, pianoKeyPositions } from "./keyPositions";

export interface PianoProps {
  pressedKeys?: Iterable<number>;
  orientation?: "horizontal" | "vertical";
  width?: number | string;
  height?: number | string;
  style?: CSSProperties;
  ariaLabel?: string;
}

export function Piano({
  pressedKeys = [],
  orientation = "horizontal",
  width = "100%",
  height = "auto",
  style,
  ariaLabel = "88-key piano",
}: PianoProps) {
  const pressed = new Set(pressedKeys);
  const vertical = orientation === "vertical";
  const pressedWhite = pianoKeyPositions.filter(
    (key) => key.type === "white" && pressed.has(key.row),
  );
  const pressedBlack = pianoKeyPositions.filter(
    (key) => key.type === "black" && pressed.has(key.row),
  );

  const keyboard = (
    <g>
      {/* 1. Normal white keys. */}
      <image href="/piano/piano-base.svg" x={0} y={0} width={PIANO_WIDTH} height={PIANO_HEIGHT} />
      {/* 2. Pressed white keys. */}
      {pressedWhite.map((key) => (
        <image
          key={key.row}
          href="/piano/pressed-white-key.svg"
          x={key.x}
          y={key.y}
          width={key.width}
          height={key.height}
          opacity={1}
        />
      ))}
      {/* 3. Every normal black key, always above white-key highlights. */}
      <image
        href="/piano/piano-black-keys.svg"
        x={0}
        y={0}
        width={PIANO_WIDTH}
        height={PIANO_HEIGHT}
      />
      {/* 4. Pressed black keys. */}
      {pressedBlack.map((key) => (
        <image
          key={key.row}
          href="/piano/pressed-black-key.svg"
          x={key.x}
          y={key.y}
          width={key.width}
          height={key.height}
          opacity={1}
        />
      ))}
    </g>
  );

  return (
    <svg
      viewBox={vertical ? `0 0 ${PIANO_HEIGHT} ${PIANO_WIDTH}` : `0 0 ${PIANO_WIDTH} ${PIANO_HEIGHT}`}
      width={width}
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
      style={{ display: "block", ...style }}
    >
      {vertical ? <g transform={`translate(${PIANO_HEIGHT} 0) rotate(90)`}>{keyboard}</g> : keyboard}
    </svg>
  );
}

export default Piano;
