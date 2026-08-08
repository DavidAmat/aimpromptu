/**
 * One rendered page, read off the DOM and written out as PDF drawing operators.
 *
 * The sheet is already vector when it reaches here — the drawing package emits an SVG of lines,
 * rectangles, filled polygons and glyphs, and nothing else. So the page is not photographed and
 * pasted in: every one of those becomes the PDF operator that means the same thing, and the result
 * is as sharp as the printer is rather than as sharp as whatever resolution we chose to snapshot
 * at. It is also a fraction of the size, which matters when a piece runs to thirty pages.
 *
 * Everything is read through `getComputedStyle` and `getCTM` rather than off the attributes,
 * because a colour may arrive as a stylesheet rule and a brace is drawn inside a scaled group. What
 * the browser worked out is what the page shows, so it is what gets written.
 */

import type { EmbeddableFont } from "./opentype";

/** A 2×3 affine matrix, in the order PDF's `cm` operator wants. */
type Matrix = [number, number, number, number, number, number];

const IDENTITY: Matrix = [1, 0, 0, 1, 0, 0];

function multiply(outer: Matrix, inner: Matrix): Matrix {
  const [a, b, c, d, e, f] = outer;
  const [a2, b2, c2, d2, e2, f2] = inner;
  return [
    a * a2 + c * b2,
    b * a2 + d * b2,
    a * c2 + c * d2,
    b * c2 + d * d2,
    a * e2 + c * f2 + e,
    b * e2 + d * f2 + f,
  ];
}

/** Two decimals is a hundredth of a CSS pixel — far under what a printer can resolve. */
const n = (value: number): string =>
  Number.isFinite(value) ? String(Math.round(value * 100) / 100) : "0";

export interface DrawnPage {
  /** The content stream, in CSS pixels with y running down the page. */
  ops: string;
  /** Every glyph asked for from the embedded font, so its widths can be written. */
  glyphs: Set<number>;
  /** Every constant alpha used, so a graphics state can be made for each. */
  alphas: Set<number>;
}

/** Which PDF font a drawn run is written with. `notation` is the embedded one. */
type FontChoice = "notation" | "sans" | "sansBold" | "serif" | "serifItalic" | "symbol";

export const PDF_BASE_FONTS: Record<Exclude<FontChoice, "notation">, string> = {
  sans: "Helvetica",
  sansBold: "Helvetica-Bold",
  serif: "Times-Roman",
  serifItalic: "Times-Italic",
  symbol: "Symbol",
};

/**
 * Turn one `.grid-page` element into drawing operators.
 *
 * Coordinates come out relative to the page's own top-left corner and in CSS pixels, the units the
 * layout was done in. Turning those into paper millimetres is one scale, applied once, by the
 * caller — so nothing in here has to know what size the paper is.
 */
export function drawPage(page: HTMLElement, font: EmbeddableFont): DrawnPage {
  const origin = page.getBoundingClientRect();
  const out: string[] = [];
  const glyphs = new Set<number>();
  const alphas = new Set<number>();
  const state = new PageWriter(out, glyphs, alphas, font, origin);
  state.walk(page, 1);
  return { ops: out.join("\n"), glyphs, alphas };
}

class PageWriter {
  private readonly out: string[];
  private readonly glyphs: Set<number>;
  private readonly alphas: Set<number>;
  private readonly font: EmbeddableFont;
  private readonly origin: DOMRect;

  constructor(
    out: string[],
    glyphs: Set<number>,
    alphas: Set<number>,
    font: EmbeddableFont,
    origin: DOMRect,
  ) {
    this.out = out;
    this.glyphs = glyphs;
    this.alphas = alphas;
    this.font = font;
    this.origin = origin;
  }

  /** Depth-first in document order, which is also paint order. */
  walk(node: Element, inherited: number): void {
    for (const child of Array.from(node.children)) {
      const style = getComputedStyle(child);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const alpha = inherited * numberOf(style.opacity, 1);
      if (alpha <= 0.004) continue;

      if (child instanceof SVGSVGElement) {
        this.drawSvg(child, alpha);
        continue;
      }
      this.drawHtmlText(child, style, alpha);
      this.walk(child, alpha);
    }
  }

  // -----------------------------------------------------------------------------------------
  // The score
  // -----------------------------------------------------------------------------------------

  private drawSvg(svg: SVGSVGElement, alpha: number): void {
    const box = svg.getBoundingClientRect();
    const offset: Matrix = [1, 0, 0, 1, box.left - this.origin.left, box.top - this.origin.top];
    this.walkSvg(svg, offset, alpha);
  }

