/**
 * The note and range tools of the new sheet in the browser (implementation 03, Phase 7).
 *
 * On a temporary copy of a version of My library that the AI wrote (7 Years by default; the copy is deleted at the
 * end, the library is only read), each tool through the page, checked against the backend:
 * - the note toolbox: a figure set by hand (pressed, then back to the rule), a finger, a beam cut and joined again,
 *   the grace note switch, a trill over three onsets, a note taken off the page with Delete (and undone);
 * - the range selection: a drag in the strip above the staves marks a stretch (a band) and opens the range toolbox;
 *   **Right** narrows it; an 8va over the right hand; a clef for the left hand; an armadura; the notes of the stretch
 *   handed to the note toolbox;
 * - **Enhance with AI** opens its dialog from both toolboxes. With `--live` one real request writes a short stretch
 *   again with words (a few cents): the stretch gets the pale veil, then the answer is one step of undo.
 *
 * Zoomed pictures of each edited line go to `--out`.
 *
 *     npm run check:frames-tools -- --out /tmp/frames-tools [--live]
 */

import { mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-frames-tools') },
    version: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
    live: { type: 'boolean', default: false },
  },
});
const base = values.base;
const api = `${base}/api`;
mkdirSync(values.out, { recursive: true });
await signIn(base);

const failures = [];
const check = (what, ok, detail = '') => {
  console.log(`${ok ? 'ok  ' : 'FAIL'}  ${what}${detail ? `  (${detail})` : ''}`);
  if (!ok) failures.push(what);
};
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
const frameOf = (ref) => Number(ref.split(':')[0]);

