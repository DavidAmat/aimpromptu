/** Scalable 88-key piano with reusable pressed-key SVG overlays. */

import type { CSSProperties } from "react";
import { PIANO_HEIGHT, PIANO_WIDTH, pianoKeyPositions } from "./keyPositions";
import { grays } from "../ui/palette";

/** How big the octave number on each Do is, and how far its baseline sits off the key's foot. */
const OCTAVE_LABEL_SIZE = 11;
const OCTAVE_LABEL_BASELINE = 8;

export interface PianoProps {
  pressedKeys?: Iterable<number>;
  /**
   * A colour for particular keys, overriding the one the pressed-key artwork carries.
   *
   * The keyboard says *what* is sounding; on a two-staff page a reader also needs to know *which
   * hand* is playing it, and colour is the only thing on a keyboard left to say it with. A row
   * named here is drawn in that colour whether or not it is in `pressedKeys`, so a caller can
   * colour exactly the notes it knows about and leave the rest to the artwork.
   */
  keyColours?: Readonly<Record<number, string>>;
  /**
   * A key was clicked, by row. Leave it out and the keyboard is a picture, which is what the views
   * that only report what is sounding want.
   */
  onKeyPress?: (row: number) => void;
  orientation?: "horizontal" | "vertical";
  width?: number | string;
  height?: number | string;
  style?: CSSProperties;
  ariaLabel?: string;
  /** What each key is called on hover, when the keyboard can be clicked. */
  keyTitle?: (row: number) => string;
}

