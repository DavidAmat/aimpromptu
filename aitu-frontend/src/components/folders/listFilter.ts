/**
 * **Filter** of My projects and My Library (implementation 04-3, Phase 1, plan section 4.3): a dropdown for the
 * artist, then one for each primary key the items use (Film, TV show, …), whose options are its secondary keys with
 * how many items have them. Choices combine: an artist and a film leave the items that have both.
 *
 * The options are worked out from the rows on the page (they carry their artists and their metadata), and the
 * choices are kept in the address (`?artist=Enya&films=The Lord of the Rings`).
 */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { TagRow } from "../../api";
import { TAG_KEYS } from "./tagWords";

export interface FilterChoice {
  artist: string | null;
  /** `primary key -> the secondary key chosen`. */
  tags: Record<string, string>;
}

export function useListFilter(): [FilterChoice, (change: { artist?: string | null; tag?: [string, string | null] }) => void] {
  const [params, setParams] = useSearchParams();
  const choice = useMemo<FilterChoice>(() => {
    const tags: Record<string, string> = {};
    for (const key of TAG_KEYS) {
      const value = params.get(key);
      if (value) tags[key] = value;
    }
    return { artist: params.get("artist"), tags };
  }, [params]);
  const change = useCallback(
    (next: { artist?: string | null; tag?: [string, string | null] }) => {
      setParams((current) => {
        const out = new URLSearchParams(current);
        if (next.artist !== undefined) {
          if (next.artist === null) out.delete("artist");
          else out.set("artist", next.artist);
        }
        if (next.tag) {
          const [key, value] = next.tag;
          if (value === null) out.delete(key);
          else out.set(key, value);
        }
        return out;
      });
    },
    [setParams],
  );
  return [choice, change];
}

const same = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: "base" }) === 0;

/** The rows the choice leaves. */
export function filtered<T>(rows: readonly T[], choice: FilterChoice, artistsOf: (row: T) => string[], tagsOf: (row: T) => TagRow[]): T[] {
  return rows.filter((row) => {
    if (choice.artist !== null && !artistsOf(row).some((name) => same(name, choice.artist as string))) return false;
    return Object.entries(choice.tags).every(([key, value]) =>
      tagsOf(row).some((tag) => tag.category === key && same(tag.value, value)),
    );
  });
}
