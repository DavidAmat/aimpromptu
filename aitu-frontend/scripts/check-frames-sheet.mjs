/**
 * The new Sheet step in the browser (implementation 03, Phase 5): the sheet without compases, to see and to hear.
 *
 * Without credits, on a temporary copy of a version of My library that Sonnet wrote (7 Years by default; the copy
 * is deleted at the end, the library is only read):
 * - the Sheet step draws the new sheet (`[data-frames-sheet]`, a `data-note` on every notehead), and the steps are
 *   Source, Audio, Notes, Sheet (no Hands);
 * - a click on the sheet moves the cursor there (`[data-frames-cursor]`, `data-ms`) and lights its notes
 *   (`[data-lit]`); Play moves the cursor;
 * - a sheet the AI enhanced has the AI symbol next to its title (tooltip **Enhanced with AI**; implementation 04, Phase 1)
 *   and offers **Enhance it again with AI**; the bar has
 *   no switch to the old vexflow-v2 sheet (removed in implementation 03, Phases 8B and 10);
 * - an old address of the Hands step opens the Sheet step.
 *
 * With `--live` (it spends Sonnet credits: a few cents), a new project from a clip of `--seconds` of that song's
 * audio: transcribed, then its Sheet step starts Sonnet by itself; the check records the segment at Sonnet (pale),
 * each segment that comes back (it appears column by column), the time of each step, and at the end the hands in
 * the notes (Notes Falling's colours). The project is deleted at the end.
 *
 *     npm run check:frames-sheet -- --out /tmp/frames-sheet [--live --seconds 40]
 */

import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-frames-sheet') },
    version: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
    live: { type: 'boolean', default: false },
    seconds: { type: 'string', default: '40' },
    from: { type: 'string', default: '30' },
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
  return answer.status === 204 ? null : answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
useSession(browser);
const problems = [];
async function open(route) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  // A 404 on `/rhythm` is how a page asks whether the old sheet saved its title lines; the browser logs it too.
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400 && !(r.status() === 404 && /\/rhythm$/.test(r.url()))) problems.push(`${r.status()} ${r.url()}`); });
  await page.goto(new URL(route, base).toString());
  return page;
}
const drawn = (page) => page.locator('[data-frames-sheet] [data-note]').first().waitFor({ timeout: 120000 });
const shot = (page, name, clip) => page.screenshot({ path: path.join(values.out, `${name}.png`), ...(clip ? { clip } : {}) });

