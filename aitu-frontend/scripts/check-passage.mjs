/**
 * Recording in Sheet (implementation 02, Phase 9; on the new sheet since implementation 03, Phase 8B), walked in a
 * headless Chromium.
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), on
 * **temporary copies** only, deleted at the end with every passage open on them:
 *
 * 1. a stretch of a copy is marked and **Record this passage** opens its page: the Current drawn,
 *    no take yet;
 * 2. a take is recorded with Chromium's fake microphone, and another added from a file: the
 *    passage's own audio played twice as slowly (ffmpeg), as a reader playing along slowly would;
 * 3. **Write the proposal** reads the file take (the GPU job): the Proposal is drawn in the key of
 *    the Current;
 * 4. **Fit** finds the speed (×2) and the window; the window is dragged;
 * 5. **Promote → Fit to the window** with the recording: the song keeps its length, the sheet opens
 *    with the promotion as its last step; undo and redo give the part back exactly; every join of
 *    the audio plays its own file (`scripts/check_joins.py`);
 * 6. **Replace the whole passage** at ×1: the dialog says how much longer the song gets, and it does;
 * 7. a blank sheet's **Record a passage** puts a take in: the steps appear;
 * 8. **Discard this passage** leaves the song as it was; narrow and dark screenshots.
 *
 * With `--played` the takes from a file are sent with the keys of the stretch as played notes (the song's notes at
 * the take's speed), so **Write the proposal** reads them without the transcription model: the check runs while the
 * GPU is busy (the GPU job of step 3 is then not walked).
 *
 *     npm run check:passage
 *     npm run check:passage -- --song Elefants --out /tmp/passage [--played]
 */

import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { markStretch as markOnSheet, waitForFrames, watchSheets } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'passage') },
    base: { type: 'string', default: 'http://localhost:5173' },
    song: { type: 'string', default: 'Elefants' },
    played: { type: 'boolean', default: false },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });
const scratchDir = mkdtempSync(path.join(tmpdir(), 'aitu-check-passage-'));

