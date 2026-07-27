/**
 * Brand palette — the single source of truth for color in this app.
 *
 * Ported from `context/colors/color-palette.md` (originally a Python dict for
 * seaborn). Alias names are kept verbatim so a conversation about "dark Green"
 * or "light Blue" maps 1:1 onto the code.
 *
 * Rule: no component ever writes a hex literal. Import `palette` for a raw
 * alias, or `semantic` for a decided product meaning.
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
 * The extra grays the palette doc explicitly allows ("free to use all the
 * spectrum of grays you want"). Defined here so they are still not hex
 * literals scattered across components.
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
  /** Processing-step pills (raw -> collapsed -> clean -> two-hands). */
  steps: {
    raw: palette.dark.Gray,
    collapsed: palette.dark.Lavender,
    clean: palette.dark.Cyan,
    "two-hands": palette.dark.Blue,
  },
  /** Feedback states, reused by MUI's theme palette. */
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
} as const;

/** Hand-aware lookup used by the matrix grid and the roll views. */
export function handColors(hand: "left" | "right" | "single") {
  if (hand === "left") return semantic.leftHand;
  if (hand === "right") return semantic.rightHand;
  return semantic.matrixOneHand;
}