  private walkSvg(node: Element, offset: Matrix, inherited: number): void {
    for (const child of Array.from(node.children)) {
      if (child.tagName === "title" || child.tagName === "desc" || child.tagName === "defs") {
        continue;
      }
      const style = getComputedStyle(child);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const alpha = inherited * numberOf(style.opacity, 1);
      if (alpha <= 0.004) continue;

      if (child instanceof SVGGraphicsElement && !(child instanceof SVGGElement)) {
        this.drawShape(child, style, offset, alpha);
      }
      this.walkSvg(child, offset, alpha);
    }
  }

  private drawShape(
    element: SVGGraphicsElement,
    style: CSSStyleDeclaration,
    offset: Matrix,
    alpha: number,
  ): void {
    const ctm = element.getCTM();
    const local: Matrix = ctm ? [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f] : IDENTITY;
    const matrix = multiply(offset, local);

    if (element instanceof SVGTextElement) {
      this.drawSvgText(element, style, matrix, alpha);
      return;
    }

    const path = pathOf(element);
    if (!path) return;
    const fill = colourOf(style.fill);
    const stroke = colourOf(style.stroke);
    const strokeWidth = numberOf(style.strokeWidth, 1);
    if (!fill && (!stroke || strokeWidth <= 0)) return;

    this.open(matrix, alpha * numberOf(style.fillOpacity, 1) * numberOf(style.strokeOpacity, 1));
    if (fill) this.out.push(`${fill.join(" ")} rg`);
    if (stroke) {
      this.out.push(`${stroke.join(" ")} RG`, `${n(strokeWidth)} w`);
      this.out.push(`${CAPS[style.strokeLinecap] ?? 0} J`, `${JOINS[style.strokeLinejoin] ?? 0} j`);
      const dashes = dashesOf(style.strokeDasharray);
      this.out.push(`[${dashes.map(n).join(" ")}] ${n(numberOf(style.strokeDashoffset, 0))} d`);
    }
    this.out.push(path);
    this.out.push(fill && stroke ? "B" : fill ? "f" : "S");
    this.out.push("Q");
  }

  /**
   * Text placed one character at a time, at the position the browser put it.
   *
   * Not "draw this string and hope": the sheet centres, right-aligns and kerns its labels, and a
   * music glyph sits where the engraver's arithmetic put it to a fraction of a pixel. Asking the
   * DOM where each character actually landed makes the PDF agree with the screen by construction,
   * and means no font metrics have to be reimplemented here to place anything.
   */
  private drawSvgText(
    element: SVGTextElement,
    style: CSSStyleDeclaration,
    matrix: Matrix,
    alpha: number,
  ): void {
    const fill = colourOf(style.fill);
    if (!fill) return;
    const size = numberOf(style.fontSize, 10);
    const text = element.textContent ?? "";
    if (!text.trim() && !text) return;

    const runs = new Runs();
    const total = element.getNumberOfChars();
    for (let index = 0; index < total; index += 1) {
      const character = text[index];
      if (character === undefined) continue;
      if (character === " ") {
        runs.break();
        continue;
      }
      let point: DOMPoint;
      try {
        point = element.getStartPositionOfChar(index);
      } catch {
        continue;
      }
      const placed = this.encode(character, style);
      if (!placed) continue;
      runs.add(placed.choice, placed.code, point.x, point.y);
    }
    this.emitRuns(runs.done(), matrix, fill, size, alpha * numberOf(style.fillOpacity, 1));
  }

  // -----------------------------------------------------------------------------------------
  // The page's own furniture — its title, its running head, its number
  // -----------------------------------------------------------------------------------------

  /**
   * The title and the page number are ordinary HTML, so they are measured rather than transformed.
   *
   * One rectangle per character says where it sits across the line; the baseline is worked out from
   * the font's own ascent and the half-leading the browser added, which is the same sum the browser
   * did to lay the line out in the first place.
   */
  private drawHtmlText(element: Element, style: CSSStyleDeclaration, alpha: number): void {
    const fill = colourOf(style.color);
    if (!fill) return;
    const size = numberOf(style.fontSize, 12);
    const metrics = fontMetrics(style.font || `${style.fontSize} ${style.fontFamily}`, size);
    const lineHeight =
      style.lineHeight === "normal" ? metrics.height : numberOf(style.lineHeight, metrics.height);

    const runs = new Runs();
    for (const node of Array.from(element.childNodes)) {
      if (node.nodeType !== Node.TEXT_NODE) continue;
      const text = node.textContent ?? "";
      const range = document.createRange();
      for (let index = 0; index < text.length; index += 1) {
        const character = text[index];
        if (character === undefined) continue;
        if (character === " ") {
          runs.break();
          continue;
        }
        const placed = this.encode(character, style);
        if (!placed) continue;
        range.setStart(node, index);
        range.setEnd(node, index + 1);
        const box = range.getBoundingClientRect();
        if (box.width === 0 && box.height === 0) continue;
        runs.add(
          placed.choice,
          placed.code,
          box.left - this.origin.left,
          box.top - this.origin.top + (lineHeight - metrics.height) / 2 + metrics.ascent,
        );
      }
    }
    this.emitRuns(runs.done(), IDENTITY, fill, size, alpha);
  }

