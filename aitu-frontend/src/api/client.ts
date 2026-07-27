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

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    return JSON.stringify(payload);
  } catch {
    return response.statusText || "Request failed";
  }
}

/** Perform a request and decode the JSON body as `T`. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, signal } = options;

  const response = await fetch(buildUrl(path, query), {
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

  const response = await fetch(buildUrl(path), { method: "POST", body: form });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as T;
}

export const api = { request, upload, buildUrl, API_BASE };
