/**
 * Give every version of My library its hands and its piano sheet, through the real pages
 * (implementation 02, Phase 12, the user's rule of 2026-10-16: a version of the library always
 * has its piano sheet).
 *
 * The 30 songs the Phase 3 migration filed had notes but no hands and no sheet. For each version
 * whose Sheet step is not ready, as the user would do it:
 *
 * 1. **Edit**: a copy in Projects (`POST /projects/{id}/edit`; the one already open, if any);
 * 2. the Hands step: **Predict hands**, then **Save**;
 * 3. the Sheet step: drawn on arrival from the defaults, then **Save**;
 * 4. **Save to library → Replace the version** (`POST /projects/{copy}/library` with `replace`):
 *    the version gets the copy's content, its earlier state goes to its history, the copy goes.
 *
 * It writes into the real library, on purpose: run it only when that is what is wanted, after
 * `make db-backup`. One line per step, with its time; a screenshot of each sheet; a summary in
 * `.run/sheet-library.json`.
 *
 *     node scripts/sheet-library.mjs [--only <title>] [--list]
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'sheet-library') },
    base: { type: 'string', default: 'http://localhost:5173' },
    only: { type: 'string', default: '' },
    list: { type: 'boolean', default: false },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });

const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
const stepState = async (part, step) =>
  (await json(`${api}/pieces/${part}/status`)).steps.find((one) => one.step === step);
const waitFor = async (what, test, seconds) => {
  const until = Date.now() + seconds * 1000;
  for (;;) {
    if (await test()) return;
    if (Date.now() > until) throw new Error(`${what}: not after ${seconds} s`);
    await new Promise((done) => setTimeout(done, 500));
  }
};
const log = (line) => console.log(`${new Date().toISOString().slice(11, 19)} ${line}`);

// ---------------------------------------------------------------------- what to do

const todo = [];
for (const row of await json(`${api}/library/songs`)) {
  const song = await json(`${api}/library/songs/${row.id}`);
  for (const version of song.versions) {
    if (values.only && !song.title.toLowerCase().includes(values.only.toLowerCase())) continue;
    const states = await Promise.all(version.parts.map((part) => stepState(part, 'sheet')));
    if (states.every((state) => state.state === 'ready')) continue;
    todo.push({ song: song.title, version: version.name, project: version.projectId, parts: version.parts, editCopy: version.editCopy });
  }
}
log(`${todo.length} versions without a ready piano sheet`);
for (const one of todo) log(`  ${one.song} (${one.version})${one.parts.length > 1 ? `, ${one.parts.length} parts` : ''}${one.editCopy ? ', an edit copy is open' : ''}`);
if (values.list || todo.length === 0) process.exit(0);

// ---------------------------------------------------------------------- the pages

const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));

const summary = [];
for (const [index, one] of todo.entries()) {
  const label = `[${index + 1}/${todo.length}] ${one.song} (${one.version})`;
  const started = Date.now();
  const times = {};
  const time = async (name, work) => {
    const at = Date.now();
    const result = await work();
    times[name] = Math.round((Date.now() - at) / 100) / 10;
    return result;
  };
  try {
    const copy = await time('edit', () => post(`${api}/projects/${one.project}/edit`));
    const parts = (await json(`${api}/projects/${copy.id}/parts`)).parts.map((part) => part.id);
    if (parts.length !== 1) throw new Error(`${parts.length} parts: this script does one part`);
    const part = parts[0];
    log(`${label}: copy ${copy.id}`);

    await time('hands', async () => {
      await page.goto(`${base}/projects/${copy.id}/hands`);
      const predict = page.getByRole('button', { name: 'Predict hands', exact: true });
      await predict.waitFor({ timeout: 120000 });
      await page.waitForTimeout(400);
      await predict.click();
      const said = (await page.locator('[data-predicted]').textContent({ timeout: 300000 })) ?? '';
      await page.getByRole('button', { name: 'Save', exact: true }).first().click();
      await page.waitForFunction(
        () => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '',
        null,
        { timeout: 120000 },
      );
      await waitFor('the Hands step ready', async () => (await stepState(part, 'hands')).state === 'ready', 60);
      log(`${label}: hands saved (${said.trim()})`);
    });

    await time('sheet', async () => {
      await page.goto(`${base}/projects/${copy.id}/sheet`);
      await page.waitForSelector('.grid-notehead', { timeout: 300000 });
      await page.waitForTimeout(500);
      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await waitFor('the Sheet step ready', async () => (await stepState(part, 'sheet')).state === 'ready', 120);
      await page.screenshot({ path: path.join(out, `${String(index + 1).padStart(2, '0')}-${one.song.replace(/[^\w]+/g, '-')}.png`) });
      log(`${label}: sheet saved`);
    });

    // Leave the page first: Replace moves the folder the page's player reads its audio from.
    await page.goto('about:blank');
    await time('replace', () => post(`${api}/projects/${copy.id}/library`, { replace: true }));
    const after = await Promise.all(one.parts.map((p) => stepState(p, 'sheet')));
    if (!after.every((state) => state.state === 'ready')) throw new Error('the version is still without a ready sheet');
    const seconds = Math.round((Date.now() - started) / 1000);
    log(`${label}: done in ${seconds} s (edit ${times.edit} s, hands ${times.hands} s, sheet ${times.sheet} s, replace ${times.replace} s)`);
    summary.push({ ...one, ok: true, seconds, times });
  } catch (error) {
    log(`${label}: FAILED: ${error.message}`);
    summary.push({ ...one, ok: false, error: error.message, times });
    await page.screenshot({ path: path.join(out, `${String(index + 1).padStart(2, '0')}-FAILED.png`) }).catch(() => {});
  }
}
await browser.close();

const done = summary.filter((one) => one.ok).length;
writeFileSync(path.join(here, '..', '..', '.run', 'sheet-library.json'), JSON.stringify({ problems, summary }, null, 2));
log(`${done} of ${summary.length} versions now have their piano sheet${problems.length ? `; page errors: ${problems.length}` : ''}`);
for (const problem of problems.slice(0, 10)) log(`  ${problem}`);
process.exit(done === summary.length ? 0 : 1);
