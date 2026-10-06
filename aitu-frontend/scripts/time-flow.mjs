/**
 * The whole flow, timed, on three pieces (implementation 08, Phase 9, Task 9.1).
 *
 * `check:flow` checks every gesture of the flow page on one piece. This walks the flow the way a
 * reader does, from the audio to the saved piano sheet, and times each step from the press of its
 * button to its result on screen:
 *
 * - `in`: the piece arriving. An upload (the request), a YouTube download (Download to the Audio
 *   tab), or a library piece opened from Projects (the click to the step it resumes on);
 * - `transcribe`: Transcribe to the first note received in the live view (`firstNote`), and to the saved notes on screen
 *   (`notes`); `backend` is no longer on screen (implementation 02, Phase 1) and stays empty;
 * - `hands`: Predict hands to its answer on screen (`predict`), then Save (`save`);
 * - `sheet`: the Sheet tab to the page (`open`), the Sheet tab to the first
 *   notehead drawn (`firstSheet`), then Save (`save`).
 *
 * The three pieces, all temporary, deleted at the end, so the library is never changed:
 *
 * 1. Superestrella: its audio uploaded as a new piece (as `check:flow` does);
 * 2. a library piece: a copy made by `POST /projects/{id}/duplicate` (as `bench:sheet` does), opened from
 *    the library list, transcribed again with MuScriptor (the confirmation is pressed);
 * 3. a new YouTube URL, downloaded on the Source tab.
 *
 *     npm run time:flow
 *     npm run time:flow -- --library fb0b0989 --youtube <url> --out result.json --keep
 *
 * It needs `make up`. `--keep` leaves the three pieces in the library (to look at them after).
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const SUPERESTRELLA = 'a585f9eb-36a1-49a0-9f0c-2626f3d292da';
const { values } = parseArgs({
  options: {
    // A file to upload; Superestrella's own stored audio when absent.
    audio: { type: 'string' },
    // The Winner Takes It All, 5:56: the longest piece of the library, ByteDance notes, no hands.
    library: { type: 'string', default: 'fb0b0989' },
    // Yann Tiersen, "Comptine d'un autre été, l'après-midi", 2:21, solo piano; not in the library.
    youtube: { type: 'string', default: 'https://www.youtube.com/watch?v=znfYwABeSZ0' },
    only: { type: 'string' },
    keep: { type: 'boolean', default: false },
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string' },
    shots: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'time-flow') },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
mkdirSync(values.shots, { recursive: true });

const engine = await (await fetch(`${api}/matrix/engine`)).json();
console.log(`Engine: ${JSON.stringify(engine)}`);

/** A temporary copy of a library piece (`POST /projects/{id}/duplicate`): new ids, the same audio
 * files, no history, staging or video. */
