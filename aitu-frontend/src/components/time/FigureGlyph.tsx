/**
 * The seven figures, drawn small enough to put on a button.
 *
 * A picker that says "Corchea (eighth)" in a dropdown asks a reader to translate twice: from the
 * shape they can see on the page to a word, and from the word back to the shape. A row of the
 * shapes themselves is one glance, and it is how every notation program has asked this question for
 * thirty years.
 *
 * Drawn here rather than taken from the engraving font, for one reason: the font belongs to the
 * drawing package and is installed into the document by it, so a control that used it would go
 * blank on any screen where the sheet has not been drawn yet — which includes the first thing a
 * reader sees. These are seven shapes; the cost of owning them is a file this size.
 *
 * The proportions are the conventional ones: a notehead a little over one staff space wide, tilted
 * about twenty degrees, and a stem some three and a half spaces tall on the right of it.
 */

import type { FigureName } from "../../api";
import { FIGURE_SHORT } from "../../music/figures";

/** How many flags hang off the stem, and whether the head is filled and has one at all. */
const SHAPE: Record<FigureName, { filled: boolean; stem: boolean; flags: number; dot: boolean }> = {
  redonda: { filled: false, stem: false, flags: 0, dot: false },
  blanca: { filled: false, stem: true, flags: 0, dot: false },
  dottedBlanca: { filled: false, stem: true, flags: 0, dot: true },
  negra: { filled: true, stem: true, flags: 0, dot: false },
  dottedNegra: { filled: true, stem: true, flags: 0, dot: true },
  corchea: { filled: true, stem: true, flags: 1, dot: false },
  semicorchea: { filled: true, stem: true, flags: 2, dot: false },
  fusa: { filled: true, stem: true, flags: 3, dot: false },
  semifusa: { filled: true, stem: true, flags: 4, dot: false },
};

/** Where the notehead sits in the box, and how far the stem reaches. */
const HEAD_X = 8.5;
const HEAD_Y = 25;
const HEAD_RX = 5.4;
const HEAD_RY = 3.9;
const STEM_X = 13.6;
const STEM_TOP = 4;
/** The first flag hangs from the top of the stem; each one after it is this far down. */
const FLAG_STEP = 4.2;

export interface FigureGlyphProps {
  figure: FigureName;
  /** How tall the glyph is drawn, in pixels. The box keeps its proportions. */
  size?: number;
  /** Anything that is not `currentColor` — a pill that is filled draws its own contrast. */
  colour?: string;
}

export function FigureGlyph({
  figure,
  size = 26,
  colour = "currentColor",
}: FigureGlyphProps) {
  const shape = SHAPE[figure];
  const width = (size * 26) / 32;
  return (
    <svg
      viewBox="0 0 26 32"
      width={width}
      height={size}
      role="img"
      aria-label={FIGURE_SHORT[figure]}
      style={{ display: "block", overflow: "visible" }}
    >
      {/*
        A redonda has no stem, so its head is drawn a touch wider and upright — which is what a
        whole note actually looks like. Everything else is the tilted oval.
      */}
      <ellipse
        cx={HEAD_X}
        cy={HEAD_Y}
        rx={shape.stem ? HEAD_RX : HEAD_RX + 0.9}
        ry={HEAD_RY}
        transform={shape.stem ? `rotate(-20 ${HEAD_X} ${HEAD_Y})` : undefined}
        fill={shape.filled ? colour : "none"}
        stroke={colour}
        strokeWidth={shape.filled ? 0 : 1.7}
      />
      {shape.stem ? (
        <line
          x1={STEM_X}
          y1={HEAD_Y - 1.4}
          x2={STEM_X}
          y2={STEM_TOP}
          stroke={colour}
          strokeWidth={1.5}
          strokeLinecap="round"
        />
      ) : null}
      {Array.from({ length: shape.flags }, (_, index) => (
        <path
          key={index}
          // One hook per beam level, each starting a little further down the stem — which is how a
          // fusa reads as three beams rather than as one thick smear.
          d={`M ${STEM_X} ${STEM_TOP + index * FLAG_STEP}
              c 4.6 1.6 6.4 4.2 5.6 7.6
              c -0.6 -3.4 -2.6 -4.8 -5.6 -5.4 Z`}
          fill={colour}
          stroke="none"
        />
      ))}
      {shape.dot ? (
        <circle cx={HEAD_X + HEAD_RX + 3.4} cy={HEAD_Y} r={1.5} fill={colour} />
      ) : null}
    </svg>
  );
}

export default FigureGlyph;
