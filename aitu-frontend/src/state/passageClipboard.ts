/**
 * The app's clipboard for a copied passage (implementation 02, plan section 12, Phase 8).
 *
 * **Copy** keeps a reference, never the notes or the audio: the part, the stretch in milliseconds,
 * and what to call it on the Paste button. The backend reads the passage itself when it is pasted,
 * so a copied passage can be as long as a song.
 *
 * Kept in the browser's storage, so it outlives moving to another project and reaches every tab of
 * the app. Command-C also puts it in the system clipboard as JSON text, and Command-V reads one from
 * there: the page is plain HTTP on the home network, where the browser offers the system clipboard
 * only inside the copy and paste events themselves.
 */

import { useCallback, useSyncExternalStore } from "react";
import type { PassageRef } from "../api";

export const PASSAGE_TYPE = "aimpromptu/passage";
const STORAGE_KEY = "aitu.clipboard.passage";
const CHANGED = "aitu-clipboard-changed";

export interface CopiedPassage extends PassageRef {
  type: typeof PASSAGE_TYPE;
  /** The project the part belongs to, and its title when it was copied. */
  project: string;
  title: string;
}

function isPassage(value: unknown): value is CopiedPassage {
  if (typeof value !== "object" || value === null) return false;
  const found = value as Record<string, unknown>;
  return (
    found.type === PASSAGE_TYPE &&
    typeof found.part === "string" &&
    typeof found.fromMs === "number" &&
    typeof found.toMs === "number" &&
    found.toMs > found.fromMs
  );
}

/** A copied passage from text (the system clipboard), or `null` when the text is not one. */
export function passageFromText(text: string | null | undefined): CopiedPassage | null {
  if (!text || !text.includes(PASSAGE_TYPE)) return null;
  try {
    const parsed: unknown = JSON.parse(text);
    return isPassage(parsed) ? { ...parsed, title: String(parsed.title ?? "") } : null;
  } catch {
    return null;
  }
}

export function passageText(passage: CopiedPassage): string {
  return JSON.stringify(passage);
}

let cachedRaw: string | null = null;
let cached: CopiedPassage | null = null;

/** The passage copied last, or `null`. */
export function readCopied(): CopiedPassage | null {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    raw = null;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = passageFromText(raw);
  }
  return cached;
}

export function writeCopied(passage: CopiedPassage): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, passageText(passage));
  } catch {
    // A private window may refuse storage: the passage is still in the system clipboard when it
    // was copied with Command-C.
  }
  window.dispatchEvent(new Event(CHANGED));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The passage copied last, kept up to date across the pages and tabs of the app, and a setter. */
export function usePassageClipboard(): [CopiedPassage | null, (passage: CopiedPassage) => void] {
  const copied = useSyncExternalStore(subscribe, readCopied, () => null);
  const copy = useCallback((passage: CopiedPassage) => writeCopied(passage), []);
  return [copied, copy];
}

/** How long a passage plays, as the Paste button says it: `12.4 s`. */
export function passageLength(passage: PassageRef): string {
  const seconds = (passage.toMs - passage.fromMs) / 1000;
  return `${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)} s`;
}
