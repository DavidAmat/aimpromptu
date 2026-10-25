/**
 * The note toolbox of the new sheet (implementation 03, Phase 6): what can be said about the notes picked on it.
 *
 * Phase 6 has the first tool, the hand: **Right / Left** writes the hand of every picked note into the notes
 * themselves (the numeric truth, plan section 3.7), and the sheet is drawn again. The figures, fingers, beams and
 * the rest of the old note toolbox come in Phase 7, on the same edit model. The panel is the old one's: titled
 * with the note's printed name (`Do-# 5`) or the number of notes, the time under it, dragged by its title bar.
 */

import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import type { SheetNote } from "../../../../api";
import { spanishNoteName } from "../../../../music/noteNames";
import { Segmented, Toolbox } from "../../../../ui";
import { formatSeconds } from "../sheetConstants";

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

/** `C#5` as the sheet prints it, in solfège: `Do-# 5`. */
function printedName(pitch: string): string {
  const match = /^([A-G])([#b]?)(-?\d+)$/.exec(pitch);
  if (!match) return pitch;
  const [, letter, sign, octave] = match;
  return spanishNoteName({ letter, accidental: sign === "#" ? 1 : sign === "b" ? -1 : 0, octave: Number(octave) });
}

export function FramesNoteToolbox({
  picked,
  notes,
  at,
  frameMs = 40,
  onClose,
  onMoveHand,
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
  /** An edit is on its way. */
  busy: boolean;
  /** Why the notes cannot be changed now (the AI is writing the sheet), or `null`. */
  locked: string | null;
}) {
  const known = picked.map((ref) => notes.get(ref)).filter((note): note is SheetNote => note !== undefined);
  const frames = known.map((note) => Number(note.ref.split(":")[0])).sort((a, b) => a - b);
  const first = frames[0];
  const last = frames[frames.length - 1];
  const time = (frame: number) => formatSeconds((frame * frameMs) / 1000);
  const hands = new Set(known.map((note) => note.hand));
  const handNow: Hand | "mixed" = hands.size === 1 ? [...hands][0]! : "mixed";

  return (
    <Toolbox
      open={known.length > 0}
      title={known.length === 1 ? printedName(known[0].pitch) : `${known.length} notes`}
      subtitle={first === undefined ? undefined : first === last ? time(first) : `${time(first)} – ${time(last)}`}
      initialPosition={at ?? { x: 420, y: 140 }}
      onClose={onClose}
    >
      <Stack spacing={1.25} data-frames-note-toolbox>
        {/*
          Which hand plays them, written into the notes: a note's figure is its length up to the next note of its
          hand, so its neighbours may change figure too. The AI may change it again on its next run.
        */}
        <Row label="Hand">
          <Segmented<Hand | "mixed">
            label="Which hand plays these notes"
            value={handNow}
            disabled={busy || locked !== null}
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
      </Stack>
    </Toolbox>
  );
}

export default FramesNoteToolbox;
