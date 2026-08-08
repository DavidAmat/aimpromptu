/**
 * A very small PDF writer — enough to hold vector drawings and an embedded font.
 *
 * Written here rather than pulled in, because what the sheet needs from a PDF is a short list:
 * pages, paths, text, and one font file carried along. A library that does forms, encryption and
 * annotations would be a megabyte of dependency for `lineTo`.
 *
 * Object numbers are handed out first and filled in later, so a page can name the font it uses
 * before the font has been built.
 */

const ascii = new TextEncoder();

/** zlib-wrapped deflate, which is exactly what `/FlateDecode` reads. */
async function deflate(data: Uint8Array): Promise<Uint8Array | null> {
  if (typeof CompressionStream === "undefined") return null;
  const stream = new Blob([data as BlobPart]).stream().pipeThrough(new CompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

/** A PDF name or number key with its already-serialised value. */
export type PdfDict = Record<string, string>;

function serialiseDict(dict: PdfDict): string {
  return `<< ${Object.entries(dict)
    .map(([key, value]) => `/${key} ${value}`)
    .join(" ")} >>`;
}

/**
 * A PDF string in `(...)` form.
 *
 * Only used for metadata; drawn text goes out as hex, so that a byte over 127 needs no escaping.
 */
export function pdfString(text: string): string {
  return `(${text.replace(/[\\()]/g, (c) => `\\${c}`).replace(/[\r\n]/g, " ")})`;
}

export class PdfDocument {
  private readonly bodies = new Map<number, Uint8Array>();
  private next = 1;

  /** Take an object number now and fill it in whenever. */
  reserve(): number {
    return this.next++;
  }

  put(number: number, body: string): void {
    this.bodies.set(number, ascii.encode(body));
  }

  /**
   * Store a stream object, compressed when the browser can.
   *
   * `Length` has to be the length of what is actually written, so it is set here rather than by the
   * caller, and `Filter` only appears when something was in fact deflated.
   */
  async putStream(
    number: number,
    dict: PdfDict,
    data: Uint8Array,
    { compress = true }: { compress?: boolean } = {},
  ): Promise<void> {
    const packed = compress ? await deflate(data) : null;
    const payload = packed ?? data;
    const full: PdfDict = {
      ...dict,
      Length: String(payload.length),
      ...(packed ? { Filter: "/FlateDecode" } : {}),
    };
    const head = ascii.encode(`${serialiseDict(full)}\nstream\n`);
    const tail = ascii.encode("\nendstream");
    const body = new Uint8Array(head.length + payload.length + tail.length);
    body.set(head, 0);
    body.set(payload, head.length);
    body.set(tail, head.length + payload.length);
    this.bodies.set(number, body);
  }

  putDict(number: number, dict: PdfDict): void {
    this.put(number, serialiseDict(dict));
  }

  /** Assemble the file. Every reserved number must have been filled in. */
  toBlob(catalog: number): Blob {
    const parts: BlobPart[] = [];
    const offsets: number[] = new Array(this.next).fill(0);
    let at = 0;
    const push = (bytes: Uint8Array) => {
      parts.push(bytes as BlobPart);
      at += bytes.length;
    };

    // 1.6, because the embedded font is carried as OpenType rather than as a bare CFF.
    push(ascii.encode("%PDF-1.6\n%âãÏÓ\n"));
    for (let number = 1; number < this.next; number += 1) {
      const body = this.bodies.get(number);
      if (!body) throw new Error(`PDF object ${number} was reserved and never written`);
      offsets[number] = at;
      push(ascii.encode(`${number} 0 obj\n`));
      push(body);
      push(ascii.encode("\nendobj\n"));
    }

    const xrefAt = at;
    let xref = `xref\n0 ${this.next}\n0000000000 65535 f \n`;
    for (let number = 1; number < this.next; number += 1) {
      xref += `${String(offsets[number]).padStart(10, "0")} 00000 n \n`;
    }
    xref += `trailer\n<< /Size ${this.next} /Root ${catalog} 0 R >>\nstartxref\n${xrefAt}\n%%EOF\n`;
    push(ascii.encode(xref));

    return new Blob(parts, { type: "application/pdf" });
  }
}
