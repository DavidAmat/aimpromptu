/**
 * The words of a lyrics block on the page (implementation 03, Phase 8A++): its fonts, its sizes, and the wrap the page
 * shows while a block is made narrower or wider.
 *
 * The backend wraps a block's words to its width with the widths of these same fonts (`sheet/engrave/lyric_text.py`,
 * measured from `public/fonts` by `scripts/measure-lyric-fonts.mjs`) and draws the lines. While a side handle is
 * dragged the page wraps the words itself, measured with a canvas, so they follow the pointer; the drawing that comes
 * back when the pointer is let go has the same lines.
 */

import type { LyricFont } from "../../../../api";

/** The size of the words, in staff spaces: the default and the limits (the backend's `LYRIC_SIZE`, ...). */
export const LYRIC_SIZE = 1.4;
export const LYRIC_MIN = 0.8;
export const LYRIC_MAX = 4.2;
/** The distance between two lines of a block, in its size (the engine's `LYRIC_LEADING`). */
export const LYRIC_LEADING = 1.2;

/** The fonts of the lyrics toolbox, as the drawing names them (`svg.LYRIC_FAMILIES`). */
export const LYRIC_FONTS: readonly { value: LyricFont; label: string; family: string }[] = [
  { value: "lora", label: "Lora", family: "Lora, Georgia, serif" },
  { value: "geist", label: "Geist", family: "Geist, system-ui, sans-serif" },
  { value: "montserrat", label: "Montserrat", family: "Montserrat, system-ui, sans-serif" },
];

export function familyOf(font: LyricFont | undefined): string {
  return (LYRIC_FONTS.find((one) => one.value === font) ?? LYRIC_FONTS[0]!).family;
}

let canvas: CanvasRenderingContext2D | null = null;

/** The width of one line of words at `size` (any unit: the answer is in the same). */
function widthOf(text: string, size: number, font: LyricFont | undefined, bold: boolean, italic: boolean): number {
  canvas ??= document.createElement("canvas").getContext("2d");
  if (!canvas) return text.length * size * 0.5;
  // Measured at 100 px and scaled: a canvas rounds small sizes.
  canvas.font = `${italic ? "italic" : "normal"} ${bold ? 700 : 400} 100px ${familyOf(font)}`;
  return (canvas.measureText(text).width / 100) * size;
}

/** The lines of a block's words: one per line break, and each wrapped at the spaces to `width` (the backend's rule). */
export function wrapWords(
  text: string,
  width: number | null | undefined,
  size: number,
  font: LyricFont | undefined,
  bold: boolean,
  italic: boolean,
): string[] {
  return text.split("\n").flatMap((paragraph) => {
    const words = paragraph.split(/\s+/).filter(Boolean);
    if (!width || words.length < 2) return [width ? words.join(" ") : paragraph];
    const out: string[] = [];
    let line = words[0]!;
    for (const word of words.slice(1)) {
      const longer = `${line} ${word}`;
      if (widthOf(longer, size, font, bold, italic) <= width) line = longer;
      else {
        out.push(line);
        line = word;
      }
    }
    out.push(line);
    return out;
  });
}
