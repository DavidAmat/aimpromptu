/**
 * The range toolbox: what a marked stretch of frames can carry, one pill each.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import VisibilityIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffOutlined";
import type { Dispatch, SetStateAction } from "react";
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
  type FigureName,
  type KeySignatureName,
  type Peak,
  type TimeScorePayload,
} from "../../../api";
import RangeRerecordPanel from "../../../components/editing/RangeRerecordPanel";
import type { EditHistory } from "../../../hooks/useEditHistory";
import type { PrintedHand } from "../../../music/renderOverrides";
import { Toolbox } from "../../../ui";
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
  figure,
  selected,
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
  figure: FigureName;
  selected: Peak | null;
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
  const { keySignature, keyChanges, clefChanges, ottavas, stretches } = state;
  const {
    keyChanges: setKeyChanges,
    clefChanges: setClefChanges,
    ottavas: setOttavas,
    lyrics: setLyrics,
  } = set;
  return (
    <Toolbox
      open={framesToolbox && range !== null}
      title="Frames"
      subtitle={
        range
          ? `f${range.fromColumn} – f${range.toColumn - 1} · ${formatSeconds(
              (range.fromColumn * frameMs) / 1000,
            )} → ${formatSeconds((range.toColumn * frameMs) / 1000)}`
          : undefined
      }
      initialPosition={framesAt ?? { x: 24, y: 140 }}
      onClose={closeFrames}
      headerAction={
        /*
          The same music, picked the other way round. It is disabled rather than hidden when the
          stretch holds no notes on the staves in scope, so the tooltip can say which of the two
          it is — an empty stretch, or a hand that is silent through it.
        */
        <Tooltip
          title={
            notesUnderRange.length === 0
              ? "No notes begin inside this stretch on the staff it is about"
              : `Pick the ${notesUnderRange.length} note${
                  notesUnderRange.length === 1 ? "" : "s"
                } that begin inside this stretch and open the note toolbox on them`
          }
        >
          <span>
            <Button
              size="small"
              color="inherit"
              disabled={notesUnderRange.length === 0 || !canSelectNotes}
              startIcon={<SwapHorizIcon fontSize="small" />}
              onClick={selectNotesUnderRange}
              sx={{ textTransform: "none", whiteSpace: "nowrap" }}
            >
              Select notes
            </Button>
          </span>
        </Tooltip>
      }
    >
      <Stack spacing={1.5}>
        {/*
          Which staff this stretch is about, asked first because it changes what everything under
          it means and what the highlight on the page covers.

          A clef and an octave bracket belong to one hand; a key signature is drawn on both clefs
          and a line of words is sung over the piece, so those two read this and ignore it. The
          labels are one letter because the reader is aiming at them, not reading them.
        */}
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center" }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 42 }}>
            Applies to
          </Typography>
          <ButtonGroup size="small">
            {([
              ["both", "Both"],
              ["right", "R"],
              ["left", "L"],
            ] as const).map(([side, label]) => (
              <Button
                key={side}
                variant={rangeHand === side ? "contained" : "outlined"}
                onClick={() => setRangeHand(side)}
                sx={{ minWidth: 34, px: 1 }}
                title={
                  side === "both"
                    ? "The whole system: the highlight covers both staves"
                    : `Only the ${side} hand: the highlight covers that staff alone`
                }
              >
                {label}
              </Button>
            ))}
          </ButtonGroup>
        </Stack>

        {/*
          One pill per thing this stretch can carry, and only that thing's controls below it.

          Laid out as a grid rather than a row: there are six of them, and a row of six on a panel
          this wide put half of them off the edge. A pill wears the accent colour when this stretch
          already carries that setting, so what has been edited here is visible before anything is
          opened.
        */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 0.75,
          }}
        >
          {FRAME_TABS.map((tab) => (
            <Chip
              key={tab.id}
              size="small"
              label={tab.label}
              onClick={() => setFrameTab(tab.id)}
              // Two signals that must not collide: colour says *this stretch already carries
              // one*, fill says *this is the pill you are looking at*. Folding them into one
              // would hide the first behind the second the moment a marked pill was opened.
              color={editedHere[tab.id] ? "secondary" : "default"}
              variant={frameTab === tab.id ? "filled" : "outlined"}
              sx={{ fontWeight: frameTab === tab.id ? 600 : 400 }}
            />
          ))}
        </Box>

        {frameTab === "key" ? (
          <Stack spacing={1.5}>
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
              fullWidth
            >
              {KEY_SIGNATURES.map((name) => (
                <MenuItem key={name} value={name}>
                  {KEY_LABELS[name]}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                size="small"
                disabled={!range || !score}
                onClick={() => {
                  if (!range || !score) return;
                  setKeyChanges(
                    applyKeySignatureRange(
                      keyChanges,
                      {
                        fromFrame: range.fromColumn,
                        toFrame: range.toColumn,
                        keySignature: passageKey as KeySignature,
                      },
                      keySignature as KeySignature,
                      score.envelope.frameCount,
                    ),
                  );
                }}
              >
                Apply
              </Button>
              <Button
                size="small"
                color="error"
                disabled={!range || !score || !editedHere.key}
                startIcon={<DeleteOutlineIcon />}
                onClick={() => {
                  if (!range || !score) return;
                  setKeyChanges(
                    clearKeySignatureRange(
                      keyChanges,
                      {
                        fromFrame: range.fromColumn,
                        toFrame: range.toColumn,
                      },
                      keySignature as KeySignature,
                      score.envelope.frameCount,
                    ),
                  );
                }}
              >
                Remove
              </Button>
            </Stack>
          </Stack>
        ) : null}

        {frameTab === "octave" ? (
          <Stack spacing={1}>
            {/*
              One row per staff in scope. Narrowing to a hand above leaves one row here, which is
              the panel's answer to being asked the same question twice: the reader has already
              said which hand, and a second L/R inside the pill was the thing they were saying it
              to.
            */}
            {handsInScope.map((side) => {
              const active = range
                ? ottavaAtFrame(ottavas, side, range.fromColumn)
                : undefined;
              return (
                <Stack
                  key={side}
                  direction="row"
                  spacing={0.75}
                  sx={{ alignItems: "center" }}
                >
                  {handsInScope.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 34 }}>
                      {side === "left" ? "L" : "R"}
                    </Typography>
                  ) : null}
                  {OTTAVA_CHOICES.map((choice) => (
                    <Chip
                      key={choice.kind}
                      size="small"
                      label={choice.label}
                      title={choice.hint}
                      disabled={!range || !score}
                      color={
                        active?.kind === choice.kind ? "secondary" : "default"
                      }
                      variant={
                        active?.kind === choice.kind ? "filled" : "outlined"
                      }
                      onClick={() => {
                        if (!range || !score) return;
                        // Pressing the bracket already on clears it, so one chip is both the way
                        // in and the way out and there is no separate "none".
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
                                score.envelope.frameCount,
                              ),
                        );
                      }}
                    />
                  ))}
                  {/*
                    Take the bracket off the page without taking the reading off the piece.

                    A player who already knows a passage is played an octave up does not need a
                    dashed line over every bar of it saying so, and above the right hand is the
                    most crowded strip on the page. The notes stay written exactly where the
                    bracket puts them — that is the whole difference between this and the trash
                    beside it — so a hidden bracket is still there, and its corner marks are how
                    a reader gets back to it. Delete does the same thing from the keyboard.
                  */}
                  <IconButton
                    size="small"
                    title={
                      active?.hidden
                        ? "Draw the bracket again. The notes do not move either way."
                        : "Hide the bracket and keep the reading — or press Delete. The notes stay written where it puts them."
                    }
                    disabled={!range || !active}
                    onClick={() => {
                      if (!range || !active) return;
                      setOttavaHidden([side], range.fromColumn, !active.hidden);
                    }}
                  >
                    {active?.hidden ? (
                      <VisibilityOffIcon fontSize="small" />
                    ) : (
                      <VisibilityIcon fontSize="small" />
                    )}
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    title="Remove the bracket on this hand. The notes go back to where they sound, in ledger lines if that is where they are."
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
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Stack>
              );
            })}
          </Stack>
        ) : null}

        {/*
          Which clef each hand in scope prints over this stretch.

          The answer to a hand that spends a passage far outside its own staff, and a better one
          than an octave bracket where the passage is long: under a bracket the notes are written
          an octave from where they sound and the reader has to hold that in mind, while on the
          other clef they are written exactly where they sound. Nothing moves and nothing is
          renamed — a clef decides which lines the noteheads are drawn on and nothing else.
        */}
        {frameTab === "clef" ? (
          <Stack spacing={1}>
            {handsInScope.map((side) => {
              const active = range
                ? clefAtFrame(range.fromColumn, side, clefChanges)
                : DEFAULT_CLEF[side];
              return (
                <Stack
                  key={side}
                  direction="row"
                  spacing={0.75}
                  sx={{ alignItems: "center" }}
                >
                  {handsInScope.length > 1 ? (
                    <Typography variant="body2" sx={{ minWidth: 34 }}>
                      {side === "left" ? "L" : "R"}
                    </Typography>
                  ) : null}
                  {CLEF_CHOICES.map((choice) => (
                    <Chip
                      key={choice.clef}
                      size="small"
                      label={choice.label}
                      title={choice.hint}
                      disabled={!range || !score}
                      color={active === choice.clef ? "secondary" : "default"}
                      variant={active === choice.clef ? "filled" : "outlined"}
                      onClick={() => {
                        if (!range || !score) return;
                        // Asking for the clef the hand already reads is asking for nothing, so
                        // the stretch goes back to the hand's own rather than storing a
                        // transition that changes nothing.
                        setClefChanges(
                          choice.clef === DEFAULT_CLEF[side]
                            ? clearClefRange(
                                clefChanges,
                                {
                                  hand: side,
                                  fromFrame: range.fromColumn,
                                  toFrame: range.toColumn,
                                },
                                score.envelope.frameCount,
                              )
                            : applyClefRange(
                                clefChanges,
                                {
                                  hand: side,
                                  fromFrame: range.fromColumn,
                                  toFrame: range.toColumn,
                                  clef: choice.clef,
                                },
                                score.envelope.frameCount,
                              ),
                        );
                      }}
                    />
                  ))}
                  <IconButton
                    size="small"
                    color="error"
                    title="Back to the clef this hand normally reads"
                    disabled={!range || !score || active === DEFAULT_CLEF[side]}
                    onClick={() => {
                      if (!range || !score) return;
                      setClefChanges(
                        clearClefRange(
                          clefChanges,
                          {
                            hand: side,
                            fromFrame: range.fromColumn,
                            toFrame: range.toColumn,
                          },
                          score.envelope.frameCount,
                        ),
                      );
                    }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Stack>
              );
            })}
          </Stack>
        ) : null}

        {frameTab === "spacing" && range ? (
          <Stack spacing={1}>
            <Typography variant="caption" color="text.secondary">
              How much room this stretch takes, against what the page measured
              for it. Only the columns inside it move, and the sheet redraws as
              the handle moves so the right spot can be found by looking at it.
            </Typography>
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
              aria-label="How much room this stretch takes"
            />
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Typography variant="body2" sx={{ minWidth: 54 }}>
                {Math.round(spacingHere * 100)}%
              </Typography>
              <IconButton
                size="small"
                color="error"
                title="Back to the page's own spacing"
                disabled={spacingHere === 1}
                onClick={clearSpacingRange}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Stack>
            {/*
              Said out loud because the pills above promise otherwise. A column is one slice of
              wall clock and both staves share it — that is the whole of what makes the two hands
              line up (D-22) — so there is no such thing as widening a column for one hand. The
              clef and the octave bracket honour the hand pills; this one cannot.
            */}
            <Typography variant="caption" color="text.secondary">
              Both staves, whichever hand is chosen above: a column is one slice
              of the clock and the two hands share it.
            </Typography>
          </Stack>
        ) : null}

        {frameTab === "lyrics" && range ? (
          <Stack spacing={1.5}>
            <TextField
              size="small"
              label="Lyrics"
              multiline
              maxRows={3}
              value={lyricText}
              placeholder="The line sung over this stretch"
              onChange={(event) =>
                setLyricDraft({ forRange: rangeKey, text: event.target.value })
              }
              helperText="Drawn above the right hand, over the marked stretch. Drag the block to move it, drag its right edge to fold the words into more lines. It never moves a note."
            />
            {lyricHere ? (
              <>
                {/*
                  Per lyric and not per page, because the reason for changing it is per lyric:
                  one line is three words over eight seconds and the next a whole sentence over
                  one.
                */}
                <Stack spacing={0.5}>
                  <Typography variant="caption" color="text.secondary">
                    Text size — {Math.round(lyricHere.fontSize ?? LYRIC_FONT_SIZE)} px
                  </Typography>
                  <Slider
                    size="small"
                    value={lyricHere.fontSize ?? LYRIC_FONT_SIZE}
                    min={MIN_LYRIC_FONT_SIZE}
                    max={MAX_LYRIC_FONT_SIZE}
                    step={1}
                    valueLabelDisplay="auto"
                    onChange={(_event, value) =>
                      setLyrics((current) =>
                        current.map((line) =>
                          line === lyricHere
                            ? { ...line, fontSize: value as number }
                            : line,
                        ),
                      )
                    }
                  />
                </Stack>
                {lyricHere.offsetX !== undefined ||
                lyricHere.offsetY !== undefined ||
                lyricHere.width !== undefined ? (
                  <Button
                    size="small"
                    onClick={() =>
                      setLyrics((current) =>
                        // Built back up rather than picked apart, because "no answer" here is
                        // the field being absent and not a number meaning nothing.
                        current.map((line) =>
                          line === lyricHere
                            ? {
                                fromColumn: line.fromColumn,
                                toColumn: line.toColumn,
                                text: line.text,
                                ...(line.fontSize === undefined
                                  ? {}
                                  : { fontSize: line.fontSize }),
                              }
                            : line,
                        ),
                      )
                    }
                  >
                    Put the block back over its stretch
                  </Button>
                ) : null}
              </>
            ) : null}
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                variant="contained"
                disabled={lyricText.trim().length === 0}
                onClick={() => {
                  const text = lyricText.trim();
                  setLyrics((current) => [
                    ...current.filter(
                      (line) =>
                        line.fromColumn >= range.toColumn ||
                        line.toColumn <= range.fromColumn,
                    ),
                    {
                      fromColumn: range.fromColumn,
                      toColumn: range.toColumn,
                      text,
                    },
                  ]);
                  setLyricDraft(null);
                }}
              >
                Write it here
              </Button>
              {lyricHere ? (
                <Button
                  size="small"
                  onClick={() => {
                    setLyrics((current) =>
                      current.filter((line) => line !== lyricHere),
                    );
                    setLyricDraft(null);
                  }}
                >
                  Take it off
                </Button>
              ) : null}
            </Stack>
          </Stack>
        ) : null}

        {frameTab === "rerecord" && range && audioUuid ? (
          <Stack spacing={1.5}>
            <Alert severity="warning" variant="outlined">
              Playing this stretch again writes over the recording.{" "}
              <strong>Command-Z cannot take it back</strong>, and accepting it
              also forgets every edit you could have taken back until now.
            </Alert>
            <RangeRerecordPanel
              audioUuid={audioUuid}
              frameMs={frameMs}
              fromColumn={range.fromColumn}
              toColumn={range.toColumn}
              anchorFigure={figure}
              anchorMs={selected?.medianMs}
              speedChanges={stretches.map((stretch) => ({
                startFrame: stretch.startFrame,
                anchorMs: stretch.anchorMs,
              }))}
              clickIntervalMs={((): number => {
                let ms = selected?.medianMs ?? 480;
                for (const stretch of stretches) {
                  if (stretch.startFrame <= range.fromColumn) ms = stretch.anchorMs;
                }
                return ms;
              })()}
              onRangeChange={(start, end) => {
                const fromColumn = Math.max(0, Math.round((start * 1000) / frameMs));
                const toColumn = Math.max(
                  fromColumn + 1,
                  Math.round((end * 1000) / frameMs),
                );
                setRange({ fromColumn, toColumn });
              }}
              onAccepted={() => onRerecordAccepted(range)}
            />
          </Stack>
        ) : null}

        {/*
          No **Save with the piece** here any more.

          Every panel on this page edits the same one reading, and a save button inside one of
          them read as saving that panel's own part of it. The bar that follows the reader down
          the sheet carries the only Save there is, beside Remove all, which is where a reader
          looking for either of them goes.
        */}
      </Stack>
    </Toolbox>
  );
}

export default RangeToolbox;