  // -----------------------------------------------------------------------------------------

  /** Which PDF font draws this character, and the code that font calls it. */
  private encode(
    character: string,
    style: CSSStyleDeclaration,
  ): { choice: FontChoice; code: number } | null {
    const family = style.fontFamily.toLowerCase();
    if (family.includes("bravura")) {
      const gid = this.font.gidFor(character.codePointAt(0) ?? 0);
      if (!gid) return null;
      this.glyphs.add(gid);
      return { choice: "notation", code: gid };
    }
    const winAnsi = WIN_ANSI.get(character) ?? (isLatin1(character) ? character.charCodeAt(0) : 0);
    if (!winAnsi) {
      const symbol = SYMBOL.get(character);
      return symbol === undefined ? null : { choice: "symbol", code: symbol };
    }
    const serif = family.includes("serif") && !family.includes("sans-serif");
    const italic = style.fontStyle === "italic" || style.fontStyle === "oblique";
    const bold = numberOf(style.fontWeight, 400) >= 600 || style.fontWeight === "bold";
    const choice: FontChoice = serif
      ? italic
        ? "serifItalic"
        : "serif"
      : bold
        ? "sansBold"
        : "sans";
    return { choice, code: winAnsi };
  }

  /**
   * Write the placed runs out.
   *
   * The whole page is drawn with the y axis running down, which is upside down as far as PDF is
   * concerned. Rather than flip the page and then flip every glyph back, the text matrix carries a
   * negative y scale, so a glyph comes out the right way up in a coordinate system that does not
   * agree with it.
   */
  private emitRuns(
    runs: readonly Run[],
    matrix: Matrix,
    fill: readonly number[],
    size: number,
    alpha: number,
  ): void {
    if (runs.length === 0) return;
    this.open(matrix, alpha);
    this.out.push(`${fill.join(" ")} rg`, "BT");
    let current: FontChoice | null = null;
    for (const run of runs) {
      if (run.choice !== current) {
        current = run.choice;
        this.out.push(`/${FONT_KEY[run.choice]} 1 Tf`);
      }
      const width = run.choice === "notation" ? 4 : 2;
      this.out.push(
        `${n(size)} 0 0 ${n(-size)} ${n(run.x)} ${n(run.y)} Tm`,
        `<${run.codes.map((code) => code.toString(16).padStart(width, "0")).join("")}> Tj`,
      );
    }
    this.out.push("ET", "Q");
  }

  /** `q`, the element's own transform, and its alpha. Always closed with `Q`. */
  private open(matrix: Matrix, alpha: number): void {
    this.out.push("q");
    if (matrix.some((value, index) => value !== IDENTITY[index])) {
      this.out.push(`${matrix.map(n).join(" ")} cm`);
    }
    const rounded = Math.round(Math.min(Math.max(alpha, 0), 1) * 100) / 100;
    if (rounded < 1) {
      this.alphas.add(rounded);
      this.out.push(`/GS${String(Math.round(rounded * 100)).padStart(3, "0")} gs`);
    }
  }
}

interface Run {
  choice: FontChoice;
  codes: number[];
  x: number;
  y: number;
}

/**
 * Characters gathered into the longest runs that can safely be drawn as one string.
 *
 * A music glyph is placed on its own, to the position the engraver computed for it. A word is not:
 * the labels are laid out in whatever sans face the reader's machine has, and the PDF writes them
 * in Helvetica, so placing each letter at the browser's position would print a word at Helvetica's
 * shapes and the other font's letter spacing — visibly gappy. Each word is placed once instead and
 * left to space itself, which is right inside the word and off by a hair at its end.
 */
class Runs {
  private readonly runs: Run[] = [];
  private open = false;

