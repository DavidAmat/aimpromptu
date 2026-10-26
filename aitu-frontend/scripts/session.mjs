/**
 * Signing in, for the scripts that drive the app (implementation 02, Phase 4: every route but
 * `/auth/login` needs a session).
 *
 * The scripts act as the master user. The username and the password come from the environment
 * (`AITU_CHECK_USERNAME`, `AITU_CHECK_PASSWORD`), or else from `.env` at the repository root
 * (`AITU_MASTER_USERNAME`, default `master`, and `AITU_MASTER_PASSWORD`), the same values the
 * backend made the master user from.
 *
 *     import { signIn, useSession } from './session.mjs';
 *     await signIn(base);           // every `fetch` of the script now sends the cookie
 *     useSession(browser);          // every `browser.newPage()` starts signed in
 */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const COOKIE = 'aitu_session';

function fromDotEnv() {
  const file = path.join(here, '..', '..', '.env');
  if (!existsSync(file)) return {};
  const values = {};
  for (const line of readFileSync(file, 'utf8').split('\n')) {
    const match = /^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (match) values[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
  return values;
}

export function credentials() {
  const env = fromDotEnv();
  const username = process.env.AITU_CHECK_USERNAME || env.AITU_MASTER_USERNAME || 'master';
  const password = process.env.AITU_CHECK_PASSWORD || env.AITU_MASTER_PASSWORD || '';
  if (!password) {
    throw new Error('No password to sign in with: set AITU_MASTER_PASSWORD in .env, or AITU_CHECK_PASSWORD');
  }
  return { username, password };
}

let session = null;

/** Sign in through `${base}/api/auth/login`, and make every later `fetch` send the cookie. */
export async function signIn(base) {
  const original = globalThis.fetch;
  const answer = await original(`${base}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials()),
  });
  if (!answer.ok) throw new Error(`Sign in failed: ${answer.status} ${await answer.text()}`);
  const cookie = (answer.headers.getSetCookie?.() ?? [answer.headers.get('set-cookie') ?? ''])
    .map((line) => line.split(';')[0])
    .find((pair) => pair.startsWith(`${COOKIE}=`));
  if (!cookie) throw new Error('Sign in answered no session cookie');
  session = { base, value: cookie.slice(COOKIE.length + 1) };
  globalThis.fetch = (input, init = {}) => {
    const headers = new Headers(init.headers);
    headers.set('Cookie', `${COOKIE}=${session.value}`);
    return original(input, { ...init, headers });
  };
  return session;
}

/** Every `browser.newPage()` opens in a context that already has the session cookie. */
export function useSession(browser) {
  if (!session) throw new Error('Call signIn(base) before useSession(browser)');
  const { base, value } = session;
  browser.newPage = async (options = {}) => {
    const context = await browser.newContext(options);
    await context.addCookies([{ name: COOKIE, value, url: base, httpOnly: true, sameSite: 'Lax' }]);
    return context.newPage();
  };
  return browser;
}
