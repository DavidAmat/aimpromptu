/**
 * The two performance targets of the Notes tab (implementation 08, plan section 9.5, Phase 7):
 * 60 frames per second with 10,000 rectangles, and no frame dropped while 100 chunk messages per
 * second arrive. It opens `/dev/roll-bench` (development builds only) in a headless Chromium for
 * each scenario and prints what the page measured.
 *
 *     npm run bench:roll
 *     npm run bench:roll -- --out ../context/implementations/08-new-algorithm-notes-detection-muscriptor/measurements/phase-7-roll.json
 *
 * A headless Chromium on this machine paints the canvas in software, with no GPU: a browser with
 * a screen (the Mac) paints faster, so these numbers are the slow side.
 */

import { writeFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string' },
    notes: { type: 'string', default: '10000' },
  },
});

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on('pageerror', (error) => problems.push(error.message));
page.on('console', (message) => { if (message.type() === 'error') problems.push(message.text()); });
const results = [];
try {
  for (const scenario of ['play', 'scroll', 'whole', 'live', 'idle']) {
    await page.goto(`${values.base}/dev/roll-bench?scenario=${scenario}&notes=${values.notes}`);
    await page.waitForFunction(() => window.__rollBench !== undefined, null, { timeout: 30000 });
    const result = await page.evaluate(() => window.__rollBench);
    results.push(result);
    const { frameInterval: f, paintMs: p } = result;
    console.log(
      `${scenario.padEnd(6)} ${String(result.notes).padStart(6)} notes` +
        `${result.messagesPerSecond ? `, ${result.messagesPerSecond} messages/s` : ''}` +
        ` | ${result.fps} fps, frame gap median ${f.median} ms, p95 ${f.p95}, max ${f.max}, dropped ${result.dropped}/${f.count}` +
        ` | paint median ${p.median} ms, p95 ${p.p95}, max ${p.max} | long tasks ${result.longTasks}`,
    );
  }
} finally {
  await browser.close();
}
if (problems.length) console.log(`\nProblems:\n${problems.join('\n')}`);
if (values.out) {
  writeFileSync(values.out, `${JSON.stringify({ measuredOn: new Date().toISOString(), browser: 'headless Chromium (software canvas)', viewport: '1440x900', results }, null, 2)}\n`);
  console.log(`\nWritten to ${values.out}`);
}
