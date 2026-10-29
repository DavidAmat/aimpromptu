/** The dropdowns of **Filter** (implementation 04-3, Phase 1): see `listFilter.ts` for what they choose. */

import Stack from "@mui/material/Stack";
import type { TagRow } from "../../api";
import { FilterChip, type FilterChipOption } from "../../ui";
import { filtered, type FilterChoice } from "./listFilter";
import { tagKeyLabel, TAG_KEYS } from "./tagWords";

function counted(values: string[]): FilterChipOption[] {
  const counts = new Map<string, { label: string; count: number }>();
  for (const value of values) {
    const key = value.toLocaleLowerCase();
    const found = counts.get(key);
    if (found) found.count += 1;
    else counts.set(key, { label: value, count: 1 });
  }
  return [...counts.values()]
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }))
    .map((one) => ({ value: one.label, label: one.label, count: one.count }));
}

export function FilterBar<T>({
  rows,
  choice,
  onChange,
  artistsOf,
  tagsOf,
}: {
  rows: readonly T[];
  choice: FilterChoice;
  onChange: (change: { artist?: string | null; tag?: [string, string | null] }) => void;
  artistsOf: (row: T) => string[];
  tagsOf: (row: T) => TagRow[];
}) {
  // Each dropdown counts within what the other choices leave, so a count is what a click would show.
  const artistOptions = counted(
    filtered(rows, { ...choice, artist: null }, artistsOf, tagsOf).flatMap((row) => [...new Set(artistsOf(row))]),
  );
  const keys = TAG_KEYS.filter((key) => choice.tags[key] !== undefined || rows.some((row) => tagsOf(row).some((tag) => tag.category === key)));
  return (
    <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, alignItems: "center" }} data-testid="filter-bar">
      {artistOptions.length > 0 || choice.artist !== null ? (
        <FilterChip
          data-testid="filter-artist"
          label="Artist"
          anyLabel="Any artist"
          options={artistOptions}
          value={choice.artist}
          onChange={(value) => onChange({ artist: value })}
        />
      ) : null}
      {keys.map((key) => {
        const { [key]: _mine, ...others } = choice.tags;
        void _mine;
        const options = counted(
          filtered(rows, { ...choice, tags: others }, artistsOf, tagsOf).flatMap((row) =>
            [...new Set(tagsOf(row).filter((tag) => tag.category === key).map((tag) => tag.value))],
          ),
        );
        return (
          <FilterChip
            key={key}
            data-testid={`filter-${key}`}
            label={tagKeyLabel(key)}
            anyLabel={`Any ${tagKeyLabel(key).toLocaleLowerCase()}`}
            options={options}
            value={choice.tags[key] ?? null}
            onChange={(value) => onChange({ tag: [key, value] })}
          />
        );
      })}
    </Stack>
  );
}

export default FilterBar;
