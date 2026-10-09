/**
 * The **Lyrics** tab of the sheet toolbox (plan section 11.5).
 *
 * A piece of the pool is edited in place by clicking it: each line of its words then becomes a
 * piece of its own, in the same place, so a line break splits it.
 *
 * Paste the lyrics and **Save lyrics**: they are kept with the part and the field opens with them
 * every time. **Add to the pool** makes each line a **lyrics piece** in the **pool**. A piece is dragged from
 * the pool and dropped on the sheet, where it snaps to the frame under it; on the sheet it is
 * moved (it snaps again) and its right edge pulled to the frame it should end on. While this tab
 * is open a click on a piece picks it (Command-click adds one), and marking a stretch above the
 * staves picks every piece over it. The picked pieces have the edit toolbar: merge, split, line
 * break, smaller and larger, back to the pool, delete. Every action is one undo step.
 */

import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArchiveIcon from "@mui/icons-material/ArchiveOutlined";
import CallMergeIcon from "@mui/icons-material/CallMergeOutlined";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import KeyboardReturnIcon from "@mui/icons-material/KeyboardReturnOutlined";
import TextDecreaseIcon from "@mui/icons-material/TextDecrease";
import TextIncreaseIcon from "@mui/icons-material/TextIncrease";
import type { LyricLine } from "../../../api";
import { IconAction, PillButton } from "../../../ui";
import {
  backToPool,
  breakLine,
  editPoolPiece,
  mergePieces,
  piecesFromText,
  resizePieces,
  splitPiece,
  type Outcome,
} from "./lyricsPieces";

/** What a drag from the pool carries: the place of the piece in the pool. */
export const POOL_DRAG_TYPE = "application/x-aitu-lyrics-piece";

