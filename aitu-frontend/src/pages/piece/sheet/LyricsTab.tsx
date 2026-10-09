/**
 * The **Lyrics** tab of the sheet toolbox (plan section 11.5).
 *
 * The box beside a pool piece's cross picks it; only consecutive pieces can be picked, and
 * **Merge**, beside the pool's title, joins them in the place of the first (the way back from a split
 * made by mistake).
 * A piece of the pool is edited in place by clicking it: Enter (or the scissors at the end of the
 * field) splits it where the cursor is into two pieces in the same place and closes the field.
 *
 * Paste the lyrics and **Save lyrics**: the words and the pool are kept with the part (any change of
 * either offers the button again) and the tab opens with them
 * every time. **Add to the pool** makes each line a **lyrics piece** in the **pool**. A piece is dragged from
 * the pool and dropped on the sheet, where it snaps to the frame under it; on the sheet it is
 * moved (it snaps again) and its right edge pulled to the frame it should end on. While this tab
 * is open a click on a piece picks it (Command-click adds one), and marking a stretch above the
 * staves picks every piece over it. The picked pieces have the edit toolbar: merge, split, line
 * break, smaller and larger, back to the pool, delete. Every action is one undo step.
 */

import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArchiveIcon from "@mui/icons-material/ArchiveOutlined";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckBoxIcon from "@mui/icons-material/CheckBox";
import CheckBoxOutlineBlankIcon from "@mui/icons-material/CheckBoxOutlineBlank";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
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
  mergePoolPieces,
  placedInPool,
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
  onPoolDrag,
  pasted,
  setPasted,
  savedText,
  poolUnsaved,
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
  /** A piece of the pool started (its place) or stopped (`null`) being dragged. */
  onPoolDrag: (index: number | null) => void;
  /** What is in the lyrics field; held by the page, so a draft outlives a change of tab. */
  pasted: string;
  setPasted: (text: string) => void;
  /** The lyrics saved with the part, or `null` when none are. */
  savedText: string | null;
  /** The pool is not the one saved. */
  poolUnsaved: boolean;
  savingText: boolean;
  onSaveText: (text: string) => void;
}) {
  /** The words or the pool are not the ones saved: **Save lyrics** saves both. */
  const unsavedText = pasted.trim() !== (savedText ?? "").trim() || poolUnsaved;
  const [draft, setDraft] = useState<{ forFrom: number; text: string } | null>(null);
  /** The piece of the pool whose words are being edited, and what they are now. */
  const [poolEdit, setPoolEdit] = useState<{ index: number; text: string } | null>(null);
  const poolInput = useRef<HTMLInputElement | null>(null);
  /**
   * Set once the field has been closed by a key or the split, so the blur its removal fires does
   * not keep the change a second time (or keep one that Escape dropped).
   */
  const poolEditClosed = useRef(false);
  /**
   * The pieces of the pool picked with Command-click, by place, for the pool they were picked in:
   * any change of the pool (an edit, a merge, a new piece) lets them go, so a place never names
   * another piece.
   */
  const [poolPicked, setPoolPicked] = useState<{ forPool: readonly string[]; at: number[] }>({
    forPool: pool,
    at: [],
  });
  const pickedInPool = poolPicked.forPool === pool ? poolPicked.at : [];
  /**
   * The picked pieces are always one run of consecutive pieces, because only those can be merged:
   * with nothing picked any piece can be; then only the piece just before or just after the run is
   * added, and only an end of the run is let go.
   */
  const pickLow = pickedInPool.length > 0 ? Math.min(...pickedInPool) : -1;
  const pickHigh = pickedInPool.length > 0 ? Math.max(...pickedInPool) : -1;
  const canTogglePick = (index: number) =>
    pickedInPool.length === 0 ||
    index === pickLow ||
    index === pickHigh ||
    index === pickLow - 1 ||
    index === pickHigh + 1;
  const togglePoolPick = (index: number) => {
    if (!canTogglePick(index)) return;
    setPoolPicked({
      forPool: pool,
      at: pickedInPool.includes(index)
        ? pickedInPool.filter((at) => at !== index)
        : [...pickedInPool, index],
    });
  };

  /** Keep `text` as the piece's words: each line a piece of its own, in the same place. */
  const commitPoolEdit = (text = poolEdit?.text) => {
    if (!poolEdit || poolEditClosed.current || text === undefined) return;
    poolEditClosed.current = true;
    const { index } = poolEdit;
    setPoolEdit(null);
    if (text === pool[index]) return;
    setPool((current) => editPoolPiece(current, index, text));
  };
  /** Split the piece where the cursor is: the words before it and the words after, two pieces. */
  const splitPoolEdit = () => {
    if (!poolEdit) return;
    const { text } = poolEdit;
    const caret = poolInput.current?.selectionStart ?? text.length;
    commitPoolEdit(`${text.slice(0, caret)}\n${text.slice(caret)}`);
  };
  const field = useRef<HTMLTextAreaElement | null>(null);

  const chosen = lyrics.filter((line) => picked.includes(line.fromColumn));
  /** Which pieces of the pool are on the sheet: they keep their place, with a green tick. */
  const placed = placedInPool(pool, lyrics);
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
            {unsavedText || (savedText === null && pool.length === 0) ? "Save lyrics" : "Lyrics saved"}
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
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 0.75, minHeight: 30 }}>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
              Pool ({pool.length}
              {placed.some(Boolean) ? `, ${placed.filter(Boolean).length} on the sheet` : ""})
            </Typography>
            {/* Joins the picked pieces; it needs two, next to each other. */}
            <PillButton
              kind={pickedInPool.length >= 2 ? "primary" : "secondary"}
              size="small"
              disabled={pickedInPool.length < 2}
              startIcon={<CallMergeIcon fontSize="small" />}
              title={
                pickedInPool.length < 2
                  ? "Tick the boxes of two or more pieces next to each other"
                  : `Join the ${pickedInPool.length} ticked pieces into one`
              }
              onClick={() => setPool((current) => mergePoolPieces(current, pickedInPool))}
              data-lyrics-pool-merge
            >
              Merge
            </PillButton>
          </Stack>
          <Stack
            spacing={0.5}
            sx={{ maxHeight: 260, overflowY: "auto", pr: 0.5 }}
            data-lyrics-pool={pool.length}
          >
            {pool.map((text, index) => {
              if (poolEdit?.index === index) {
                return (
                  <TextField
                    key={`${index}:editing`}
                    size="small"
                    autoFocus
                    value={poolEdit.text}
                    inputRef={poolInput}
                    onChange={(event) => setPoolEdit({ index, text: event.target.value })}
                    onBlur={() => commitPoolEdit()}
                    onKeyDown={(event) => {
                      // Enter splits where the cursor is and closes the field; leaving the field
                      // keeps the words as typed; Escape drops the change.
                      if (event.key === "Escape") {
                        event.stopPropagation();
                        poolEditClosed.current = true;
                        setPoolEdit(null);
                      } else if (event.key === "Enter") {
                        event.preventDefault();
                        splitPoolEdit();
                      }
                    }}
                    slotProps={{
                      htmlInput: {
                        "aria-label": "Words of this piece; Enter splits it where the cursor is",
                        "data-lyrics-pool-edit": index,
                      },
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            {/*
                              A press here would blur the field (and keep the words unsplit)
                              before the click; keeping the focus keeps the cursor where the split
                              goes.
                            */}
                            <span onMouseDown={(event) => event.preventDefault()}>
                              <IconAction
                                title="Split here"
                                shortcut="Enter"
                                icon={<ContentCutIcon fontSize="small" />}
                                onClick={splitPoolEdit}
                                data-testid="lyrics-pool-split"
                              />
                            </span>
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                );
              }
              const ticked = pickedInPool.includes(index);
              const free = canTogglePick(index);
              return (
                <Box
                  // Two pieces may have the same words, so the place is part of the key.
                  key={`${index}:${text}`}
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.setData(POOL_DRAG_TYPE, String(index));
                    event.dataTransfer.effectAllowed = "copy";
                    onPoolDrag(index);
                  }}
                  onDragEnd={() => onPoolDrag(null)}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    minHeight: 32,
                    pl: placed[index] ? 0.75 : 1.5,
                    pr: 0.25,
                    borderRadius: 4,
                    bgcolor: ticked ? "action.selected" : "action.hover",
                    outline: ticked ? 1 : 0,
                    outlineColor: "text.primary",
                    cursor: "grab",
                  }}
                  data-lyrics-piece={index}
                  data-placed={placed[index] ? "yes" : "no"}
                  data-pool-picked={ticked ? "yes" : "no"}
                >
                  {placed[index] ? (
                    <CheckCircleIcon
                      fontSize="small"
                      sx={{ color: "success.main" }}
                    />
                  ) : null}
                  <Typography
                    variant="body2"
                    noWrap
                    title={`${text}: ${placed[index] ? "on the sheet; drag to place it again" : "drag onto the sheet"}, or click to edit`}
                    onClick={() => {
                      poolEditClosed.current = false;
                      setPoolEdit({ index, text });
                    }}
                    sx={{ flex: 1, cursor: "text", py: 0.5 }}
                  >
                    {text}
                  </Typography>
                  <IconAction
                    title={ticked ? "Untick" : "Tick to merge it with the pieces next to it"}
                    disabledTitle={
                      ticked
                        ? "Untick the pieces at the ends first"
                        : "Only a piece next to the ticked ones can be merged with them"
                    }
                    icon={
                      ticked ? (
                        <CheckBoxIcon fontSize="small" />
                      ) : (
                        <CheckBoxOutlineBlankIcon fontSize="small" />
                      )
                    }
                    active={ticked}
                    disabled={!free}
                    onClick={() => togglePoolPick(index)}
                    placement="top"
                    data-testid={`lyrics-pool-pick-${index}`}
                  />
                  <IconAction
                    title="Remove from the pool"
                    icon={<CancelIcon fontSize="small" />}
                    onClick={() => setPool((current) => current.filter((_, at) => at !== index))}
                    placement="top"
                    data-testid={`lyrics-pool-remove-${index}`}
                  />
                </Box>
              );
            })}
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
