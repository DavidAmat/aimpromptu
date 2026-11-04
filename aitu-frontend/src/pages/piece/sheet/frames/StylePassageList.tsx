/**
 * The list of **Copy this style** (implementation 06, plan section 4.2): the reference, then the passages of the song
 * the code found like it, in the order of the song, each with the number and the colour the sheet draws it with, its
 * time, its frames and how similar it is. All ticked at first; a passage not ticked is neither drawn nor written.
 */

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import type { StylePassage } from "../../../../api";
import { formatTime } from "../../../../audio/time";
import { timestampSx } from "../../../../ui/timestamps";
import { batchColour, passageKey, REFERENCE_COLOUR } from "./batches";
import { BatchNumber } from "./BatchNumber";

const FRAME_SECONDS = 0.04;
/** From here a passage is "Very similar": in the study of Phase 1 the repeats score 0.84 and more, the variants of a
 * cover 0.6 to 0.8. */
const VERY_SIMILAR = 0.8;

/** The key of a passage: "a tone higher", "3 semitones lower"; "" in the same key. */
function keyWords(shift: number): string {
  const size = Math.abs(shift);
  if (size === 0) return "";
  const step = size === 1 ? "a semitone" : size === 2 ? "a tone" : `${size} semitones`;
  return `${step} ${shift > 0 ? "higher" : "lower"}`;
}

/** "Very similar, a tone higher". */
function similarWords(passage: StylePassage): string {
  return [passage.score >= VERY_SIMILAR ? "Very similar" : "Similar", keyWords(passage.shift)].filter(Boolean).join(", ");
}

function Row({ start, end, words, children }: { start: number; end: number; words: string; children: ReactNode }) {
  return (
    <>
      {children}
      <Typography variant="body2" sx={{ ...timestampSx, flexShrink: 0 }}>
        {formatTime(start * FRAME_SECONDS)} – {formatTime(end * FRAME_SECONDS)}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
        f{start}-f{end}
      </Typography>
      <Typography variant="body2" color="text.secondary" noWrap title={words} sx={{ flex: 1, minWidth: 0, textAlign: "right" }}>
        {words}
      </Typography>
    </>
  );
}

const ROW = { display: "flex", alignItems: "center", gap: 1, minHeight: 36, borderBottom: 1, borderColor: "divider" };
/** Where the tick of a passage is, on the row of the reference. */
const TICK_WIDTH = 34;

export interface StylePassageListProps {
  reference: readonly [number, number];
  /** `null`: not known yet. */
  passages: readonly StylePassage[] | null;
  /** The keys of the passages not ticked. */
  off: readonly string[];
  onOff: (keys: string[]) => void;
}

export function StylePassageList({ reference, passages, off, onOff }: StylePassageListProps) {
  const found = passages ?? [];
  const toggle = (key: string) => onOff(off.includes(key) ? off.filter((one) => one !== key) : [...off, key]);
  return (
    <Box data-style-list>
      <Box sx={ROW} data-style-reference>
        <Row start={reference[0]} end={reference[1]} words="The reference">
          <Box sx={{ width: TICK_WIDTH, flexShrink: 0, display: "flex", justifyContent: "center" }}>
            <BatchNumber colour={REFERENCE_COLOUR} size={24}>
              R
            </BatchNumber>
          </Box>
        </Row>
      </Box>
      {found.length > 0 ? (
        <>
          {/* Eight rows and a half: the row cut in two says the list goes on. */}
          <Box sx={{ maxHeight: 310, overflowY: "auto" }}>
            {found.map((passage, index) => {
              const key = passageKey(passage);
              return (
                <Box key={key} component="label" sx={{ ...ROW, cursor: "pointer" }} data-style-passage={index + 1}>
                  <Row start={passage.start} end={passage.end} words={similarWords(passage)}>
                    <Checkbox
                      size="small"
                      checked={!off.includes(key)}
                      onChange={() => toggle(key)}
                      sx={{ p: 0.5, width: TICK_WIDTH, flexShrink: 0 }}
                      slotProps={{ input: { "aria-label": `Passage ${index + 1}` } }}
                    />
                    <BatchNumber colour={batchColour(index)} size={24}>
                      {index + 1}
                    </BatchNumber>
                  </Row>
                </Box>
              );
            })}
          </Box>
          <Stack direction="row" spacing={0.5} sx={{ pt: 0.5 }} data-style-bulk>
            <Button size="small" onClick={() => onOff([])} disabled={off.length === 0}>
              Select all
            </Button>
            <Button size="small" onClick={() => onOff(found.map(passageKey))} disabled={off.length >= found.length}>
              Deselect all
            </Button>
          </Stack>
        </>
      ) : null}
    </Box>
  );
}

export default StylePassageList;
