/**
 * The three pills at the top of My projects and My Library (implementation 04-3, Phase 1, plan section 4.3):
 * **Folders**, **All** (the list as it was) and **Filter**.
 *
 * The pill chosen is in the address (`?view=folders`), so a reload and the back button keep it, and in the browser,
 * so the page opens again on the last one. The first visit opens **All**.
 */

import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

export type ListView = "folders" | "all" | "filter";


const isView = (value: string | null): value is ListView => value === "folders" || value === "all" || value === "filter";

function stored(key: string): ListView | null {
  try {
    const value = window.localStorage.getItem(key);
    return isView(value) ? value : null;
  } catch {
    return null;
  }
}

/** The view on show and its setter; `storageKey` keeps the last one in the browser. */
export function useListView(storageKey: string): [ListView, (view: ListView) => void] {
  const [params, setParams] = useSearchParams();
  const asked = params.get("view");
  const view: ListView = isView(asked) ? asked : (stored(storageKey) ?? "all");
  const setView = useCallback(
    (next: ListView) => {
      try {
        window.localStorage.setItem(storageKey, next);
      } catch {
        // A browser that keeps nothing still shows the view; only the next visit opens on All.
      }
      setParams(
        (current) => {
          const out = new URLSearchParams(current);
          out.set("view", next);
          return out;
        },
        { replace: false },
      );
    },
    [storageKey, setParams],
  );
  return [view, setView];
}
