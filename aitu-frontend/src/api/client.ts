/**
 * Typed fetch wrapper for aitu-backend. No component calls `fetch` directly:
 * every request goes through here, and every route lives in a per-router module
 * next to this file, mirroring the backend's `api/` package.
 */

/** Base URL with any trailing slash removed. */
export const API_BASE = (import.meta.env.VITE_AITU_API_URL ?? "http://127.0.0.1:8765").replace(
  /\/$/,
  "",
);

/** An error carrying the HTTP status and the backend's `detail` string. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`${status} — ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** `501` means the endpoint exists but its epic has not landed yet. */
  get notImplemented(): boolean {
    return this.status === 501;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** JSON body; omit for GET. */
  body?: unknown;
  /** Appended as a query string, skipping `undefined` values. */
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
}

export function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

/**
 * One line of English from whatever the backend answered with.
 *
 * A refusal the backend wrote itself is a sentence, and it is used as it stands. A **422** is not:
 * FastAPI answers those with a list of objects, one per field it would not take, and the whole list
 * was being printed as raw JSON — which is how a reader ended up looking at
 * `{"detail":[{"type":"greater_than_equal","loc":["body","staffGaps",0,"gap"],...}]}` and learned
 * nothing from it. The field and the reason are the two parts that mean something, so those are
 * what is said: `staffGaps → 0 → gap: Input should be greater than or equal to 24`.
 */
function sayValidation(detail: readonly unknown[]): string {
  const said = detail
    .map((entry) => {
      const one = entry as { loc?: unknown[]; msg?: unknown };
      const where = (one.loc ?? [])
        // `body` is every request's first step and says nothing about which field it was.
        .filter((step) => step !== "body")
        .join(" \u2192 ");
      const why = typeof one.msg === "string" ? one.msg : "was refused";
      return where ? `${where}: ${why}` : why;
    })
    .filter((line) => line.length > 0);
  return said.length > 0 ? said.join("; ") : "The request was refused.";
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) return sayValidation(payload.detail);
    return JSON.stringify(payload);
  } catch {
    return response.statusText || "Request failed";
  }
}

async function fetchOrExplain(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") throw caught;
    const error = new Error("Could not reach the backend. Is make serve still running?");
    error.cause = caught;
    throw error;
  }
}

/** Perform a request and decode the JSON body as `T`. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, signal } = options;

  const response = await fetchOrExplain(buildUrl(path, query), {
    method,
    signal,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Multipart upload (audio files, imported JSON). */
export async function upload<T>(
  path: string,
  file: File,
  fields: Record<string, string> = {},
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  for (const [key, value] of Object.entries(fields)) form.append(key, value);

  const response = await fetchOrExplain(buildUrl(path), { method: "POST", body: form });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as T;
}

export const api = { request, upload, buildUrl, API_BASE };
