/**
 * The range toolbox: what a marked stretch of frames can carry, one tab each (plan section 11.6).
 *
 * Key, clef and octave bracket of the stretch, its lyrics, its spacing, where the piece changes
 * speed, and Re-record. Each control is an icon action with a tooltip or a labelled field; what a
 * control does is said in its tooltip, not in a caption under it (the 09 guidelines). The tabs
 * carry a dot when this stretch already has that setting, so what was edited here shows before it
 * is opened.
 */

import { useState, type Dispatch, type SetStateAction } from "react";
import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import VisibilityIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffOutlined";
import {
  applyClefRange,
  applyKeySignatureRange,
  applyOttava,
  clearClefRange,
  clearKeySignatureRange,
  clearOttavaRange,
  clefAtFrame,
  LYRIC_FONT_SIZE,
  MAX_LYRIC_FONT_SIZE,
  MIN_LYRIC_FONT_SIZE,
  ottavaAtFrame,
  type KeySignature,
} from "@aimpromptu/grid-notation";
import {
  KEY_LABELS,
  KEY_SIGNATURES,
  type KeySignatureName,
  type TimeScorePayload,
} from "../../../api";
import RangeRerecordPanel from "../../../components/editing/RangeRerecordPanel";
import type { EditHistory } from "../../../hooks/useEditHistory";
import type { PrintedHand } from "../../../music/renderOverrides";
import { IconAction, PillButton, Segmented, Toolbox } from "../../../ui";
import {
  CLEF_CHOICES,
  DEFAULT_CLEF,
  formatSeconds,
  FRAME_TABS,
  OTTAVA_CHOICES,
  type FrameTab,
  type RangeHand,
} from "./sheetConstants";
import type { SheetEdits } from "./sheetEdits";
import type { FrameRange, RangeActions } from "./useRangeActions";

/** The slowest and the fastest a speed change goes, against the speed of the piece. */
const MIN_SPEED = 50;
const MAX_SPEED = 200;

const HAND_OPTIONS = [
  { value: "both" as const, label: "Both", tooltip: "Both staves" },
  { value: "right" as const, label: "Right", tooltip: "The right hand's staff only" },
  { value: "left" as const, label: "Left", tooltip: "The left hand's staff only" },
];

