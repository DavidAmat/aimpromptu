/**
 * A small keyboard to pick one key (plan section 7.4): the **From** and **To** of a notes
 * transposition, the key of a grace note.
 *
 * The 88 keys at half the size of the drawn piano (624 px), in a container that scrolls on a narrow
 * screen and starts with the picked key in view. The name of a key is Spanish, as everywhere a key
 * is named to the user (`Do 4` is middle C), and shows on hover. With the keyboard focused, the
 * arrows move by a semitone (left, right) or an octave (up, down).
 */

import { useEffect, useRef, type KeyboardEvent } from "react";
import Box from "@mui/material/Box";
import { spanishNoteShort } from "../music/noteNames";
import { pianoKeyPositions, PIANO_HEIGHT, PIANO_WIDTH } from "../piano/keyPositions";
import { grays, semantic } from "./palette";
import { useScheme } from "./schemeContext";
import { ui } from "./tokens";

const SCALE = 0.5;
const LOWEST = 21;
const HIGHEST = 108;

export interface MiniPianoProps {
  /** The picked key, as a MIDI number; `null` when none is picked. */
  value: number | null;
  onChange: (midi: number) => void;
  /** What the key is for, for a screen reader: "Transpose from". */
  label: string;
  disabled?: boolean;
}

export function MiniPiano({ value, onChange, label, disabled }: MiniPianoProps) {
  useScheme();
  const scroller = useRef<HTMLDivElement | null>(null);
  const width = PIANO_WIDTH * SCALE;
  const height = PIANO_HEIGHT * SCALE * 0.7;
  const whites = pianoKeyPositions.filter((key) => key.type === "white");
  const blacks = pianoKeyPositions.filter((key) => key.type === "black");

  // The picked key in view when the keyboard is wider than its container.
  useEffect(() => {
    const box = scroller.current;
    const key = pianoKeyPositions.find((one) => one.midi === value);
    if (!box || !key) return;
    const x = key.x * SCALE;
    if (x < box.scrollLeft || x > box.scrollLeft + box.clientWidth - 20) box.scrollLeft = x - box.clientWidth / 2;
  }, [value]);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (disabled) return;
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -12, ArrowUp: 12 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const from = value ?? 60;
    onChange(Math.min(HIGHEST, Math.max(LOWEST, from + step)));
  };

  const fill = (midi: number, black: boolean) =>
    midi === value ? semantic.rightHand.onset : black ? grays.charcoal : ui.paper;

  return (
    <Box
      ref={scroller}
      role="slider"
      tabIndex={disabled ? -1 : 0}
      aria-label={label}
      aria-valuemin={LOWEST}
      aria-valuemax={HIGHEST}
      aria-valuenow={value ?? undefined}
      aria-valuetext={value === null ? "No key" : spanishNoteShort(value)}
      onKeyDown={onKeyDown}
      sx={{
        overflowX: "auto",
        maxWidth: "100%",
        borderRadius: 1,
        opacity: disabled ? 0.5 : 1,
        "&:focus-visible": { outline: `2px solid ${ui.text}`, outlineOffset: 2 },
      }}
    >
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
        {[...whites, ...blacks].map((key) => {
          const black = key.type === "black";
          return (
            <rect
              key={key.midi}
              x={key.x * SCALE + 0.5}
              y={0.5}
              width={key.width * SCALE - 1}
              height={(black ? height * 0.62 : height) - 1}
              rx={1.5}
              fill={fill(key.midi, black)}
              stroke={black ? grays.charcoal : ui.lineStrong}
              strokeWidth={1}
              style={{ cursor: disabled ? "default" : "pointer" }}
              onClick={() => !disabled && onChange(key.midi)}
              data-midi={key.midi}
            >
              <title>{spanishNoteShort(key.midi)}</title>
            </rect>
          );
        })}
      </svg>
    </Box>
  );
}

export default MiniPiano;
