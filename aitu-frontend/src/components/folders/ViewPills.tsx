/** The three pills of My projects and My Library: **Folders**, **All**, **Filter** (see `listView.ts`). */

import Stack from "@mui/material/Stack";
import { Pill } from "../../ui";
import type { ListView } from "./listView";

const VIEWS: { value: ListView; label: string }[] = [
  { value: "folders", label: "Folders" },
  { value: "all", label: "All" },
  { value: "filter", label: "Filter" },
];

export function ViewPills({ value, onChange }: { value: ListView; onChange: (view: ListView) => void }) {
  return (
    <Stack direction="row" spacing={1} role="radiogroup" aria-label="View" data-testid="view-pills">
      {VIEWS.map((one) => (
        <span key={one.value} role="radio" aria-checked={value === one.value} data-testid={`view-${one.value}`}>
          <Pill label={one.label} selected={value === one.value} onClick={() => onChange(one.value)} />
        </span>
      ))}
    </Stack>
  );
}

export default ViewPills;