const browser = await chromium.launch();
useSession(browser);
const problems = [];
/** The staff width the page draws at (its own request): the geometry of the checks must be the page's. */
let pageWidth = 130;
async function open(route) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  page.on('console', (m) => { if (m.type() === 'error' && !/status of (404|400)/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  page.on('response', (r) => {
    if (r.status() >= 400 && !(r.status() === 404 && /\/rhythm$/.test(r.url()))) problems.push(`${r.status()} ${r.url()}`);
    const width = /\/sheet\/[^/?]+(?:\/[a-z]+)?\?width=(\d+)/.exec(r.url());
    if (width) pageWidth = Number(width[1]);
  });
  await page.goto(new URL(route, base).toString());
  await page.locator('[data-frames-sheet] [data-note]').first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(500);
  return page;
}
const notesToolbox = (page) => page.locator('[data-frames-note-toolbox]');
const rangeToolbox = (page) => page.locator('[data-frames-range-toolbox]');
const now = async (part) => json(`${api}/sheet/${part}?width=${pageWidth}`);
const noteOf = async (part, ref) => (await now(part)).notes.find((n) => n.ref === ref);
async function clickHead(page, ref, modifiers = []) {
  const head = page.locator(`[data-frames-sheet] [data-note~="${ref}"]`).first();
  await head.scrollIntoViewIfNeeded();
  const box = await head.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (const key of modifiers) await page.keyboard.down(key);
  await page.mouse.down();
  await page.mouse.up();
  for (const key of modifiers) await page.keyboard.up(key);
  await page.waitForTimeout(150);
}
/** Press a control and wait for the sheet the backend answers (or its refusal). */
async function press(page, locator, pattern = /\/sheet\/[^/]+\/(reading|remove|undo|redo)/) {
  const [response] = await Promise.all([page.waitForResponse((r) => pattern.test(r.url())), locator.click()]);
  await page.waitForTimeout(250);
  return response;
}
/** A zoomed picture of the line that holds `frame`, with no toolbox over it. */
async function lineShot(page, sheet, frame, name) {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(250);
  const column = sheet.columns.find((c) => c.frame >= frame) ?? sheet.columns[0];
  const system = sheet.systems[column.system];
  const svg = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  const scale = svg.width / sheet.width;
  const top = svg.y + (system.top - 3) * scale;
  await page.evaluate((y) => window.scrollBy(0, y - 200), top);
  await page.waitForTimeout(200);
  const box = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  const x = box.x + Math.max(0, column.x - 30) * scale;
  await page.screenshot({
    path: path.join(values.out, `${name}.png`),
    clip: { x, y: box.y + (system.top - 3) * scale, width: Math.min(720, box.x + box.width - x), height: (system.bottom - system.top + 6) * scale },
  });
}

const made = [];
try {
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  const first = await now(part);
  check('a copy of a sheet the AI wrote can be edited', first.editable === true && first.llm.enhanced === true);
  const page = await open(`/projects/${part}/sheet`);

  // ------------------------------------------------------------------ the note toolbox
  // Right-hand notes in a beam group of three or more, on the second line.
  const second = first.columns.find((c) => c.system === 1).frame;
  const right = first.notes.filter((n) => n.hand === 'right' && !n.grace && frameOf(n.ref) >= second);
  const counts = {};
  for (const n of right) if (n.beam !== null) counts[n.beam] = (counts[n.beam] ?? new Set()).add(frameOf(n.ref));
  const group = Object.entries(counts).find(([, frames]) => frames.size >= 3);
  const groupNotes = right.filter((n) => String(n.beam) === group[0]);
  const columns = [...new Set(groupNotes.map((n) => frameOf(n.ref)))].sort((a, b) => a - b);
  const headAt = (frame) => groupNotes.find((n) => frameOf(n.ref) === frame).ref;
  const target = headAt(columns[1]);
  await lineShot(page, first, columns[0], '00-line-before');

  await clickHead(page, headAt(columns[2]));
  await press(page, page.getByTestId('beam-break'));
  let sheet = await now(part);
  const beamAt = (frame) => sheet.notes.find((n) => n.ref === headAt(frame))?.beam;
  check('the beam cut in front of the third note', beamAt(columns[1]) !== beamAt(columns[2]), `${beamAt(columns[1])} / ${beamAt(columns[2])}`);
  await lineShot(page, sheet, columns[0], '03-beam-cut');
  await clickHead(page, headAt(columns[2]));
  check('the cut button now joins', (await page.getByTestId('beam-break').getAttribute('aria-label'))?.startsWith('Join') === true);
  await press(page, page.getByTestId('beam-break'));
  sheet = await now(part);
  check('joined again', beamAt(columns[1]) === beamAt(columns[2]));

  await clickHead(page, target);
  await notesToolbox(page).waitFor();
  const figure = (await noteOf(part, target)).figure;
  await press(page, page.getByTestId('figure-4'));
  let note = await noteOf(part, target);
  check('a figure set by hand: the note is a negra, out of its beam', note.figure === 4 && note.fixed && note.beam === null, JSON.stringify({ figure: note.figure, beam: note.beam }));
  await lineShot(page, await now(part), columns[0], '01-negra');
  await clickHead(page, target);
  await press(page, page.getByRole('button', { name: 'Back to the figures of the rule' }));
  note = await noteOf(part, target);
  check('Back to the rule gives it its figure again', note.figure === figure && !note.fixed);

  await clickHead(page, target);
  await press(page, notesToolbox(page).locator('[data-finger="3"]'));
  note = await noteOf(part, target);
  check('a finger: 3 on the note', note.finger === 3);
  check('the finger is drawn', (await page.locator('[data-frames-sheet] svg .finger').count()) >= 1);
  await lineShot(page, await now(part), columns[0], '02-finger');

  await clickHead(page, headAt(columns[1]));
  await press(page, page.getByTestId('grace'));
  note = await noteOf(part, headAt(columns[1]));
  check('the grace switch writes it as a grace note', note.grace === true && note.graceRule === 'on');
  await lineShot(page, await now(part), columns[0], '04-grace');
  await clickHead(page, headAt(columns[1]));
  await press(page, page.getByRole('button', { name: 'Back to the grace rule' }));
  check('back to the grace rule', (await noteOf(part, headAt(columns[1]))).graceRule === null);

  await clickHead(page, headAt(columns[0]));
  await clickHead(page, headAt(columns[1]), ['Control']);
  await clickHead(page, headAt(columns[2]), ['Control']);
  await press(page, page.getByTestId('ornament-trill'));
  sheet = await now(part);
  const trilled = sheet.notes.find((n) => n.ref === headAt(columns[0]));
  check('a trill over three onsets: one note with tr, the other two not drawn', trilled?.ornaments.includes('trill') && !sheet.notes.some((n) => n.ref === headAt(columns[1])));
  await lineShot(page, sheet, columns[0], '05-trill');
  await page.keyboard.press('Control+z');
  await page.waitForResponse((r) => /\/undo/.test(r.url()));
  await page.waitForTimeout(300);
  check('undo prints the notes again', (await now(part)).notes.some((n) => n.ref === headAt(columns[1])));

  await clickHead(page, target);
  await page.keyboard.press('Delete');
  await page.waitForResponse((r) => /\/remove/.test(r.url()));
  await page.waitForTimeout(300);
  check('Delete takes the note off the page', !(await now(part)).notes.some((n) => n.ref === target));
  const undoTitle = await page.getByTestId('sheet-undo').getAttribute('aria-label');
  check('Undo names it', /Take a note off the page/.test(undoTitle ?? ''), undoTitle);
  await page.getByTestId('sheet-undo').click();
  await page.waitForResponse((r) => /\/undo/.test(r.url()));
  await page.waitForTimeout(300);
  check('undo brings it back', (await now(part)).notes.some((n) => n.ref === target));

  // ------------------------------------------------------------------ the range selection
  sheet = await now(part);
  const line = sheet.systems[1];
  // Just above the ink of the line, in the strip (a press on a notehead picks the note instead).
  const stripY = Math.max(line.top - 0.6, line.staff_top - 3.3);
  const onLine = sheet.columns.filter((c) => c.system === 1);
  const from = onLine[2];
  const to = onLine[Math.min(onLine.length - 2, 12)];
  /** The sheet on screen now, scrolled so that the line is in view: its box and its scale. */
  const placed = async () => {
    // After an undo the drawing is put in again: wait until it has a box.
    await page.waitForTimeout(400);
    const svg = page.locator('[data-frames-sheet] svg').first();
    await svg.waitFor();
    const before = await svg.boundingBox();
    const scale = before.width / sheet.width;
    await page.evaluate((top) => window.scrollBy(0, top - 250), before.y + line.top * scale);
    await page.waitForTimeout(200);
    const box = await svg.boundingBox();
    return { box, scale, y: box.y + stripY * scale };
  };
  /** Drag in the strip from the third column of the line to about the thirteenth. */
  const markStretch = async () => {
    const { box, scale, y } = await placed();
    await page.mouse.move(box.x + from.x * scale, y);
    await page.mouse.down();
    await page.mouse.move(box.x + to.x * scale, y, { steps: 8 });
    await page.mouse.up();
    await rangeToolbox(page).waitFor({ timeout: 5000 });
  };
  const { box, scale, y } = await placed();
  await page.mouse.move(box.x + from.x * scale, y);
  await page.waitForTimeout(150);
  check('the strip shows under the pointer', (await page.locator('[data-range-strip]').count()) === 1);
  await page.mouse.down();
  await page.mouse.move(box.x + to.x * scale, y, { steps: 8 });
  await page.mouse.up();
  await rangeToolbox(page).waitFor({ timeout: 5000 });
  const band = page.locator('[data-range-band]').first();
  const start = Number(await band.getAttribute('data-start'));
  const end = Number(await band.getAttribute('data-end'));
  check('a drag in the strip marks the stretch and opens the range toolbox', start === from.frame && end > to.frame, `${start}-${end}`);
  await page.screenshot({ path: path.join(values.out, '06-range.png') });

  await rangeToolbox(page).getByRole('button', { name: 'Right' }).click();
  await rangeToolbox(page).locator('[data-tab="octave"]').click();
  await press(page, rangeToolbox(page).locator('[data-ottava="right:8va"]'));
  sheet = await now(part);
  const inRight = sheet.notes.filter((n) => n.hand === 'right' && frameOf(n.ref) >= start && frameOf(n.ref) < end);
  check('8va over the right hand of the stretch', inRight.length > 0 && inRight.every((n) => n.ottava === 1));
  await lineShot(page, sheet, start, '07-8va');
  await page.keyboard.press('Control+z');
  await page.waitForResponse((r) => /\/undo/.test(r.url()));

  // Mark it again (Escape dropped it for the picture), on the left hand: the treble clef.
  await markStretch();
  await rangeToolbox(page).getByRole('button', { name: 'Left' }).click();
  await rangeToolbox(page).locator('[data-tab="clef"]').click();
  await press(page, rangeToolbox(page).locator('[data-clef="left:treble"]'));
  sheet = await now(part);
  check('a treble clef for the left hand over the stretch', sheet.reading.clefChanges.some(([f, hand, clef]) => f === start && hand === 'left' && clef === 'treble'));
  check('the clef tab carries its dot', (await rangeToolbox(page).locator('[data-tab="clef"]').getAttribute('data-edited')) === 'yes');
  await lineShot(page, sheet, start, '08-clef');
  await page.keyboard.press('Control+z');
  await page.waitForResponse((r) => /\/undo/.test(r.url()));

  await markStretch();
  const want = sheet.reading.key === 2 ? 3 : 2;
  await rangeToolbox(page).getByTestId('range-key').click();
  await page.getByRole('option').filter({ hasText: `${want} sharps` }).first().click();
  await press(page, rangeToolbox(page).getByTestId('range-key-apply'));
  sheet = await now(part);
  check('an armadura for the stretch', sheet.reading.keyChanges.some(([f]) => f === start), JSON.stringify(sheet.reading.keyChanges.slice(0, 3)));
  await lineShot(page, sheet, start, '09-key');
  await page.keyboard.press('Control+z');
  await page.waitForResponse((r) => /\/undo/.test(r.url()));

  await markStretch();
  await page.getByTestId('range-to-notes').click();
  await notesToolbox(page).waitFor();
  check('the notes of the stretch go to the note toolbox', (await page.locator('[data-selected]').count()) > 3);
  await page.getByTestId('notes-to-frames').click();
  await rangeToolbox(page).waitFor();
  check('and back to the frames', (await page.locator('[data-range-band]').count()) >= 1);

  // ------------------------------------------------------------------ Enhance with AI of a stretch
  await page.getByTestId('range-enhance').click();
  await page.getByTestId('stretch-words').waitFor();
  check('Enhance with AI opens its dialog from the range toolbox', true);
  if (!values.live) {
    await page.getByRole('button', { name: 'Cancel' }).click();
  } else {
    await page.getByTestId('stretch-words').fill('Put the melody notes in the right hand and the accompaniment in the left hand.');
    const asked = Date.now();
    await page.getByTestId('stretch-confirm').click();
    await page.locator('[data-segment-state="working"]').first().waitFor({ timeout: 15000 });
    check('the stretch gets the pale veil while the AI writes it', true);
    await page.screenshot({ path: path.join(values.out, '10-working.png') });
    await page.waitForFunction(() => !document.querySelector('[data-segment-state="working"]'), null, { timeout: 180000 });
    const seconds = Math.round((Date.now() - asked) / 1000);
    await page.waitForTimeout(2500);
    sheet = await now(part);
    check(
      'the AI wrote the stretch again, one step of undo',
      sheet.history.undo === 'Enhance a stretch with AI' && sheet.llm.enhanced,
      `${seconds} s, $${sheet.llm.usd}`,
    );
    await page.screenshot({ path: path.join(values.out, '11-written.png') });
    await lineShot(page, sheet, start, '11-line-written');
  }
  await page.close();
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
