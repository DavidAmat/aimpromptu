/**
 * The passages chosen on the page of **From other projects** (implementation 02, plan section 10.4,
 * Phase 10), before they are saved as a project.
 *
 * Like the copied passage, the list holds references only (a part and a stretch of it): the backend
 * reads the music when **Save as song** or **Save as integrated playlist** makes the project. It is
 * kept in the browser's storage, so a reload or a visit to another page does not lose it, and it is
 * emptied once the project is made.
 */

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "aitu.compose.draft";
const CHANGED = "aitu-compose-changed";

export type Join = "sequential" | "subheader";

export interface DraftPassage {
  /** Tells two passages of the same stretch apart in the list. */
  key: string;
  part: string;
  /** The project the part belongs to, and what to call the passage. */
  project: string;
  title: string;
  /** The stretch in ms of the part; both `null` for all of it. */
  fromMs: number | null;
  toMs: number | null;
  /** How it joins the passage before it (the first has none). */
  join: Join;
  /** The title of the part a subheader starts; the passage's title when empty. */
  subheader: string;
}

function isPassage(value: unknown): value is DraftPassage {
  if (typeof value !== "object" || value === null) return false;
  const found = value as Record<string, unknown>;
  return typeof found.key === "string" && typeof found.part === "string" && typeof found.title === "string";
}

let cachedRaw: string | null = null;
let cached: DraftPassage[] = [];

function read(): DraftPassage[] {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    raw = null;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    try {
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      cached = Array.isArray(parsed) ? parsed.filter(isPassage) : [];
    } catch {
      cached = [];
    }
  }
  return cached;
}

function write(next: DraftPassage[]): void {
  try {
    if (next.length === 0) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // A private window may refuse storage: the list then lasts as long as the page.
    cachedRaw = JSON.stringify(next);
    cached = next;
  }
  window.dispatchEvent(new Event(CHANGED));
}

function subscribe(onChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) onChange();
  };
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function newPassageKey(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** The chosen passages, and the way to change them. */
export function useComposeDraft(): [DraftPassage[], (next: DraftPassage[]) => void] {
  const passages = useSyncExternalStore(subscribe, read, () => []);
  const set = useCallback((next: DraftPassage[]) => write(next), []);
  return [passages, set];
}
