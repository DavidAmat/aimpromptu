/**
 * The range toolbox of the new sheet (implementation 03, Phase 7): what a marked stretch of frames can carry, as the
 * old range toolbox, on the edit model of the new sheet (each change written at once, one step of undo).
 *
 * The first line names the frame numbers of the stretch's first and last columns (implementation 04-3, Phase 2b), as
 * the sheet prints them; the title bar is too full for them (the line under the title has the times).
 *
 * The first row says which staff the stretch is about (**Both / Right / Left**): the highlight on the sheet shrinks
 * to that staff, and **Clef** and **Octave** act on that hand alone. Then one tab per thing a stretch carries, a dot
 * on the tab when this stretch already carries it:
 *
 * - **Key**: the armadura of the stretch, drawn on both clefs (✓), or the armadura of the piece again (🗑). When
 *   another armadura prints fewer signs over the stretch, a button names it ("Use D major here").
 * - **Clef**: the clef of each hand in scope over the stretch, then its own clef again after it; **Clefs by the rule**
 *   writes the clefs and 8va the clef rules give the stretch.
 * - **Octave**: an octave line over each hand in scope (8va, 15ma, 8vb, 15mb), pressed again or 🗑 to remove it. A
 *   bass clef takes no 8va or 15ma.
 *
 * The spacing of a stretch, its speed and the hidden or dragged octave lines of the old sheet are not here: the user
 * dropped them (Phase 7). The title bar hands the stretch to the note toolbox (*Select the notes in this stretch*)
 * and asks the AI to write the stretch again with the user's words; Phase 8B adds the old title bar's actions:
 * **Record this passage**, **Start a new part here** (the parts of a project) and **Copy this stretch**.
 */

import { useEffect, useState } from "react";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CallSplitIcon from "@mui/icons-material/CallSplitOutlined";
import CheckIcon from "@mui/icons-material/Check";
import ContentCopyIcon from "@mui/icons-material/ContentCopyOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecordOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import { sheetApi, type ReadingEdit, type SheetNote, type SheetReading, type StretchKeys } from "../../../../api";
import { IconAction, Logo, PillButton, Segmented, Toolbox } from "../../../../ui";
import { formatSeconds } from "../sheetConstants";
import { ARMADURAS, frameOf, framesLabel, keyName } from "./readingTools";

export type RangeHand = "both" | "right" | "left";
type Hand = SheetNote["hand"];
type Tab = "key" | "clef" | "octave";

const TABS: { id: Tab; label: string }[] = [
  { id: "key", label: "Key" },
  { id: "clef", label: "Clef" },
  { id: "octave", label: "Octave" },
];

const HAND_OPTIONS = [
  { value: "both" as const, label: "Both", tooltip: "Both staves" },
  { value: "right" as const, label: "Right", tooltip: "The right hand's staff only" },
  { value: "left" as const, label: "Left", tooltip: "The left hand's staff only" },
];

const OWN_CLEF: Record<Hand, string> = { right: "treble", left: "bass" };

const CLEFS = [
  { clef: "treble", label: "Treble", hint: "the G clef, where the right hand normally reads" },
  { clef: "bass", label: "Bass", hint: "the F clef, where the left hand normally reads" },
];

const OTTAVAS = [
  { value: 1, label: "8va", hint: "written an octave lower than it sounds" },
  { value: 2, label: "15ma", hint: "written two octaves lower than it sounds" },
  { value: -1, label: "8vb", hint: "written an octave higher than it sounds" },
  { value: -2, label: "15mb", hint: "written two octaves higher than it sounds" },
];

/** The armadura in force at `frame`. */
function keyAt(reading: SheetReading, frame: number): number {
  let key = reading.key;
  for (const [at, value] of reading.keyChanges) if (at <= frame) key = value;
  return key;
}

