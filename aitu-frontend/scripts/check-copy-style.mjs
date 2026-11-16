/**
 * **Copy this style** (implementation 06, Phase 3), walked in a headless Chromium on a temporary copy of a project (the
 * copy is deleted at the end). The passages are found by the backend (`GET .../llm/style`, free, no AI); every request
 * that would start the AI is caught in the browser and a stand-in answers it, so no request reaches the AI:
 * - with nothing selected the tab is off; with a stretch marked it opens after **A stretch**, with **Both, Right, Left**,
 *   the Model, and no level, no patterns, no chords, no Batches;
 * - the list: the reference, then each passage with a tick, its time, its frames and how similar it is, all ticked;
 *   the reference (named) and the passages are drawn on the sheet with the numbers of the list;
 * - a passage not ticked leaves the sheet and the cost; **Deselect all** turns the button off, **Select all** brings
 *   them back; the keyboard ticks a passage; another hand asks again, with its own ticks;
 * - no passage found, a stretch too long or too short, a list that cannot be read and **Try again**; a passage in
 *   another key; twelve passages; a narrow window;
 * - **Copy this style** sends the reference, the hand, the words and the passages ticked; the panel says the AI checks,
 *   then waits after batch 1 with the passages dropped and why, and the marks copied; an answer to the AI and **Go on**
 *   ask the backend; the history shows the run with its reference and its check;
 * - a run whose check drops every passage says so, and offers no Revert.
 *
 *     npm run check:copy-style
 */

import { mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { markStretch, waitForFrames, watchSheets } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    project: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-copy-style') },
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

const RUN = 'style0123456';
const EMPTY_RUN = 'style0000000';
/** The model of the stand-in run: the history does not show it, so no real model is named. */
const MODEL = 'stand-in-model';

const browser = useSession(await chromium.launch());
const made = [];
try {
  const copy = await (await fetch(`${api}/projects/${values.project}/duplicate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).json();
  made.push(copy.id);
  const part = copy.parts?.[0]?.uuid ?? copy.parts?.[0] ?? copy.id;

  // A stretch of the song with three passages or more, as the backend finds them.
  let found = null;
  for (let start = 200; start < 4000 && !found; start += 150) {
    const answer = await (await fetch(`${api}/sheet/${part}/llm/style?start=${start}&end=${start + 220}&hand=both`)).json();
    if (answer.passages.length >= 3) found = { start, end: start + 220 };
  }
  check('the song has a stretch with three passages or more', found !== null, JSON.stringify(found));
  if (!found) throw new Error('No stretch to work on.');

  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watchSheets(page);
  const problems = [];
  page.on('console', (m) => { if (m.type() === 'error' && !/status of (500|502)|net::ERR_ABORTED/.test(m.text())) problems.push(m.text()); });
  page.on('pageerror', (e) => problems.push(e.message));
  const shot = (name) => page.screenshot({ path: path.join(values.out, `${name}.png`) });

  // The list: the backend's, unless `standIn` answers instead.
  let standIn = null;
  const asked = [];
  await page.route(new RegExp(`/api/sheet/${part}/llm/style(\\?.*)?$`), async (route) => {
    const request = route.request();
    if (request.method() === 'POST') {
      sent.push({ url: request.url(), body: request.postDataJSON() });
      phase = 'running';
      return route.fulfill({ status: 202, json: { jobId: 'fake-job', status: 'queued' } });
    }
    asked.push(request.url());
    if (standIn === 'error') return route.fulfill({ status: 500, json: { detail: 'Stand-in.' } });
    if (standIn) return route.fulfill({ json: standIn });
    return route.continue();
  });

  // The run: a stand-in says it goes, then how it ends; its log is a stand-in too.
  let phase = 'idle';
  const sent = [];
  let windows = [];
  let ending = null;
  let release; let ended = new Promise((r) => { release = r; });
  await page.route(new RegExp(`/api/sheet/${part}(\\?.*)?$`), async (route) => {
    if (route.request().method() !== 'GET' || phase !== 'running') return route.continue();
    const res = await route.fetch(); const body = await res.json();
    body.llm = { ...body.llm, state: 'running', jobId: 'fake-job', canRun: false }; body.editable = false;
    body.segments = windows.map(([start, end], k) => ({ start, end, state: k === 0 ? 'working' : 'waiting' }));
    return route.fulfill({ response: res, json: body });
  });
  // The stream ends after each answer and the browser opens it again: the first says the AI checks, the next how it ends.
  let opened = 0;
  await page.route(/\/api\/matrix\/progress\/fake-job/, async (route) => {
    opened += 1;
    if (opened === 1) {
      return route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: 'retry: 200\nevent: sheet\ndata: {"phase":"style","total":3,"checking":true}\n\n' });
    }
    await ended;
    phase = 'done';
    await route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: `event: sheet\ndata: {"phase":"check","status":"ok","kept":2,"total":3}\n\nevent: done\ndata: ${JSON.stringify(ending)}\n\n` });
  });
  let logs = {};
  let listed = [];
  await page.route(new RegExp(`/api/sheet/${part}/llm/runs(/.*)?$`), async (route) => {
    const url = route.request().url();
    if (route.request().method() === 'POST') {
      sent.push({ url, body: route.request().postDataJSON?.() ?? null });
      return route.fulfill({ status: 202, json: { jobId: 'fake-job-2', status: 'queued' } });
    }
    const id = /\/llm\/runs\/([^/?]+)/.exec(url)?.[1];
    return route.fulfill({ json: id ? logs[id] : listed });
  });

  await page.goto(`${base}/projects/${part}/sheet`);
  await waitForFrames(page);
  const dialog = page.locator('[data-enhance-dialog]');
  const tabs = dialog.getByRole('group', { name: 'What the AI works on' });
  const status = () => dialog.locator('[data-enhance-status]').innerText();
  const confirm = page.getByTestId('style-confirm');
  const list = dialog.locator('[data-style-list]');
  const rows = list.locator('[data-style-passage]');
  const drawn = () => page.locator('[data-frames-sheet] [data-batch]').evaluateAll((els) => [...new Set(els.map((e) => Number(e.getAttribute('data-batch'))))].sort((a, b) => a - b).join(','));
  /** The list has its answer: the status says something else than the search. */
  const answered = () => page.waitForFunction(() => !/^Looking/.test(document.querySelector('[data-enhance-status]')?.textContent ?? 'Looking'), null, { timeout: 8000 });
  const hand = (name) => dialog.getByRole('group', { name: 'Which hand' }).getByRole('button', { name, exact: true }).click();

  await page.getByTestId('header-enhance-with-ai').click();
  await dialog.waitFor({ timeout: 5000 });
  check('tabs: A stretch, Copy this style, The whole song', (await tabs.getByRole('button').allInnerTexts()).join('|') === 'A stretch|Copy this style|The whole song');
  check('nothing selected: Copy this style is off', await tabs.getByRole('button', { name: 'Copy this style' }).isDisabled());
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await dialog.waitFor({ state: 'hidden' });

  // One note picked: the tab is open, in the hand of the note, and a single note is too short to be a reference.
  const drawnNow = await (await fetch(`${api}/sheet/${part}?width=148`)).json();
  const note = drawnNow.notes.find((one) => one.hand === 'left');
  const head = page.locator(`[data-frames-sheet] [data-note~="${note.ref}"]`).first();
  await head.scrollIntoViewIfNeeded();
  const noteBox = await head.boundingBox();
  await page.mouse.click(noteBox.x + noteBox.width / 2, noteBox.y + noteBox.height / 2);
  await page.locator('[data-frames-note-toolbox]').waitFor({ timeout: 5000 });
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog.waitFor({ timeout: 5000 });
  await tabs.getByRole('button', { name: 'Copy this style' }).click();
  await answered();
  check('one note picked: the hand of the note, too short', new URL(asked.at(-1)).searchParams.get('hand') === 'left' && (await status()) === 'Select a longer stretch.' && (await confirm.isDisabled()), await status());
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await dialog.waitFor({ state: 'hidden' });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  await markStretch(page, api, { from: 0.2, to: 0.5 });
  const fields = page.locator('[data-frames-range-toolbox]');
  await fields.locator('[data-range-from]').fill(String(found.start));
  await fields.locator('[data-range-to]').fill(String(found.end));
  await fields.locator('[data-range-to]').press('Enter');
  await page.waitForTimeout(500);
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog.waitFor({ timeout: 5000 });
  await tabs.getByRole('button', { name: 'Copy this style' }).click();
  await answered();

  const query = new URL(asked.at(-1)).searchParams;
  const reference = [Number(query.get('start')), Number(query.get('end'))];
  const backend = await (await fetch(asked.at(-1))).json();
  const n = backend.passages.length;
  check('the tab asks the backend for the passages of the selection', query.get('hand') === 'both' && n >= 3, `f${reference[0]}-f${reference[1]}, ${n} passages`);
  check('Both, Right, Left', (await dialog.getByRole('group', { name: 'Which hand' }).getByRole('button').allInnerTexts()).join('|') === 'Both|Right|Left');
  check('no level, no patterns, no chords, no Batches', (await dialog.locator('[data-level-controls], [data-pattern-gallery], [data-batches], [data-testid="level-chords"]').count()) === 0);
  check('the Model selector stays', (await dialog.getByTestId('ai-model').count()) === 1);
  check('the reference is the first row of the list', new RegExp(`f${reference[0]}-f${reference[1]}.*The reference`, 's').test(await list.locator('[data-style-reference]').innerText()));
  check('one row per passage, all ticked', (await rows.count()) === n && (await rows.locator('input:checked').count()) === n);
  const first = await rows.first().innerText();
  check('a row: its time, its frames, how similar', /\d\d:\d\d\.\d\d – \d\d:\d\d\.\d\d/.test(first) && /f\d+-f\d+/.test(first) && /Similar|Very similar/.test(first), first.replace(/\n/g, ' | '));
  await page.waitForTimeout(300);
  check('the sheet draws the reference, named', (await page.locator('[data-frames-sheet] [data-batch-reference]').count()) >= 1 && (await page.locator('[data-frames-sheet] [data-batch-reference] text').allTextContents()).join() === 'The reference');
  const every = Array.from({ length: n }, (_, k) => k + 1).join(',');
  check('and each passage with the number of its row', (await drawn()) === every, await drawn());
  const full = await status();
  check('the status line: the reference stays, the passages, the cost, the time, Undo', new RegExp(`^The reference stays as it is\\. ${n} passages\\. About \\$\\d+\\.\\d\\d, about \\d+ minutes?\\. Undo takes it back\\.$`).test(full), full);
  check('the button says Copy this style', (await confirm.innerText()).trim() === 'Copy this style' && (await confirm.isEnabled()));
  await page.waitForTimeout(400);
  await shot('01-list');

  await rows.nth(1).locator('input').click();
  await page.waitForTimeout(200);
  const others = Array.from({ length: n }, (_, k) => k + 1).filter((k) => k !== 2).join(',');
  check('a passage not ticked leaves the sheet, the others keep their numbers', (await drawn()) === others, await drawn());
  const cost = (text) => Number(/About \$(\d+\.\d\d)/.exec(text)?.[1]);
  check('and the status follows, from the backend\'s estimates', (await status()).includes(`${n - 1} passage`) && cost(await status()) === backend.costs[n - 1].usd, await status());
  await list.getByRole('button', { name: 'Deselect all' }).click();
  await page.waitForTimeout(200);
  check('Deselect all: nothing drawn but the reference, the button off', (await drawn()) === '' && (await page.locator('[data-batch-reference]').count()) >= 1 && (await confirm.isDisabled()) && (await status()) === 'Tick a passage first.', await status());
  await list.getByRole('button', { name: 'Select all', exact: true }).click();
  await page.waitForTimeout(200);
  check('Select all brings them back', (await rows.locator('input:checked').count()) === n && (await drawn()) === every);
  await rows.first().locator('input').focus();
  await page.keyboard.press('Space');
  check('the keyboard ticks a passage', (await rows.locator('input:checked').count()) === n - 1);
  await page.getByTestId('style-words').focus();
  let reached = false;
  for (let k = 0; k < 6 && !reached; k += 1) {
    await page.keyboard.press('Tab');
    reached = await confirm.evaluate((el) => el === document.activeElement);
  }
  check('Tab reaches the button from the words', reached);

  const before = asked.length;
  await hand('Right');
  await answered();
  await page.waitForTimeout(400);
  check('another hand asks again', asked.length > before && new URL(asked.at(-1)).searchParams.get('hand') === 'right');
  check('and starts with all ticked', (await rows.count()) > 0 && (await rows.locator('input:checked').count()) === (await rows.count()));
  check('with one hand the status says the other stays', /^The reference and the left hand stay as they are\./.test(await status()), await status());
  await shot('02-right-hand');

  // The states of the list, each from a stand-in: the hand asks again.
  const again = async (answer, name = 'Left') => { standIn = answer; await hand(name); await answered(); await page.waitForTimeout(150); };
  const nothing = { reference, hand: 'left', model: MODEL, passages: [], threshold: 0.6, max: 12, tooLong: false, tooShort: false, requests: 0, usd: 0, minutes: 0, costs: [{ requests: 0, usd: 0, minutes: 0 }] };
  await again(nothing);
  check('no passage found: it says so, the button is off', (await status()) === 'No passage of the song is like this one.' && (await confirm.isDisabled()) && (await rows.count()) === 0, await status());
  await shot('03-no-passage');
  await again({ ...nothing, tooLong: true, hand: 'right' }, 'Right');
  check('a stretch too long', (await status()) === 'Select a shorter stretch.' && (await confirm.isDisabled()), await status());
  await again({ ...nothing, tooShort: true }, 'Left');
  check('a stretch too short', (await status()) === 'Select a longer stretch.' && (await confirm.isDisabled()), await status());
  await again('error', 'Right');
  check('a list that cannot be read says so and offers Try again', (await status()) === 'The passages could not be read.' && (await page.getByTestId('style-again').isVisible()) && (await confirm.isDisabled()), await status());
  await shot('04-error');
  standIn = null;
  await page.getByTestId('style-again').click();
  await answered();
  check('Try again reads the list', (await rows.count()) > 0 && (await page.getByTestId('style-again').count()) === 0);

  const twelve = Array.from({ length: 12 }, (_, k) => ({ start: 10000 + k * 1000, end: 10400 + k * 1000, score: k % 2 ? 0.92 : 0.64, shift: [0, 2, -3, 1, -1, 6][k % 6] }));
  await again({ ...nothing, hand: 'left', passages: twelve, costs: Array.from({ length: 13 }, (_, k) => ({ requests: k ? k + 1 : 0, usd: k * 0.03, minutes: k })) });
  const texts = await rows.allInnerTexts();
  check('a passage in another key says it', /Similar$/.test(texts[0].trim()) && /Very similar, a tone higher/.test(texts[1]) && /Similar, 3 semitones lower/.test(texts[2]) && /a semitone higher/.test(texts[3]), texts.slice(0, 4).map((t) => t.split('\n').at(-1)).join(' / '));
  check('twelve passages fit the dialog: the list scrolls, the button stays', (await rows.count()) === 12 && (await confirm.isVisible()));
  const room = await list.evaluate((el) => el.scrollWidth <= el.clientWidth + 1);
  check('the longest row needs no scroll sideways', room);
  await shot('05-twelve');
  await page.setViewportSize({ width: 480, height: 800 });
  await page.waitForTimeout(400);
  check('narrow: no scroll sideways in the list', await list.evaluate((el) => el.scrollWidth <= el.clientWidth + 1));
  await shot('06-narrow');
  await page.setViewportSize({ width: 2200, height: 1100 });
  await page.waitForTimeout(400);
  await shot('07-wide');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(300);

  // ------------------------------------------------------------------ the run
  standIn = null;
  await hand('Both');
  await answered();
  await page.waitForTimeout(300);
  check('a hand comes back as the user left it', (await rows.locator('input:checked').count()) === n - 1 && !(await rows.first().locator('input').isChecked()));
  await list.getByRole('button', { name: 'Select all', exact: true }).click();
  const shown = (await (await fetch(asked.at(-1))).json()).passages;
  await rows.nth(1).locator('input').click();
  const ticked = shown.filter((_, k) => k !== 1);
  windows = ticked.map((one) => [one.start, one.end]);
  await page.getByTestId('style-words').fill('Keep the last note of each passage.');
  const talk = (k, [start, end]) => ({
    k, start, end, status: 'ok', target: 'F1 frames', declared: [], errors: [['P1: the melody lost f100 C5']],
    messages: [{ role: 'user', content: '# Copy this style...' }, { role: 'assistant', content: '```...```' }],
    explain: ['I wrote the octaves as thirds, as in the reference.'], rules: [],
    copied: { spelling: 3, finger: 2 }, copiedText: '3 spellings and 2 fingers copied',
  });
  const passage = (one, k, keep, why) => ({ k, start: one.start, end: one.end, score: one.score, shift: one.shift, columns: [], keep, why });
  const dropped = ticked[1];
  const kept = ticked.filter((one) => one !== dropped);
  logs[RUN] = {
    id: RUN, kind: 'style', created: '2026-11-04T11:00:00+00:00', state: 'waiting', usd: 0.04, requests: 2, system: '...',
    request: { hand: 'both', start: reference[0], end: reference[1], words: 'Keep the last note of each passage.', model: MODEL, prompt: '1', windows: kept.map((one) => [one.start, one.end]) },
    plan: { k: -1, start: reference[0], end: reference[1], status: 'ok', messages: [], errors: [], explain: [], rules: [], declared: [], target: '' },
    passages: ticked.map((one, k) => passage(one, k, one !== dropped, one === dropped ? 'the bridge: another melody' : 'the same melody')),
    rules: [], batches: [talk(0, windows[0])],
  };
  listed = [{ id: RUN, kind: 'style', reference, passages: logs[RUN].passages, log: true, created: logs[RUN].created, state: 'waiting', level: null, hand: 'both', patterns: [], strict: [], words: logs[RUN].request.words, model: MODEL, batches: [{ k: 0, start: windows[0][0], end: windows[0][1], status: 'ok' }], total: kept.length, usd: 0.04 }];
  ending = { type: 'done', style: 'ok', hand: 'both', batches: 1, total: kept.length, dropped: 1, usd: 0.04, before: 3, waiting: true, run: RUN };

  await confirm.click();
  const panel = page.locator('[data-ai-run-panel]');
  await panel.waitFor({ timeout: 8000 });
  await page.waitForFunction(() => /checking/.test(document.querySelector('[data-ai-run-panel] h6')?.textContent ?? ''), null, { timeout: 8000 });
  const body = sent.find((one) => /\/llm\/style$/.test(one.url))?.body;
  check('the button sends the reference, the hand, the words and the passages ticked',
    body?.start === reference[0] && body?.end === reference[1] && body?.hand === 'both' && body?.words === 'Keep the last note of each passage.' && JSON.stringify(body?.passages) === JSON.stringify(windows) && body?.model === undefined,
    JSON.stringify(body));
  check('the dialog closes, the panel says the AI checks the passages', (await dialog.count()) === 0 && (await panel.locator('h6').innerText()) === 'The AI is checking the passages');
  check('no passage is being written during the check', !/Being written/.test(await panel.locator('[data-ai-run-batches]').innerText()));
  await shot('08-checking');
  release();
  await page.waitForFunction(() => document.querySelector('[data-ai-run-panel]')?.getAttribute('data-ai-run-panel') === 'done', null, { timeout: 10000 });
  await panel.locator('[data-ai-run-explained] [data-ai-run]').waitFor({ timeout: 8000 });
  check('after the first passage the panel waits', (await panel.locator('h6').innerText()) === 'Check batch 1');
  check('and counts the batches kept, not the passages dropped', new RegExp(`^1 of ${kept.length} batches, \\$0\\.04$`).test((await panel.locator('p').first().innerText()).trim()), await panel.locator('p').first().innerText());
  const drop = panel.locator('[data-run-passage="dropped"]');
  check('a passage dropped by the check is shown, with the reason', (await drop.count()) === 1 && new RegExp(`f${dropped.start}-f${dropped.end}.*the bridge: another melody`, 's').test(await drop.innerText()), await drop.innerText());
  check('the panel lists only the dropped ones', (await panel.locator('[data-run-passage="kept"]').count()) === 0);
  check('the marks copied are said', (await panel.locator('[data-run-copied]').innerText()) === '3 spellings and 2 fingers copied from the reference.');
  check('Go on names what is left', new RegExp(kept.length === 2 ? 'Go on with the other batch' : `Go on with the other ${kept.length - 1} batches`).test(await page.getByTestId('run-continue').innerText()), await page.getByTestId('run-continue').innerText());
  await shot('09-waiting');
  await page.getByTestId('run-answer-1').fill('Leave the top note out.');
  await page.getByTestId('run-again-1').click();
  await page.waitForTimeout(400);
  check('an answer writes the passage again', sent.find((one) => /\/batches\/0\/again$/.test(one.url))?.body?.words === 'Leave the top note out.');
  await page.getByTestId('run-continue').click();
  await page.waitForTimeout(400);
  check('Go on asks the backend', sent.some((one) => one.url.endsWith(`/llm/runs/${RUN}/continue`)));

  await page.getByTestId('ai-run-history').click();
  const history = page.locator('[data-ai-history]');
  await history.locator('[data-ai-run]').waitFor({ timeout: 5000 });
  check('the history opens the run: Copy this style, both hands', /Copy this style, both hands/.test(await history.innerText()));
  check('with its reference', new RegExp(`The reference: .*f${reference[0]}-f${reference[1]}`, 's').test(await history.locator('[data-run-reference]').innerText()));
  check('and the check: kept, dropped, why', (await history.locator('[data-run-passage="kept"]').count()) === kept.length && /Kept: the same melody/.test(await history.locator('[data-run-check]').innerText()) && /Dropped: the bridge/.test(await history.locator('[data-run-check]').innerText()));
  await shot('10-history-run');
  await history.getByRole('button', { name: 'Back to the history' }).click();
  const row = history.locator(`[data-history-run="${RUN}"]`);
  await row.waitFor({ timeout: 5000 });
  const line = await row.innerText();
  check('the list says the kind, the batches and the passages dropped', /Copy this style, both hands/.test(line) && new RegExp(`1 of ${kept.length} batches\\s+· 1 dropped`).test(line), line.replace(/\n/g, ' | '));
  await shot('11-history-list');
  // Without a panel at the right the sheet is laid out once more for the whole width: a drag must wait for it.
  const laidOut = page.waitForResponse((answer) => new RegExp(`/api/sheet/${part}\\?.*width=`).test(answer.url()));
  await page.getByTestId('ai-history-close').click();
  await laidOut;
  await waitForFrames(page);

  // ------------------------------------------------------------------ a check that keeps no passage
  await markStretch(page, api, { from: 0.2, to: 0.5 });
  await fields.locator('[data-range-from]').fill(String(found.start));
  await fields.locator('[data-range-to]').fill(String(found.end));
  await fields.locator('[data-range-to]').press('Enter');
  await page.waitForTimeout(500);
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog.waitFor({ timeout: 5000 });
  await tabs.getByRole('button', { name: 'Copy this style' }).click();
  await answered();
  logs[EMPTY_RUN] = {
    ...logs[RUN], id: EMPTY_RUN, state: 'done', batches: [], usd: 0.01, requests: 1,
    request: { ...logs[RUN].request, windows: [] },
    passages: shown.map((one, k) => passage(one, k, false, 'another melody')),
  };
  ending = { type: 'done', style: 'dropped', hand: 'both', batches: 0, total: 0, dropped: shown.length, usd: 0.01, before: 4, run: EMPTY_RUN };
  windows = shown.map((one) => [one.start, one.end]);
  opened = 1;
  ended = new Promise((r) => { release = r; });
  await confirm.click();
  await panel.waitFor({ timeout: 8000 });
  await page.waitForTimeout(600);
  release();
  await page.waitForFunction(() => document.querySelector('[data-ai-run-panel]')?.getAttribute('data-ai-run-panel') === 'done', null, { timeout: 10000 });
  await panel.locator('[data-ai-run-explained] [data-ai-run]').waitFor({ timeout: 8000 });
  await page.waitForTimeout(300);
  check('when the check keeps no passage the run says so', (await panel.locator('[data-ai-run-notice]').innerText()) === 'The AI kept no passage. The sheet stays as it was.', await panel.locator('[data-ai-run-notice]').innerText());
  check('each one is shown with the reason', (await panel.locator('[data-run-passage="dropped"]').count()) === shown.length);
  check('and there is nothing to Revert', (await page.getByTestId('ai-run-revert').count()) === 0);
  await shot('12-all-dropped');
  await page.getByTestId('ai-run-close').click();
  check('no error on the page', problems.length === 0, problems.slice(0, 3).join(' | '));
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await browser.close();
}

console.log(failures.length ? `${failures.length} failed` : 'all passed');
process.exitCode = failures.length ? 1 : 0;
