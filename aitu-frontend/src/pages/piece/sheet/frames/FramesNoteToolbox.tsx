/**
 * The note toolbox of the new sheet (implementations 03, Phases 6 and 7): what can be said about the notes picked on
 * it. Every control writes at once (no Save) and is one step of undo; the sheet comes back drawn again.
 *
 * - **The figures**: the seven shapes; one is pressed when every picked chord prints it. Pressing one sets the
 *   figure by hand (the rule keeps it, and it is never a grace note); ⌫ gives the chords back the rule's figure.
 * - **Finger** 1 to 5: one number on every picked note, or on a single chord one number per note (the smallest from
 *   the lowest note up in the right hand, the largest in the left).
 * - **Hand** Right / Left: written into the notes (Phase 6).
 * - **Beam**: join the picked notes as one group (pressed again, the beam goes away); cut the group in front of the
 *   first one, or join it to the group before.
 * - **Grace**: write the picked notes as grace notes of the next note of their hand, or as normal notes, whatever the
 *   grace rule says (the user's switch, Phase 7); ⌫ back to the rule.
 * - **Marks**: a trill, a mordent or a turn over picked onsets that follow one another (the first one is written,
 *   the others are played inside it); a rolled chord; a fermata. Pressed again, the mark goes away.
 * - 🗑 takes the notes off the page (Delete): they leave the notes, and undo brings them back.
 * - **The keyboard** (the user's request of 2026-10-26, Phase 8A), when the picked notes are in one column: the
 *   column's keys lit in their hand's colour, both hands. A dark key adds a note to the column, in the picked hand
 *   and as long as its chord; a lit key takes that note off. Each press is one step of undo. Notes picked in several
 *   columns show no keyboard: like the keyboard panel, it is the chord of one moment. ⌘ (or Control, or Shift) and
 *   a click on a lit key picks that note or lets it go (the user's request of 2026-10-26): the picked notes' keys
 *   keep their full colour with a dot (the other lit keys turn pale), and **Hand** then moves only them. A note added
 *   on the keyboard is the one picked after.
 *
 * The title bar hands the selection to the range toolbox (*Select the frames of these notes*) and asks the AI to write
 * the stretch of these notes again with the user's words. The panel is the old one's: titled with the note's printed
 * name (`Do-# 5`) or the number of notes, the time under it, dragged by its title bar.
 */

import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesomeOutlined";
import BackspaceIcon from "@mui/icons-material/BackspaceOutlined";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import LinkIcon from "@mui/icons-material/LinkOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import type { ReadingEdit, SheetNote } from "../../../../api";
import FigureGlyph from "../../../../components/time/FigureGlyph";
import { FIGURE_SHORT } from "../../../../music/figures";
import { spanishNoteName, spanishNoteShort } from "../../../../music/noteNames";
import { keepKeyInView } from "../../../../piano/keyPositions";
import { IconAction, MiniKeys, Segmented, Toolbox } from "../../../../ui";
import { HAND_COLOUR, formatSeconds } from "../sheetConstants";
import {
  CHORD_ORNAMENTS,
  FIGURES,
  FINGERS,
  SPAN_ORNAMENTS,
  chordOf,
  frameOf,
  handColumns,
  handForKey,
  midiOf,
  oneColumn,
} from "./readingTools";

type Hand = SheetNote["hand"];

/** A row of the toolbox: a short label, then its controls (as the old note toolbox). */
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

/** An ornament as the page prints it: a short word in the serif italic of the marks. */
function MarkGlyph({ text }: { text: string }) {
  return (
    <Box component="span" sx={{ fontFamily: "serif", fontStyle: "italic", fontWeight: 700, fontSize: 15, lineHeight: 1, px: 0.25 }}>
      {text}
    </Box>
  );
}