  add(choice: FontChoice, code: number, x: number, y: number): void {
    const last = this.runs[this.runs.length - 1];
    const joinable =
      this.open && last !== undefined && last.choice === choice && choice !== "notation";
    if (joinable) last.codes.push(code);
    else this.runs.push({ choice, codes: [code], x, y });
    this.open = true;
  }

  /** A space, or anything else that ends a word. */
  break(): void {
    this.open = false;
  }

  done(): readonly Run[] {
    return this.runs;
  }
}

export const FONT_KEY: Record<FontChoice, string> = {
  notation: "FN",
  sans: "FS",
  sansBold: "FB",
  serif: "FR",
  serifItalic: "FI",
  symbol: "FY",
};

// ---------------------------------------------------------------------------------------------
// Reading the DOM
// ---------------------------------------------------------------------------------------------

const CAPS: Record<string, number> = { butt: 0, round: 1, square: 2 };
const JOINS: Record<string, number> = { miter: 0, round: 1, bevel: 2 };

function numberOf(value: string | number | null | undefined, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) ? parsed : fallback;
}

/** `rgb(…)` as PDF's 0–1 triple, or `null` for anything that paints nothing. */
function colourOf(value: string): [number, number, number] | null {
  if (!value || value === "none" || value === "transparent") return null;
  const parts = value.match(/[\d.]+/g);
  if (!parts || parts.length < 3) return null;
  const alpha = parts.length > 3 ? Number(parts[3]) : 1;
  if (alpha === 0) return null;
  return [Number(parts[0]) / 255, Number(parts[1]) / 255, Number(parts[2]) / 255].map(
    (channel) => Math.round(channel * 1000) / 1000,
  ) as [number, number, number];
}

function dashesOf(value: string): number[] {
  if (!value || value === "none") return [];
  return value
    .split(/[\s,]+/)
    .map((part) => Number.parseFloat(part))
    .filter((part) => Number.isFinite(part));
}

/** The outline of one shape, as PDF path operators. */
function pathOf(element: SVGGraphicsElement): string | null {
  if (element instanceof SVGLineElement) {
    const { x1, y1, x2, y2 } = element;
    return `${n(x1.baseVal.value)} ${n(y1.baseVal.value)} m ${n(x2.baseVal.value)} ${n(
      y2.baseVal.value,
    )} l`;
  }
  if (element instanceof SVGRectElement) {
    const x = element.x.baseVal.value;
    const y = element.y.baseVal.value;
    const width = element.width.baseVal.value;
    const height = element.height.baseVal.value;
    if (width <= 0 || height <= 0) return null;
    const radius = Math.min(element.rx.baseVal.value || 0, width / 2, height / 2);
    if (radius <= 0) return `${n(x)} ${n(y)} ${n(width)} ${n(height)} re`;
    return roundedRect(x, y, width, height, radius);
  }
  if (element instanceof SVGCircleElement) {
    const cx = element.cx.baseVal.value;
    const cy = element.cy.baseVal.value;
    const r = element.r.baseVal.value;
    return r > 0 ? roundedRect(cx - r, cy - r, 2 * r, 2 * r, r) : null;
  }
  if (element instanceof SVGPathElement) return convertPath(element.getAttribute("d") ?? "");
  return null;
}

/** Four arcs, each a bezier with the usual circle constant. */
function roundedRect(x: number, y: number, width: number, height: number, r: number): string {
  const k = r * 0.5523;
  const right = x + width;
  const bottom = y + height;
  return [
    `${n(x + r)} ${n(y)} m`,
    `${n(right - r)} ${n(y)} l`,
    `${n(right - r + k)} ${n(y)} ${n(right)} ${n(y + r - k)} ${n(right)} ${n(y + r)} c`,
    `${n(right)} ${n(bottom - r)} l`,
    `${n(right)} ${n(bottom - r + k)} ${n(right - r + k)} ${n(bottom)} ${n(right - r)} ${n(bottom)} c`,
    `${n(x + r)} ${n(bottom)} l`,
    `${n(x + r - k)} ${n(bottom)} ${n(x)} ${n(bottom - r + k)} ${n(x)} ${n(bottom - r)} c`,
    `${n(x)} ${n(y + r)} l`,
    `${n(x)} ${n(y + r - k)} ${n(x + r - k)} ${n(y)} ${n(x + r)} ${n(y)} c`,
    "h",
  ].join(" ");
}

