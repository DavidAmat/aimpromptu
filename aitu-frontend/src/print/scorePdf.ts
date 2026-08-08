/**
 * The sheet, as a PDF file.
 *
 * The pages themselves are drawn by the notation package, which re-wraps the music to the paper
 * exactly the way it re-wraps it to a narrower window — so nothing is scaled down to fit, and a
 * line that will not fit across an A4 page breaks earlier and carries on below instead of running
 * off the edge. Narrowing the margins gives every line more room before it has to break, which is
 * why the margins are a control the reader can turn rather than a constant.
 *
 * What happens here is only the last step: the drawn pages are read off the DOM and written out as
 * PDF operators, in CSS pixels, with one scale applied at the top of each page to turn those into
 * paper. Bravura travels with the file, so the notes are the same shapes on any machine.
 */

import { drawPage, FONT_KEY, PDF_BASE_FONTS } from "./drawPage";
import { readOpenType, type EmbeddableFont } from "./opentype";
import { PdfDocument, pdfString } from "./pdf";

/** CSS pixels per point. The layout is done in pixels; paper is measured in points. */
const PT_PER_PX = 72 / 96;

/** Where the font the notes are drawn in is served from. Fetched only when a PDF is asked for. */
const NOTATION_FONT_URL = `${import.meta.env.BASE_URL}fonts/bravura.otf`;

let notationFont: Promise<EmbeddableFont> | null = null;

function loadNotationFont(): Promise<EmbeddableFont> {
  notationFont ??= fetch(NOTATION_FONT_URL)
    .then((response) => {
      if (!response.ok) throw new Error(`The notation font could not be loaded (${response.status})`);
      return response.arrayBuffer();
    })
    .then(readOpenType)
    .catch((error: unknown) => {
      notationFont = null;
      throw error;
    });
  return notationFont;
}

export interface ScorePdfOptions {
  /** Printed in the document's properties. */
  title?: string;
  /** Called with a fraction between 0 and 1 as the pages are written. */
  onProgress?: (done: number, total: number) => void;
}

/**
 * Write every `.grid-page` inside `host` to one PDF.
 *
 * The elements have to be laid out — on screen or off to one side, but not `display: none` — since
 * every position in the file is one the browser worked out.
 */
