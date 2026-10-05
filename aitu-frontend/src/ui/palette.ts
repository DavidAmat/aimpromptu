/**
 * The colours of the music: the two hands, the selection, the piano roll, the
 * waveform, the marks drawn over a note or a video frame.
 *
 * Everything around the music (page, sidebar, text, lines, buttons) is black, white
 * and grey and comes from `tokens.ts` (implementation 02, plan section 7.1). This
 * file is the one place colour is spent, so the sheet and the piano roll are the
 * most colourful things on any screen.
 *
 * The aliases are the ones of `context/colors/color-palette.md`, kept verbatim so a
 * conversation about "dark Green" or "light Blue" maps 1:1 onto the code. No
 * component writes a hex literal: it imports `palette` for a raw alias, or
 * `semantic` for a decided meaning.
 */

export type Shade = "dark" | "light";

export type ColorAlias =
  | "Blue"
  | "Pink"
  | "Lavender"
  | "Yellow"
  | "Green"
  | "Orange"
  | "Brown"
  | "Red"
  | "Cyan"
  | "Gray";

export const palette: Record<Shade, Record<ColorAlias, string>> = {
  dark: {
    Blue: "#4681ff",
    Pink: "#ff6495",
    Lavender: "#816eff",
    Yellow: "#ffc83c",
    Green: "#3cdcb4",
    Orange: "#ff8b32",
    Brown: "#664E3C",
    Red: "#FE6060",
    Cyan: "#00E7E7",
    Gray: "#393939",
  },
  light: {
    Blue: "#A2C0FF",
    Pink: "#FFB1CA",
    Lavender: "#C0B6FF",
    Yellow: "#FFE39D",
    Green: "#9DEDD9",
    Orange: "#FFC598",
    Brown: "#B2A69D",
    Red: "#FEAFAF",
    Cyan: "#B2F7F7",
    Gray: "#9C9C9C",
  },
};

/**
 * The greys of the drawn music: the ink of a struck note, the grey of a held one,
 * the keys of a drawn piano. The greys of the page are tokens (`tokens.ts`).
 */
export const grays = {
  ink: "#151515",
  charcoal: "#242424",
  slate: "#5A5A5A",
  silver: "#C7C7C7",
  mist: "#E6E6E6",
  paper: "#FAFAFA",
  white: "#FFFFFF",
} as const;

/**
 * Product meanings decided by the features spec. Components reference these,
 * not the raw aliases, whenever the color carries meaning.
 */
export const semantic = {
  /** Matrix grid, one-hand view: struck vs held. */
  matrixOneHand: {
    onset: grays.ink,
    sustain: grays.silver,
  },
  /** Matrix grid and piano roll, two-hands view. */
  leftHand: {
    onset: palette.dark.Green,
    sustain: palette.light.Green,
  },
  rightHand: {
    onset: palette.dark.Blue,
    sustain: palette.light.Blue,
  },
  /** Piano SVG: a key currently sounding. */
  pressedKey: palette.dark.Blue,
  /** Marks drawn on the music: a note marked to come off, a recording dot, a live feed. */
  status: {
    info: palette.dark.Blue,
    success: palette.dark.Green,
    warning: palette.dark.Orange,
    error: palette.dark.Red,
  },
  /** Waveform / range selector. */
  waveform: {
    body: palette.light.Blue,
    selection: palette.dark.Lavender,
    cursor: palette.dark.Pink,
  },
  /**
   * The Notes tab's piano roll visualization (implementation 08, plan section 9.5): a dark panel,
   * as in the MuScriptor examples, so the rectangles are the brightest thing on it.
   *
   * The notes before the hand split are orange, not the red of the examples: on this app red
   * means "no hand" or "marked to come off", and blue and green are the two hands.
   */
  roll: {
    background: "#1d1e23",
    /** The rows of the black keys, a little darker, so the octaves can be read at a glance. */
    blackRow: "#17181c",
    /** The line under every C. */
    octaveLine: "#2b2d35",
    grid: "#2a2c33",
    gridStrong: "#3a3d46",
    ruler: "#15161a",
    rulerText: "#9a9eab",
    /** The part of the piece the live transcription has already covered. */
    transcribed: "rgba(255, 255, 255, 0.035)",
    /** After the end of the piece. */
    afterEnd: "rgba(0, 0, 0, 0.35)",
    keyWhite: "#d9dbe2",
    keyBlack: "#2a2b31",
    keyLine: "#8e919c",
    keyLabel: "#3a3c44",
    note: palette.dark.Orange,
    noteBorder: "rgba(0, 0, 0, 0.45)",
    selected: palette.light.Lavender,
    selectedBorder: palette.dark.Lavender,
    band: "rgba(192, 182, 255, 0.16)",
    playhead: palette.dark.Pink,
  },
} as const;

/** Hand-aware lookup used by the matrix grid and the roll views. */
export function handColors(hand: "left" | "right" | "single") {
  if (hand === "left") return semantic.leftHand;
  if (hand === "right") return semantic.rightHand;
  return semantic.matrixOneHand;
}
