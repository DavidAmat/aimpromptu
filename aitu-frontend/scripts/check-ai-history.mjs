/**
 * The first batch first and the history of AI runs (implementation 04-5, the user, 2026-10-31), walked in a headless
 * Chromium on a temporary copy of a project (deleted at the end). No AI is asked: the browser is told a level run is
 * going, its end says it waits after batch 1, the run's log is a stand-in, and the requests that would start the AI
 * are caught and recorded:
 * - at the end, the panel of the run says "Check batch 1" and shows the AI's explanation, its rules and the check's
 *   refusals; an answer to the AI sends `POST .../llm/runs/{id}/batches/0/again` with the words; **Go on with the
 *   other 3 batches** sends `POST .../llm/runs/{id}/continue`;
 * - **History** opens the history of AI runs: the runs latest first; a run opens with its batches; a run made before
 *   the history shows its plan; the back arrow returns to the list; **Close** hides it.
 *
 *     npm run check:ai-history
 */

import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { waitForFrames } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    project: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const failures = [];
const check = (what, ok, detail = '') => {
  console.log(`${ok ? 'ok  ' : 'FAIL'}  ${what}${detail ? `  (${detail})` : ''}`);
  if (!ok) failures.push(what);
};

const RUN = 'abcdef123456';
/** The model of the stand-in run: the history does not show it, so no real model is named (implementation 04-6). */
const MODEL = 'stand-in-model';
const windows = [[5, 600], [600, 1200], [1200, 1700], [1700, 2216]];
const talk = {
  k: 0, start: 5, end: 600, status: 'ok', target: 'F1 frames', declared: ['pattern L f5-f600: left easy 1'],
  messages: [{ role: 'user', content: '# Level easy...' }, { role: 'assistant', content: '```...```' }],
  errors: [['L: the hand covers 26 semitones inside two negras (at most 24 at this level)']],
  explain: ['The left hand plays the root, then the triad, on every chord.', 'I kept the right hand as it is.'],
  rules: ['A chord of one negra plays its root only.'],
};
const log = {
  id: RUN, created: '2026-10-31T11:00:00+00:00', state: 'waiting', usd: 0.03, requests: 3, system: '...',
  request: { level: 'easy', hand: 'left', patterns: ['left easy 1'], strict: ['left easy 1'], words: 'Fa2, then the triad.', model: MODEL, windows },
  plan: { k: -1, start: 5, end: 2216, status: 'ok', messages: [], errors: [], explain: [], rules: [], declared: [], target: '' },
  rules: [
    { text: 'On each chord, the root in octave 2 as a blanca, then the triad as a blanca.', source: 'plan', ref: 'left easy 1' },
    { text: 'A chord of one negra plays its root only.', source: 'batch 1', ref: null },
  ],
  batches: [talk],
};
const listed = [
  { id: RUN, log: true, created: log.created, state: 'waiting', level: 'easy', hand: 'left', patterns: ['left easy 1'], strict: ['left easy 1'], words: log.request.words, model: MODEL, batches: [{ k: 0, start: 5, end: 600, status: 'ok' }], total: 4, usd: 0.03 },
  { id: 'record-0', log: false, created: '2026-10-30T20:46:57+00:00', state: 'done', level: 'easy', hand: 'left', patterns: ['left easy 5'], strict: [], words: '', model: null, batches: [{ k: 0, start: 5, end: 628, status: 'ok' }], total: 1, usd: 0.1, plan: ['S1 f5-f612 L=left easy 5 | Low note and rocking corcheas'], declared: ['pattern L f5-f35: keep'] },
];

