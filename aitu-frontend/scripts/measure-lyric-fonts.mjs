/**
 * The widths of the lyrics fonts, measured in the browser (implementation 03, Phase 8A++).
 *
 * The backend draws a lyrics block and wraps its words to the block's width, but it has no text metrics. This
 * script loads the app's own font files (`public/fonts`, declared in `src/index.css`), measures the advance of every
 * character the table covers in each face (Lora, Geist and Montserrat, the fonts of the lyrics toolbox; normal, italic, bold, bold italic) and freezes them as
 * `aitu-backend/src/aitu_backend/sheet/engrave/lyric_fonts.json`, in thousandths of the font size. A character the
 * table does not hold is measured as an `n` by the engine.
 *
 * Kerning is not measured: the browser kerns the words it draws, which makes a line a little narrower than the sum
 * of its characters, never wider, so a wrapped line always fits its block.
 *
 *     npm run measure:lyric-fonts
 */

import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: {
      type: 'string',
      default: path.join(here, '../../aitu-backend/src/aitu_backend/sheet/engrave/lyric_fonts.json'),
    },
  },
});

/** The families of a lyrics block: the key the sheet stores, and the CSS family (`src/index.css`). */
const FAMILIES = { lora: 'Lora', geist: 'Geist', montserrat: 'Montserrat' };
const STYLES = {
  normal: ['normal', 400],
  italic: ['italic', 400],
  bold: ['normal', 700],
  bolditalic: ['italic', 700],
};
/** Printable ASCII, Latin-1, and the punctuation of the PDF's WinAnsi set that words use. */
const CHARS = [
  ...Array.from({ length: 95 }, (_, i) => String.fromCharCode(32 + i)),
  ...Array.from({ length: 96 }, (_, i) => String.fromCharCode(160 + i)),
  ...'‘’‚“”„–—…•€‹›'.split(''),
].join('');

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(values.base);
  const table = await page.evaluate(
    async ({ families, styles, chars }) => {
      const SIZE = 400;
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      const out = {};
      const fallback = (font) => {
        context.font = font.replace(/"[^"]+"/, 'monospace');
        return context.measureText('Hamburgefonstiv').width;
      };
      for (const [key, family] of Object.entries(families)) {
        out[key] = {};
        for (const [name, [style, weight]] of Object.entries(styles)) {
          // At 400 px: Chrome's canvas measures a much larger size with another face, and a small one in whole pixels.
          const font = `${style} ${weight} ${SIZE}px "${family}"`;
          await document.fonts.load(font, chars);
          if (!document.fonts.check(font, 'a')) throw new Error(`${font} did not load`);
          context.font = font;
          if (Math.abs(context.measureText('Hamburgefonstiv').width - fallback(font)) < 1) {
            throw new Error(`${font} measures as the fallback face`);
          }
          context.font = font;
          out[key][name] = [...chars].map((c) => Math.round((context.measureText(c.repeat(20)).width / 20 / SIZE) * 1000));
        }
      }
      return out;
    },
    { families: FAMILIES, styles: STYLES, chars: CHARS },
  );
  const lines = [
    '{',
    '  "about": "Advance widths of the lyrics fonts in thousandths of the font size, one per character of chars; measured in the browser from aitu-frontend/public/fonts by aitu-frontend/scripts/measure-lyric-fonts.mjs",',
    `  "chars": ${JSON.stringify(CHARS)},`,
    '  "fonts": {',
    Object.entries(table)
      .map(
        ([key, styles]) =>
          `    ${JSON.stringify(key)}: {\n` +
          Object.entries(styles)
            .map(([name, widths]) => `      ${JSON.stringify(name)}: ${JSON.stringify(widths)}`)
            .join(',\n') +
          '\n    }',
      )
      .join(',\n'),
    '  }',
    '}',
    '',
  ];
  writeFileSync(values.out, lines.join('\n'));
  for (const [key, styles] of Object.entries(table)) {
    const n = CHARS.indexOf('n');
    console.log(`${key}: n ${Object.entries(styles).map(([name, widths]) => `${name} ${widths[n]}`).join(', ')}`);
  }
  console.log(`wrote ${values.out} (${CHARS.length} characters)`);
} finally {
  await browser.close();
}
