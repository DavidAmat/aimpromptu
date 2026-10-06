/**
 * A screenshot of the running app, taken with a headless Chromium (implementation 08, Phase 3).
 *
 * The user looks at the app from the Mac, through a tunnel. An agent on the Ubuntu machine has no
 * screen, so it takes its own pictures with this before asking the user to look.
 *
 *     npm run screenshot -- /projects
 *     npm run screenshot -- /projects/<uuid>/sheet --wait .grid-notehead
 *     npm run screenshot -- /admin/lab/video --out /tmp/lab.png --width 1600 --height 1000 --full
 *
 * Options:
 *   --piece <uuid>      make this piece the working piece (session storage) before the page opens
 *   --wait <selector>   wait for this CSS selector before the picture (default: network quiet)
 *   --delay <ms>        wait this long after that (default 500), for animations and canvases
 *   --out <file.png>    default ../.run/screenshots/<path>.png (ignored by git)
 *   --width, --height   the window, default 1440 x 900; --full takes the whole page
 *   --base <url>        default http://localhost:5173 (the app of `make up` or `make serve`)
 *   --theme dark        the dark scheme of the user menu (default light)
 *   --signed-out        do not sign in (the sign-in page); otherwise signed in as the master user,
 *                       with the password of .env (scripts/session.mjs)
 *
 * It prints every console error and failed request of the page, since a blank picture with an
 * error behind it is the usual way a page fails. Once per machine: `npx playwright install chromium`.
 */

import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    piece: { type: 'string' },
    wait: { type: 'string' },
    delay: { type: 'string', default: '500' },
    out: { type: 'string' },
    width: { type: 'string', default: '1440' },
    height: { type: 'string', default: '900' },
    full: { type: 'boolean', default: false },
    base: { type: 'string', default: 'http://localhost:5173' },
    // The page as somebody signed out sees it (the sign-in page); signed in as the master user
    // otherwise (scripts/session.mjs).
    'signed-out': { type: 'boolean', default: false },
    // The colour scheme: light (default) or dark, as the user menu sets it.
    theme: { type: 'string', default: 'light' },
  },
});

const route = positionals[0] ?? '/';
const url = new URL(route, values.base).toString();
const slug = route.replace(/^\/+|\/+$/g, '').replace(/[^a-z0-9]+/gi, '-') || 'home';
const out = path.resolve(
  values.out ?? path.join(here, '..', '..', '.run', 'screenshots', `${slug}.png`),
);
mkdirSync(path.dirname(out), { recursive: true });

const browser = await chromium.launch();
if (!values['signed-out']) {
  await signIn(values.base);
  useSession(browser);
}
const page = await browser.newPage({
  viewport: { width: Number(values.width), height: Number(values.height) },
});
// MUI keeps the user's theme in the browser's storage, under `mui-mode`.
await page.addInitScript((mode) => window.localStorage.setItem('mui-mode', mode), values.theme);

const problems = [];
page.on('console', (message) => {
  if (message.type() === 'error') problems.push(`console: ${message.text()}`);
});
page.on('pageerror', (error) => problems.push(`page error: ${error.message}`));
page.on('response', (response) => {
  if (response.status() >= 400) problems.push(`${response.status()} ${response.url()}`);
});
// ERR_ABORTED is the page cancelling its own request (React runs each effect twice in development,
// and the first run's request is aborted), not a failure.
page.on('requestfailed', (request) => {
  const reason = request.failure()?.errorText ?? '';
  if (!reason.includes('ERR_ABORTED')) problems.push(`failed: ${request.url()} (${reason})`);
});

if (values.piece) {
  // The working piece lives in session storage (`aitu.workingArtifact`).
  const artifact = JSON.stringify({ audioUuid: values.piece, label: values.piece, frameMs: 40 });
  await page.addInitScript((value) => {
    window.sessionStorage.setItem('aitu.workingArtifact', value);
  }, artifact);
}

const started = Date.now();
await page.goto(url, { waitUntil: 'networkidle' });
if (values.wait) await page.waitForSelector(values.wait, { timeout: 30_000 });
await page.waitForTimeout(Number(values.delay));
await page.screenshot({ path: out, fullPage: values.full });
await browser.close();

console.log(`${url} -> ${out} (${Date.now() - started} ms)`);
for (const problem of problems) console.log(`  ${problem}`);
if (problems.length === 0) console.log('  no console error, no failed request');