/** The clef of a hand in force at `frame`. */
function clefAt(reading: SheetReading, hand: Hand, frame: number): string {
  let clef = reading.clefs[hand] ?? OWN_CLEF[hand];
  for (const [at, side, value] of reading.clefChanges) if (side === hand && at <= frame) clef = value;
  return clef;
}

export function FramesRangeToolbox({
  audioUuid,
  range,
  columns,
  reading,
  notes,
  at,
  frameMs = 40,
  rangeHand,
  setRangeHand,
  onClose,
  onEdit,
  onSelectNotes,
  onEnhance,
  onCopy,
  onRecordPassage,
  onSplit,
  busy,
  locked,
}: {
  audioUuid: string;
  /** The stretch marked, in frames (`end` excluded). */
  range: { start: number; end: number } | null;
  /** The drawn columns of the sheet (their frames name the stretch in the title). */
  columns: readonly { frame: number }[];
  reading: SheetReading;
  notes: readonly SheetNote[];
  at: { x: number; y: number } | undefined;
  frameMs?: number;
  rangeHand: RangeHand;
  setRangeHand: (hand: RangeHand) => void;
  onClose: () => void;
  /** One reading edit on the stretch (the stretch is added by the page). */
  onEdit: (edit: Omit<ReadingEdit, "start" | "end">) => void;
  onSelectNotes: () => void;
  /** Ask the AI to write the stretch again (`null`: the AI cannot be asked here). */
  onEnhance: (() => void) | null;
  /** **Copy this stretch**: its notes, sheet and audio, for a Paste anywhere. */
  onCopy: () => void;
  /** **Record this passage**: the page of the stretch, to record it again (`null`: not here). */
  onRecordPassage: (() => void) | null;
  /** **Start a new part here** (the parts of a project; `null`: not here, or the stretch starts the part). */
  onSplit: (() => void) | null;
  busy: boolean;
  locked: string | null;
}) {
  const [tab, setTab] = useState<Tab>("key");
  const [draft, setDraft] = useState<{ forRange: string; fifths: number } | null>(null);
  const [hint, setHint] = useState<{ forRange: string; keys: StretchKeys } | null>(null);
  const rangeKey = range ? `${range.start}:${range.end}` : "";
  const off = busy || locked !== null;
  const why = locked ?? undefined;
  const hands: Hand[] = rangeHand === "both" ? ["right", "left"] : [rangeHand];

  // The armadura with the fewest signs over the stretch: asked once per stretch (and again after an edit of it).
  const keysNow = JSON.stringify(reading.keyChanges) + reading.key;
  useEffect(() => {
    if (!range) return;
    const controller = new AbortController();
    sheetApi
      .stretchKeys(audioUuid, range.start, range.end, controller.signal)
      .then((keys) => setHint({ forRange: `${range.start}:${range.end}`, keys }))
      .catch(() => undefined);
    return () => controller.abort();
  }, [audioUuid, range, keysNow]);
  const keys = hint?.forRange === rangeKey ? hint.keys : null;

  if (!range) return null;
  const inside = notes.filter((note) => {
    const frame = frameOf(note.ref);
    return frame >= range.start && frame < range.end;
  });
  const keyHere = keyAt(reading, range.start);
  const chosen = draft?.forRange === rangeKey ? draft.fifths : keyHere;
  const ottavaOf = (hand: Hand) => {
    const mine = inside.filter((note) => note.hand === hand);
    const values = new Set(mine.map((note) => note.ottava));
    return mine.length > 0 && values.size === 1 ? [...values][0]! : null;
  };
  const edited: Record<Tab, boolean> = {
    key:
      keyHere !== reading.key || reading.keyChanges.some(([frame]) => frame > range.start && frame < range.end),
    clef:
      hands.some((hand) => clefAt(reading, hand, range.start) !== OWN_CLEF[hand]) ||
      reading.clefChanges.some(([frame, side]) => hands.includes(side) && frame > range.start && frame < range.end),
    octave: inside.some((note) => hands.includes(note.hand) && note.ottava !== 0),
  };
  const time = (frame: number) => formatSeconds((frame * frameMs) / 1000);
  const better = keys && keys.fewest !== keys.key && keys.fewestSigns < keys.signs ? keys : null;

  return (
    <Toolbox
      open
      title="Frames"
      subtitle={`${time(range.start)} – ${time(range.end)}`}
      initialPosition={at ?? { x: 24, y: 140 }}
      onClose={onClose}
      headerAction={
        <>
          {onRecordPassage ? (
            <IconAction
              title="Record this passage"
              icon={<FiberManualRecordIcon fontSize="small" />}
              onClick={onRecordPassage}
              disabled={off}
              disabledTitle={why}
              data-testid="range-record"
            />
          ) : null}
          {onSplit ? (
            <IconAction
              title="Start a new part here"
              icon={<CallSplitIcon fontSize="small" />}
              onClick={onSplit}
              disabled={off}
              disabledTitle={why}
              data-testid="range-split"
            />
          ) : null}
          <IconAction
            title="Copy this stretch"
            shortcut="⌘C"
            icon={<ContentCopyIcon fontSize="small" />}
            onClick={onCopy}
            data-testid="range-copy"
          />
          {onEnhance ? (
            <IconAction
              title="Enhance this stretch with AI, with your own words"
              icon={<Logo height={20} />}
              onClick={onEnhance}
              disabled={off || inside.length === 0}
              disabledTitle={why ?? "No notes begin inside this stretch"}
              data-testid="range-enhance"
            />
          ) : null}
          <IconAction
            title={`Select the ${inside.filter((note) => hands.includes(note.hand)).length} notes in this stretch`}
            disabledTitle="No notes begin inside this stretch on this staff"
            icon={<SwapHorizIcon fontSize="small" />}
            disabled={!inside.some((note) => hands.includes(note.hand))}
            onClick={onSelectNotes}
            data-testid="range-to-notes"
          />
        </>
      }
    >
      <Stack spacing={1.5} data-frames-range-toolbox>
        <Typography variant="body2" sx={{ fontWeight: 600 }} data-range-frames>
          {framesLabel(range, columns)}
        </Typography>
        <Segmented<RangeHand> label="Which staff" value={rangeHand} options={HAND_OPTIONS} onChange={setRangeHand} />

        <Box role="tablist" aria-label="What this stretch carries" sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 0.75 }}>
          {TABS.map((one) => (
            <Badge
              key={one.id}
              color="warning"
              variant="dot"
              invisible={!edited[one.id]}
              sx={{ display: "block", "& .MuiBadge-badge": { right: 6, top: 6 } }}
            >
              <Chip
                size="small"
                role="tab"
                aria-selected={tab === one.id}
                label={one.label}
                onClick={() => setTab(one.id)}
                color={tab === one.id ? "primary" : "default"}
                variant={tab === one.id ? "filled" : "outlined"}
                sx={{ width: "100%" }}
                data-edited={edited[one.id] ? "yes" : "no"}
                data-tab={one.id}
              />
            </Badge>
          ))}
        </Box>

        {tab === "key" ? (
          <Stack spacing={1}>
            {better ? (
              <Box>
                <PillButton
                  size="small"
                  disabled={off}
                  onClick={() => onEdit({ action: "key", value: better.fewest })}
                  data-passage-key={better.fewest}
                >
                  Use {keyName(better.fewest)} here ({better.signs - better.fewestSigns} fewer signs)
                </PillButton>
              </Box>
            ) : null}
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <TextField
                select
                size="small"
                label="Key"
                value={chosen}
                onChange={(event) => setDraft({ forRange: rangeKey, fifths: Number(event.target.value) })}
                sx={{ flex: 1 }}
                data-testid="range-key"
              >
                {ARMADURAS.map((one) => (
                  <MenuItem key={one.fifths} value={one.fifths}>
                    {one.label}
                  </MenuItem>
                ))}
              </TextField>
              <IconAction
                title="Use this key here"
                icon={<CheckIcon fontSize="small" />}
                disabled={off || chosen === keyHere}
                disabledTitle={why}
                onClick={() => onEdit({ action: "key", value: chosen })}
                data-testid="range-key-apply"
              />
              <IconAction
                title="Back to the key of the piece"
                icon={<DeleteOutlineIcon fontSize="small" />}
                danger
                disabled={off || !edited.key}
                disabledTitle={why}
                onClick={() => onEdit({ action: "key", value: null })}
              />
            </Stack>
          </Stack>
        ) : null}

        {tab === "clef" ? (
          <Stack spacing={1}>
            {hands.map((hand) => {
              const active = clefAt(reading, hand, range.start);
              return (
                <Stack key={hand} direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                  {hands.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 40 }}>
                      {hand === "left" ? "Left" : "Right"}
                    </Typography>
                  ) : null}
                  {CLEFS.map((choice) => (
                    <Tooltip key={choice.clef} title={locked ?? choice.hint}>
                      <Chip
                        size="small"
                        label={choice.label}
                        disabled={off}
                        color={active === choice.clef ? "primary" : "default"}
                        variant={active === choice.clef ? "filled" : "outlined"}
                        onClick={() => onEdit({ action: "clef", staff: hand, value: choice.clef })}
                        data-clef={`${hand}:${choice.clef}`}
                      />
                    </Tooltip>
                  ))}
                  <IconAction
                    title="Back to this hand's own clef"
                    icon={<DeleteOutlineIcon fontSize="small" />}
                    danger
                    disabled={off || (active === OWN_CLEF[hand] && !edited.clef)}
                    disabledTitle={why}
                    onClick={() => onEdit({ action: "clef", staff: hand, value: null })}
                  />
                </Stack>
              );
            })}
            <Box>
              <PillButton size="small" kind="quiet" disabled={off} onClick={() => onEdit({ action: "clef-rule", staff: rangeHand })} data-testid="clef-rule">
                Clefs by the rule
              </PillButton>
            </Box>
          </Stack>
        ) : null}

        {tab === "octave" ? (
          <Stack spacing={1}>
            {hands.map((hand) => {
              const active = ottavaOf(hand);
              const bass = inside.some((note) => note.hand === hand && clefAt(reading, hand, frameOf(note.ref)) === "bass");
              const plays = inside.some((note) => note.hand === hand);
              return (
                <Stack key={hand} direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                  {hands.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 40 }}>
                      {hand === "left" ? "Left" : "Right"}
                    </Typography>
                  ) : null}
                  {OTTAVAS.map((choice) => {
                    const refused = !plays
                      ? `The ${hand} hand plays nothing in this stretch`
                      : choice.value > 0 && bass
                        ? "A bass clef takes no 8va: write the stretch in the treble clef first"
                        : null;
                    return (
                      <Tooltip key={choice.value} title={locked ?? refused ?? choice.hint}>
                        <span>
                          <Chip
                            size="small"
                            label={choice.label}
                            disabled={off || refused !== null}
                            color={active === choice.value ? "primary" : "default"}
                            variant={active === choice.value ? "filled" : "outlined"}
                            onClick={() =>
                              onEdit({ action: "ottava", staff: hand, value: active === choice.value ? 0 : choice.value })
                            }
                            data-ottava={`${hand}:${choice.label}`}
                          />
                        </span>
                      </Tooltip>
                    );
                  })}
                  <IconAction
                    title="Remove the octave line"
                    icon={<DeleteOutlineIcon fontSize="small" />}
                    danger
                    disabled={off || !inside.some((note) => note.hand === hand && note.ottava !== 0)}
                    disabledTitle={why}
                    onClick={() => onEdit({ action: "ottava", staff: hand, value: 0 })}
                  />
                </Stack>
              );
            })}
          </Stack>
        ) : null}
      </Stack>
    </Toolbox>
  );
}

export default FramesRangeToolbox;
