/**
 * The Enhance with AI dialog in the browser (implementation 04, Phase 4).
 *
 * Without credits, on a temporary copy of a version of My library that the AI enhanced (7 Years by default; the copy
 * is deleted at the end, the library is only read). The requests that would start the AI are caught in the browser
 * and answered by a stand-in, so no request reaches the AI:
 * - with nothing selected, **Enhance it again with AI** opens the dialog on **The whole song**: **A stretch** is off;
 *   the tab offers **A level** (chosen on an enhanced sheet) or **Write it all again**, and no Simplify without a
 *   level (the user, 2026-10-30);
 * - **A level** of the whole song shows the hands (the whole sheet, the right hand only, the left hand only), a level
 *   per hand, the patterns approved for each level, the cost and the minutes, and the **gallery of patterns inside the
 *   dialog**: the hands rewritten only (the left hand first), at the hand's level, drawn by the app's engine; a
 *   pattern ticked there is added; **Write the level** sends `POST /sheet/{uuid}/llm/level-copy` with the level of
 *   each hand and the patterns; **Write it all again** says its time and cost and sends `POST /sheet/{uuid}/llm`;
 * - with one note picked, the header's button opens the dialog on **A stretch**, in the hand of that note; the note
 *   toolbox's own button too; **Left** says the right hand stays; **A level** of the left hand shows its gallery only
 *   and sends `POST /sheet/{uuid}/llm/level` with its frames; **Enhance with AI** sends the stretch with that hand and
 *   the user's words;
 * - in the gallery, **Select all** ticks every pattern of the level on the pill, **Deselect all** unticks the hand
 *   (the level is then sent with no pattern, `exact`), **Approved** ticks the approved ones again (2026-10-30);
 * - the **model** (GPT-6.1 Terra by default, Sonnet 5.5 costs more) and the **batches** (- and +), drawn on the sheet
 *   with one number each, the dialog at the right beside the sheet; the run sends both (2026-10-30).
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

  // ------------------------------------------------------------------ the whole song: a level (the user, 2026-10-30)
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog(page).waitFor({ timeout: 5000 });
  const tabs = dialog(page).getByRole('group', { name: 'What the AI works on' });
  check('nothing selected: the dialog opens on The whole song', (await tabs.getByRole('button', { name: 'The whole song' }).getAttribute('aria-pressed')) === 'true');
  check('and A stretch is off', await tabs.getByRole('button', { name: 'A stretch' }).isDisabled());
  const does = dialog(page).getByRole('group', { name: 'What the AI does' });
  check('the whole song: A level or Write it all again', (await does.getByRole('button').allInnerTexts()).join('|') === 'A level|Write it all again');
  check('an enhanced sheet opens on A level', (await does.getByRole('button', { name: 'A level' }).getAttribute('aria-pressed')) === 'true');
  check('no Simplify without a level', (await dialog(page).getByText(/^Simplify/).count()) === 0);
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
  const gallery = dialog(page).locator('[data-pattern-gallery]');
  await gallery.waitFor({ timeout: 5000 });
  check('the gallery is inside the dialog, on the left hand first', /^Left hand/.test(await gallery.getByRole('group', { name: 'The patterns of which hand' }).locator('[aria-pressed="true"]').innerText()));
  check('at the easy level, with its patterns drawn', (await gallery.locator('[data-pattern^="left easy "]').count()) >= 10);
  await page.waitForTimeout(1500);
  const drawn = await gallery.locator('[data-pattern="left easy 1"] img').evaluate((img) => img.complete && img.naturalWidth > 0);
  check('each pattern has its drawing', drawn);
  check('the approved ones are ticked', await gallery.locator('[data-pattern="left easy 2"] input').isChecked());
  check('the status says a new project, the cost and the minutes', /A new project in My projects.*About \$\d+\.\d\d, about \d+ minutes?/.test(await dialog(page).locator('[data-enhance-status]').innerText()));
  // The model and the batches (the user, 2026-10-30): the batches drawn on the sheet, the dialog at its right.
  const count = () => dialog(page).locator('[data-batch-count]').innerText().then(Number);
  const drawnBatches = () => page.locator('[data-frames-sheet] [data-batch]').evaluateAll((els) => new Set(els.map((e) => e.getAttribute('data-batch'))).size);
  await page.waitForFunction(() => document.querySelectorAll('[data-frames-sheet] [data-batch]').length > 0, null, { timeout: 5000 }).catch(() => undefined);
  const first = await count();
  check('the batches of the run are drawn on the sheet, one number each', first >= 1 && (await drawnBatches()) === first, `${first} batches`);
  check('GPT-6.1 Terra is the model by default', (await dialog(page).getByTestId('ai-model').inputValue()) === 'gpt-6.1-terra');
  const costOf = async () => Number(/About \$(\d+\.\d\d)/.exec(await dialog(page).locator('[data-enhance-status]').innerText())?.[1]);
  const terraCost = await costOf();
  await dialog(page).getByRole('button', { name: 'More batches' }).click();
  await dialog(page).getByRole('button', { name: 'More batches' }).click();
  await page.waitForFunction((n) => document.querySelector('[data-batch-count]')?.textContent === String(n), first + 2, { timeout: 5000 }).catch(() => undefined);
  await page.waitForTimeout(500);
  check('+ twice: two batches more, drawn', (await count()) === first + 2 && (await drawnBatches()) === first + 2, `${await count()} / ${await drawnBatches()}`);
  await dialog(page).getByRole('button', { name: 'Fewer batches' }).click();
  await page.waitForTimeout(600);
  check('- once: one fewer', (await count()) === first + 1);
  await dialog(page).getByTestId('ai-model').locator('..').click();
  await page.getByRole('option', { name: 'Sonnet 5.5' }).click();
  await page.waitForTimeout(700);
  check('Sonnet 5.5 costs more than GPT-6.1 Terra', (await costOf()) > terraCost, `${terraCost} -> ${await costOf()}`);
  const panel = await dialog(page).locator('.MuiDialog-paper').boundingBox();
  const drawing = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  check('the dialog sits at the right, beside the sheet', panel.x > 700 && drawing.x + drawing.width <= panel.x + 2, `${Math.round(drawing.x + drawing.width)} <= ${Math.round(panel.x)}`);
  await settled(page);
  await shot(page, '08-batches');
  await settled(page);
  await shot(page, '01-whole-song');
  await gallery.locator('[data-pattern="left easy 5"]').scrollIntoViewIfNeeded();
  await gallery.locator('[data-pattern="left easy 5"]').click();
  check('a pattern ticked in the gallery is added', /^Left: easy 2, easy 1, easy 3, easy 12, easy 5 · /.test(await patternsText()), await patternsText());
  await dialog(page).getByRole('group', { name: 'The level of the right hand' }).getByRole('button', { name: 'Hard' }).click();
  check('hard for the right hand takes its patterns', /Right: hard 1, hard 17, hard 15, hard 4$/.test(await patternsText()), await patternsText());
  check('and the gallery shows the right hand at hard', (await gallery.locator('[data-pattern^="right hard "]').count()) >= 10 && (await gallery.locator('[data-pattern^="left "]').count()) === 0);
  // Select all, Deselect all and Approved (the user, 2026-10-30): the hand shown, the level on its pill.
  const bulk = gallery.locator('[data-pattern-bulk]');
  const ticked = (prefix) => gallery.locator(`[data-pattern^="${prefix}"] input:checked`).count();
  await bulk.getByRole('button', { name: 'Deselect all' }).click();
  check('Deselect all unticks the hand shown', (await ticked('right ')) === 0 && /Right: none\. No pattern for the right hand/.test(await patternsText()), await patternsText());
  check('and keeps the other hand', /^Left: easy 2, easy 1, easy 3, easy 12, easy 5 · /.test(await patternsText()));
  await bulk.getByRole('button', { name: 'Select all', exact: true }).click();
  check('Select all ticks every pattern of the level on the pill', (await ticked('right hard ')) === (await gallery.locator('[data-pattern^="right hard "]').count()));
  check('and only that level', (await patternsText()).split(' · ')[1].split(', ').every((one) => /^(Right: )?hard \d+$/.test(one)), await patternsText());
  await settled(page);
  await shot(page, '07-select-all');
  await bulk.getByRole('button', { name: 'Approved' }).click();
  check('Approved ticks the approved patterns again', /Right: hard 1, hard 17, hard 15, hard 4$/.test(await patternsText()), await patternsText());
  await settled(page);
  await shot(page, '04-level-whole-song');
  await which.getByRole('button', { name: 'Right hand only' }).click();
  check('one hand: one level and its gallery only',
    (await dialog(page).getByRole('group', { name: /^The level of the/ }).count()) === 1 &&
    (await gallery.getByRole('group', { name: 'The patterns of which hand' }).count()) === 0 &&
    (await gallery.locator('[data-pattern^="left "]').count()) === 0);
  await which.getByRole('button', { name: 'The whole sheet' }).click();
  await page.getByTestId('song-confirm').click();
  await page.waitForTimeout(600);
  const levelCopy = sent.find((s) => /\/llm\/level-copy$/.test(s.url));
  check(
    'Write the level sends the level of each hand and the patterns',
    levelCopy?.body?.right === 'hard' && levelCopy?.body?.left === 'easy' && levelCopy?.body?.hand === 'both' &&
      levelCopy?.body?.patterns?.includes('left easy 5') && levelCopy?.body?.patterns?.includes('right hard 17') && levelCopy?.body?.exact === true &&
      levelCopy?.body?.model === 'claude-sonnet-5-5' && levelCopy?.body?.batches >= 1,
    JSON.stringify(levelCopy?.body),
  );
  check('the page says the stand-in refused', /Stand-in/.test(await page.locator('[data-edit-error]').first().innerText().catch(() => '')));
  check('and the dialog closes', (await dialog(page).count()) === 0);
  check('and the batches leave the sheet', (await page.locator('[data-frames-sheet] [data-batch]').count()) === 0);

  // ------------------------------------------------------------------ the whole song: Write it all again
  await page.getByTestId('header-enhance-with-ai').click();
  await dialog(page).waitFor({ timeout: 5000 });
  await dialog(page).getByRole('group', { name: 'What the AI does' }).getByRole('button', { name: 'Write it all again' }).click();
  check('Write it all again changes the button', (await page.getByTestId('song-confirm').innerText()).trim() === 'Write it all again');
  check('and says its time and cost', /in about \d+ minutes?.*About \$\d+\.\d\d/.test(await dialog(page).locator('[data-enhance-status]').innerText()), await dialog(page).locator('[data-enhance-status]').innerText());
  check('without levels or patterns', (await dialog(page).locator('[data-level-controls]').count()) === 0);
  await page.getByTestId('song-confirm').click();
  await page.waitForTimeout(600);
  check('Write it all again sends the whole run', sent.some((s) => /\/llm$/.test(s.url)));

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
  check('and the gallery of that hand only', (await dialog(page).locator('[data-pattern^="left easy "]').count()) >= 10 && (await dialog(page).locator('[data-pattern^="right "]').count()) === 0);
  // The estimate comes with the plan of the batches: wait for its price.
  await page.waitForFunction(() => /About \$\d/.test(document.querySelector('[data-enhance-status]')?.textContent ?? ''), null, { timeout: 5000 }).catch(() => undefined);
  check('the stretch status says the right hand stays and the cost', /The right hand stays as it is\. About \$\d+\.\d\d/.test(await dialog(page).locator('[data-enhance-status]').innerText()), await dialog(page).locator('[data-enhance-status]').innerText());
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
  // Deselect all: the level is sent with no pattern, exactly (the AI writes the hand by the level's rules only).
  await head.scrollIntoViewIfNeeded();
  const picked = await head.boundingBox();
  await page.mouse.click(picked.x + picked.width / 2, picked.y + picked.height / 2);
  await page.locator('[data-frames-note-toolbox]').waitFor({ timeout: 5000 });
  await page.getByTestId('notes-enhance').click();
  await dialog(page).waitFor({ timeout: 5000 });
  await dialog(page).getByRole('group', { name: 'How' }).getByRole('button', { name: 'A level' }).click();
  await dialog(page).locator('[data-pattern-bulk]').getByRole('button', { name: 'Deselect all' }).click();
  await page.getByTestId('stretch-confirm').click();
  await page.waitForTimeout(600);
  const none = sent.filter((s) => /\/llm\/level$/.test(s.url)).at(-1);
  check('Deselect all sends the level with no pattern', none !== level && none?.body?.patterns?.length === 0 && none?.body?.exact === true, JSON.stringify(none?.body));
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
