/**
 * The new sheet on a page, for the checks that drive the app (implementation 03, Phase 8B: every screen draws the new
 * sheet, so the old sheet's hooks `.grid-note-target` and `.grid-frame-ruler` are gone).
 *
 *     import { markStretch, waitForFrames, watchSheets } from './frames-page.mjs';
 *     watchSheets(page);                          // remember the width each sheet is drawn at
 *     await waitForFrames(page);                  // a notehead of the new sheet, or the blank sheet's empty state
 *     await markStretch(page, api, { from: 0.3, to: 0.6 });   // a drag in the strip above the first line
 *
 * A page can hold several sheets (the page of a passage: the Current and the Proposal): `scope` is a selector of the
 * element around one (`[data-passage-proposal]`). Each sheet page carries the part it draws (`data-part`).
 */

/** The width each part's sheet was last asked for by the page, by part. */
const widths = new Map();

/** Remember the width the page draws each sheet at (its own requests): the geometry of a check must be the page's. */
export function watchSheets(page) {
  page.on('response', (r) => {
    const found = /\/api\/sheet\/([0-9a-f-]+)(?:\/[a-z]+)?\?(?:[^#]*&)?width=(\d+)/.exec(r.url());
    if (found) widths.set(found[1], Number(found[2]));
  });
}

/** Wait for the new sheet in `scope`: a notehead, or (`empty`) the blank sheet's empty state. */
export async function waitForFrames(page, { scope = '', timeout = 90000, empty = false } = {}) {
  const inside = scope ? `${scope} ` : '';
  const wanted = empty ? `${inside}[data-sheet-page] >> text=Nothing to write yet.` : `${inside}[data-frames-sheet] [data-note]`;
  await page.locator(wanted).first().waitFor({ timeout });
  await page.waitForTimeout(500);
}

/** The part the sheet in `scope` draws. */
export async function partOf(page, scope = '') {
  return page.locator(`${scope ? `${scope} ` : ''}[data-sheet-page]`).first().getAttribute('data-part');
}

/** The sheet of `part` as the page draws it now (its width). */
export async function sheetNow(api, part) {
  const answer = await fetch(`${api}/sheet/${part}?width=${widths.get(part) ?? 130}`);
  if (!answer.ok) throw new Error(`GET sheet ${part}: ${answer.status}`);
  return answer.json();
}

/**
 * Mark a stretch on the new sheet: a drag in the strip above line `line`, from the column `from` of the way along it
 * to the column `to` of the way (fractions of the line's columns). Returns the stretch the drag covers, in frames
 * (`end` is the column after the last one, as the page marks it).
 */
export async function markStretch(page, api, { scope = '', from, to, line = 0 }) {
  const part = await partOf(page, scope);
  const sheet = await sheetNow(api, part);
  const system = sheet.systems[line];
  const onLine = sheet.columns.filter((c) => c.system === line);
  const pick = (share) => onLine[Math.min(onLine.length - 1, Math.max(0, Math.round(share * (onLine.length - 1))))];
  const [a, b] = [pick(from), pick(to)];
  const svg = page.locator(`${scope ? `${scope} ` : ''}[data-frames-sheet] svg`).first();
  await svg.scrollIntoViewIfNeeded();
  const before = await svg.boundingBox();
  const scale = before.width / sheet.width;
  // Just above the ink of the line, in the strip (a press on a notehead picks the note instead).
  const stripY = Math.max(system.top - 0.6, system.staff_top - 3.3);
  await page.evaluate((y) => window.scrollBy(0, y - 300), before.y + stripY * scale);
  await page.waitForTimeout(250);
  const box = await svg.boundingBox();
  const y = box.y + stripY * scale;
  await page.mouse.move(box.x + a.x * scale, y);
  await page.mouse.down();
  await page.mouse.move(box.x + b.x * scale, y, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(400);
  const next = sheet.columns[sheet.columns.indexOf(b) + 1];
  return { start: a.frame, end: next ? next.frame : b.frame + 1, part };
}
