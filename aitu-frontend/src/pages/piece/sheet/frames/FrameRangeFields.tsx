/**
 * The frames of a marked stretch in its toolbox (implementation 04-3, Phase 2b): "From frame [283] to frame [495]",
 * the frame numbers of its first and last columns as the sheet prints them. Both are fields: new numbers, then
 * Enter or leaving both fields (going from one to the other applies nothing), mark the columns from one frame to the
 * other (`rangeOfFrames`); Escape puts the numbers of the stretch back.
 */

import { useRef, useState, type FocusEvent, type KeyboardEvent } from "react";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { framesOfRange, rangeOfFrames } from "./readingTools";

type Range = { start: number; end: number };

export function FrameRangeFields({
  range,
  columns,
  onFrames,
}: {
  range: Range;
  /** The drawn columns of the sheet, in time order. */
  columns: readonly { frame: number }[];
  /** Mark another stretch (`end` excluded, as the strip marks it). */
  onFrames: (next: Range) => void;
}) {
  const key = `${range.start}:${range.end}`;
  const group = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<{ key: string; from: string; to: string } | null>(null);
  const shown = framesOfRange(range, columns);
  const from = draft?.key === key ? draft.from : String(shown.first);
  const to = draft?.key === key ? draft.to : String(shown.last);
  const edit = (field: "from" | "to", value: string) =>
    setDraft({ key, from, to, [field]: value.replace(/[^0-9]/g, "") });
  const commit = () => {
    if (draft?.key !== key) return;
    setDraft(null);
    const next = rangeOfFrames(Number(draft.from), Number(draft.to), columns);
    if (next && (next.start !== range.start || next.end !== range.end)) onFrames(next);
  };
  const onKey = (event: KeyboardEvent) => {
    if (event.key === "Enter") commit();
    if (event.key === "Escape") {
      event.stopPropagation();
      setDraft(null);
    }
  };
  const field = (name: "from" | "to", value: string) => (
    <TextField
      size="small"
      value={value}
      onChange={(event) => edit(name, event.target.value)}
      onBlur={(event: FocusEvent) => {
        if (!group.current?.contains(event.relatedTarget as Node | null)) commit();
      }}
      onKeyDown={onKey}
      slotProps={{ htmlInput: { inputMode: "numeric", "aria-label": name === "from" ? "First frame" : "Last frame", [`data-range-${name}`]: "" } }}
      sx={{ width: 76, "& input": { py: 0.5, px: 1, fontWeight: 600, fontVariantNumeric: "tabular-nums" } }}
    />
  );
  return (
    <Stack ref={group} direction="row" spacing={0.75} sx={{ alignItems: "center" }} data-range-frames>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        From frame
      </Typography>
      {field("from", from)}
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        to frame
      </Typography>
      {field("to", to)}
    </Stack>
  );
}

export default FrameRangeFields;
