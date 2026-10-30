/**
 * The Enhance with AI dialog in the browser (implementation 04, Phase 4).
 *
 * Without credits, on a temporary copy of a version of My library that the AI enhanced (7 Years by default; the copy
 * is deleted at the end, the library is only read). The requests that would start the AI are caught in the browser
 * and answered by a stand-in, so no request reaches the AI:
 * - with nothing selected, **Enhance it again with AI** opens the dialog on **The whole song**: **A stretch** is off,
 *   the four runs show their cost, **Simplify the left hand** is chosen, the button says **Simplify**, and **Write it
 *   all again** changes it;
 * - **Simplify** sends `POST /sheet/{uuid}/llm/simplify` with the hand chosen;
 * - with one note picked, the header's button opens the dialog on **A stretch**, in the hand of that note; the note
 *   toolbox's own button too; **Left** says the right hand stays; **Enhance with AI** sends the stretch with that hand
 *   and the user's words.
 * - The levels (implementation 04-3, Phase 4): **A level** of the whole song shows the hands (the whole sheet, the
 *   right hand only, the left hand only), a level per hand, the patterns approved for each level, and the cost; the
 *   catalog opens on the left hand at its level with the drawings of the app's engine, a pattern selected there is
 *   added; **Write the level** sends `POST /sheet/{uuid}/llm/level-copy` with the level of each hand and the
 *   patterns. On a stretch, **A level** of the left hand sends `POST /sheet/{uuid}/llm/level` with its frames.
 *
 *     npm run check:enhance-dialog -- --out /tmp/enhance-dialog
 */

import { mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { sheetNow, waitForFrames } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-enhance-dialog') },
    version: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
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
const post = async (url, body) => {
  const answer = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
  if (!answer.ok) throw new Error(`POST ${url}: ${answer.status} ${await answer.text()}`);
  return answer.json();
};

const browser = await chromium.launch();
useSession(browser);
const problems = [];
const shot = (page, name) => page.screenshot({ path: path.join(values.out, `${name}.png`) });
/** The dialog once its opening has ended (MUI fades it in): its opacity. */
const settled = async (page) => {
  await page.waitForTimeout(500);
  return page.locator('[data-enhance-dialog] .MuiDialog-container').evaluate((el) => Number(getComputedStyle(el).opacity));
};
const dialog = (page) => page.locator('[data-enhance-dialog]');

const made = [];
try {
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  // The stand-in's refusal is said on the page as an error: expected, not a problem.
  page.on('console', (m) => { if (m.type() === 'error' && !/status of (404|409)/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  // Every request that would start the AI is caught here and answered "busy": the AI is never asked.
  const sent = [];
  await page.route(/\/api\/sheet\/[^/]+\/llm(\/stretch|\/simplify|\/level|\/level-copy)?$/, (route) => {
    const request = route.request();
    if (request.method() !== 'POST') return route.continue();
    sent.push({ url: request.url(), body: request.postDataJSON?.() ?? null });
    return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'Stand-in: the AI was not asked.' }) });
  });
  await page.goto(`${base}/projects/${part}/sheet`);
  await waitForFrames(page);

  // ------------------------------------------------------------------ the whole song
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog(page).waitFor({ timeout: 5000 });
  const tabs = dialog(page).getByRole('group', { name: 'What the AI works on' });
  check('nothing selected: the dialog opens on The whole song', (await tabs.getByRole('button', { name: 'The whole song' }).getAttribute('aria-pressed')) === 'true');
  check('and A stretch is off', await tabs.getByRole('button', { name: 'A stretch' }).isDisabled());
  const runs = ['level', 'simplify-left', 'simplify-right', 'simplify-both', 'all'];
  await page.waitForFunction(() => document.querySelectorAll('[data-enhance-dialog] [data-testid^="song-run-"]').length === 5 && /\$\d/.test(document.querySelector('[data-enhance-dialog] [data-testid="song-run-all"]')?.textContent ?? ''), null, { timeout: 5000 }).catch(() => undefined);
  const costs = [];
  for (const run of runs) costs.push((await dialog(page).getByTestId(`song-run-${run}`).innerText()).replace(/\s+/g, ' ').trim());
  check('the five runs, each with its cost', costs.every((text) => /\$\d+\.\d\d$/.test(text)), costs.join(' | '));
  check('an enhanced sheet: Simplify the left hand is chosen', await dialog(page).getByTestId('song-run-simplify-left').locator('input').isChecked());
  check('the button says Simplify', (await page.getByTestId('song-confirm').innerText()).trim() === 'Simplify');
  check('the dialog is opaque once open', (await settled(page)) === 1);
  await shot(page, '01-whole-song');
  await dialog(page).getByTestId('song-run-all').click();
  check('Write it all again changes the button', (await page.getByTestId('song-confirm').innerText()).trim() === 'Write it all again');
  await dialog(page).getByTestId('song-run-simplify-right').click();
  await page.getByTestId('song-confirm').click();
  await page.waitForTimeout(600);
  const simplify = sent.find((s) => /\/llm\/simplify$/.test(s.url));
  check('Simplify sends the hand chosen', simplify?.body?.hand === 'right', JSON.stringify(simplify?.body));
  check('and the dialog closes', (await dialog(page).count()) === 0);

  // ------------------------------------------------------------------ a level of the whole song
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog(page).waitFor({ timeout: 5000 });
  await dialog(page).getByTestId('song-run-level').click();
  const which = dialog(page).getByRole('group', { name: 'Which hands' });
  check('A level: the whole sheet, the right hand only, the left hand only',
    (await which.getByRole('button').allInnerTexts()).join('|') === 'The whole sheet|Right hand only|Left hand only');
  check('the button says Write the level', (await page.getByTestId('song-confirm').innerText()).trim() === 'Write the level');
  check('a level for each hand, easy first',
    (await dialog(page).getByRole('group', { name: 'The level of the right hand' }).getByRole('button', { name: 'Easy' }).getAttribute('aria-pressed')) === 'true' &&
    (await dialog(page).getByRole('group', { name: 'The level of the left hand' }).getByRole('button', { name: 'Easy' }).getAttribute('aria-pressed')) === 'true');
  const patternsText = () => dialog(page).locator('[data-level-patterns]').innerText();
  await page.waitForFunction(() => /easy 2/.test(document.querySelector('[data-level-patterns]')?.textContent ?? ''), null, { timeout: 5000 }).catch(() => undefined);
  check('the patterns approved for easy are selected', (await patternsText()) === 'Left: easy 2, easy 1, easy 3, easy 12 · Right: easy 2, easy 1', await patternsText());
  await dialog(page).getByRole('group', { name: 'The level of the right hand' }).getByRole('button', { name: 'Hard' }).click();
  check('hard for the right hand takes its patterns', /Right: hard 1, hard 17, hard 15, hard 4$/.test(await patternsText()), await patternsText());
  check('the status says a new project and the cost', /A new project in My projects.*About \$\d+\.\d\d, about \d+ minutes?/.test(await dialog(page).locator('[data-enhance-status]').innerText()));
  await settled(page);
  await shot(page, '04-level-whole-song');
  await page.getByTestId('open-catalog').click();
  const catalog = page.locator('[data-pattern-catalog]');
  await catalog.waitFor({ timeout: 5000 });
  check('the catalog opens on the left hand', /^Left hand/.test(await catalog.getByRole('group', { name: 'Which hand' }).locator('[aria-pressed="true"]').innerText()));
  check('at its level, with the easy patterns', (await catalog.locator('[data-pattern^="left easy "]').count()) >= 10);
  await page.waitForTimeout(1500);
  const drawn = await catalog.locator('[data-pattern="left easy 5"] img').evaluate((img) => img.complete && img.naturalWidth > 0);
  check('each pattern has its drawing', drawn);
  await shot(page, '05-catalog');
  await catalog.locator('[data-pattern="left easy 5"]').click();
  await page.getByTestId('catalog-done').click();
  check('a pattern selected in the catalog is added', /^Left: easy 2, easy 1, easy 3, easy 12, easy 5 · /.test(await patternsText()), await patternsText());
  await page.getByTestId('song-confirm').click();
  await page.waitForTimeout(600);
  const levelCopy = sent.find((s) => /\/llm\/level-copy$/.test(s.url));
  check(
    'Write the level sends the level of each hand and the patterns',
    levelCopy?.body?.right === 'hard' && levelCopy?.body?.left === 'easy' && levelCopy?.body?.hand === 'both' &&
      levelCopy?.body?.patterns?.includes('left easy 5') && levelCopy?.body?.patterns?.includes('right hard 17'),
    JSON.stringify(levelCopy?.body),
  );
  check('the page says the stand-in refused', /Stand-in/.test(await page.locator('[data-edit-error]').first().innerText().catch(() => '')));

  // ------------------------------------------------------------------ a stretch
  const sheet = await sheetNow(api, part);
  const note = sheet.notes.find((n) => n.hand === 'left' && sheet.columns.some((c) => c.frame === Number(n.ref.split(':')[0]) && c.system === 1));
  const head = page.locator(`[data-frames-sheet] [data-note~="${note.ref}"]`).first();
  await head.scrollIntoViewIfNeeded();
  const box = await head.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.locator('[data-frames-note-toolbox]').waitFor({ timeout: 5000 });
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog(page).waitFor({ timeout: 5000 });
  check('one note picked: the dialog opens on A stretch', (await tabs.getByRole('button', { name: 'A stretch' }).getAttribute('aria-pressed')) === 'true');
  const hands = dialog(page).getByRole('group', { name: 'Which hand' });
  check('in the hand of that note', (await hands.getByRole('button', { name: 'Left' }).getAttribute('aria-pressed')) === 'true');
  check('the status says the right hand stays', /The right hand stays as it is/.test(await dialog(page).locator('[data-enhance-status]').innerText()));
  await settled(page);
  await shot(page, '02-stretch');
  await hands.getByRole('button', { name: 'Both' }).click();
  check('Both: no hand is said to stay', !/stays as it is/.test(await dialog(page).locator('[data-enhance-status]').innerText()));
  await tabs.getByRole('button', { name: 'The whole song' }).click();
  check('the whole song can still be chosen', (await dialog(page).getByTestId('song-confirm').count()) === 1);
  await dialog(page).getByRole('button', { name: 'Cancel' }).click();
  await page.waitForTimeout(300);

  await page.getByTestId('notes-enhance').click();
  await dialog(page).waitFor({ timeout: 5000 });
  check('the note toolbox opens it on A stretch too', (await tabs.getByRole('button', { name: 'A stretch' }).getAttribute('aria-pressed')) === 'true');
  // A level of the stretch, the left hand: one level, its frames.
  await dialog(page).getByRole('group', { name: 'How' }).getByRole('button', { name: 'A level' }).click();
  check('a level of one hand: one level only', (await dialog(page).getByRole('group', { name: /^The level of the/ }).count()) === 1);
  check('the stretch status says the right hand stays and the cost', /The right hand stays as it is\. About \$\d+\.\d\d/.test(await dialog(page).locator('[data-enhance-status]').innerText()));
  await dialog(page).getByRole('group', { name: 'The level of the left hand' }).getByRole('button', { name: 'Medium' }).click();
  await settled(page);
  await shot(page, '06-level-stretch');
  await page.getByTestId('stretch-confirm').click();
  await page.waitForTimeout(600);
  const level = sent.find((s) => /\/llm\/level$/.test(s.url));
  check(
    'a level of a stretch sends its frames, the hand and the patterns of its level',
    level?.body?.hand === 'left' && level?.body?.left === 'medium' && level?.body?.end > level?.body?.start &&
      level?.body?.patterns?.join(',') === 'left medium 15,left medium 2,left medium 10,left medium 7',
    JSON.stringify(level?.body),
  );
  await head.scrollIntoViewIfNeeded();
  const again = await head.boundingBox();
  await page.mouse.click(again.x + again.width / 2, again.y + again.height / 2);
  await page.locator('[data-frames-note-toolbox]').waitFor({ timeout: 5000 });
  await page.getByTestId('notes-enhance').click();
  await dialog(page).waitFor({ timeout: 5000 });
  await page.getByTestId('stretch-words').fill('Make the octaves single notes.');
  await page.getByTestId('stretch-confirm').click();
  await page.waitForTimeout(600);
  const stretch = sent.find((s) => /\/llm\/stretch$/.test(s.url));
  check(
    'Enhance with AI sends the stretch, its hand and the words',
    stretch?.body?.staff === 'left' && stretch?.body?.instruction === 'Make the octaves single notes.' && stretch?.body?.notes?.includes(note.ref),
    JSON.stringify(stretch?.body),
  );
  check('no request reached the AI', (await sheetNow(api, part)).llm.state !== 'running');
  await shot(page, '03-after');
  await page.close();
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