export function RangeToolbox({
  open: framesToolbox,
  range,
  setRange,
  frameMs,
  framesAt,
  onClose: closeFrames,
  onSelectNotes: selectNotesUnderRange,
  canSelectNotes,
  rangeHand,
  setRangeHand,
  frameTab,
  setFrameTab,
  rangeActions,
  setPassageDraft,
  setLyricDraft,
  score,
  state,
  set,
  setOttavaHidden,
  audioUuid,
  anchorMs,
  onRerecordAccepted,
}: {
  open: boolean;
  range: FrameRange | null;
  setRange: Dispatch<SetStateAction<FrameRange | null>>;
  frameMs: number;
  framesAt: { x: number; y: number } | undefined;
  onClose: () => void;
  onSelectNotes: () => void;
  canSelectNotes: boolean;
  rangeHand: RangeHand;
  setRangeHand: Dispatch<SetStateAction<RangeHand>>;
  frameTab: FrameTab;
  setFrameTab: Dispatch<SetStateAction<FrameTab>>;
  rangeActions: RangeActions;
  setPassageDraft: Dispatch<
    SetStateAction<{ forRange: string; value: KeySignatureName } | null>
  >;
  setLyricDraft: Dispatch<SetStateAction<{ forRange: string; text: string } | null>>;
  score: TimeScorePayload | null;
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  setOttavaHidden: (hands: readonly PrintedHand[], atColumn: number, hidden: boolean) => void;
  audioUuid: string;
  /** The length of the highest pile of gaps, which the whole piece is named from. */
  anchorMs: number | null;
  onRerecordAccepted: (range: FrameRange) => void;
}) {
  const {
    rangeKey,
    spacingHere,
    setRangeSpacing,
    clearSpacingRange,
    handsInScope,
    editedHere,
    lyricHere,
    lyricText,
    passageKey,
    notesUnderRange,
  } = rangeActions;
  const { keySignature, keyChanges, clefChanges, ottavas, stretches, anchorFigure } = state;
  const {
    keyChanges: setKeyChanges,
    clefChanges: setClefChanges,
    ottavas: setOttavas,
    lyrics: setLyrics,
    stretches: setStretches,
  } = set;
  const frameCount = score?.envelope.frameCount;

  return (
    <Toolbox
      open={framesToolbox && range !== null}
      title="Frames"
      subtitle={
        range
          ? `${formatSeconds((range.fromColumn * frameMs) / 1000)} – ${formatSeconds(
              (range.toColumn * frameMs) / 1000,
            )}`
          : undefined
      }
      initialPosition={framesAt ?? { x: 24, y: 140 }}
      onClose={closeFrames}
      headerAction={
        /*
          The same music, picked the other way round. Disabled rather than hidden when the stretch
          holds no notes on the staves in scope, so the tooltip can say so.
        */
        <IconAction
          title={`Select the ${notesUnderRange.length} note${
            notesUnderRange.length === 1 ? "" : "s"
          } in this stretch`}
          disabledTitle="No notes begin inside this stretch on this staff"
          icon={<SwapHorizIcon fontSize="small" />}
          disabled={notesUnderRange.length === 0 || !canSelectNotes}
          onClick={selectNotesUnderRange}
        />
      }
    >
      <Stack spacing={1.5}>
        <Segmented<RangeHand>
          label="Which staff"
          value={rangeHand}
          options={HAND_OPTIONS}
          onChange={setRangeHand}
        />

        {/*
          One tab per thing this stretch can carry. A dot says this stretch already carries that
          setting; the filled tab is the one open. Two signals, so opening a marked tab does not
          hide that it was marked.
        */}
        <Box
          role="tablist"
          aria-label="What this stretch carries"
          sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0.75 }}
        >
          {FRAME_TABS.map((tab) => (
            <Badge
              key={tab.id}
              color="warning"
              variant="dot"
              invisible={!editedHere[tab.id]}
              sx={{ display: "block", "& .MuiBadge-badge": { right: 6, top: 6 } }}
            >
              <Chip
                size="small"
                role="tab"
                aria-selected={frameTab === tab.id}
                label={tab.label}
                onClick={() => setFrameTab(tab.id)}
                color={frameTab === tab.id ? "primary" : "default"}
                variant={frameTab === tab.id ? "filled" : "outlined"}
                sx={{ width: "100%" }}
                data-edited={editedHere[tab.id] ? "yes" : "no"}
              />
            </Badge>
          ))}
        </Box>

        {frameTab === "key" ? (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <TextField
              select
              size="small"
              label="Key"
              value={passageKey}
              onChange={(event) =>
                setPassageDraft({
                  forRange: rangeKey,
                  value: event.target.value as KeySignatureName,
                })
              }
              sx={{ flex: 1 }}
            >
              {KEY_SIGNATURES.map((name) => (
                <MenuItem key={name} value={name}>
                  {KEY_LABELS[name]}
                </MenuItem>
              ))}
            </TextField>
            <IconAction
              title="Use this key here"
              icon={<CheckIcon fontSize="small" />}
              disabled={!range || frameCount === undefined}
              onClick={() => {
                if (!range || frameCount === undefined) return;
                setKeyChanges(
                  applyKeySignatureRange(
                    keyChanges,
                    {
                      fromFrame: range.fromColumn,
                      toFrame: range.toColumn,
                      keySignature: passageKey as KeySignature,
                    },
                    keySignature as KeySignature,
                    frameCount,
                  ),
                );
              }}
            />
            <IconAction
              title="Back to the key of the piece"
              icon={<DeleteOutlineIcon fontSize="small" />}
              danger
              disabled={!range || frameCount === undefined || !editedHere.key}
              onClick={() => {
                if (!range || frameCount === undefined) return;
                setKeyChanges(
                  clearKeySignatureRange(
                    keyChanges,
                    { fromFrame: range.fromColumn, toFrame: range.toColumn },
                    keySignature as KeySignature,
                    frameCount,
                  ),
                );
              }}
            />
          </Stack>
        ) : null}

        {frameTab === "octave" ? (
          <Stack spacing={1}>
            {/* One row per staff in scope; narrowing to one hand above leaves one row. */}
            {handsInScope.map((side) => {
              const active = range ? ottavaAtFrame(ottavas, side, range.fromColumn) : undefined;
              return (
                <Stack key={side} direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                  {handsInScope.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 40 }}>
                      {side === "left" ? "Left" : "Right"}
                    </Typography>
                  ) : null}
                  {OTTAVA_CHOICES.map((choice) => (
                    <Tooltip key={choice.kind} title={choice.hint}>
                      <Chip
                        size="small"
                        label={choice.label}
                        disabled={!range || frameCount === undefined}
                        color={active?.kind === choice.kind ? "primary" : "default"}
                        variant={active?.kind === choice.kind ? "filled" : "outlined"}
                        onClick={() => {
                          if (!range || frameCount === undefined) return;
                          // The bracket already on clears it: one chip is the way in and out.
                          setOttavas(
                            active?.kind === choice.kind
                              ? clearOttavaRange(ottavas, side, {
                                  fromColumn: range.fromColumn,
                                  toColumn: range.toColumn,
                                })
                              : applyOttava(
                                  ottavas,
                                  {
                                    kind: choice.kind,
                                    hand: side,
                                    fromColumn: range.fromColumn,
                                    toColumn: range.toColumn,
                                  },
                                  frameCount,
                                ),
                          );
                        }}
                      />
                    </Tooltip>
                  ))}
                  {/*
                    Hide keeps the notes written where the bracket puts them and only takes the
                    dashed line off; its corner marks stay, as the way back to it. Delete does the
                    same from the keyboard.
                  */}
                  <IconAction
                    title={active?.hidden ? "Show the bracket" : "Hide the bracket, keep the notes where they are"}
                    shortcut={active?.hidden ? undefined : "Delete"}
                    icon={
                      active?.hidden ? (
                        <VisibilityOffIcon fontSize="small" />
                      ) : (
                        <VisibilityIcon fontSize="small" />
                      )
                    }
                    disabled={!range || !active}
                    onClick={() => {
                      if (!range || !active) return;
                      setOttavaHidden([side], range.fromColumn, !active.hidden);
                    }}
                  />
                  <IconAction
                    title="Remove the bracket"
                    icon={<DeleteOutlineIcon fontSize="small" />}
                    danger
                    disabled={!range || !active}
                    onClick={() => {
                      if (!range) return;
                      setOttavas(
                        clearOttavaRange(ottavas, side, {
                          fromColumn: range.fromColumn,
                          toColumn: range.toColumn,
                        }),
                      );
                    }}
                  />
                </Stack>
              );
            })}
          </Stack>
        ) : null}

        {/*
          Which clef each hand in scope prints over this stretch. Nothing moves and nothing is
          renamed: a clef decides which lines the noteheads are drawn on and nothing else.
        */}
        {frameTab === "clef" ? (
          <Stack spacing={1}>
            {handsInScope.map((side) => {
              const active = range
                ? clefAtFrame(range.fromColumn, side, clefChanges)
                : DEFAULT_CLEF[side];
              return (
                <Stack key={side} direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                  {handsInScope.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 40 }}>
                      {side === "left" ? "Left" : "Right"}
                    </Typography>
                  ) : null}
                  {CLEF_CHOICES.map((choice) => (
                    <Tooltip key={choice.clef} title={choice.hint}>
                      <Chip
                        size="small"
                        label={choice.label}
                        disabled={!range || frameCount === undefined}
                        color={active === choice.clef ? "primary" : "default"}
                        variant={active === choice.clef ? "filled" : "outlined"}
                        onClick={() => {
                          if (!range || frameCount === undefined) return;
                          // The clef the hand already reads stores nothing: the stretch goes back.
                          setClefChanges(
                            choice.clef === DEFAULT_CLEF[side]
                              ? clearClefRange(
                                  clefChanges,
                                  { hand: side, fromFrame: range.fromColumn, toFrame: range.toColumn },
                                  frameCount,
                                )
                              : applyClefRange(
                                  clefChanges,
                                  {
                                    hand: side,
                                    fromFrame: range.fromColumn,
                                    toFrame: range.toColumn,
                                    clef: choice.clef,
                                  },
                                  frameCount,
                                ),
                          );
                        }}
                      />
                    </Tooltip>
                  ))}
                  <IconAction
                    title="Back to this hand's own clef"
                    icon={<DeleteOutlineIcon fontSize="small" />}
                    danger
                    disabled={!range || frameCount === undefined || active === DEFAULT_CLEF[side]}
                    onClick={() => {
                      if (!range || frameCount === undefined) return;
                      setClefChanges(
                        clearClefRange(
                          clefChanges,
                          { hand: side, fromFrame: range.fromColumn, toFrame: range.toColumn },
                          frameCount,
                        ),
                      );
                    }}
                  />
                </Stack>
              );
            })}
          </Stack>
        ) : null}

        {/*
          How much room this stretch takes against what the page measured. Both staves, whichever
          hand is chosen: a column is one slice of the clock and the two hands share it (D-22).
        */}
        {frameTab === "spacing" && range ? (
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Slider
              size="small"
              min={25}
              max={400}
              step={5}
              marks={[{ value: 100 }]}
              value={Math.round(spacingHere * 100)}
              onChange={(_, value) => setRangeSpacing((value as number) / 100)}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${value}%`}
              disabled={!score}
              aria-label="Room this stretch takes, on both staves"
              sx={{ flex: 1 }}
            />
            <Typography variant="body2" sx={{ minWidth: 44, textAlign: "right" }}>
              {Math.round(spacingHere * 100)}%
            </Typography>
            <IconAction
              title="Back to the page's own spacing"
              icon={<RestartAltIcon fontSize="small" />}
              disabled={spacingHere === 1}
              onClick={clearSpacingRange}
            />
          </Stack>
        ) : null}

        {frameTab === "speed" && range ? (
          <SpeedTab
            key={rangeKey}
            fromColumn={range.fromColumn}
            anchorMs={anchorMs}
            anchorFigure={anchorFigure}
            stretches={stretches}
            setStretches={setStretches}
          />
        ) : null}

        {frameTab === "lyrics" && range ? (
          <Stack spacing={1.5}>
            <TextField
              size="small"
              label="Lyrics"
              multiline
              maxRows={3}
              value={lyricText}
              onChange={(event) => setLyricDraft({ forRange: rangeKey, text: event.target.value })}
            />
            {lyricHere ? (
              <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 36 }}>
                  Size
                </Typography>
                <Slider
                  size="small"
                  value={lyricHere.fontSize ?? LYRIC_FONT_SIZE}
                  min={MIN_LYRIC_FONT_SIZE}
                  max={MAX_LYRIC_FONT_SIZE}
                  step={1}
                  valueLabelDisplay="auto"
                  aria-label="Text size of these words"
                  onChange={(_event, value) =>
                    setLyrics((current) =>
                      current.map((line) =>
                        line === lyricHere ? { ...line, fontSize: value as number } : line,
                      ),
                    )
                  }
                  sx={{ flex: 1 }}
                />
                <IconAction
                  title="Put the words back over their stretch"
                  icon={<RestartAltIcon fontSize="small" />}
                  disabled={
                    lyricHere.offsetX === undefined &&
                    lyricHere.offsetY === undefined &&
                    lyricHere.width === undefined
                  }
                  onClick={() =>
                    setLyrics((current) =>
                      // Built back up rather than picked apart, because "no answer" here is the
                      // field being absent and not a number meaning nothing.
                      current.map((line) =>
                        line === lyricHere
                          ? {
                              fromColumn: line.fromColumn,
                              toColumn: line.toColumn,
                              text: line.text,
                              ...(line.fontSize === undefined ? {} : { fontSize: line.fontSize }),
                            }
                          : line,
                      ),
                    )
                  }
                />
              </Stack>
            ) : null}
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <PillButton
                kind="primary"
                size="small"
                disabled={lyricText.trim().length === 0}
                onClick={() => {
                  const text = lyricText.trim();
                  setLyrics((current) => [
                    ...current.filter(
                      (line) => line.fromColumn >= range.toColumn || line.toColumn <= range.fromColumn,
                    ),
                    { fromColumn: range.fromColumn, toColumn: range.toColumn, text },
                  ]);
                  setLyricDraft(null);
                }}
              >
                {lyricHere ? "Change the words" : "Add the words"}
              </PillButton>
              {lyricHere ? (
                <IconAction
                  title="Remove these words"
                  icon={<DeleteOutlineIcon fontSize="small" />}
                  danger
                  onClick={() => {
                    setLyrics((current) => current.filter((line) => line !== lyricHere));
                    setLyricDraft(null);
                  }}
                />
              ) : null}
            </Stack>
          </Stack>
        ) : null}

        {frameTab === "rerecord" && range && audioUuid ? (
          <Stack spacing={1.5}>
            {/* A warning that applies every time: this edit is the one undo cannot reach. */}
            <Alert severity="warning" variant="outlined">
              Accepting writes over the recording. Undo cannot take it back.
            </Alert>
            <RangeRerecordPanel
              audioUuid={audioUuid}
              frameMs={frameMs}
              fromColumn={range.fromColumn}
              toColumn={range.toColumn}
              anchorFigure={anchorFigure}
              anchorMs={anchorMs ?? undefined}
              speedChanges={stretches.map((stretch) => ({
                startFrame: stretch.startFrame,
                anchorMs: stretch.anchorMs,
              }))}
              clickIntervalMs={((): number => {
                let ms = anchorMs ?? 480;
                for (const stretch of stretches) {
                  if (stretch.startFrame <= range.fromColumn) ms = stretch.anchorMs;
                }
                return ms;
              })()}
              onRangeChange={(start, end) => {
                const fromColumn = Math.max(0, Math.round((start * 1000) / frameMs));
                const toColumn = Math.max(fromColumn + 1, Math.round((end * 1000) / frameMs));
                setRange({ fromColumn, toColumn });
              }}
              onAccepted={() => onRerecordAccepted(range)}
            />
          </Stack>
        ) : null}
      </Stack>
    </Toolbox>
  );
}

/**
 * Where the piece changes speed: from the start of the stretch, its notes are named as if played at
 * this speed, against the speed of the whole piece.
 *
 * The stored value is still a length in milliseconds for the main figure (`speedChanges` of the
 * reading, rule 3: no BPM). The tab shows it as a percentage of the piece's own speed, because
 * that is how a reader thinks about "this part goes faster", and milliseconds are not on screen.
 * The sheet is drawn again on its own once the change is made.
 */
function SpeedTab({
  fromColumn,
  anchorMs,
  anchorFigure,
  stretches,
  setStretches,
}: {
  fromColumn: number;
  anchorMs: number | null;
  anchorFigure: string;
  stretches: SheetEdits["stretches"];
  setStretches: EditHistory<SheetEdits>["set"]["stretches"];
}) {
  const here = stretches.find((stretch) => stretch.startFrame === fromColumn) ?? null;
  // The speed already in force at the start of the stretch: the last change before it, or 100 %.
  let inForce = anchorMs;
  for (const stretch of stretches) {
    if (stretch.startFrame <= fromColumn) inForce = stretch.anchorMs;
  }
  const percentOf = (ms: number | null) =>
    anchorMs && ms ? Math.round((anchorMs / ms) * 100) : 100;
  const [percent, setPercent] = useState(percentOf(inForce));
  const changed = percent !== percentOf(inForce);
  if (!anchorMs) return null;
  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <Slider
          size="small"
          min={MIN_SPEED}
          max={MAX_SPEED}
          step={5}
          marks={[{ value: 100 }]}
          value={percent}
          onChange={(_, value) => setPercent(value as number)}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value}%`}
          aria-label={`Speed from here, against the speed of the piece (the ${anchorFigure})`}
          sx={{ flex: 1 }}
        />
        <Typography variant="body2" sx={{ minWidth: 44, textAlign: "right" }}>
          {percent}%
        </Typography>
        <IconAction
          title="Change the speed from here"
          icon={<CheckIcon fontSize="small" />}
          disabled={!changed}
          onClick={() => {
            const ms = Math.round((anchorMs * 100) / percent);
            setStretches((current) =>
              [
                ...current.filter((one) => one.startFrame !== fromColumn),
                { startFrame: fromColumn, anchorMs: ms },
              ].sort((a, b) => a.startFrame - b.startFrame),
            );
          }}
        />
        <IconAction
          title="Remove the speed change here"
          icon={<DeleteOutlineIcon fontSize="small" />}
          danger
          disabled={here === null}
          onClick={() =>
            setStretches((current) => current.filter((one) => one.startFrame !== fromColumn))
          }
        />
      </Stack>
      {stretches.length > 1 || (stretches.length === 1 && here === null) ? (
        <Box>
          <PillButton kind="quiet" size="small" onClick={() => setStretches([])}>
            Remove every speed change ({stretches.length})
          </PillButton>
        </Box>
      ) : null}
    </Stack>
  );
}

export default RangeToolbox;