const browser = useSession(await chromium.launch());
const made = [];
try {
  const copy = await (await fetch(`${api}/projects/${values.project}/duplicate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).json();
  made.push(copy.id);
  const part = copy.parts?.[0]?.uuid ?? copy.parts?.[0] ?? copy.id;
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  let phase = 'running';
  const sent = [];
  let release; const ended = new Promise((r) => { release = r; });
  await page.route(new RegExp(`/api/sheet/${part}(\\?.*)?$`), async (route) => {
    if (route.request().method() !== 'GET' || phase !== 'running') return route.continue();
    const res = await route.fetch(); const body = await res.json();
    body.llm = { ...body.llm, state: 'running', jobId: 'fake-job', canRun: false }; body.editable = false;
    body.segments = windows.map(([start, end], k) => ({ start, end, state: k === 0 ? 'working' : 'waiting', staff: 2 }));
    return route.fulfill({ response: res, json: body });
  });
  await page.route(/\/api\/matrix\/progress\/fake-job/, async (route) => {
    await ended;
    phase = 'done';
    await route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: `event: done\ndata: {"type":"done","level":"ok","batches":1,"total":4,"usd":0.03,"before":3,"waiting":true,"run":"${RUN}"}\n\n` });
  });
  await page.route(new RegExp(`/api/sheet/${part}/llm/runs(/.*)?$`), async (route) => {
    const url = route.request().url();
    if (route.request().method() === 'POST') {
      sent.push({ url, body: route.request().postDataJSON?.() ?? null });
      return route.fulfill({ status: 202, json: { jobId: 'fake-job-2', status: 'queued' } });
    }
    if (url.endsWith(`/llm/runs/${RUN}`)) return route.fulfill({ json: log });
    return route.fulfill({ json: listed });
  });
  await page.goto(`${base}/projects/${part}/sheet`);
  await waitForFrames(page);
  const panel = page.locator('[data-ai-run-panel]');
  await panel.waitFor({ timeout: 8000 });
  release();
  await page.waitForFunction(() => document.querySelector('[data-ai-run-panel]')?.getAttribute('data-ai-run-panel') === 'done', null, { timeout: 8000 });
  await panel.locator('[data-ai-run-explained] [data-ai-run]').waitFor({ timeout: 8000 });
  check('at the end the panel says to check batch 1', (await panel.locator('h6').innerText()) === 'Check batch 1');
  check('it shows the AI explanation of batch 1', /root, then the triad, on every chord/.test(await panel.locator('[data-run-explain]').first().innerText()));
  check('and the rules the AI follows', /root in octave 2 as a blanca/.test(await panel.locator('[data-run-rules]').innerText()));
  check('and the check refusals', /refused 1 answer/.test(await panel.locator('[data-run-refused]').innerText()));
  await page.screenshot({ path: '../.run/screenshots/ai-history-01-waiting.png' });
  check('Write this batch again waits for an answer', await page.getByTestId('run-again-1').isDisabled());
  await page.getByTestId('run-answer-1').fill('Play the triad as negras when the chord lasts two negras.');
  await page.getByTestId('run-again-1').click();
  await page.waitForTimeout(500);
  const again = sent.find((s) => /\/batches\/0\/again$/.test(s.url));
  check('an answer to the AI writes batch 1 again with the words', again?.body?.words === 'Play the triad as negras when the chord lasts two negras.', JSON.stringify(again?.body));
  await page.getByTestId('run-continue').click();
  await page.waitForTimeout(500);
  check('Go on with the other 3 batches asks the backend', sent.some((s) => s.url.endsWith(`/llm/runs/${RUN}/continue`)));

  await page.getByTestId('ai-run-history').click();
  const history = page.locator('[data-ai-history]');
  await history.waitFor({ timeout: 5000 });
  await history.locator('[data-ai-run]').waitFor({ timeout: 5000 });
  check('History opens on the run just made', (await history.locator('[data-ai-run]').getAttribute('data-ai-run')) === RUN && /easy 1 \(Strict\)/.test(await history.innerText()));
  await history.getByRole('button', { name: 'Back to the history' }).click();
  await history.locator('[data-history-run]').first().waitFor({ timeout: 5000 });
  const rows = await history.locator('[data-history-run]').evaluateAll((els) => els.map((e) => e.getAttribute('data-history-run')));
  check('the history lists the runs, the latest first', rows.join(',') === `${RUN},record-0`, rows.join(','));
  await page.screenshot({ path: '../.run/screenshots/ai-history-02-list.png' });
  await history.locator('[data-history-run="record-0"]').click();
  check('a run made before the history shows its plan', /made before the history/.test(await history.locator('[data-ai-run-old]').innerText()) && /S1 f5-f612/.test(await history.innerText()));
  await page.getByTestId('ai-history-close').click();
  await page.waitForTimeout(300);
  check('Close hides the history', (await history.count()) === 0);
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await browser.close();
}

console.log(failures.length ? `${failures.length} failed` : 'all passed');
process.exitCode = failures.length ? 1 : 0;
