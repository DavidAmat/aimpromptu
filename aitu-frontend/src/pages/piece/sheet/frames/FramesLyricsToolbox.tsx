/**
 * The lyrics toolbox of the new sheet (implementation 03, Phase 8A++, the user's request of 2026-10-26): what can be
 * said about the lyrics pieces picked on the sheet. It opens beside them when a piece is clicked; every control
 * writes at once and is one step of undo, and the sheet comes back drawn again.
 *
 * - **Words** (one piece picked): typed in place; Enter splits the piece where the cursor is.
 * - **Font**: Lora, Geist or Montserrat, each name written in its own font. The PDF prints Lora as Times and the
 *   other two as Helvetica.
 * - **Size**: the size of the words (the corner handle of a block does the same on the sheet).
 * - **Normal, bold, italic**.
 * - **Back in the line of words**: a block moved or made narrower by hand goes back above its first frame, its words
 *   on one line again (its frames, size and style stay).
 * - The old toolbar's actions: merge, split, a new line, back to the pool, delete.
 *
 * Where a block sits and how wide it is are set on the sheet itself (drag the block, its side handle, its corner);
 * when its words sound, on the bar of its frames in the strip above the staves.
 */

import { useRef, useState } from "react";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Divider from "@mui/material/Divider";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArchiveIcon from "@mui/icons-material/ArchiveOutlined";
import CallMergeIcon from "@mui/icons-material/CallMergeOutlined";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import FormatBoldIcon from "@mui/icons-material/FormatBold";
import FormatItalicIcon from "@mui/icons-material/FormatItalic";
import KeyboardReturnIcon from "@mui/icons-material/KeyboardReturnOutlined";
import VerticalAlignBottomIcon from "@mui/icons-material/VerticalAlignBottom";
import type { LyricFont, LyricLine } from "../../../../api";
import { IconAction, Toolbox } from "../../../../ui";
import { backToPool, breakLine, mergePieces, splitPiece, type Outcome } from "../lyricsPieces";
import { formatSeconds } from "../sheetConstants";
import { LYRIC_FONTS, LYRIC_MAX, LYRIC_MIN, LYRIC_SIZE } from "./lyricsText";
import type { BlockChange } from "./useFramesLyrics";

/** A row of the toolbox: a short label, then its controls (as the note toolbox). */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 52 }}>
        {label}
      </Typography>
      {children}
    </Stack>
  );
}