/** `C#5` as the sheet prints it, in solfège: `Do-# 5`. */
function printedName(pitch: string): string {
  const match = /^([A-G])([#b]?)(-?\d+)$/.exec(pitch);
  if (!match) return pitch;
  const [, letter, sign, octave] = match;
  return spanishNoteName({ letter, accidental: sign === "#" ? 1 : sign === "b" ? -1 : 0, octave: Number(octave) });
}

/**
 * The picked column's chord on a small keyboard: a dark key adds a note there, a lit key takes it off, and ⌘ and a
 * click on a lit key picks that note or lets it go (the picked ones dotted).
 */
function ChordKeys({
  picked,
  column,
  onKey,
  disabled,
  why,
}: {
  picked: readonly SheetNote[];
  /** Every note of the picked column, both hands. */
  column: readonly SheetNote[];
  onKey: (midi: number, add: boolean) => void;
  disabled: boolean;
  why: string | undefined;
}) {
  const scroller = useRef<HTMLDivElement | null>(null);
  const keys = column.map((note) => midiOf(note.ref));
  const middle = keys.length > 0 ? Math.round((Math.min(...keys) + Math.max(...keys)) / 2) : null;
  const frame = column.length > 0 ? frameOf(column[0]!.ref) : null;
  // The chord in view when another column is picked (a key pressed keeps the place: the chord stays in view).
  useEffect(() => keepKeyInView(scroller.current, middle, 0.5), [frame, middle]);
  const colours: Record<number, string> = {};
  for (const note of column) colours[midiOf(note.ref)] = HAND_COLOUR[note.hand];
  const title = (midi: number) => {
    if (why) return `${spanishNoteShort(midi)}. ${why}`;
    const lit = column.find((note) => midiOf(note.ref) === midi);
    if (lit) return `${spanishNoteShort(midi)}, ${lit.hand} hand: take it off. ⌘-click: pick it or let it go`;
    return `${spanishNoteShort(midi)}: add it to the ${handForKey(midi, picked, column)} hand`;
  };
  return (
    <Box
      ref={scroller}
      role="group"
      aria-label="The keys of this chord"
      sx={{ overflowX: "auto", maxWidth: "100%", borderRadius: 1, opacity: disabled ? 0.5 : 1 }}
      data-chord-keys
    >
      <MiniKeys
        colours={colours}
        picked={new Set(picked.map((note) => midiOf(note.ref)))}
        onPress={onKey}
        title={title}
        disabled={disabled}
        octaves
      />
    </Box>
  );
}

export function FramesNoteToolbox({
  picked,
  notes,
  at,
  frameMs = 40,
  onClose,
  onMoveHand,
  onEdit,
  onRemove,
  onChordKey,
  onSelectFrames,
  onEnhance,
  busy,
  locked,
}: {
  /** The refs picked (`"<frame>:<midi>"`). */
  picked: readonly string[];
  /** Every drawn note, by ref. */
  notes: ReadonlyMap<string, SheetNote>;
  /** Where the panel opens, beside the notes. */
  at: { x: number; y: number } | undefined;
  frameMs?: number;
  onClose: () => void;
  onMoveHand: (hand: Hand) => void;
  /** One reading edit on the picked notes (the refs are added by the page). */
  onEdit: (edit: Omit<ReadingEdit, "notes">) => void;
  onRemove: () => void;
  /** A key of the chord keyboard pressed: add that key to the picked column, or take it off; with `add`, pick it. */
  onChordKey: (midi: number, add: boolean) => void;
  /** Hand the selection to the range toolbox: the frames these notes cover. */
  onSelectFrames: () => void;
  /** Ask the AI to write the stretch of these notes again (`null`: the AI cannot be asked here). */
  onEnhance: (() => void) | null;
  /** An edit is on its way. */
  busy: boolean;
  /** Why the notes cannot be changed now (the AI is writing the sheet), or `null`. */
  locked: string | null;
}) {
  const known = picked.map((ref) => notes.get(ref)).filter((note): note is SheetNote => note !== undefined);
  const frames = known.map((note) => frameOf(note.ref)).sort((a, b) => a - b);
  const first = frames[0];
  const last = frames[frames.length - 1];
  const time = (frame: number) => formatSeconds((frame * frameMs) / 1000);
  const hands = new Set(known.map((note) => note.hand));
  const handNow: Hand | "mixed" = hands.size === 1 ? [...hands][0]! : "mixed";
  const off = busy || locked !== null;
  const why = locked ?? undefined;

  // The chords the picked notes belong to: a figure, a beam, a grace note and an ornament belong to a chord.
  const all = [...notes.values()];
  const chordKeys = [...new Set(known.map(chordOf))];
  const chords = chordKeys.map((key) => all.filter((note) => chordOf(note) === key));
  const heads = chords.map((chord) => chord[0]!).filter(Boolean);
  const figures = new Set(heads.map((note) => (note.grace ? null : note.figure)));
  const figureNow = figures.size === 1 ? [...figures][0] : null;
  const anyFixed = known.some((note) => note.fixed);
  const oneChord = chords.length === 1 && known.length > 1 ? chords[0]! : null;
  const fingersNow = new Set(known.map((note) => note.finger).filter((finger): finger is number => finger !== null));

  // Beams: one hand, notes that follow one another.
  const oneHand = handNow !== "mixed";
  const columns = oneHand ? handColumns(all)[handNow] : [];
  const picks = [...new Set(heads.filter((note) => !note.grace).map((note) => frameOf(note.ref)))].sort((a, b) => a - b);
  const beams = new Set(heads.map((note) => note.beam));
  const oneGroup = beams.size === 1 && [...beams][0] !== null ? [...beams][0]! : null;
  const groupSize = oneGroup === null ? 0 : new Set(all.filter((note) => note.beam === oneGroup).map(chordOf)).size;
  const joinedHere = oneGroup !== null && groupSize === chords.length;
  const beamable = oneHand && picks.length >= 2 && heads.every((note) => !note.grace && (note.figure ?? 0) >= 8);
  const firstPick = picks[0];
  const before = firstPick === undefined ? undefined : columns[columns.indexOf(firstPick) - 1];
  const beamOf = (frame: number | undefined) =>
    frame === undefined ? null : (all.find((note) => note.hand === handNow && !note.grace && frameOf(note.ref) === frame)?.beam ?? null);
  const startsGroup = firstPick !== undefined && beamOf(firstPick) !== beamOf(before) && beamOf(before) !== null;

  const graceNow = heads.length > 0 && heads.every((note) => note.grace);
  const anyGraceRule = known.some((note) => note.graceRule !== null);
  const hasMark = (kind: string) => heads.length > 0 && heads.every((note) => note.ornaments.includes(kind));

  // The keyboard: the picked notes' one column, both hands.
  const columnFrame = oneColumn(known);
  const columnNotes = columnFrame === null ? [] : all.filter((note) => frameOf(note.ref) === columnFrame);

  return (
    <Toolbox
      open={known.length > 0}
      title={known.length === 1 ? printedName(known[0].pitch) : `${known.length} notes`}
      subtitle={first === undefined ? undefined : first === last ? time(first) : `${time(first)} – ${time(last)}`}
      initialPosition={at ?? { x: 420, y: 140 }}
      onClose={onClose}
      headerAction={
        <>
          {onEnhance ? (
            <IconAction
              title="Enhance these notes with AI, with your own words"
              icon={<AutoAwesomeIcon fontSize="small" />}
              onClick={onEnhance}
              disabled={off}
              disabledTitle={why}
              data-testid="notes-enhance"
            />
          ) : null}
          <IconAction
            title="Select the frames of these notes"
            icon={<SwapHorizIcon fontSize="small" />}
            onClick={onSelectFrames}
            data-testid="notes-to-frames"
          />
        </>
      }
    >
      <Stack spacing={1.25} data-frames-note-toolbox>
        {columnFrame !== null ? (
          <>
            <ChordKeys picked={known} column={columnNotes} onKey={onChordKey} disabled={off} why={why} />
            <Divider />
          </>
        ) : null}

        {/* The figures, as the shapes they print as; nothing moves in time. */}
        <Stack direction="row" spacing={0.25} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
          {FIGURES.map(({ figure, name }) => (
            <IconAction
              key={figure}
              title={`Write ${chords.length === 1 ? "as a" : `all ${chords.length} chords as a`} ${FIGURE_SHORT[name].toLowerCase()}`}
              icon={<FigureGlyph figure={name} size={22} />}
              active={figureNow === figure}
              disabled={off}
              disabledTitle={why}
              onClick={() => onEdit({ action: "figure", value: figure })}
              data-testid={`figure-${figure}`}
            />
          ))}
          <IconAction
            title="Back to the figures of the rule"
            icon={<BackspaceIcon fontSize="small" />}
            disabled={off || !anyFixed}
            disabledTitle={why ?? "No figure here was set by hand"}
            onClick={() => onEdit({ action: "figure", value: null })}
          />
        </Stack>

        <Divider />

        <Row label="Finger">
          <ButtonGroup size="small" disabled={off}>
            {FINGERS.map((finger) => (
              <Tooltip
                key={finger}
                title={
                  oneChord
                    ? `Finger ${finger}. Press up to ${oneChord.length} numbers, one per note`
                    : `Finger ${finger} on every note picked`
                }
              >
                <Button
                  variant={fingersNow.has(finger) ? "contained" : "outlined"}
                  onClick={() => {
                    const now = [...fingersNow];
                    const next = oneChord
                      ? now.includes(finger)
                        ? now.filter((one) => one !== finger)
                        : [...now, finger].slice(-oneChord.length)
                      : now.length === 1 && now[0] === finger
                        ? []
                        : [finger];
                    onEdit({ action: "finger", value: next });
                  }}
                  data-finger={finger}
                  sx={{ minWidth: 32, px: 0 }}
                >
                  {finger}
                </Button>
              </Tooltip>
            ))}
          </ButtonGroup>
          <IconAction
            title="Remove the finger numbers"
            icon={<BackspaceIcon fontSize="small" />}
            disabled={off || fingersNow.size === 0}
            disabledTitle={why}
            onClick={() => onEdit({ action: "finger", value: [] })}
          />
        </Row>

        {/*
          Which hand plays them, written into the notes: a note's figure is its length up to the next note of its
          hand, so its neighbours may change figure too. The AI may change it again on its next run.
        */}
        <Row label="Hand">
          <Segmented<Hand | "mixed">
            label="Which hand plays these notes"
            value={handNow}
            disabled={off}
            options={[
              { value: "right", label: "Right", tooltip: locked ?? "Play with the right hand" },
              { value: "left", label: "Left", tooltip: locked ?? "Play with the left hand" },
            ]}
            onChange={(side) => {
              if (side !== "mixed" && side !== handNow) onMoveHand(side);
            }}
          />
          {busy ? <CircularProgress size={14} sx={{ ml: 1 }} /> : null}
        </Row>

        <Row label="Beam">
          <IconAction
            title={joinedHere ? "Remove the beam" : "Beam these notes as one group"}
            disabledTitle={why ?? "Pick two or more notes of one hand, all a corchea or shorter"}
            icon={<LinkIcon fontSize="small" />}
            active={joinedHere}
            disabled={off || (!beamable && !joinedHere)}
            onClick={() => onEdit({ action: "beam-join" })}
            data-testid="beam-join"
          />
          <IconAction
            title={startsGroup ? "Join to the beam before" : "Start a new beam here"}
            disabledTitle={why ?? "Pick a note of one hand"}
            icon={<ContentCutIcon fontSize="small" />}
            active={startsGroup}
            disabled={off || !oneHand || picks.length === 0}
            onClick={() => onEdit({ action: "beam-break" })}
            data-testid="beam-break"
          />
        </Row>

        <Row label="Grace">
          <IconAction
            title={graceNow ? "Write as normal notes" : "Write as grace notes of the next note"}
            disabledTitle={why}
            icon={<FigureGlyph figure="corchea" size={graceNow ? 22 : 15} />}
            active={graceNow}
            disabled={off}
            onClick={() => onEdit({ action: "grace", value: graceNow ? "off" : "on" })}
            data-testid="grace"
          />
          <IconAction
            title="Back to the grace rule"
            icon={<BackspaceIcon fontSize="small" />}
            disabled={off || !anyGraceRule}
            disabledTitle={why ?? "These notes follow the grace rule"}
            onClick={() => onEdit({ action: "grace", value: null })}
          />
        </Row>

        <Row label="Marks">
          {SPAN_ORNAMENTS.map(({ kind, glyph, title }) => (
            <IconAction
              key={kind}
              title={hasMark(kind) ? `Print the ${kind} as notes` : title}
              disabledTitle={why ?? "Pick notes of one hand"}
              icon={<MarkGlyph text={glyph} />}
              active={hasMark(kind)}
              disabled={off || !oneHand}
              onClick={() => onEdit({ action: "ornament", value: kind })}
              data-testid={`ornament-${kind}`}
            />
          ))}
          <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
          {CHORD_ORNAMENTS.map(({ kind, glyph, title }) => (
            <IconAction
              key={kind}
              title={hasMark(kind) ? `Remove the ${kind === "arpeggio" ? "rolled chord" : "fermata"}` : title}
              disabledTitle={why}
              icon={<MarkGlyph text={glyph} />}
              active={hasMark(kind)}
              disabled={off}
              onClick={() => onEdit({ action: "ornament", value: kind })}
              data-testid={`ornament-${kind}`}
            />
          ))}
        </Row>

        <Divider />

        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <IconAction
            title={`Take ${known.length === 1 ? "this note" : `these ${known.length} notes`} off the page`}
            shortcut="Delete"
            icon={<DeleteOutlineIcon />}
            danger
            disabled={off}
            disabledTitle={why}
            onClick={onRemove}
            data-testid="notes-remove"
          />
          {known.length > 1 ? (
            <Typography variant="body2" color="text.secondary">
              {oneChord
                ? oneChord.length > known.length
                  ? `${known.length} notes of a chord of ${oneChord.length}`
                  : `One chord of ${oneChord.length}`
                : `${chords.length} chords`}
            </Typography>
          ) : null}
        </Stack>
      </Stack>
    </Toolbox>
  );
}

export default FramesNoteToolbox;
