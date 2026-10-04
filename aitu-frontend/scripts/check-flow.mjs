/**
 * The flow page, walked in a headless Chromium (implementation 08, Phase 6).
 *
 * The flow page is mostly gestures on a canvas and navigation between tabs, which no unit check
 * reaches. This drives the real page through the running app (`make up`), on a temporary copy of
 * an audio file that it uploads first and deletes at the end, so the library is never changed:
 *
 * - `/` opens `/piece/new`; a piece opens on the step it reached; a disabled tab says why;
 * - on the Audio tab: drag, a click that clears, the two edges, the playhead in the ruler and on a
 *   double-click, zoom to the selection, Delete, the save bar, the leave dialog, undo and redo,
 *   Save, playback jumping over the cut, Restore and Discard, zoom;
 * - Transcribe (skipped with `--no-transcribe`), followed live on the Notes tab (the notes drawn
 *   grow, the progress bar moves), then the editor: select, move, undo and redo, resize, add,
 *   delete, a band, Save (checked against `GET /pieces/{uuid}/notes`), undo after the save, and
 *   playback from the ruler;
 * - the Hands tab (Predict hands, the filter, R and L, Save) and the Sheet tab (Write the sheet and
 *   Save; a notes edit makes it stale, its banner, Write the sheet again, Save).
 *
 *     npm run check:flow
 *     npm run check:flow -- --audio ../some.mp3 --out /tmp/flow --no-transcribe
 *
 * Screenshots go to `--out` (default `../.run/screenshots/flow`, ignored by git). The two pieces
 * `b99bc3ae` (with a piano sheet) and `a585f9eb` (transcribed only) of the library are opened, not
 * changed. Transcribing takes about 25 s on the GPU.
 */

import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    audio: {
      type: 'string',
      default: path.join(here, '..', '..', 'aitu-backend', 'data', 'audio', 'a585f9eb-36a1-49a0-9f0c-2626f3d292da', 'original.mp3'),
    },
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'flow') },
    base: { type: 'string', default: 'http://localhost:5173' },
    'no-transcribe': { type: 'boolean', default: false },
  },
});
const base = values.base;
// The backend through the page's own proxy, as the browser reaches it.
const api = `${base}/api`;
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });

const results = [];
const check = (label, ok, extra = '') => {
  results.push(`${ok ? '  ok  ' : '  FAIL'} ${label}${extra ? ` (${extra})` : ''}`);
};

const form = new FormData();
form.append('file', new Blob([readFileSync(values.audio)]), path.basename(values.audio));
form.append('alias', 'check:flow (temporary)');
const uploaded = await fetch(`${api}/audio/upload`, { method: 'POST', body: form });
if (!uploaded.ok) throw new Error(`The upload failed: ${uploaded.status} ${await uploaded.text()}`);
const uuid = (await uploaded.json()).uuid;

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
// A 404 on `/rhythm` is how the Sheet tab asks whether a reading exists; the browser logs it too.
const expected404 = (url) => /\/time\/[^/]+\/rhythm$/.test(url);
page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400 && !(r.status() === 404 && expected404(r.url()))) problems.push(`${r.status()} ${r.url()}`); });
const shot = (name) => page.screenshot({ path: path.join(out, `${name}.png`) });
const readout = async () => (await page.locator('text=/Selected region/').first().textContent()) ?? '';