const made = [];
try {
  // ------------------------------------------------------------------ a copy of a version Sonnet wrote
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  const page = await open(`/projects/${part}/sheet`);
  const begin = Date.now();
  await drawn(page);
  check('the Sheet step draws the new sheet', true, `${Date.now() - begin} ms`);
  const tabs = await page.locator('[role="tab"]').allInnerTexts();
  check('the steps are Source, Audio, Notes, Sheet', !tabs.some((t) => /Hands/.test(t)), tabs.join(' | '));
  const root = page.locator('[data-frames-sheet]');
  check('the copy keeps the sheet Sonnet wrote', (await root.getAttribute('data-source')) === 'llm');
  check('a sheet the AI enhanced has the AI symbol next to its title', (await page.locator('[data-sheet-header] [data-ai-mark] [data-enhanced]').count()) === 1);
  check('and offers Enhance it again with AI', (await page.getByTestId('enhance-with-ai').innerText()).trim() === 'Enhance it again with AI');
  await page.waitForTimeout(600);
  await shot(page, '01-sheet-step');

  const box = await root.boundingBox();
  await page.mouse.click(box.x + box.width * 0.5, box.y + 300);
  await page.waitForTimeout(400);
  const ms = Number(await page.locator('[data-frames-cursor]').getAttribute('data-ms'));
  check('a click on the sheet moves the cursor there', ms > 5000, `${ms} ms`);
  check('the notes under the cursor are lit', (await page.locator('[data-lit]').count()) > 0);
  await page.keyboard.press('Space');
  await page.waitForTimeout(1500);
  await page.keyboard.press('Space');
  const later = Number(await page.locator('[data-frames-cursor]').getAttribute('data-ms'));
  check('Play moves the cursor', later > ms + 500, `${ms} -> ${later} ms`);

  // The old sheet is gone (Phase 8B): no switch on the bar.
  check('the bar has no switch to the old sheet', (await page.getByTestId('old-sheet').count()) === 0);

  await page.goto(`${base}/projects/${part}/hands`);
  await page.waitForURL('**/sheet');
  check('an old address of the Hands step opens the Sheet step', page.url().endsWith('/sheet'));
  await page.close();

  // ------------------------------------------------------------------ live: a new transcription goes to Sonnet
  if (values.live) {
    const work = mkdtempSync(path.join(os.tmpdir(), 'frames-sheet-'));
    const original = await fetch(`${api}/audio/${values.version}/file?original=true`);
    writeFileSync(path.join(work, 'song'), Buffer.from(await original.arrayBuffer()));
    const clip = path.join(work, 'clip.mp3');
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-ss', values.from, '-t', values.seconds, '-i', path.join(work, 'song'), clip]);
    const form = new FormData();
    form.append('file', new Blob([readFileSync(clip)]), 'clip.mp3');
    form.append('alias', 'check:frames-sheet (temporary)');
    const uploaded = await json(`${api}/audio/upload`, { method: 'POST', body: form });
    made.push(uploaded.uuid);
    const uuid = uploaded.uuid;
    const job = await post(`${api}/matrix/transcribe`, { audioUuid: uuid });
    for (let i = 0; i < 600; i += 1) {
      const state = await json(`${api}/matrix/jobs/${job.jobId}`);
      if (state.status === 'done') break;
      if (state.status === 'error') throw new Error(`transcription: ${state.error}`);
      await new Promise((r) => setTimeout(r, 1000));
    }
    const before = await json(`${api}/matrix/${uuid}/events`);
    check('a new transcription has no hand colours (Notes Falling)', before.events.every((e) => e.hand === null));

    const live = await open(`/projects/${uuid}/sheet`);
    const start = Date.now();
    await drawn(live);
    check('the algorithm\'s sheet is drawn at once', true, `${Date.now() - start} ms`);
    const seen = [];
    let lastStates = '';
    let shots = 0;
    for (let i = 0; i < 1200; i += 1) {
      const now = await live.evaluate(() => {
        const root = document.querySelector('[data-frames-sheet]');
        return {
          llm: root?.getAttribute('data-llm'),
          working: document.querySelectorAll("[data-segment-state='working']").length,
          revealing: document.querySelectorAll('[data-revealing]').length,
        };
      });
      const key = `${now.llm}|${now.working}|${now.revealing > 0}`;
      if (key !== lastStates) {
        lastStates = key;
        seen.push({ t: Math.round((Date.now() - start) / 100) / 10, ...now });
        console.log(`  ${seen.at(-1).t} s  llm ${now.llm}  pale boxes ${now.working}  appearing ${now.revealing}`);
        if ((now.working > 0 || now.revealing > 0) && shots < 6) {
          shots += 1;
          await shot(live, `02-live-${String(shots).padStart(2, '0')}`);
        }
      }
      if (now.llm === 'done' && now.working === 0 && now.revealing === 0) break;
      await live.waitForTimeout(250);
    }
    check('Sonnet started by itself and a segment looked pale while it worked', seen.some((s) => s.working > 0));
    check('a segment that came back appeared little by little', seen.some((s) => s.revealing > 0));
    check('Sonnet finished', lastStates.startsWith('done'), `${Math.round((Date.now() - start) / 1000)} s`);
    await shot(live, '03-live-done');
    const after = await json(`${api}/matrix/${uuid}/events`);
    const handed = after.events.filter((e) => !e.removed && e.hand !== null).length;
    check('the hands are in the notes (Notes Falling\'s colours)', handed > 0, `${handed} of ${after.events.length}`);
    const sheet = await json(`${api}/sheet/${uuid}?width=130`);
    check('the stored sheet is Sonnet\'s', sheet.source !== 'algorithm', `${sheet.source}, $${sheet.llm.usd}`);
    writeFileSync(path.join(values.out, 'live.json'), JSON.stringify({ seen, usd: sheet.llm.usd, segments: sheet.segments }, null, 1));
    await live.close();
  }
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