export function Piano({
  pressedKeys = [],
  keyColours,
  onKeyPress,
  orientation = "horizontal",
  width = "100%",
  height = "auto",
  style,
  ariaLabel = "88-key piano",
  keyTitle,
}: PianoProps) {
  const pressed = new Set(pressedKeys);
  const vertical = orientation === "vertical";
  // `height="auto"` is not a length, so as an SVG *attribute* it is rejected and
  // the browser logs an error. As a *style* it is the ordinary CSS keyword and
  // does what the caller means: take the height the aspect ratio implies.
  const autoHeight = height === "auto";
  /**
   * Lit at all, and lit in a colour of its own.
   *
   * A colour named for a key lights it. The alternative — only colouring keys that are already in
   * `pressedKeys` — would make every caller pass the same rows twice.
   */
  const litRows = new Set([...pressed, ...Object.keys(keyColours ?? {}).map(Number)]);
  const lit = pianoKeyPositions.filter((key) => litRows.has(key.row));
  const litWhite = lit.filter((key) => key.type === "white");
  const litBlack = lit.filter((key) => key.type === "black");
  /** A key drawn in its own colour is a rectangle; one in the default colour is the artwork. */
  const colourOf = (row: number) => keyColours?.[row];

  const keyboard = (
    <g>
      {/* 1. Normal white keys. */}
      <image href="/piano/piano-base.svg" x={0} y={0} width={PIANO_WIDTH} height={PIANO_HEIGHT} />
      {/* 2. Pressed white keys. */}
      {litWhite.map((key) => {
        const colour = colourOf(key.row);
        return colour ? (
          <rect
            key={key.row}
            x={key.x + 0.5}
            y={key.y + 0.5}
            width={key.width - 1}
            height={key.height - 1}
            rx={2}
            fill={colour}
            stroke={grays.charcoal}
          />
        ) : (
          <image
            key={key.row}
            href="/piano/pressed-white-key.svg"
            x={key.x}
            y={key.y}
            width={key.width}
            height={key.height}
            opacity={1}
          />
        );
      })}
      {/* 3. Every normal black key, always above white-key highlights. */}
      <image
        href="/piano/piano-black-keys.svg"
        x={0}
        y={0}
        width={PIANO_WIDTH}
        height={PIANO_HEIGHT}
      />
      {/* 4. Pressed black keys. */}
      {litBlack.map((key) => {
        const colour = colourOf(key.row);
        return colour ? (
          <rect
            key={key.row}
            x={key.x + 0.5}
            y={key.y + 0.5}
            width={key.width - 1}
            height={key.height - 1}
            rx={2}
            fill={colour}
            stroke={grays.charcoal}
          />
        ) : (
          <image
            key={key.row}
            href="/piano/pressed-black-key.svg"
            x={key.x}
            y={key.y}
            width={key.width}
            height={key.height}
            opacity={1}
          />
        );
      })}
      {/*
        5. The octave numbers, one on every Do.

        A keyboard of eighty-eight keys has no landmarks. Middle C looks exactly like every other C,
        so saying which note is lit means counting white keys from one end — and a reader who wants
        to tell somebody "the B4 is wrong" has no way to know it is the B4. One small number at the
        foot of each Do is the whole fix, and it is what a beginner's keyboard has printed on it.

        The number is the octave in the same reckoning the rest of the app uses: middle C is C4, so
        the Do below it carries a 3 and the Do above a 5. Drawn after the lit keys so it survives on
        a coloured one, and in white there, because slate on a filled key is hard to read.

        Left off when the keyboard is stood on end. There the whole drawing is turned a quarter
        turn, so the numbers would lie on their sides, and that view labels its own notes anyway.
      */}
      {vertical
        ? null
        : pianoKeyPositions
            .filter((key) => key.type === "white" && key.midi % 12 === 0)
            .map((key) => (
              <text
                key={`octave-${key.row}`}
                x={key.x + key.width / 2}
                y={PIANO_HEIGHT - OCTAVE_LABEL_BASELINE}
                textAnchor="middle"
                fontSize={OCTAVE_LABEL_SIZE}
                fontFamily="Inter, ui-sans-serif, system-ui, sans-serif"
                fill={litRows.has(key.row) ? grays.white : grays.slate}
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {key.midi / 12 - 1}
              </text>
            ))}

      {/*
        6. The targets, last of all and invisible.

        Drawn as their own layer rather than by making the artwork clickable, because the artwork is
        four images: the white keys are one picture, so there is nothing in it to attach a key to.
        The black ones come after the white ones for the usual reason — where they overlap, the
        black key is the one on top and the one a reader means.
      */}
      {onKeyPress
        ? [
            ...pianoKeyPositions.filter((key) => key.type === "white"),
            ...pianoKeyPositions.filter((key) => key.type === "black"),
          ].map((key) => (
            <rect
              key={`hit-${key.row}`}
              x={key.x}
              y={key.y}
              width={key.width}
              height={key.height}
              fill="transparent"
              stroke="none"
              style={{ cursor: "pointer" }}
              role="button"
              tabIndex={-1}
              aria-label={keyTitle?.(key.row) ?? key.en}
              onClick={(event) => {
                event.stopPropagation();
                onKeyPress(key.row);
              }}
            >
              <title>{keyTitle?.(key.row) ?? key.en}</title>
            </rect>
          ))
        : null}
    </g>
  );

  return (
    <svg
      viewBox={vertical ? `0 0 ${PIANO_HEIGHT} ${PIANO_WIDTH}` : `0 0 ${PIANO_WIDTH} ${PIANO_HEIGHT}`}
      width={width}
      height={autoHeight ? undefined : height}
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
      style={{ display: "block", ...(autoHeight ? { height: "auto" } : null), ...style }}
    >
      {/*
        Standing the keyboard up turns it a quarter turn *anticlockwise*, not
        clockwise. That puts the bass at the bottom and the treble at the top,
        which is how a roll is read, and it leaves the fronts of the white keys
        facing right — towards the notes arriving at them.
      */}
      {vertical ? <g transform={`translate(0 ${PIANO_WIDTH}) rotate(-90)`}>{keyboard}</g> : keyboard}
    </svg>
  );
}

export default Piano;