try {
  const reset = await (await fetch(`${api}/audio/${uuid}/cuts`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cuts: [] }) })).json();
  const before = reset.audioRevision;

  // 1. The new piece: only Source is enabled.
  await page.goto(`${base}/`);
  await page.waitForURL('**/piece/new');
  await page.waitForSelector('text=Audio library');
  await page.waitForTimeout(600);
  await shot('01-new');
  const disabled = await page.locator('[role=tab][aria-disabled=true]').count();
  check('/ goes to /piece/new with 4 tabs disabled', disabled === 4, `disabled=${disabled}`);

  // 2. Resume: a piece with a sheet opens on Sheet, a transcribed one on Notes.
  await page.goto(`${base}/piece/b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7`);
  await page.waitForURL('**/sheet');
  check('a piece with a piano sheet opens on the Sheet tab', page.url().endsWith('/sheet'));
  await page.goto(`${base}/piece/a585f9eb-36a1-49a0-9f0c-2626f3d292da`);
  await page.waitForURL('**/notes');
  check('a transcribed piece opens on the Notes tab', page.url().endsWith('/notes'));
  await page.goto(`${base}/piece/a585f9eb-36a1-49a0-9f0c-2626f3d292da/sheet`);
  await page.waitForURL('**/notes');
  check('a disabled tab in the address goes to the resume step', page.url().endsWith('/notes'));
  const sheetTab = page.getByRole('tab', { name: /^5\. Sheet/ });
  await sheetTab.locator('span').last().hover();
  await page.waitForSelector('[role=tooltip]');
  const tip = await page.locator('[role=tooltip]').textContent();
  check('the disabled Sheet tab says why', /Predict hands first/.test(tip ?? ''), tip);
  await shot('02-notes-tooltip');

  // 3. The new upload opens on Audio.
  await page.goto(`${base}/piece/${uuid}`);
  await page.waitForURL('**/audio');
  await page.waitForSelector('canvas');
  await page.waitForTimeout(500);
  await shot('03-audio');
  check('a new piece opens on the Audio tab', page.url().endsWith('/audio'));

  // 4. Select 30% to 40% of the waveform (moved to 25% to 45% below) and Delete.
  const canvas = page.locator('canvas').nth(1);
  const box = await canvas.boundingBox();
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width * 0.3, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.35, y, { steps: 5 });
  await page.mouse.move(box.x + box.width * 0.4, y, { steps: 5 });
  await page.mouse.up();
  const selText = await page.locator('text=/^Selection /').textContent();
  check('a drag selects a part', /Selection/.test(selText ?? ''), selText);

  // 4b. Each place of the waveform has one job (the ruler moves the playhead, an edge moves only
  //     that edge, a click clears), and a press never leaves the selection following the pointer.
  const frames = (text) => {
    const [m, s] = text.split(':');
    return Math.round((Number(m) * 60 + Number(s)) * 100);
  };
  const selection = async () => {
    const text = (await page.locator('text=/^(Selection |No selection)/').textContent()) ?? '';
    const found = text.match(/(\d\d:\d\d\.\d\d) – (\d\d:\d\d\.\d\d)/);
    return found ? [frames(found[1]), frames(found[2])] : null;
  };
  const playhead = async () =>
    frames((await page.locator('text=/^\\d\\d:\\d\\d\\.\\d\\d \\//').first().textContent()).split(' ')[0]);
  const totalFrames = (await (await fetch(`${api}/audio/${uuid}/cuts`)).json()).totalFrames;
  const xOf = (frame) => box.x + (frame / totalFrames) * box.width;
  const near = (a, b) => Math.abs(a - b) <= 30; // about 2 pixels of the whole view
  const yRuler = box.y + 12;

  await page.mouse.click(box.x + box.width * 0.6, y);
  await page.waitForTimeout(150);
  check('a click in the waveform clears the selection', (await selection()) === null);
  check('and does not move the playhead', (await playhead()) === 0);
  await page.mouse.move(box.x + box.width * 0.7, y, { steps: 5 });
  await page.mouse.move(box.x + box.width * 0.2, y, { steps: 5 });
  check('moving the pointer afterwards selects nothing', (await selection()) === null);

  await page.mouse.move(box.x + box.width * 0.3, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.4, y, { steps: 8 });
  await page.mouse.up();
  const [firstStart, firstEnd] = await selection();
  await page.mouse.move(xOf(firstEnd) + 7, y + 30);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.45, y + 30, { steps: 8 });
  await page.mouse.up();
  const afterEnd = await selection();
  check('dragging the end edge moves only the end', afterEnd[0] === firstStart && near(afterEnd[1], totalFrames * 0.45), JSON.stringify(afterEnd));
  await page.mouse.move(xOf(afterEnd[0]) - 8, y - 30);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.25, y - 30, { steps: 8 });
  await page.mouse.up();
  const afterStart = await selection();
  check('dragging the start edge moves only the start', afterStart[1] === afterEnd[1] && near(afterStart[0], totalFrames * 0.25), JSON.stringify(afterStart));
  await shot('04b-edges');

  await page.mouse.click(box.x + box.width * 0.5, yRuler);
  await page.waitForTimeout(150);
  check('a press in the ruler moves the playhead', near(await playhead(), totalFrames * 0.5), String(await playhead()));
  await page.mouse.move(box.x + box.width * 0.5, yRuler);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.55, yRuler, { steps: 5 });
  await page.mouse.up();
  check('a drag in the ruler moves it along', near(await playhead(), totalFrames * 0.55), String(await playhead()));
  check('and leaves the selection alone', JSON.stringify(await selection()) === JSON.stringify(afterStart));
  await page.mouse.dblclick(box.x + box.width * 0.7, y);
  await page.waitForTimeout(150);
  check('a double-click moves the playhead', near(await playhead(), totalFrames * 0.7), String(await playhead()));
  check('and keeps the selection', JSON.stringify(await selection()) === JSON.stringify(afterStart), JSON.stringify(await selection()));

  await page.getByRole('button', { name: 'Zoom to the selection' }).click();
  await page.waitForTimeout(200);
  const zoomed = (await page.locator('text=/^View /').textContent()) ?? '';
  const [viewStart, viewEnd] = zoomed.match(/\d\d:\d\d\.\d\d/g).map(frames);
  check('Zoom to the selection frames it with a margin', viewStart < afterStart[0] && viewEnd > afterStart[1] && viewEnd - viewStart < totalFrames / 2, zoomed);
  await shot('04c-zoomed-selection');
  await page.getByRole('button', { name: 'Show the whole audio' }).click();
  await page.waitForTimeout(150);
  await page.keyboard.press('Delete');
  await page.waitForSelector('text=/Unsaved: 1 cut/');
  await page.waitForTimeout(200);
  await shot('04-deleted');
  check('Delete makes a cut and the save bar says it', true, await readout());

  // 5. Leaving with unsaved cuts asks first.
  await page.getByRole('tab', { name: /^3\. Notes/ }).click();
  await page.waitForSelector('text=Unsaved changes');
  await shot('05-leave-dialog');
  check('leaving the tab asks to save or discard', page.url().endsWith('/audio'));
  await page.getByRole('button', { name: 'Stay' }).click();
  await page.waitForTimeout(300);
  check('Stay keeps the tab', page.url().endsWith('/audio'));

  // 6. Undo and redo.
  await page.keyboard.press('Control+z');
  await page.waitForTimeout(200);
  check('undo takes the cut back', (await page.locator('text=/Unsaved:/').count()) === 0, await readout());
  await page.keyboard.press('Control+Shift+z');
  await page.waitForTimeout(200);
  check('redo puts it again', (await page.locator('text=/Unsaved: 1 cut/').count()) > 0);

  // 7. Save.
  await page.getByRole('button', { name: 'Save', exact: true }).first().click();
  await page.waitForTimeout(800);
  const saved = await (await fetch(`${api}/audio/${uuid}/cuts`)).json();
  check('Save writes the cut', saved.cuts.length === 1 && saved.audioRevision === before + 1, JSON.stringify(saved.cuts));
  check('the save bar goes away', (await page.locator('text=/Unsaved:/').count()) === 0);
  const [cutStart, cutEnd] = saved.cuts[0];

  // 8. Play over the cut: from 1 s before it, for 2 s.
  const fraction = (f) => f / saved.totalFrames;
  await page.mouse.click(box.x + box.width * fraction(cutStart - 100), yRuler);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Play all' }).click();
  await page.waitForTimeout(1800);
  await shot('06-playing');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.waitForTimeout(200);
  const clock = await page.locator('text=/^\\d\\d:\\d\\d\\.\\d\\d \\//').first().textContent();
  const [mm, ss] = clock.split(' ')[0].split(':');
  const at = Math.round((Number(mm) * 60 + Number(ss)) * 100);
  check('Play all jumps over the cut', at > cutEnd && at < cutEnd + 150, `cut ${cutStart}-${cutEnd}, stopped at ${at}`);

  // 9. Click in the cut, Restore, then Discard.
  await page.mouse.click(box.x + box.width * fraction((cutStart + cutEnd) / 2), y);
  const restore = page.getByRole('button', { name: 'Restore' });
  check('a click in a cut selects it and enables Restore', await restore.isEnabled());
  await restore.click();
  await page.waitForSelector('text=/Unsaved: no cut/');
  await page.getByRole('button', { name: 'Discard' }).click();
  await page.waitForTimeout(200);
  check('Discard goes back to the saved cut', (await page.locator('text=/Unsaved:/').count()) === 0, await readout());

  // 10. Zoom with Control and the wheel.
  await page.mouse.move(box.x + box.width * 0.5, y);
  await page.keyboard.down('Control');
  for (let i = 0; i < 6; i += 1) await page.mouse.wheel(0, -300);
  await page.keyboard.up('Control');
  await page.waitForTimeout(300);
  const viewText = await page.locator('text=/^View /').textContent();
  check('Control and the wheel zoom in', !/View 00:00.00 – 03:0/.test(viewText ?? ''), viewText);
  await shot('07-zoomed');
  for (let i = 0; i < 6; i += 1) { await page.keyboard.down('Control'); await page.mouse.wheel(0, -400); await page.keyboard.up('Control'); }
  await page.waitForTimeout(300);
  await shot('08-zoomed-frames');

  if (!values['no-transcribe']) {
  // 11. Transcribe, and watch the live piano roll visualization on the Notes tab.
  await page.getByRole('button', { name: /^Transcribe/ }).click();
  await page.waitForURL('**/notes');
  check('Transcribe opens the Notes tab', page.url().endsWith('/notes'));
  // Orange pixels on the lower canvas: how much of the notes is drawn.
  const drawn = () => page.evaluate(() => {
    const canvas = document.querySelector('canvas[data-roll=base]');
    if (!canvas) return -1;
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0;
    for (let i = 0; i < data.length; i += 16) if (data[i] > 200 && data[i + 1] > 100 && data[i + 1] < 170 && data[i + 2] < 90) count += 1;
    return count;
  });
  const barText = () => page.locator('[data-bar=position]').textContent();
  await page.waitForFunction(() => /\d:\d\d \/ \d:\d\d/.test(document.querySelector('[data-bar=position]')?.textContent ?? ''), null, { timeout: 30000 });
  const early = await drawn();
  const earlyText = await barText();
  await page.waitForTimeout(3000);
  const later = await drawn();
  const laterText = await barText();
  await shot('09-transcribing');
  check('the live view draws the notes as they arrive', early >= 0 && later > early, `${early} then ${later} pixels`);
  check('the progress bar moves with the transcription', earlyText !== laterText, `${earlyText} then ${laterText}`);
  const liveRight = (await page.locator('[data-bar=details]').textContent()) ?? '';
  check('the bar says the notes, the time taken and the time left', /notes · \d:\d\d elapsed/.test(liveRight), liveRight);
  await page.getByRole('button', { name: 'Play', exact: true }).waitFor({ timeout: 90000 });
  await page.waitForTimeout(600);
  await shot('10-transcribed');
  const status = await (await fetch(`${api}/pieces/${uuid}/status`)).json();
  check('the notes are ready after the transcription', status.steps[2].state === 'ready', JSON.stringify(status.steps[2].details));
  const took = (await page.locator('text=/^Transcribed in /').textContent()) ?? '';
  check('the page says how long the transcription took', /Transcribed in \d:\d\d/.test(took), took);

  // 12. The editor: select, move, undo and redo, resize, add, delete, a band, save.
  await page.getByRole('button', { name: 'Show the whole piece' }).click();
  await page.getByRole('button', { name: 'Zoom in' }).click();
  await page.getByRole('button', { name: 'Zoom in' }).click();
  await page.waitForTimeout(300);
  const notesBefore = await (await fetch(`${api}/pieces/${uuid}/notes`)).json();
  const top = page.locator('canvas[data-roll=top]');
  const roll = await top.boundingBox();
  const geometry = async () => page.evaluate(() => {
    const canvas = document.querySelector('canvas[data-roll=base]');
    const [low, high] = canvas.dataset.keys.split(',').map(Number);
    return { start: Number(canvas.dataset.viewStart), pxPerSec: Number(canvas.dataset.pxPerSec), low, high };
  });
  const g = await geometry();
  const rowHeight = (roll.height - 24) / (g.high - g.low + 1);
  const px = (ms) => roll.x + 46 + ((ms - g.start) * g.pxPerSec) / 1000;
  const py = (key) => roll.y + 24 + (g.high - key + 0.5) * rowHeight;
  const spanEnd = g.start + ((roll.width - 46) * 1000) / g.pxPerSec;
  const notes = notesBefore.id.map((id, i) => ({ id, key: notesBefore.key[i], on: notesBefore.onMs[i], len: notesBefore.lenMs[i] }));
  const clearAfter = (note, ms) => !notes.some((other) => other.id !== note.id && other.key === note.key && other.on > note.on && other.on < note.on + note.len + ms);
  const inView = (note) => note.on > g.start + 500 && note.on + note.len + 400 < spanEnd && note.key > g.low && note.key < g.high;
  const target = notes.find((note) => inView(note) && note.len >= 300 && clearAfter(note, 1500));
  const victim = notes.find((note) => inView(note) && note.len >= 150 && note.id !== target?.id && note.key !== target?.key);
  if (!target || !victim) throw new Error('no note to edit in the view');
  // The unsaved changes, as the Save button of the floating toolbar carries them ('' when none).
  const unsaved = async () => ((await page.locator('[data-unsaved]').first().getAttribute('data-unsaved').catch(() => '')) || null);
  const selectionName = async () => (await page.locator('[data-selection-name]').first().textContent({ timeout: 2000 }).catch(() => '')) ?? '';
  const spanish = (midi) => `${['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'][midi % 12]} ${Math.floor(midi / 12) - 1}`;
  // Coloured pixels on the keyboard strip of the upper canvas: the keys lit there.
  const litKeys = () => page.evaluate(() => {
    const canvas = document.querySelector('canvas[data-roll=top]');
    const ratio = canvas.width / canvas.getBoundingClientRect().width;
    const data = canvas.getContext('2d').getImageData(0, Math.round(24 * ratio), Math.round(40 * ratio), canvas.height - Math.round(24 * ratio)).data;
    let count = 0;
    for (let i = 3; i < data.length; i += 4) if (data[i] > 0) count += 1;
    return count;
  });

  await page.mouse.click(px(target.on + target.len / 2), py(target.key));
  await page.waitForTimeout(150);
  const picked = await selectionName();
  check('a click on a note selects it and names it in Spanish', picked === spanish(target.key + 21), `${picked}, expected ${spanish(target.key + 21)}`);
  check('the key of the selected note is lit on the keyboard', (await litKeys()) > 0);
  await shot('11-selected');

  const dx = (0.2 * g.pxPerSec);
  await page.mouse.move(px(target.on + target.len / 2), py(target.key));
  await page.mouse.down();
  await page.mouse.move(px(target.on + target.len / 2) + dx / 2, py(target.key), { steps: 4 });
  await page.mouse.move(px(target.on + target.len / 2) + dx, py(target.key), { steps: 4 });
  await page.mouse.up();
  await page.waitForTimeout(200);
  check('dragging a note moves it (the save bar says it)', (await unsaved()) === 'Unsaved: 1 note moved', await unsaved());
  await shot('12-moved');
  await page.keyboard.press('Control+z');
  await page.waitForTimeout(150);
  check('undo takes the move back', (await unsaved()) === null, await unsaved());
  await page.keyboard.press('Control+Shift+z');
  await page.waitForTimeout(150);
  check('redo moves it again', (await unsaved()) === 'Unsaved: 1 note moved', await unsaved());

  const movedEnd = target.on + 200 + target.len;
  await page.mouse.move(px(movedEnd) - 3, py(target.key));
  await page.mouse.down();
  await page.mouse.move(px(movedEnd) - 3 - (0.1 * g.pxPerSec), py(target.key), { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(150);
  check('dragging the right edge is the same note changed (still 1 note moved)', (await unsaved()) === 'Unsaved: 1 note moved', await unsaved());

  // An empty place: a key with no note within 1 s, in the middle of the view.
  const middle = Math.round((g.start + spanEnd) / 2 / 10) * 10;
  let emptyKey = null;
  for (let key = g.high - 3; key > g.low + 3 && emptyKey === null; key -= 1) {
    if (!notes.some((note) => Math.abs(note.key - key) <= 1 && note.on < middle + 1000 && note.on + note.len > middle - 1000)) emptyKey = key;
  }
  if (emptyKey === null) throw new Error('no empty place in the view');
  await page.mouse.dblclick(px(middle), py(emptyKey));
  await page.waitForTimeout(200);
  check('a double-click on empty space adds a note', (await unsaved()) === 'Unsaved: 1 note moved, 1 added', await unsaved());

  await page.mouse.click(px(victim.on + victim.len / 2), py(victim.key));
  await page.keyboard.press('Delete');
  await page.waitForTimeout(200);
  check('Delete deletes the selected note', (await unsaved()) === 'Unsaved: 1 note moved, 1 deleted, 1 added', await unsaved());
  await shot('13-edited');

  await page.mouse.move(px(g.start + 200), py(g.high - 1) - rowHeight / 2 + 1);
  await page.mouse.down();
  await page.mouse.move(px((g.start + spanEnd) / 2), py(g.low + 1), { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(150);
  const banded = await selectionName();
  check('a drag on empty space selects a band of notes', /^\d+ notes/.test(banded), banded);
  await shot('14-band');
  await page.keyboard.press('Escape');

  await page.getByRole('button', { name: 'Save', exact: true }).first().click();
  await page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 5000 });
  const notesAfter = await (await fetch(`${api}/pieces/${uuid}/notes`)).json();
  const after = (id) => { const i = notesAfter.id.indexOf(id); return i < 0 ? null : { key: notesAfter.key[i], on: notesAfter.onMs[i], len: notesAfter.lenMs[i] }; };
  const movedNote = after(target.id);
  check('Save writes the move and the shorter length', movedNote && movedNote.on === target.on + 200 && movedNote.len === target.len - 100, JSON.stringify({ before: target, after: movedNote }));
  check('Save writes the delete', after(victim.id) === null);
  const addedIds = notesAfter.id.filter((id) => !notesBefore.id.includes(id));
  const addedNote = addedIds.length === 1 ? after(addedIds[0]) : null;
  check('Save writes the added note, 250 ms on that key', addedNote && addedNote.key === emptyKey && Math.abs(addedNote.on - middle) <= 30 && addedNote.len === 250, JSON.stringify(addedNote));
  check('Save raises the notes revision by one', notesAfter.revision === notesBefore.revision + 1, `${notesBefore.revision} -> ${notesAfter.revision}`);
  await page.keyboard.press('Control+z');
  await page.waitForTimeout(150);
  check('undo after a save is an unsaved change again', /^Unsaved: /.test((await unsaved()) ?? ''), await unsaved());
  await page.keyboard.press('Control+Shift+z');
  await page.waitForTimeout(150);
  check('and redo brings back the saved state', (await unsaved()) === null, await unsaved());

  // 13. Playback: the ruler moves the playhead, Play starts there, and the playhead keeps the
  //     pace of the audio; the sounding notes and their keys are lit (picture 15).
  const clock = async () => {
    const text = (await page.locator('[data-bar=position]').textContent()) ?? '';
    const [minutes, seconds] = text.split(' ')[0].split(':').map(Number);
    return (minutes * 60 + seconds) * 1000;
  };
  // Clicking Save scrolled the page to show the button: measure the canvas again.
  const shifted = (await top.boundingBox()).y - roll.y;
  await page.mouse.click(px(target.on + 100), roll.y + shifted + 10);
  await page.waitForTimeout(150);
  const rested = await clock();
  check('a press in the ruler moves the playhead', Math.abs(rested - (target.on + 100)) <= 30, `${rested} ms, aimed at ${target.on + 100}`);
  await page.getByRole('button', { name: 'Play', exact: true }).click();
  const pressed = Date.now();
  while ((await clock()) === rested && Date.now() - pressed < 5000) await page.waitForTimeout(20);
  const startedAfter = Date.now() - pressed;
  const first = await clock();
  // The pace is measured once the audio has settled; its first tenths of a second are the start.
  await page.waitForTimeout(300);
  const from = await clock();
  const t1 = Date.now();
  await page.waitForTimeout(1200);
  const to = await clock();
  const wall = Date.now() - t1;
  await shot('15-playing');
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.waitForTimeout(200);
  const pausedAt = await clock();
  const notesNow = await (await fetch(`${api}/pieces/${uuid}/notes`)).json();
  const soundingNow = notesNow.onMs.some((on, i) => on <= pausedAt && on + notesNow.lenMs[i] > pausedAt + 10);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(150);
  if (soundingNow) check('after a pause, the keys of the notes still sounding stay lit', (await litKeys()) > 0, `paused at ${pausedAt} ms`);
  await shot('15b-paused');
  check('Play starts from the playhead', first >= rested && first < rested + 300, `started after ${startedAfter} ms, at ${first} ms`);
  check('the playhead keeps the pace of the audio', Math.abs((to - from) - wall) < 150, `${to - from} ms of audio in ${wall} ms`);

  // 14. The Hands tab: Predict hands with its progress, the filter, a note to the other hand, Save,
  //     and the hand colours on the Notes tab.
  await page.getByRole('tab', { name: /^4\. Hands/ }).click();
  await page.waitForURL('**/hands');
  const predictButton = page.getByRole('button', { name: 'Predict hands', exact: true });
  await predictButton.waitFor();
  await page.waitForTimeout(400);
  await shot('16-hands-before');
  await predictButton.click();
  let sawProgress = false;
  for (let i = 0; i < 100 && !sawProgress; i += 1) {
    sawProgress = (await page.locator('[role=status]').count()) > 0;
    if (!sawProgress) await page.waitForTimeout(10);
  }
  if (sawProgress) await shot('17-predicting');
  check('Predict hands shows a progress bar while it runs', sawProgress);
  const predictedText = (await page.locator('text=/^Predicted in /').textContent({ timeout: 30000 })) ?? '';
  check('Predict hands says what it found', /Predicted in \d+\.\d s · \d+ notes changed hand/.test(predictedText), predictedText);
  const progressWidth = await page.evaluate(() => document.querySelector('[role=status]')?.getBoundingClientRect().width ?? 0);
  check('the progress bar is gone at the end', progressWidth === 0, String(progressWidth));
  await page.waitForTimeout(300);
  await shot('18-predicted');
  check('the prediction is an unsaved change', /^Unsaved: \d+ notes with another hand$/.test((await unsaved()) ?? ''), await unsaved());
  const handsTab = page.getByRole('tab', { name: /^4\. Hands/ });
  check('while it is unsaved, the Hands tab shows a pencil, not a tick', (await handsTab.locator('[data-testid=EditOutlinedIcon]').count()) === 1 && (await handsTab.locator('[data-testid=CheckCircleIcon]').count()) === 0);
  const coloured = await page.evaluate(() => {
    const canvas = document.querySelector('canvas[data-roll=base]');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let blue = 0;
    let green = 0;
    for (let i = 0; i < data.length; i += 16) {
      if (data[i] < 190 && data[i + 1] > 170 && data[i + 2] > 230) blue += 1; // light blue
      if (data[i] < 180 && data[i + 1] > 215 && data[i + 2] > 190 && data[i + 2] < 225) green += 1; // light green
    }
    return { blue, green };
  });
  check('the rectangles take the colours of the two hands', coloured.blue > 50 && coloured.green > 50, JSON.stringify(coloured));
  await page.getByRole('button', { name: 'Right', exact: true }).click();
  await page.waitForTimeout(250);
  await shot('19-right-only');
  await page.getByRole('button', { name: 'Both hands', exact: true }).click();
  // One note to the other hand, by its key: the note the walk moved earlier.
  const g2 = await geometry();
  const box2 = await top.boundingBox();
  const rows2 = (box2.height - 24) / (g2.high - g2.low + 1);
  const at2 = (ms) => box2.x + 46 + ((ms - g2.start) * g2.pxPerSec) / 1000;
  const handsNow = (await (await fetch(`${api}/pieces/${uuid}/notes`)).json());
  const visible = handsNow.id.map((id, i) => ({ id, key: handsNow.key[i], on: handsNow.onMs[i], len: handsNow.lenMs[i] }))
    .find((note) => note.len >= 200 && note.on > g2.start + 300 && at2(note.on + note.len) < box2.x + box2.width - 20 && note.key > g2.low && note.key < g2.high);
  if (visible) {
    await page.mouse.click(at2(visible.on + visible.len / 2), box2.y + 24 + (g2.high - visible.key + 0.5) * rows2);
    await page.keyboard.press('r');
    await page.keyboard.press('l');
    await page.waitForTimeout(150);
  }
  check('R and L move the selected note between the hands', Boolean(visible));
  // The notes without a hand: select them, then go through them with the arrows.
  const handlessButton = page.getByRole('button', { name: 'Select the notes without a hand' });
  if (await handlessButton.count()) {
    await handlessButton.click();
    await page.getByRole('button', { name: 'Next note without a hand' }).click();
    await page.waitForTimeout(250);
    const reviewText = (await page.locator('[data-review]').first().textContent().catch(() => '')) ?? '';
    check('the arrows go to one note without a hand at a time', /^1 \/ \d+$/.test(reviewText) && /^(Do|Re|Mi|Fa|Sol|La|Si)#? \d$/.test(await selectionName()), `${reviewText}, ${await selectionName()}`);
    await shot('19b-review');
    await page.keyboard.press('Escape');
  }
  await page.getByRole('button', { name: 'Save', exact: true }).first().click();
  await page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 10000 });
  await page.waitForTimeout(500);
  const afterHands = await (await fetch(`${api}/pieces/${uuid}/notes`)).json();
  const withHand = [...afterHands.hand].filter((h) => h !== '-').length;
  check('Save writes the hands', withHand > afterHands.id.length * 0.9, `${withHand} of ${afterHands.id.length} notes have a hand`);
  if (visible) check('the note given to the left hand is saved as left', afterHands.hand[afterHands.id.indexOf(visible.id)] === 'l');
  const handsStatus = (await (await fetch(`${api}/pieces/${uuid}/status`)).json()).steps[3];
  const handlessLeft = [...afterHands.hand].filter((h) => h === '-').length;
  check('after Save the Hands step is ready, even with notes the sheet cannot place', handsStatus.state === 'ready' && handsStatus.details.unplaced === handlessLeft, `${handsStatus.state}, ${handlessLeft} without a hand`);
  await page.waitForTimeout(300);
  check('and the Hands tab shows its tick again', (await handsTab.locator('[data-testid=CheckCircleIcon]').count()) === 1);
  check('and the Sheet tab can be opened', (await page.getByRole('tab', { name: /^5\. Sheet/ }).getAttribute('aria-disabled')) !== 'true');
  await shot('20-hands-saved');
  await page.getByRole('tab', { name: /^3\. Notes/ }).click();
  await page.waitForURL('**/notes');
  const handSwitch = page.getByLabel('Hand colours');
  await handSwitch.waitFor();
  check('the Notes tab colours by hand once the piece has hands', await handSwitch.isChecked());
  await page.waitForTimeout(300);
  await shot('21-notes-with-hands');
  await handSwitch.click();
  await page.waitForTimeout(300);
  check('Hand colours can be turned off', !(await handSwitch.isChecked()));
  await shot('22-notes-without-hands');
  await handSwitch.click();

  // 15. The Sheet tab: the piano sheet inside the flow page. A new piece has no reading yet; once
  //     written and saved the tab is ticked. A notes edit made elsewhere makes it stale: the page
  //     waits with its banner until Write the sheet, then Save makes it ready again.
  const sheetTabNow = page.getByRole('tab', { name: /^5\. Sheet/ });
  const sheetState = async () => (await (await fetch(`${api}/pieces/${uuid}/status`)).json()).steps[4].state;
  await sheetTabNow.click();
  await page.waitForURL('**/sheet');
  await page.waitForSelector('text=How this piece was played');
  check('the Sheet tab opens the piano sheet in the flow page', (await page.locator('text=Every bar below is a gap').count()) === 1);
  check('a piece with no reading says what to do', (await page.locator('[data-sheet-banner=missing]').count()) === 1, await page.locator('[data-sheet-banner]').first().textContent().catch(() => 'no banner'));
  const writeSheet = page.getByRole('button', { name: 'Write the sheet', exact: true });
  await page.waitForFunction(() => [...document.querySelectorAll('button')].some((b) => b.textContent === 'Write the sheet' && !b.disabled), null, { timeout: 30000 });
  await writeSheet.click();
  await page.waitForSelector('.grid-notehead', { timeout: 60000 });
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-sheet-banner]') === null, null, { timeout: 15000 });
  await page.waitForTimeout(400);
  check('Write the sheet and Save make the Sheet step ready, and its tab is ticked', (await sheetState()) === 'ready' && (await sheetTabNow.locator('[data-testid=CheckCircleIcon]').count()) === 1, await sheetState());
  await shot('23-sheet-saved');
  const sheetNotes = await (await fetch(`${api}/pieces/${uuid}/notes`)).json();
  const edited = await fetch(`${api}/pieces/${uuid}/notes`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      baseRevision: sheetNotes.revision,
      baseHandsRevision: sheetNotes.handsRevision,
      ops: [{ op: 'move', id: sheetNotes.id[20], onMs: sheetNotes.onMs[20] + 30, lenMs: sheetNotes.lenMs[20] }],
    }),
  });
  check('a notes edit made elsewhere makes the sheet stale', edited.ok && (await sheetState()) === 'stale', await sheetState());
  await page.reload();
  await page.waitForSelector('[data-sheet-banner=stale]');
  await page.waitForTimeout(2500);
  check('the stale sheet opens with its banner and is not drawn until Write the sheet', (await page.locator('.grid-notehead').count()) === 0);
  check('and it cannot be saved before Write the sheet', (await page.getByRole('button', { name: /^Save/ }).count()) === 0);
  await shot('24-sheet-stale');
  await writeSheet.click();
  await page.waitForSelector('.grid-notehead', { timeout: 60000 });
  const afterWrite = (await page.locator('[data-sheet-banner=stale]').textContent()) ?? '';
  check('after Write the sheet the banner asks for Save', /Press Save/.test(afterWrite), afterWrite);
  check('and the step is still stale until Save', (await sheetState()) === 'stale');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-sheet-banner]') === null, null, { timeout: 15000 });
  await page.waitForTimeout(400);
  check('Save makes the stale sheet ready again', (await sheetState()) === 'ready' && (await sheetTabNow.locator('[data-testid=CheckCircleIcon]').count()) === 1, await sheetState());
  await shot('25-sheet-ready-again');

  // 16. A hand move on a zoomed sheet (Command and the wheel, or a pinch). The rebuild used to read
  //     the emptied, content-sized box as 0 wide, and the whole page fell over.
  const firstHead = await page.locator('.grid-notehead').first().boundingBox();
  await page.mouse.move(firstHead.x, firstHead.y);
  await page.keyboard.down('Control');
  for (let i = 0; i < 3; i += 1) { await page.mouse.wheel(0, -100); await page.waitForTimeout(100); }
  await page.keyboard.up('Control');
  await page.waitForTimeout(600);
  const pick = await page.locator('.grid-note-target[data-hand=right]').nth(30);
  const pickKey = await pick.getAttribute('data-note-key');
  await pick.evaluate((node) => node.scrollIntoView({ block: 'center', inline: 'center' }));
  await page.waitForTimeout(200);
  const pickBox = await pick.boundingBox();
  // Sent to the note itself: the playhead line may stand on it and take a real click.
  await pick.evaluate((node, [x, y]) => {
    for (const type of ['pointerdown', 'pointerup', 'click']) {
      const Ctor = type === 'click' ? MouseEvent : PointerEvent;
      node.dispatchEvent(new Ctor(type, { bubbles: true, clientX: x, clientY: y, button: 0, buttons: type === 'pointerdown' ? 1 : 0, pointerId: 1, isPrimary: true }));
    }
  }, [pickBox.x + pickBox.width / 2, pickBox.y + pickBox.height / 2]);
  await page.locator('button[title^="Play with the left hand"]').click();
  const movedKey = `left:${pickKey.split(':').slice(1).join(':')}`;
  await page.waitForSelector(`.grid-note-target[data-note-key="${movedKey}"]`, { timeout: 15000 }).catch(() => null);
  check('a hand move on a zoomed sheet redraws it without an error',
    (await page.locator('text=Unexpected Application Error').count()) === 0 && (await page.locator(`.grid-note-target[data-note-key="${movedKey}"]`).count()) === 1);
  await shot('26-sheet-zoomed-move');
  }
} catch (caught) {
  check('the walk finished', false, caught instanceof Error ? caught.message.split('\n')[0] : String(caught));
} finally {
  await browser.close();
  await fetch(`${api}/audio/${uuid}`, { method: 'DELETE' });
}

console.log(results.join('\n'));
console.log(problems.length ? `\nProblems:\n${problems.join('\n')}` : '\nNo console error, no failed request.');
const failed = results.filter((line) => line.includes('FAIL')).length;
console.log(failed === 0 ? '\nEvery check passed.\n' : `\n${failed} check${failed === 1 ? '' : 's'} failed.\n`);
process.exit(failed === 0 ? 0 : 1);
