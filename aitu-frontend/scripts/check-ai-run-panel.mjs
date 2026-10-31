/**
 * The panel of an AI run (the user, 2026-10-30), walked in a headless Chromium on a temporary copy of a project (the
 * copy is deleted at the end). No AI is asked: the browser is told a run is going (the sheet answers `running` with
 * four batches), the job's end message is sent by the script, and Stop and Revert are caught and recorded:
 * - the panel opens by itself on a running run, at the right; it lists each batch with its number, time and state,
 *   and the sheet draws the same numbered batches;
 * - **Stop** sends `POST /sheet/{uuid}/llm/stop` and says it stops after this batch;
 * - at the end it says Stopped, the batches never reached are Not written, and **Revert** sends the snapshot of the
 *   run's summary (`before`), then is greyed; **Close** hides the panel.
 *
 *     npm run check:ai-run-panel
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
    body.segments = [[5, 600, 'llm'], [600, 1200, 'algorithm'], [1200, 1700, 'working'], [1700, 2216, 'waiting']].map(([start, end, state]) => ({ start, end, state, staff: 2 }));
    return route.fulfill({ response: res, json: body });
  });
  await page.route(/\/api\/matrix\/progress\/fake-job/, async (route) => {
    await ended;
    phase = 'done';
    await route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: 'event: done\ndata: {"type":"done","level":"ok","batches":2,"total":4,"usd":0.05,"before":3,"stopped":true}\n\n' });
  });
  await page.route(new RegExp(`/api/sheet/${part}/llm/(stop|revert)`), async (route) => {
    sent.push({ url: route.request().url(), body: route.request().postDataJSON?.() ?? null });
    if (/stop/.test(route.request().url())) return route.fulfill({ status: 202, json: { stopping: true } });
    const sheet = await (await fetch(`${api}/sheet/${part}?width=148`)).json();
    return route.fulfill({ json: { ...sheet, walked: 'Revert the AI run' } });
  });
  await page.goto(`${base}/projects/${part}/sheet`);
  await waitForFrames(page);
  const panel = page.locator('[data-ai-run-panel]');
  await panel.waitFor({ timeout: 8000 });
  await page.waitForTimeout(800);
  check('the panel opens by itself on a running run', (await panel.getAttribute('data-ai-run-panel')) === 'running');
  const states = async () => (await panel.locator('[data-ai-run-batch]').allInnerTexts()).map((t) => t.split('\n').at(-1).trim());
  check('each batch with its state', (await states()).join(',') === 'Written,Kept as it was,Being written,Waiting', (await states()).join(','));
  check('the sheet draws the same batches', (await page.locator('[data-frames-sheet] [data-batch]').evaluateAll((els) => [...new Set(els.map((e) => e.getAttribute('data-batch')))].join(','))) === '1,2,3,4');
  await page.getByTestId('ai-run-stop').click();
  await page.waitForTimeout(300);
  check('Stop asks the backend and says it stops after this batch', sent.some((s) => /\/llm\/stop$/.test(s.url)) && /Stopping/.test(await panel.locator('h6').innerText()));
  release();
  await page.waitForFunction(() => document.querySelector('[data-ai-run-panel]')?.getAttribute('data-ai-run-panel') === 'done', null, { timeout: 8000 });
  await page.waitForTimeout(600);
  check('the end says Stopped and what stays', (await panel.locator('h6').innerText()) === 'Stopped' && /after 2 of 4 batches/.test(await panel.locator('[data-ai-run-notice]').innerText()));
  check('the batches never reached are Not written', (await states()).join(',') === 'Written,Kept as it was,Not written,Not written', (await states()).join(','));
  await page.getByTestId('ai-run-revert').click();
  await page.waitForTimeout(800);
  check('Revert sends the snapshot of the run and is then greyed', sent.at(-1)?.body?.version === 3 && (await page.getByTestId('ai-run-revert').isDisabled()) && /Reverted/.test(await panel.locator('[data-ai-run-notice]').innerText()));
  await page.getByTestId('ai-run-close').click();
  await page.waitForTimeout(300);
  check('Close hides the panel', (await panel.count()) === 0);
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await browser.close();
}

console.log(failures.length ? `${failures.length} failed` : 'all passed');
process.exitCode = failures.length ? 1 : 0;