/** The subset of path data the drawing package emits, plus the rest of the straight-line commands. */
function convertPath(d: string): string | null {
  const tokens = d.match(/[a-zA-Z]|-?[\d.]+(?:e-?\d+)?/g);
  if (!tokens) return null;
  const out: string[] = [];
  let at = 0;
  let x = 0;
  let y = 0;
  let startX = 0;
  let startY = 0;
  let command = "";
  const next = () => Number(tokens[at++]);

  while (at < tokens.length) {
    const token = tokens[at]!;
    if (/[a-zA-Z]/.test(token)) {
      command = token;
      at += 1;
    }
    const relative = command === command.toLowerCase();
    switch (command.toUpperCase()) {
      case "M": {
        const dx = next();
        const dy = next();
        x = relative ? x + dx : dx;
        y = relative ? y + dy : dy;
        startX = x;
        startY = y;
        out.push(`${n(x)} ${n(y)} m`);
        command = relative ? "l" : "L";
        break;
      }
      case "L": {
        const dx = next();
        const dy = next();
        x = relative ? x + dx : dx;
        y = relative ? y + dy : dy;
        out.push(`${n(x)} ${n(y)} l`);
        break;
      }
      case "H": {
        const dx = next();
        x = relative ? x + dx : dx;
        out.push(`${n(x)} ${n(y)} l`);
        break;
      }
      case "V": {
        const dy = next();
        y = relative ? y + dy : dy;
        out.push(`${n(x)} ${n(y)} l`);
        break;
      }
      case "C": {
        const x1 = relative ? x + next() : next();
        const y1 = relative ? y + next() : next();
        const x2 = relative ? x + next() : next();
        const y2 = relative ? y + next() : next();
        x = relative ? x + next() : next();
        y = relative ? y + next() : next();
        out.push(`${n(x1)} ${n(y1)} ${n(x2)} ${n(y2)} ${n(x)} ${n(y)} c`);
        break;
      }
      case "Q": {
        const qx = relative ? x + next() : next();
        const qy = relative ? y + next() : next();
        const ex = relative ? x + next() : next();
        const ey = relative ? y + next() : next();
        // A quadratic is an exact cubic with the control point pulled two thirds of the way out.
        out.push(
          `${n(x + (2 / 3) * (qx - x))} ${n(y + (2 / 3) * (qy - y))} ${n(
            ex + (2 / 3) * (qx - ex),
          )} ${n(ey + (2 / 3) * (qy - ey))} ${n(ex)} ${n(ey)} c`,
        );
        x = ex;
        y = ey;
        break;
      }
      case "Z": {
        out.push("h");
        x = startX;
        y = startY;
        break;
      }
      default:
        return out.length > 0 ? out.join(" ") : null;
    }
  }
  return out.length > 0 ? out.join(" ") : null;
}

/** The font's own ascent and height, for putting an HTML line's baseline where the browser put it. */
const metricsCache = new Map<string, { ascent: number; height: number }>();

function fontMetrics(font: string, size: number): { ascent: number; height: number } {
  const cached = metricsCache.get(font);
  if (cached) return cached;
  let measured = { ascent: size * 0.8, height: size * 1.15 };
  const context = document.createElement("canvas").getContext("2d");
  if (context) {
    context.font = font;
    const box = context.measureText("Hxg");
    if (box.fontBoundingBoxAscent) {
      measured = {
        ascent: box.fontBoundingBoxAscent,
        height: box.fontBoundingBoxAscent + box.fontBoundingBoxDescent,
      };
    }
  }
  metricsCache.set(font, measured);
  return measured;
}

function isLatin1(character: string): boolean {
  const code = character.charCodeAt(0);
  return (code >= 0x20 && code <= 0x7e) || (code >= 0xa0 && code <= 0xff);
}

/** The slots WinAnsi puts somewhere other than where Latin-1 does. */
const WIN_ANSI = new Map<string, number>(
  Object.entries({
    "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85, "†": 0x86, "‡": 0x87,
    "ˆ": 0x88, "‰": 0x89, "Š": 0x8a, "‹": 0x8b, "Œ": 0x8c, "Ž": 0x8e, "‘": 0x91,
    "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97, "˜": 0x98,
    "™": 0x99, "š": 0x9a, "›": 0x9b, "œ": 0x9c, "ž": 0x9e, "Ÿ": 0x9f,
  }),
);

/** The handful of mathematical signs the sheet's labels use, in the Symbol font's own encoding. */
const SYMBOL = new Map<string, number>(
  Object.entries({
    "≈": 0xbb, "≠": 0xb9, "≤": 0xa3, "≥": 0xb3, "∞": 0xa5, "→": 0xae,
    "↑": 0xad, "↓": 0xaf, "∑": 0xe5, "√": 0xd6, "∂": 0xb6,
  }),
);