export function FramesLyricsToolbox({
  lines,
  pool,
  picked,
  at,
  frameMs = 40,
  sizeOf,
  onClose,
  setLines,
  setPool,
  setPicked,
  onShape,
  onRefused,
  busy,
  locked,
}: {
  lines: readonly LyricLine[];
  pool: readonly string[];
  /** The picked pieces, by their first frame. */
  picked: readonly number[];
  /** Where the panel opens, beside the pieces. */
  at: { x: number; y: number } | undefined;
  frameMs?: number;
  /** The size of a piece's words now, in staff spaces. */
  sizeOf: (start: number) => number;
  onClose: () => void;
  setLines: (next: readonly LyricLine[]) => void;
  setPool: (next: readonly string[]) => void;
  setPicked: (next: readonly number[]) => void;
  /** The picked blocks told something (their place, width, size or style), as one step named `label`. */
  onShape: (change: BlockChange, label: string) => void;
  onRefused: (why: string) => void;
  busy: boolean;
  locked: string | null;
}) {
  const chosen = lines.filter((line) => picked.includes(line.fromColumn));
  const only = chosen.length === 1 ? chosen[0]! : null;
  const first = chosen[0];
  const [draft, setDraft] = useState<{ forFrom: number; text: string } | null>(null);
  const field = useRef<HTMLTextAreaElement | null>(null);
  const words = only ? (draft?.forFrom === only.fromColumn ? draft.text : only.text) : "";
  const off = busy || locked !== null;
  const why = locked ?? undefined;

  const font: LyricFont = first?.block?.font ?? "lora";
  const bold = first?.block?.bold ?? false;
  const italic = first?.block?.italic ?? true;
  const size = first ? sizeOf(first.fromColumn) : LYRIC_SIZE;
  const [sizing, setSizing] = useState<{ forFrom: number; size: number } | null>(null);
  const sizeShown = sizing && sizing.forFrom === first?.fromColumn ? sizing.size : size;
  const shaped = chosen.some((line) => line.block?.dy != null || line.block?.width != null);
  const time = (frame: number) => formatSeconds((frame * frameMs) / 1000);

  const apply = (outcome: Outcome<LyricLine[]>, nextPicked?: number[]) => {
    if ("refused" in outcome) {
      onRefused(outcome.refused);
      return;
    }
    setLines(outcome.ok);
    setDraft(null);
    if (nextPicked) setPicked(nextPicked);
  };
  /** The piece with the words typed into the field, so a split or a break uses what is on screen. */
  const withWords = (): readonly LyricLine[] =>
    only && words !== only.text ? lines.map((line) => (line === only ? { ...line, text: words } : line)) : lines;
  const commitWords = () => {
    if (!only || draft?.forFrom !== only.fromColumn) return;
    const text = draft.text.trim();
    setDraft(null);
    if (text.length === 0 || text === only.text) return;
    setLines(lines.map((line) => (line === only ? { ...line, text } : line)));
  };
  const split = () => {
    if (!only) return;
    const caret = field.current?.selectionStart ?? Math.floor(words.length / 2);
    apply(splitPiece(withWords(), only.fromColumn, caret), [only.fromColumn]);
  };
  const lineBreak = () => {
    if (!only) return;
    const caret = field.current?.selectionStart ?? words.length;
    const text = breakLine(words, caret);
    setDraft(null);
    setLines(lines.map((line) => (line === only ? { ...line, text } : line)));
  };
  const pieces = chosen.length === 1 ? "this piece" : "these pieces";

  return (
    <Toolbox
      open={chosen.length > 0}
      title={chosen.length === 1 ? "Lyrics piece" : `${chosen.length} lyrics pieces`}
      subtitle={first ? `${time(first.fromColumn)} – ${time(chosen[chosen.length - 1]!.toColumn)}` : undefined}
      initialPosition={at ?? { x: 420, y: 140 }}
      onClose={onClose}
    >
      <Stack spacing={1.25} data-frames-lyrics-toolbox>
        {only ? (
          <TextField
            size="small"
            label="Words"
            multiline
            maxRows={4}
            value={words}
            inputRef={field}
            disabled={off}
            onChange={(event) => setDraft({ forFrom: only.fromColumn, text: event.target.value })}
            onBlur={commitWords}
            onKeyDown={(event) => {
              // Enter splits the piece where the cursor is; a line break is its own button.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                split();
              }
            }}
            slotProps={{ htmlInput: { "data-lyrics-words": true } }}
          />
        ) : null}

        <Row label="Font">
          <ButtonGroup size="small" disabled={off}>
            {LYRIC_FONTS.map((one) => (
              <Button
                key={one.value}
                variant={font === one.value ? "contained" : "outlined"}
                onClick={() => onShape({ font: one.value }, `Font of ${pieces}: ${one.label}`)}
                sx={{ fontFamily: one.family, textTransform: "none", px: 1 }}
                data-lyric-font={one.value}
              >
                {one.label}
              </Button>
            ))}
          </ButtonGroup>
        </Row>

        <Row label="Size">
          <Slider
            size="small"
            min={LYRIC_MIN}
            max={LYRIC_MAX}
            step={0.1}
            value={sizeShown}
            disabled={off}
            onChange={(_, value) => first && setSizing({ forFrom: first.fromColumn, size: value as number })}
            onChangeCommitted={(_, value) => {
              setSizing(null);
              onShape({ size: value as number }, `Size of ${pieces}`);
            }}
            valueLabelDisplay="auto"
            sx={{ flex: 1, mx: 1, minWidth: 100 }}
            slotProps={{ input: { "aria-label": "Size of the words", "data-lyric-size": true } as object }}
          />
        </Row>

        <Row label="Style">
          <ButtonGroup size="small" disabled={off}>
            <Button
              variant={!bold && !italic ? "contained" : "outlined"}
              onClick={() => onShape({ bold: false, italic: false }, `Normal words for ${pieces}`)}
              sx={{ textTransform: "none", px: 1 }}
              data-lyric-style="normal"
            >
              Normal
            </Button>
          </ButtonGroup>
          <IconAction
            title={bold ? "Not bold" : "Bold"}
            icon={<FormatBoldIcon fontSize="small" />}
            active={bold}
            disabled={off}
            disabledTitle={why}
            onClick={() => onShape({ bold: !bold }, bold ? `Not bold: ${pieces}` : `Bold: ${pieces}`)}
            data-testid="lyric-bold"
          />
          <IconAction
            title={italic ? "Not italic" : "Italic"}
            icon={<FormatItalicIcon fontSize="small" />}
            active={italic}
            disabled={off}
            disabledTitle={why}
            onClick={() => onShape({ italic: !italic }, italic ? `Not italic: ${pieces}` : `Italic: ${pieces}`)}
            data-testid="lyric-italic"
          />
        </Row>

        <Divider />

        <Stack direction="row" spacing={0.25} sx={{ flexWrap: "wrap", alignItems: "center" }}>
          <IconAction
            title="Back in the line of words, on one line"
            disabledTitle={why ?? "Not moved or made narrower by hand"}
            icon={<VerticalAlignBottomIcon fontSize="small" />}
            disabled={off || !shaped}
            onClick={() => onShape({ at: null, dx: 0, dy: null, width: null }, `Back in the line of words: ${pieces}`)}
            data-testid="lyric-back-in-line"
          />
          <IconAction
            title="Merge the picked pieces into one"
            disabledTitle={why ?? "Pick two or more pieces to merge"}
            icon={<CallMergeIcon fontSize="small" />}
            disabled={off || chosen.length < 2}
            onClick={() => apply(mergePieces(lines, picked), [chosen[0]!.fromColumn])}
            data-testid="lyrics-merge"
          />
          <IconAction
            title="Split the piece where the cursor is"
            shortcut="Enter"
            disabledTitle={why ?? "Pick one piece to split it"}
            icon={<ContentCutIcon fontSize="small" />}
            disabled={off || !only}
            onClick={split}
            data-testid="lyrics-split"
          />
          <IconAction
            title="New line where the cursor is"
            disabledTitle={why ?? "Pick one piece"}
            icon={<KeyboardReturnIcon fontSize="small" />}
            disabled={off || !only}
            onClick={lineBreak}
            data-testid="lyrics-break"
          />
          <IconAction
            title="Back to the pool"
            icon={<ArchiveIcon fontSize="small" />}
            disabled={off}
            disabledTitle={why}
            onClick={() => {
              const next = backToPool(lines, pool, picked);
              setLines(next.lyrics);
              setPool(next.pool);
              setPicked([]);
              setDraft(null);
            }}
            data-testid="lyrics-pool"
          />
          <IconAction
            title="Delete the picked pieces"
            shortcut="Delete"
            icon={<DeleteOutlineIcon fontSize="small" />}
            danger
            disabled={off}
            disabledTitle={why}
            onClick={() => {
              setLines(lines.filter((line) => !picked.includes(line.fromColumn)));
              setPicked([]);
              setDraft(null);
            }}
            data-testid="lyrics-delete"
          />
        </Stack>
      </Stack>
    </Toolbox>
  );
}

export default FramesLyricsToolbox;