export function LyricsTab({
  lyrics,
  pool,
  picked,
  setLyrics,
  setPool,
  setPicked,
  onRefused,
  pasted,
  setPasted,
  savedText,
  savingText,
  onSaveText,
}: {
  lyrics: readonly LyricLine[];
  pool: readonly string[];
  /** The picked pieces, by their first frame. */
  picked: readonly number[];
  setLyrics: Dispatch<SetStateAction<readonly LyricLine[]>>;
  setPool: Dispatch<SetStateAction<readonly string[]>>;
  setPicked: Dispatch<SetStateAction<readonly number[]>>;
  onRefused: (why: string) => void;
  /** What is in the lyrics field; held by the page, so a draft outlives a change of tab. */
  pasted: string;
  setPasted: (text: string) => void;
  /** The lyrics saved with the part, or `null` when none are. */
  savedText: string | null;
  savingText: boolean;
  onSaveText: (text: string) => void;
}) {
  const unsavedText = pasted.trim() !== (savedText ?? "").trim();
  const [draft, setDraft] = useState<{ forFrom: number; text: string } | null>(null);
  /** The piece of the pool whose words are being edited, and what they are now. */
  const [poolEdit, setPoolEdit] = useState<{ index: number; text: string } | null>(null);
  const commitPoolEdit = () => {
    if (!poolEdit) return;
    const { index, text } = poolEdit;
    setPoolEdit(null);
    if (text === pool[index]) return;
    setPool((current) => editPoolPiece(current, index, text));
  };
  const field = useRef<HTMLTextAreaElement | null>(null);

  const chosen = lyrics.filter((line) => picked.includes(line.fromColumn));
  const only = chosen.length === 1 ? chosen[0]! : null;
  const words = only ? (draft?.forFrom === only.fromColumn ? draft.text : only.text) : "";

  const apply = (outcome: Outcome<LyricLine[]>, nextPicked?: number[]) => {
    if ("refused" in outcome) {
      onRefused(outcome.refused);
      return;
    }
    setLyrics(outcome.ok);
    setDraft(null);
    if (nextPicked) setPicked(nextPicked);
  };

  /** The piece with the words typed into the field, so a split or a break uses what is on screen. */
  const withWords = (): readonly LyricLine[] =>
    only && words !== only.text
      ? lyrics.map((line) => (line === only ? { ...line, text: words } : line))
      : lyrics;

  const commitWords = () => {
    if (!only || draft?.forFrom !== only.fromColumn) return;
    const text = draft.text.trim();
    setDraft(null);
    if (text.length === 0 || text === only.text) return;
    setLyrics((current) => current.map((line) => (line === only ? { ...line, text } : line)));
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
    setLyrics((current) => current.map((line) => (line === only ? { ...line, text } : line)));
  };

  return (
    <Stack spacing={1.5} data-lyrics-tab>
      <Stack spacing={1}>
        <TextField
          size="small"
          label="Paste the lyrics"
          multiline
          minRows={2}
          maxRows={6}
          value={pasted}
          onChange={(event) => setPasted(event.target.value)}
          slotProps={{ htmlInput: { "data-lyrics-paste": true } }}
        />
        <Stack direction="row" spacing={1}>
          <PillButton
            kind={unsavedText ? "primary" : "secondary"}
            size="small"
            disabled={!unsavedText}
            busy={savingText}
            onClick={() => onSaveText(pasted)}
            data-lyrics-save
          >
            {unsavedText || savedText === null ? "Save lyrics" : "Lyrics saved"}
          </PillButton>
          <PillButton
            size="small"
            disabled={piecesFromText(pasted).length === 0}
            onClick={() => {
              const pieces = piecesFromText(pasted);
              setPool((current) => [...current, ...pieces]);
            }}
            data-lyrics-add
          >
            Add to the pool
          </PillButton>
        </Stack>
      </Stack>

      {pool.length > 0 ? (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
            Pool ({pool.length})
          </Typography>
          <Stack
            spacing={0.5}
            sx={{ maxHeight: 220, overflowY: "auto", pr: 0.5 }}
            data-lyrics-pool={pool.length}
          >
            {pool.map((text, index) =>
              poolEdit?.index === index ? (
                <TextField
                  key={`${index}:editing`}
                  size="small"
                  multiline
                  autoFocus
                  value={poolEdit.text}
                  onChange={(event) => setPoolEdit({ index, text: event.target.value })}
                  onBlur={commitPoolEdit}
                  onKeyDown={(event) => {
                    // Enter makes a new line (a new piece); Command-Enter or leaving the field keeps
                    // the change, Escape drops it.
                    if (event.key === "Escape") {
                      event.stopPropagation();
                      setPoolEdit(null);
                    } else if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                      event.preventDefault();
                      commitPoolEdit();
                    }
                  }}
                  slotProps={{
                    htmlInput: {
                      "aria-label": "Words of this piece; a new line makes a new piece",
                      "data-lyrics-pool-edit": index,
                    },
                  }}
                />
              ) : (
                <Chip
                  // Two pieces may have the same words, so the place is part of the key.
                  key={`${index}:${text}`}
                  label={text}
                  title={`${text} — drag onto the sheet, or click to edit`}
                  onClick={() => setPoolEdit({ index, text })}
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.setData(POOL_DRAG_TYPE, String(index));
                    event.dataTransfer.effectAllowed = "move";
                  }}
                  onDelete={() => setPool((current) => current.filter((_, at) => at !== index))}
                  sx={{
                    justifyContent: "space-between",
                    cursor: "grab",
                    borderRadius: 2,
                    "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" },
                  }}
                  data-lyrics-piece={index}
                />
              ),
            )}
          </Stack>
        </Box>
      ) : null}

      {chosen.length > 0 ? (
        <Stack spacing={1} data-lyrics-picked={chosen.length}>
          <Typography variant="body2" color="text.secondary">
            {chosen.length === 1 ? "1 piece picked" : `${chosen.length} pieces picked`}
          </Typography>
          {only ? (
            <TextField
              size="small"
              label="Words"
              multiline
              maxRows={4}
              value={words}
              inputRef={field}
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
          <Stack direction="row" spacing={0.25} sx={{ flexWrap: "wrap" }}>
            <IconAction
              title="Merge the picked pieces into one"
              disabledTitle="Pick two or more pieces to merge"
              icon={<CallMergeIcon fontSize="small" />}
              disabled={chosen.length < 2}
              onClick={() => apply(mergePieces(lyrics, picked), [chosen[0]!.fromColumn])}
              data-testid="lyrics-merge"
            />
            <IconAction
              title="Split the piece where the cursor is"
              shortcut="Enter"
              disabledTitle="Pick one piece to split it"
              icon={<ContentCutIcon fontSize="small" />}
              disabled={!only}
              onClick={split}
              data-testid="lyrics-split"
            />
            <IconAction
              title="New line where the cursor is"
              disabledTitle="Pick one piece"
              icon={<KeyboardReturnIcon fontSize="small" />}
              disabled={!only}
              onClick={lineBreak}
              data-testid="lyrics-break"
            />
            <IconAction
              title="Smaller"
              icon={<TextDecreaseIcon fontSize="small" />}
              onClick={() => setLyrics((current) => resizePieces(current, picked, -1))}
              data-testid="lyrics-smaller"
            />
            <IconAction
              title="Larger"
              icon={<TextIncreaseIcon fontSize="small" />}
              onClick={() => setLyrics((current) => resizePieces(current, picked, 1))}
              data-testid="lyrics-larger"
            />
            <IconAction
              title="Back to the pool"
              icon={<ArchiveIcon fontSize="small" />}
              onClick={() => {
                const next = backToPool(lyrics, pool, picked);
                setLyrics(next.lyrics);
                setPool(next.pool);
                setPicked([]);
                setDraft(null);
              }}
              data-testid="lyrics-pool"
            />
            <IconAction
              title="Delete the picked pieces"
              icon={<DeleteOutlineIcon fontSize="small" />}
              danger
              onClick={() => {
                setLyrics((current) => current.filter((line) => !picked.includes(line.fromColumn)));
                setPicked([]);
                setDraft(null);
              }}
              data-testid="lyrics-delete"
            />
          </Stack>
        </Stack>
      ) : null}
    </Stack>
  );
}

export default LyricsTab;
