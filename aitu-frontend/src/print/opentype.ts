/**
 * Just enough of an OpenType file to embed it in a PDF and find a glyph in it.
 *
 * The sheet is drawn in Bravura, and the notes on the page are Bravura glyphs at private-use code
 * points. A PDF cannot be told "the character U+E1D5 in this font": it addresses glyphs by their id
 * inside the file. So the character map has to be read here, on the way out, to turn each drawn
 * character into the id the page will ask for.
 *
 * Four tables, and none of them decoded further than that: `head` for the design grid, `hhea` and
 * `hmtx` for advances, `cmap` for the character map. The outlines are never parsed — the whole file
 * goes into the PDF untouched, and the reader's own font engine draws them.
 */

export interface EmbeddableFont {
  /** The file itself, to be carried into the PDF unchanged. */
  data: Uint8Array;
  unitsPerEm: number;
  /** `[xMin, yMin, xMax, yMax]`, in a 1000-unit em. */
  bbox: [number, number, number, number];
  ascent: number;
  descent: number;
  /** The glyph a character is drawn with, or 0 when the font has nothing for it. */
  gidFor(codePoint: number): number;
  /** How wide a glyph is, in a 1000-unit em. */
  advanceOf(gid: number): number;
}

export function readOpenType(buffer: ArrayBuffer): EmbeddableFont {
  const data = new Uint8Array(buffer);
  const view = new DataView(buffer);
  const tables = new Map<string, { offset: number; length: number }>();
  const count = view.getUint16(4);
  for (let i = 0; i < count; i += 1) {
    const at = 12 + 16 * i;
    const tag = String.fromCharCode(data[at]!, data[at + 1]!, data[at + 2]!, data[at + 3]!);
    tables.set(tag, { offset: view.getUint32(at + 8), length: view.getUint32(at + 12) });
  }
  const need = (tag: string) => {
    const table = tables.get(tag);
    if (!table) throw new Error(`The font has no ${tag} table`);
    return table.offset;
  };

  const head = need("head");
  const unitsPerEm = view.getUint16(head + 18);
  const scale = 1000 / unitsPerEm;
  const bbox: [number, number, number, number] = [
    Math.round(view.getInt16(head + 36) * scale),
    Math.round(view.getInt16(head + 38) * scale),
    Math.round(view.getInt16(head + 40) * scale),
    Math.round(view.getInt16(head + 42) * scale),
  ];

  const hhea = need("hhea");
  const ascent = Math.round(view.getInt16(hhea + 4) * scale);
  const descent = Math.round(view.getInt16(hhea + 6) * scale);
  const metricCount = view.getUint16(hhea + 34);
  const hmtx = need("hmtx");

  const advanceOf = (gid: number): number => {
    const index = Math.min(Math.max(gid, 0), Math.max(metricCount - 1, 0));
    const at = hmtx + index * 4;
    if (at + 2 > data.length) return 0;
    return Math.round(view.getUint16(at) * scale);
  };

  const cmap = readCmap(view, need("cmap"));

  return { data, unitsPerEm, bbox, ascent, descent, gidFor: cmap, advanceOf };
}

/**
 * The best character map the file offers, as a lookup.
 *
 * Format 12 first because it reaches past the basic plane, then format 4. A symbol font's own
 * `(3, 0)` map is taken as a last resort and asked twice: some of them index characters at `0xF000`
 * plus the byte, which is the old way of hiding a symbol font inside a text encoding.
 */
function readCmap(view: DataView, offset: number): (codePoint: number) => number {
  const tableCount = view.getUint16(offset + 2);
  const found = new Map<string, number>();
  for (let i = 0; i < tableCount; i += 1) {
    const at = offset + 4 + 8 * i;
    const platform = view.getUint16(at);
    const encoding = view.getUint16(at + 2);
    found.set(`${platform}:${encoding}`, offset + view.getUint32(at + 4));
  }
  const pick = ["3:10", "0:4", "0:6", "3:1", "0:3", "3:0"]
    .map((key) => found.get(key))
    .find((value) => value !== undefined);
  if (pick === undefined) return () => 0;

  const format = view.getUint16(pick);
  const lookup =
    format === 12
      ? readFormat12(view, pick)
      : format === 4
        ? readFormat4(view, pick)
        : () => 0;
  const symbolMap = found.has("3:0");
  return (codePoint: number) => lookup(codePoint) || (symbolMap ? lookup(0xf000 + codePoint) : 0);
}

function readFormat4(view: DataView, offset: number): (codePoint: number) => number {
  const segCount = view.getUint16(offset + 6) / 2;
  const ends = offset + 14;
  const starts = ends + segCount * 2 + 2;
  const deltas = starts + segCount * 2;
  const rangeOffsets = deltas + segCount * 2;
  return (codePoint: number) => {
    if (codePoint > 0xffff) return 0;
    for (let segment = 0; segment < segCount; segment += 1) {
      if (view.getUint16(ends + segment * 2) < codePoint) continue;
      const start = view.getUint16(starts + segment * 2);
      if (start > codePoint) return 0;
      const rangeOffset = view.getUint16(rangeOffsets + segment * 2);
      const delta = view.getInt16(deltas + segment * 2);
      if (rangeOffset === 0) return (codePoint + delta) & 0xffff;
      const at = rangeOffsets + segment * 2 + rangeOffset + (codePoint - start) * 2;
      if (at + 2 > view.byteLength) return 0;
      const gid = view.getUint16(at);
      return gid === 0 ? 0 : (gid + delta) & 0xffff;
    }
    return 0;
  };
}

function readFormat12(view: DataView, offset: number): (codePoint: number) => number {
  const groups = view.getUint32(offset + 12);
  return (codePoint: number) => {
    let low = 0;
    let high = groups - 1;
    while (low <= high) {
      const middle = (low + high) >> 1;
      const at = offset + 16 + middle * 12;
      const start = view.getUint32(at);
      const end = view.getUint32(at + 4);
      if (codePoint < start) high = middle - 1;
      else if (codePoint > end) low = middle + 1;
      else return view.getUint32(at + 8) + (codePoint - start);
    }
    return 0;
  };
}