export async function scoreToPdf(
  host: HTMLElement,
  { title, onProgress }: ScorePdfOptions = {},
): Promise<Blob> {
  const pages = Array.from(host.querySelectorAll<HTMLElement>(".grid-page"));
  if (pages.length === 0) throw new Error("There are no pages to write.");
  const font = await loadNotationFont();

  const pdf = new PdfDocument();
  const catalog = pdf.reserve();
  const pageTree = pdf.reserve();
  const notationRef = pdf.reserve();
  const baseRefs = Object.fromEntries(
    Object.keys(PDF_BASE_FONTS).map((key) => [key, pdf.reserve()]),
  ) as Record<keyof typeof PDF_BASE_FONTS, number>;

  const glyphs = new Set<number>();
  const pageRefs: number[] = [];
  const encoder = new TextEncoder();

  for (const [index, page] of pages.entries()) {
    const box = page.getBoundingClientRect();
    const widthPt = Math.round(box.width * PT_PER_PX * 100) / 100;
    const heightPt = Math.round(box.height * PT_PER_PX * 100) / 100;

    const drawn = drawPage(page, font);
    for (const glyph of drawn.glyphs) glyphs.add(glyph);

    // One transform for the whole page: pixels to points, and the y axis turned over, because a
    // PDF measures up from the bottom of the sheet and a browser measures down from the top.
    const ops = `q ${PT_PER_PX} 0 0 ${-PT_PER_PX} 0 ${heightPt} cm\n${drawn.ops}\nQ`;
    const contentRef = pdf.reserve();
    await pdf.putStream(contentRef, {}, encoder.encode(ops));

    const alphaRefs = new Map<number, number>();
    for (const alpha of drawn.alphas) {
      const ref = pdf.reserve();
      pdf.putDict(ref, { Type: "/ExtGState", ca: String(alpha), CA: String(alpha) });
      alphaRefs.set(alpha, ref);
    }

    const pageRef = pdf.reserve();
    const fontResources = [
      `/${FONT_KEY.notation} ${notationRef} 0 R`,
      ...Object.entries(baseRefs).map(
        ([key, ref]) => `/${FONT_KEY[key as keyof typeof PDF_BASE_FONTS]} ${ref} 0 R`,
      ),
    ].join(" ");
    const states = [...alphaRefs.entries()]
      .map(([alpha, ref]) => `/GS${String(Math.round(alpha * 100)).padStart(3, "0")} ${ref} 0 R`)
      .join(" ");
    pdf.putDict(pageRef, {
      Type: "/Page",
      Parent: `${pageTree} 0 R`,
      MediaBox: `[0 0 ${widthPt} ${heightPt}]`,
      Resources: `<< /Font << ${fontResources} >>${states ? ` /ExtGState << ${states} >>` : ""} >>`,
      Contents: `${contentRef} 0 R`,
    });
    pageRefs.push(pageRef);
    onProgress?.(index + 1, pages.length);
  }

  await writeNotationFont(pdf, notationRef, font, glyphs);
  for (const [key, ref] of Object.entries(baseRefs)) {
    pdf.putDict(ref, {
      Type: "/Font",
      Subtype: "/Type1",
      BaseFont: `/${PDF_BASE_FONTS[key as keyof typeof PDF_BASE_FONTS]}`,
      ...(key === "symbol" ? {} : { Encoding: "/WinAnsiEncoding" }),
    });
  }

  pdf.putDict(pageTree, {
    Type: "/Pages",
    Kids: `[${pageRefs.map((ref) => `${ref} 0 R`).join(" ")}]`,
    Count: String(pageRefs.length),
  });
  const infoRef = pdf.reserve();
  pdf.putDict(infoRef, {
    Producer: pdfString("AImpromptu"),
    ...(title ? { Title: pdfString(title) } : {}),
  });
  pdf.putDict(catalog, { Type: "/Catalog", Pages: `${pageTree} 0 R` });

  return pdf.toBlob(catalog);
}

/**
 * Bravura, carried into the file whole.
 *
 * Addressed by glyph id rather than by character, which is what `Identity-H` means: the notes are
 * at private-use code points that mean nothing outside this font, so there is no encoding worth
 * pretending to. Only the glyphs the piece actually used get a width.
 */
async function writeNotationFont(
  pdf: PdfDocument,
  ref: number,
  font: EmbeddableFont,
  glyphs: ReadonlySet<number>,
): Promise<void> {
  const descendant = pdf.reserve();
  const descriptor = pdf.reserve();
  const file = pdf.reserve();

  const widths = [...glyphs]
    .sort((a, b) => a - b)
    .map((gid) => `${gid} [${font.advanceOf(gid)}]`)
    .join(" ");

  pdf.putDict(ref, {
    Type: "/Font",
    Subtype: "/Type0",
    BaseFont: "/Bravura",
    Encoding: "/Identity-H",
    DescendantFonts: `[${descendant} 0 R]`,
  });
  pdf.putDict(descendant, {
    Type: "/Font",
    Subtype: "/CIDFontType0",
    BaseFont: "/Bravura",
    CIDSystemInfo: "<< /Registry (Adobe) /Ordering (Identity) /Supplement 0 >>",
    FontDescriptor: `${descriptor} 0 R`,
    DW: "0",
    W: `[${widths}]`,
  });
  pdf.putDict(descriptor, {
    Type: "/FontDescriptor",
    FontName: "/Bravura",
    // Symbolic: the glyphs are not letters and must not be read through a text encoding.
    Flags: "4",
    FontBBox: `[${font.bbox.join(" ")}]`,
    ItalicAngle: "0",
    Ascent: String(font.ascent),
    Descent: String(font.descent),
    CapHeight: String(font.ascent),
    StemV: "80",
    FontFile3: `${file} 0 R`,
  });
  await pdf.putStream(file, { Subtype: "/OpenType" }, font.data);
}

/** Hand the finished file to the browser as a download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** A filename that says which piece it is, with nothing in it a filesystem will object to. */
export function pdfFilenameFor(label: string | undefined): string {
  const stem = (label ?? "sheet")
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
  return `${stem || "sheet"}.pdf`;
}