async function copyPiece(prefix) {
  const listed = await (await fetch(`${api}/audio/`)).json();
  const source = listed.find((entry) => entry.uuid.startsWith(prefix.slice(0, 8)));
  if (!source) throw new Error(`No piece starts with ${prefix}`);
  const alias = `time:flow copy of ${source.alias}`;
  const answer = await fetch(`${api}/projects/${source.uuid}/duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: alias }),
  });
  if (!answer.ok) throw new Error(`The copy failed: ${answer.status} ${await answer.text()}`);
  return { uuid: (await answer.json()).parts[0], alias };
}

/** The stored audio file of a piece, as the user uploaded it (`GET /audio/{id}/file?original=true`). */
async function originalOf(uuid) {
  const answer = await fetch(`${api}/audio/${uuid}/file?original=true`);
  if (!answer.ok) throw new Error(`No audio for ${uuid}: ${answer.status}`);
  const name = /filename="?([^";]+)"?/.exec(answer.headers.get('content-disposition') ?? '')?.[1] ?? 'audio.mp3';
  return { bytes: await answer.arrayBuffer(), name };
}

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
useSession(browser);
const created = [];
const report = [];

async function walk(name, arrive) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const problems = [];
  const expected404 = (url) => /\/time\/[^/]+\/rhythm$/.test(url);
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400 && !(r.status() === 404 && expected404(r.url()))) problems.push(`${r.status()} ${r.url()}`); });
  const shot = (step) => page.screenshot({ path: path.join(values.shots, `${name}-${step}.png`) });
  const row = { piece: name, problems };
  const started = Date.now();
  try {
    // 1. The piece arrives, and the page is on its Audio tab.
    const arrived = await arrive(page, row);
    row.uuid = arrived.uuid;
    const audio = await (await fetch(`${api}/audio/${arrived.uuid}`)).json();
    row.title = audio.alias ?? audio.title;
    row.durationSeconds = Math.round(audio.durationSeconds ?? audio.duration_seconds ?? 0);
    if (!page.url().endsWith('/audio')) {
      await page.getByRole('tab', { name: 'Audio', exact: true }).click();
      await page.waitForURL('**/audio');
    }
    await page.getByRole('button', { name: /^Transcribe/ }).waitFor();
    // A reader presses Transcribe after the waveform is drawn. Pressed at once, the first note
    // waits about a second more for the page to finish loading the Audio tab.
    await page.waitForSelector('canvas');
    await page.waitForTimeout(1500);

    // 2. Transcribe, followed live on the Notes tab.
    const drawn = () => page.evaluate(() => {
      const canvas = document.querySelector('canvas[data-roll=base]');
      if (!canvas) return 0;
      const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
      let count = 0;
      for (let i = 0; i < data.length; i += 16) if (data[i] > 200 && data[i + 1] > 100 && data[i + 1] < 170 && data[i + 2] < 90) count += 1;
      return count;
    });
    const pressed = Date.now();
    await page.getByRole('button', { name: /^Transcribe/ }).click();
    // A piece with current notes asks first; a new one goes straight to the Notes tab.
    const again = page.getByRole('button', { name: 'Transcribe again', exact: true });
    const asked = await Promise.race([
      again.waitFor({ timeout: 10000 }).then(() => true),
      page.waitForURL('**/notes', { timeout: 10000 }).then(() => false),
    ]);
    if (asked) {
      row.transcribedAgain = true;
      await again.click();
    }
    await page.waitForURL('**/notes');
    // The first note of this transcription: the live bar counts the notes received. (Pixels on the
    // canvas would also count the old notes a piece transcribed again shows until the stream starts.)
    let firstNote = null;
    while (firstNote === null && Date.now() - pressed < 120000) {
      const details = (await page.locator('[data-bar=details]').textContent({ timeout: 1000 }).catch(() => '')) ?? '';
      if (/^[1-9]\d* notes/.test(details)) firstNote = Date.now() - pressed;
      else await page.waitForTimeout(20);
    }
    await page.waitForTimeout(Math.max(0, 8000 - (Date.now() - pressed)));
    const live = await drawn();
    await shot('1-live');
    await page.getByRole('button', { name: 'Play from the playhead', exact: true }).waitFor({ timeout: 600000 });
    const notesShown = Date.now() - pressed;
    // The page no longer prints "Transcribed in" (implementation 02, Phase 1): the backend's own
    // clock is not on screen any more, so only the time measured here is kept.
    const took = '';
    const notes = await (await fetch(`${api}/pieces/${arrived.uuid}/notes`)).json();
    const status = await (await fetch(`${api}/pieces/${arrived.uuid}/status`)).json();
    row.transcribe = { firstNote, livePixels: live, notes: notesShown, backend: took || null, count: notes.id.length, engine: status.steps[2].details?.engine ?? null };
    await page.waitForTimeout(500);
    await shot('2-notes');

    // 3. Predict hands, then Save.
    await page.getByRole('tab', { name: 'Hands', exact: true }).click();
    await page.waitForURL('**/hands');
    const predict = page.getByRole('button', { name: 'Predict hands', exact: true });
    await predict.waitFor();
    const predictPressed = Date.now();
    await predict.click();
    // What the prediction changed, said on the page (`data-predicted`) once it has answered.
    await page.waitForSelector('[data-predicted]', { timeout: 120000 });
    const predicted = (await page.locator('[data-predicted]').textContent()) ?? '';
    const predictTime = Date.now() - predictPressed;
    await page.waitForTimeout(300);
    await shot('3-hands');
    const savePressed = Date.now();
    await page.getByRole('button', { name: 'Save', exact: true }).first().click();
    await page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 30000 });
    const handsSaved = Date.now() - savePressed;
    const afterHands = await (await fetch(`${api}/pieces/${arrived.uuid}/notes`)).json();
    row.hands = {
      predict: predictTime,
      page: predicted,
      save: handsSaved,
      withoutHand: [...afterHands.hand].filter((h) => h === '-').length,
    };

    // 4. The Sheet tab: the first piano sheet, drawn on arrival (implementation 02, Phase 2), then
    //    Save. `open` is the tab press to the page, `firstSheet` the tab press to the first notehead
    //    (in implementation 08 it was the press of Write the sheet, a separate step after `open`).
    const sheetTab = page.getByRole('tab', { name: 'Sheet', exact: true });
    await page.waitForFunction(() => document.querySelector('[role=tab][aria-disabled=false]') !== null);
    await page.waitForFunction(() => {
      const tab = document.querySelector('[role=tab][data-step=sheet]');
      return tab && tab.getAttribute('aria-disabled') !== 'true';
    }, null, { timeout: 15000 });
    const tabPressed = Date.now();
    await sheetTab.click();
    await page.waitForURL('**/sheet');
    await page.waitForSelector('[data-sheet-page]', { timeout: 60000 });
    const sheetOpen = Date.now() - tabPressed;
    await page.waitForSelector('.grid-notehead', { timeout: 120000 });
    const firstSheet = Date.now() - tabPressed;
    await page.waitForTimeout(400);
    await shot('4-sheet');
    const sheetSavePressed = Date.now();
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 30000 });
    const sheetSaved = Date.now() - sheetSavePressed;
    const finalStatus = await (await fetch(`${api}/pieces/${arrived.uuid}/status`)).json();
    row.sheet = {
      open: sheetOpen,
      firstSheet,
      save: sheetSaved,
      noteheads: await page.locator('.grid-notehead').count(),
      steps: finalStatus.steps.map((s) => s.state).join(' '),
    };
    row.total = Date.now() - started;
    await shot('5-saved');
  } catch (caught) {
    row.error = caught instanceof Error ? caught.message.split('\n')[0] : String(caught);
    await shot('error').catch(() => {});
  } finally {
    await page.close();
  }
  report.push(row);
  console.log(JSON.stringify(row));
}

const pieces = {
  // Superestrella's audio, uploaded as a new piece.
  upload: async (page, row) => {
    const t0 = Date.now();
    const form = new FormData();
    const audio = values.audio
      ? { bytes: readFileSync(values.audio), name: path.basename(values.audio) }
      : await originalOf(SUPERESTRELLA);
    form.append('file', new Blob([audio.bytes]), audio.name);
    form.append('alias', 'time:flow upload of Superestrella');
    const answer = await fetch(`${api}/audio/upload`, { method: 'POST', body: form });
    if (!answer.ok) throw new Error(`The upload failed: ${answer.status} ${await answer.text()}`);
    const uuid = (await answer.json()).uuid;
    created.push(uuid);
    row.in = { how: 'upload', ms: Date.now() - t0 };
    await page.goto(`${base}/projects/${uuid}`);
    await page.waitForURL('**/audio');
    return { uuid };
  },
  // A library piece, copied, opened from its row in Projects.
  library: async (page, row) => {
    const { uuid, alias } = await copyPiece(values.library);
    created.push(uuid);
    await page.goto(`${base}/projects`);
    const item = page.getByText(alias, { exact: true });
    await item.waitFor({ timeout: 15000 });
    const t0 = Date.now();
    await item.click();
    await page.waitForURL(new RegExp(`/projects/${uuid}/(audio|notes|hands|sheet)$`));
    await page.locator('[role=tab][aria-selected=true]').waitFor();
    row.in = { how: 'library', ms: Date.now() - t0, opensOn: page.url().split('/').pop() };
    return { uuid };
  },
  // A new YouTube URL, downloaded on the Source tab.
  youtube: async (page, row) => {
    await page.goto(`${base}/projects/new`);
    await page.getByLabel('Paste a YouTube link').fill(values.youtube);
    // No name is asked for: the piece takes the video's title.
    const t0 = Date.now();
    await page.getByRole('button', { name: 'Download the audio', exact: true }).click();
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}\/audio$/, { timeout: 300000 });
    const uuid = page.url().split('/').at(-2);
    created.push(uuid);
    row.in = { how: 'youtube', ms: Date.now() - t0, url: values.youtube };
    return { uuid };
  },
};

try {
  for (const name of values.only ? values.only.split(',') : Object.keys(pieces)) await walk(name, pieces[name]);
} finally {
  await browser.close();
  if (!values.keep) for (const uuid of created) await fetch(`${api}/audio/${uuid}`, { method: 'DELETE' });
}

const seconds = (ms) => (ms === null || ms === undefined ? '-' : `${(ms / 1000).toFixed(1)} s`);
console.log('\npiece | length | in | first note | notes | hands | sheet ready | first sheet | total');
for (const r of report) {
  if (r.error) { console.log(`${r.piece} | FAILED: ${r.error}`); continue; }
  console.log([
    r.piece, `${r.durationSeconds} s`, seconds(r.in?.ms), seconds(r.transcribe.firstNote), seconds(r.transcribe.notes),
    seconds(r.hands.predict), seconds(r.sheet.open), seconds(r.sheet.firstSheet), seconds(r.total),
  ].join(' | '));
  if (r.problems.length) console.log(`  problems: ${r.problems.join('; ')}`);
}
if (values.out) writeFileSync(values.out, `${JSON.stringify({ date: new Date().toISOString(), engine, pieces: report }, null, 2)}\n`);
process.exit(report.every((r) => !r.error && r.problems.length === 0) ? 0 : 1);