const results = [];
const check = (label, ok, extra = '') => {
  results.push(`${ok ? '  ok  ' : '  FAIL'} ${label}${extra ? ` (${extra})` : ''}`);
};
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const send = (method, url, body) =>
  json(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

const made = new Set();
const passages = new Set();
const browser = await chromium.launch({
  args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
});
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
watchSheets(page);
// A MIDI piano for the page, played by the check (`window.__playMidi`): Web MIDI with one input.
await page.addInitScript(() => {
  const input = new EventTarget();
  Object.assign(input, { id: 'check-piano', name: 'Check piano', type: 'input', state: 'connected' });
  const access = { inputs: new Map([['check-piano', input]]), outputs: new Map(), onstatechange: null };
  navigator.requestMIDIAccess = async () => access;
  const send = (bytes) => {
    const event = new Event('midimessage');
    Object.defineProperty(event, 'data', { value: new Uint8Array(bytes) });
    Object.defineProperty(event, 'timeStamp', { value: performance.now() });
    input.dispatchEvent(event);
  };
  /** Play `[key, startMs, endMs]` notes, in real time from now; resolves when the last key is up. */
  window.__playMidi = (notes) =>
    new Promise((resolve) => {
      let last = 0;
      for (const [key, start, end] of notes) {
        setTimeout(() => send([0x90, key, 90]), start);
        setTimeout(() => send([0x80, key, 0]), end);
        last = Math.max(last, end);
      }
      setTimeout(resolve, last + 50);
    });
});
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
const audioRequests = [];
page.on('request', (r) => { if (/\/audio\/[0-9a-f-]+\/file/.test(r.url())) audioRequests.push(r.url()); });
const shot = async (name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const waitForSheet = async () => {
  await page.waitForSelector('[data-sheet-title]', { timeout: 90000 });
  await waitForFrames(page);
  await page.waitForTimeout(300);
};
/** The noteheads of the new sheet of the Current, or of the Proposal. */
const CURRENT_NOTE = '[data-passage-current] [data-frames-sheet] [data-note]';
const PROPOSAL_NOTE = '[data-passage-proposal] [data-frames-sheet] [data-note]';
const notesOf = async (id) => (await json(`${api}/pieces/${id}/notes`)).id.length;
const filesOf = async (id) => (await json(`${api}/audio/${id}/files`)).files;
const durationOf = async (id) => (await json(`${api}/audio/${id}`)).durationSeconds;
const statusOf = async (id) => json(`${api}/pieces/${id}/status`);
/** The new sheet of a part: its reference figure and its armadura. */
const readingOf = async (id) => {
  const sheet = await json(`${api}/sheet/${id}?width=130`);
  return { quarterMs: sheet.quarterMs, key: sheet.reading.key };
};
const undoButton = () => page.getByRole('button', { name: /^Undo/ }).first();
const redoButton = () => page.getByRole('button', { name: /^Redo/ }).first();
const becomes = async (read, wanted, label) => {
  for (let tries = 0; tries < 60; tries += 1) {
    if ((await read()) === wanted) return true;
    await page.waitForTimeout(500);
  }
  check(label, false, `${await read()}, wanted ${wanted}`);
  return false;
};
/** Mark a stretch of the first line of the song's sheet, from `from` to `to` of its columns: the range toolbox opens. */
const markStretch = async (from, to) => {
  await markOnSheet(page, api, { from, to });
  await page.locator('[data-frames-range-toolbox]').waitFor({ timeout: 10000 });
};
const joins = (ids) => {
  try {
    const answer = execFileSync(
      'docker',
      ['compose', 'exec', '-T', 'backend', 'python', 'scripts/check_joins.py', ...ids],
      { cwd: path.join(here, '..', '..'), encoding: 'utf8' },
    );
    return JSON.parse(answer);
  } catch (caught) {
    const text = caught.stdout ? String(caught.stdout) : '';
    try {
      return JSON.parse(text);
    } catch {
      return [{ ok: false, error: String(caught.message).slice(0, 200) }];
    }
  }
};
/** The passage's own audio, `atempo` times as fast: a take played along with it. */
const takeOf = async (part, fromMs, toMs, atempo, name) => {
  const whole = path.join(scratchDir, `${name}-song.audio`);
  writeFileSync(whole, Buffer.from(await (await fetch(`${api}/audio/${part}/file`)).arrayBuffer()));
  const take = path.join(scratchDir, `${name}.wav`);
  execFileSync('ffmpeg', [
    '-nostdin', '-v', 'error', '-y', '-ss', String(fromMs / 1000), '-t', String((toMs - fromMs) / 1000),
    '-i', whole, '-filter:a', `atempo=${atempo}`, '-ac', '1', take,
  ]);
  return take;
};
const passageId = () => /\/passages\/([0-9a-f-]+)$/.exec(page.url())?.[1] ?? null;
/** The song's notes of `[fromMs, toMs)` as keys played `atempo` times as fast (`--played`). */
const playedNotes = async (part, fromMs, toMs, atempo) => {
  const notes = await json(`${api}/pieces/${part}/notes`);
  return notes.onMs
    .map((on, i) => ({ on, len: notes.lenMs[i], key: notes.key[i] }))
    .filter((one) => one.on >= fromMs && one.on < toMs)
    .map((one) => {
      const start = (one.on - fromMs) / 1000 / atempo;
      const end = Math.min((toMs - fromMs) / 1000 / atempo, start + one.len / 1000 / atempo);
      return { midiNote: one.key + 21, start, end: Math.max(end, start + 0.05), velocity: 80 };
    });
};
/** **Add a take from a file**: the page's file field, the one its buttons open; with `--played`, through the API
 * with the keys of the stretch, and the page read again. */
const addFileTake = async (file, played = null) => {
  const before = (await json(`${api}/passages/${passageId()}`)).takes.length;
  if (values.played && played) {
    const form = new FormData();
    form.append('file', new Blob([readFileSync(file)], { type: 'audio/wav' }), path.basename(file));
    form.append('notes', JSON.stringify(played));
    const sent = await fetch(`${api}/passages/${passageId()}/takes`, { method: 'POST', body: form });
    if (!sent.ok) throw new Error(`POST take: ${sent.status} ${await sent.text()}`);
    await page.reload();
  } else {
    await page.locator('input[type=file]').setInputFiles(file);
  }
  await becomes(async () => (await json(`${api}/passages/${passageId()}`)).takes.length, before + 1, 'the take from a file is kept');
  await page.locator('[data-passage-range]').waitFor({ timeout: 60000 });
};
const writeProposal = async () => {
  await page.getByTestId('passage-write').click();
  await page.locator(PROPOSAL_NOTE).first().waitFor({ timeout: 240000 });
  await page.waitForTimeout(1200);
};

async function freshCopy(label, name) {
  const vault = await json(`${api}/projects`);
  const original = vault
    // The shortest title that names it: the song itself, not a playlist or a copy made of it.
    .filter((row) => row.step === 'sheet' && row.title.toUpperCase().includes(name.toUpperCase()) && !row.title.includes('(check-'))
    .sort((a, b) => a.title.length - b.title.length)[0];
  if (!original) throw new Error(`No project of the vault named ${name} has its piano sheet`);
  const copy = await send('POST', `${api}/projects/${original.id}/duplicate`, { title: `${original.title} (${label})` });
  made.add(copy.id);
  return { id: copy.id, title: copy.title };
}

try {
  const song = await freshCopy('check-passage', values.song);

  // 1. Record this passage.
  await page.goto(`${base}/projects/${song.id}/sheet`);
  await waitForSheet();
  await markStretch(0.3, 0.55);
  await page.getByTestId('range-record').hover();
  await shot('01-range-record');
  await page.getByTestId('range-record').click();
  await page.waitForURL(/\/passages\/[0-9a-f-]+$/, { timeout: 20000 });
  const first = passageId();
  passages.add(first);
  await page.locator(CURRENT_NOTE).first().waitFor({ timeout: 60000 });
  const opened = await json(`${api}/passages/${first}`);
  const lengthMs = opened.toMs - opened.fromMs;
  check('Record this passage opens the page of the stretch', opened.part === song.id && lengthMs > 0, `${opened.fromMs}–${opened.toMs} ms`);
  check('the Current holds the notes of the stretch', (await notesOf(opened.current)) > 0, `${await notesOf(opened.current)} notes`);
  check('no take yet: Record and Add a take from a file', (await page.getByTestId('passage-first-record').count()) === 1);
  check('the Proposal has no sheet and Promote waits for a take', await page.getByTestId('passage-promote').isDisabled());
  check('the passage is on no list', !(await json(`${api}/projects`)).some((row) => row.id === first));
  await shot('02-passage-new');

  // 2. A take with the fake microphone, then one from a file.
  await page.getByTestId('passage-first-record').click();
  await page.locator('[data-passage-recorder]').waitFor();
  await page.getByTestId('passage-start').click();
  await page.getByTestId('passage-stop').waitFor({ timeout: 10000 });
  await page.waitForTimeout(2500);
  await shot('03-recording');
  await page.getByTestId('passage-stop').click();
  await page.locator('[data-passage-range]').waitFor({ timeout: 60000 });
  const recorded = await json(`${api}/passages/${first}`);
  check('a take recorded in the browser is kept as Take 1', recorded.takes.length === 1 && recorded.takes[0].name === 'Take 1' && recorded.takes[0].seconds > 1.5, `${recorded.takes[0]?.seconds?.toFixed(2)} s`);
  await shot('04-take-range');
  const slow = await takeOf(song.id, opened.fromMs, opened.toMs, 0.5, 'slow');
  await addFileTake(slow, await playedNotes(song.id, opened.fromMs, opened.toMs, 0.5));
  const withFile = await json(`${api}/passages/${first}`);
  check('a take from a file is Take 2, the one on show', withFile.takes.length === 2 && withFile.take === withFile.takes[1].id && withFile.takes[1].name === 'Take 2');
  check('the left panel lists the Current and both takes, Take 2 chosen', (await page.locator('[data-passage-takes] [data-testid^="take-"]').count()) === 3 && (await page.getByTestId('take-take-2').getAttribute('data-selected')) === 'true');

  // 3. Write the proposal.
  await writeProposal();
  const read = await json(`${api}/passages/${first}`);
  const take = read.takes.find((one) => one.id === read.take);
  check('Write the proposal reads the take', take?.state === 'ready', take?.state);
  const currentSheet = await readingOf(opened.current);
  const takeSheet = await readingOf(take.id);
  check(
    'the Proposal is written in the armadura and figure of the Current',
    takeSheet.key === currentSheet.key && Math.abs(takeSheet.quarterMs - currentSheet.quarterMs) < 0.5,
    `${takeSheet.key} / ${currentSheet.key}, ${takeSheet.quarterMs} / ${currentSheet.quarterMs} ms`,
  );
  check('the Proposal’s hands are all given', (await statusOf(take.id)).steps.find((one) => one.step === 'sheet')?.state === 'ready');
  await shot('05-proposal');

  // 4. Fit, and the window.
  await page.getByTestId('passage-fit').click();
  await page.waitForTimeout(800);
  const fitted = await json(`${api}/passages/${first}`);
  check('Fit finds the speed the take fills the window at (played twice as slowly: ×2)', Math.abs(fitted.speed - 2) < 0.1, `×${fitted.speed}`);
  check('the speed is shown', ((await page.getByTestId('passage-speed').textContent()) ?? '').startsWith('×'), await page.getByTestId('passage-speed').textContent());
  const windowBox = page.locator('[data-passage-proposal] [data-frame-window]');
  check('the window lies over the take, from its start', (await windowBox.getAttribute('data-start')) === '0', `${await windowBox.getAttribute('data-start')}–${await windowBox.getAttribute('data-end')}`);
  const fittedTake = await readingOf(fitted.take);
  check(
    'at the take’s speed the take reads with the song’s figure as much longer',
    Math.abs(fittedTake.quarterMs - fitted.speed * currentSheet.quarterMs) < 1,
    `${fittedTake.quarterMs} ms at ×${fitted.speed}`,
  );
  await shot('06-window');
  // At ×1 the window is half the take, and can be moved over it.
  await send('PATCH', `${api}/passages/${first}`, { speed: 1, windowMs: 0 });
  await page.reload();
  await page.locator(PROPOSAL_NOTE).first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(1200);
  const grip = page.locator('[data-passage-proposal] [data-frame-window-grip]').first();
  await grip.scrollIntoViewIfNeeded();
  const gripBox = await grip.boundingBox();
  await page.mouse.move(gripBox.x + gripBox.width / 2, gripBox.y + gripBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(gripBox.x + gripBox.width / 2 + 120, gripBox.y + gripBox.height / 2, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(800);
  const dragged = await json(`${api}/passages/${first}`);
  check('the window moves with its grip, and stays where it is let go', dragged.windowMs > 0, `${dragged.windowMs} ms`);
  await page.getByTestId('passage-fit').click();
  await page.waitForTimeout(800);
  // The Proposal's toolbox offers what a take can change.
  await page.getByRole('button', { name: 'Sheet toolbox' }).click();
  const tabs = await page.locator('[data-sheet-toolbox] [role=tab], [data-sheet-toolbox] button[role=radio], [data-sheet-toolbox] [aria-label="Sheet toolbox tab"] button').allTextContents();
  check('the Proposal’s sheet toolbox: Key, Transpose, View', tabs.join(',') === 'Key,Transpose,View', tabs.join(','));
  await shot('07-proposal-toolbox');
  await page.getByRole('button', { name: 'Sheet toolbox' }).click();

  // 5. Promote: fit to the window, with the recording.
  const notesBefore = await notesOf(song.id);
  const idsBefore = JSON.stringify((await json(`${api}/pieces/${song.id}/notes`)).id);
  const filesBefore = await filesOf(song.id);
  const durationBefore = await durationOf(song.id);
  await page.getByTestId('passage-promote').click();
  await page.getByTestId('promote-window').click();
  await page.getByRole('button', { name: 'Use my recording' }).click();
  await page.waitForTimeout(800);
  check('fitting into the window says nothing of the length', (await page.getByTestId('promotion-length').count()) === 0);
  await shot('08-promote-window');
  await page.getByTestId('promotion-confirm').click();
  await page.waitForURL(new RegExp(`/projects/${song.id}/sheet$`), { timeout: 60000 });
  await waitForSheet();
  await page.waitForTimeout(800);
  const notesAfter = await notesOf(song.id);
  // One audio frame (10 ms) of slack: a part of one file says the file's own length, a part of
  // several files its length in whole frames (Phase 11: 233.348 s became 233.35 s, the same audio).
  const durationAfter = await durationOf(song.id);
  check('the song keeps its length', Math.abs(durationAfter - durationBefore) <= 0.0101, `${durationBefore} s → ${durationAfter} s`);
  // New ids: the take's notes, in place of the passage's (as many with `--played`, which plays the passage's keys).
  const idsAfter = JSON.stringify((await json(`${api}/pieces/${song.id}/notes`)).id);
  check('the take’s notes are in the song', idsAfter !== idsBefore, `${notesBefore} → ${notesAfter} notes`);
  const filesAfter = await filesOf(song.id);
  check('the take is a file of the song’s audio, between the two halves', filesAfter.length === filesBefore.length + 2 && filesAfter.some((file) => file.kind === 'recording'), filesAfter.map((file) => file.name).join(' | '));
  check('the passage is closed', (await fetch(`${api}/passages/${first}`)).status === 404);
  passages.delete(first);
  check('the promotion is the sheet’s last step', (await undoButton().getAttribute('aria-label')) === 'Undo: Promote the passage', await undoButton().getAttribute('aria-label'));
  const before = audioRequests.filter((url) => url.includes(song.id));
  check('the player asks for the new audio at a new address', new Set(before).size > 1, [...new Set(before)].map((url) => url.split('?')[1]).join(' '));
  await shot('09-promoted');
  for (const report of joins([song.id])) {
    check('every join of the promoted song plays its own file', report.ok === true, `${report.joins} joins, ${report.seconds} s`);
  }
  await undoButton().click();
  await becomes(() => notesOf(song.id), notesBefore, 'undo gives the notes back');
  check('undo gives the files back', JSON.stringify(await filesOf(song.id)) === JSON.stringify(filesBefore));
  await waitForSheet();
  await redoButton().click();
  await becomes(() => notesOf(song.id), notesAfter, 'redo promotes again');
  check('redo gives the take’s files back', JSON.stringify(await filesOf(song.id)) === JSON.stringify(filesAfter));
  await waitForSheet();

  // 6. Replace the whole passage at ×1: the song gets longer.
  await markStretch(0.65, 0.8);
  await page.getByTestId('range-record').click();
  await page.waitForURL(/\/passages\/[0-9a-f-]+$/, { timeout: 20000 });
  const second = passageId();
  passages.add(second);
  const secondOpened = await json(`${api}/passages/${second}`);
  await page.locator(CURRENT_NOTE).first().waitFor({ timeout: 60000 });
  await addFileTake(
    await takeOf(song.id, secondOpened.fromMs, secondOpened.toMs, 0.5, 'slow-2'),
    await playedNotes(song.id, secondOpened.fromMs, secondOpened.toMs, 0.5),
  );
  await writeProposal();
  const longer = await durationOf(song.id);
  await page.getByTestId('passage-promote').click();
  await page.getByTestId('promote-whole').click();
  await page.getByTestId('promotion-length').waitFor({ timeout: 20000 });
  const said = await page.getByTestId('promotion-length').textContent();
  check('Replace the whole passage says how much longer the song gets', /^The song gets \d+\.\d s longer\.$/.test(said ?? ''), said);
  await shot('10-promote-whole');
  await page.getByTestId('promotion-confirm').click();
  await page.waitForURL(new RegExp(`/projects/${song.id}/sheet$`), { timeout: 60000 });
  await waitForSheet();
  passages.delete(second);
  const grown = (await durationOf(song.id)) - longer;
  const promised = Number(/(\d+\.\d)/.exec(said ?? '')?.[1] ?? 'NaN');
  check('the song is as much longer as the dialog said', Math.abs(grown - promised) < 0.1, `${grown.toFixed(2)} s`);
  await shot('11-promoted-whole');

  // 7. A blank sheet.
  const blank = await send('POST', `${api}/projects`, { scratch: true });
  made.add(blank.id);
  await page.goto(`${base}/projects/${blank.id}/sheet`);
  await page.getByTestId('empty-record').click();
  await page.waitForURL(/\/passages\/[0-9a-f-]+$/, { timeout: 20000 });
  passages.add(passageId());
  check('a blank sheet opens a new passage, with no Current', (await page.locator('[data-passage-current]').count()) === 0);
  // Played on a MIDI piano, with no sound: the keys are the notes.
  await page.getByTestId('passage-first-record').click();
  await page.locator('[data-passage-recorder]').waitFor();
  await page.getByRole('button', { name: 'MIDI piano' }).click();
  await page.getByLabel('Sound').click();
  await page.getByRole('option', { name: 'No sound' }).click();
  await page.getByTestId('passage-start').click();
  await page.getByTestId('passage-stop').waitFor({ timeout: 10000 });
  await page.evaluate(() => window.__playMidi([[60, 200, 600], [64, 700, 1100], [67, 1200, 1900]]));
  check('the keys played are counted while recording', (await page.getByTestId('passage-keys').textContent()) === '3 keys', await page.getByTestId('passage-keys').textContent());
  await shot('12a-midi');
  await page.getByTestId('passage-stop').click();
  await page.locator('[data-passage-range]').waitFor({ timeout: 60000 });
  const midiTake = (await json(`${api}/passages/${passageId()}`)).takes[0];
  check('a take played on a MIDI piano with no sound is kept, silent, as long as its keys', midiTake.midi === true && midiTake.seconds > 2 && midiTake.seconds < 4, `${midiTake.seconds} s`);
  await writeProposal();
  const midiNotes = (await json(`${api}/pieces/${midiTake.id}/notes`)).id.length;
  const midiPitches = (await json(`${api}/matrix/${midiTake.id}/events`)).events?.map((one) => one.midiNote ?? one.midi_note) ?? [];
  check('Write the proposal keeps the keys played, not a transcription', midiNotes === 3, `${midiNotes} notes ${JSON.stringify(midiPitches)}`);
  await shot('12-new-passage');
  await page.getByTestId('passage-promote').click();
  await page.getByTestId('promotion-confirm').click();
  await page.waitForURL(new RegExp(`/projects/${blank.id}/sheet$`), { timeout: 60000 });
  await waitForSheet();
  passages.clear();
  const blankStatus = await statusOf(blank.id);
  check('with the take put in, the steps appear', !blankStatus.scratch && blankStatus.steps.every((one) => one.state === 'ready'), blankStatus.steps.map((one) => `${one.step} ${one.state}`).join(', '));

  // 8. Discard; narrow; dark.
  const notesNow = await notesOf(song.id);
  await page.goto(`${base}/projects/${song.id}/sheet`);
  await waitForSheet();
  await markStretch(0.1, 0.2);
  await page.getByTestId('range-record').click();
  await page.waitForURL(/\/passages\/[0-9a-f-]+$/, { timeout: 20000 });
  const third = passageId();
  passages.add(third);
  await page.locator(CURRENT_NOTE).first().waitFor({ timeout: 60000 });
  // A MIDI piano with the (fake) microphone: the keys are the notes, the microphone the sound.
  await page.getByTestId('passage-first-record').click();
  await page.locator('[data-passage-recorder]').waitFor();
  await page.getByRole('button', { name: 'MIDI piano' }).click();
  await page.getByLabel('Sound').click();
  await page.getByRole('option', { name: "The computer's default" }).click();
  await page.getByTestId('passage-start').click();
  await page.getByTestId('passage-stop').waitFor({ timeout: 10000 });
  await page.evaluate(() => window.__playMidi([[62, 300, 900], [65, 1000, 1500]]));
  await page.getByTestId('passage-stop').click();
  await page.locator('[data-passage-range]').waitFor({ timeout: 60000 });
  const withSoundTake = (await json(`${api}/passages/${third}`)).takes[0];
  const level = await page.evaluate(async (url) => {
    const audio = new Audio(url);
    await new Promise((resolve, reject) => { audio.addEventListener('loadedmetadata', resolve, { once: true }); audio.addEventListener('error', reject, { once: true }); });
    return audio.duration;
  }, `${api}/audio/${withSoundTake.id}/file?original=true`);
  check('a take played on a MIDI piano with a microphone keeps both: its keys and its sound', withSoundTake.midi === true && level > 1, `${level.toFixed(2)} s of sound`);
  await shot('12b-takes-panel');
  // The bin of a take, on the left.
  await page.getByTestId('take-take-1').getByRole('button', { name: 'Delete Take 1' }).click();
  await page.getByRole('button', { name: 'Delete the take' }).click();
  await becomes(async () => (await json(`${api}/passages/${third}`)).takes.length, 0, 'the bin deletes the take');
  check('the bin of a take deletes it, after a confirmation', (await json(`${api}/passages/${third}`)).takes.length === 0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(800);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check('390 px: no sideways scroll on the page of a passage', overflow <= 0, `${overflow} px`);
  await shot('13-passage-390');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.reload();
  await page.getByTestId('take-current').getByRole('button').first().click();
  await page.locator(CURRENT_NOTE).first().waitFor({ timeout: 60000 });
  await shot('14-passage-dark');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
  await page.emulateMedia({ colorScheme: 'light' });
  await page.getByRole('button', { name: 'Passage actions' }).click();
  await page.getByRole('menuitem', { name: 'Discard this passage' }).click();
  await page.getByRole('button', { name: 'Discard the passage' }).click();
  await page.waitForURL(new RegExp(`/projects/${song.id}/sheet$`), { timeout: 20000 });
  check('Discard closes the passage and leaves the song as it was', (await fetch(`${api}/passages/${third}`)).status === 404 && (await notesOf(song.id)) === notesNow);
  passages.delete(third);
} finally {
  // The page first: open, it would ask for a project being deleted.
  await browser.close();
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const left = (await json(`${api}/projects`)).filter((row) => /check-passage/.test(row.title) || made.has(row.id)).length;
  let open = 0;
  for (const id of passages) if ((await fetch(`${api}/passages/${id}`)).status !== 404) open += 1;
  check('nothing the check made is left, passages included', left === 0 && open === 0, `${left} projects, ${open} passages`);
}

// A sheet with no saved reading answers 404 for it, which the page reads as "nothing saved".
const unexpected = problems.filter(
  (line) =>
    !/401 .*\/auth\/me/.test(line) &&
    !/404 .*\/passages\/[0-9a-f-]+$/.test(line) &&
    !/Failed to load resource: .* 404/.test(line),
);
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
