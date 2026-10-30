/**
 * The **catalog** of patterns inside **Enhance with AI** (implementation 04-3, Phase 4; plan section 5.10): the gallery
 * of patterns, numbered inside each hand and level ("left hand, medium 2"), each drawn by the app's engine from its F1
 * text. First the left hand, then the right hand; pills by level. The user selects the patterns the level run uses;
 * only those go into the AI's prompt.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { CatalogPattern, LevelCatalog } from "../../../../api";
import { Pill, PillButton, Segmented } from "../../../../ui";
import { drawingUrl, shortRef, type CatalogHand } from "./patterns";

const LEVELS: { value: CatalogPattern["level"]; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
  { value: "super hard", label: "Super hard" },
];

const HAND_LABELS: Record<CatalogHand, string> = { left: "Left hand", right: "Right hand" };

export interface PatternCatalogProps {
  catalog: LevelCatalog;
  /** The hands the run writes, in the order shown (the left hand first). */
  hands: CatalogHand[];
  /** The level of each hand: the pill each hand opens on. */
  levels: Record<CatalogHand, string>;
  selected: string[];
  onDone: (selected: string[]) => void;
  onCancel: () => void;
}

export function PatternCatalog({ catalog, hands, levels, selected: start, onDone, onCancel }: PatternCatalogProps) {
  const [hand, setHand] = useState<CatalogHand>(hands[0]);
  const [level, setLevel] = useState<Record<CatalogHand, string>>(levels);
  const [selected, setSelected] = useState<string[]>(start);
  const shown = catalog.patterns.filter((one) => one.hand === hand && one.level === level[hand]);
  const toggle = (ref: string) =>
    setSelected((now) => (now.includes(ref) ? now.filter((one) => one !== ref) : [...now, ref]));
  const count = (side: CatalogHand) => selected.filter((ref) => ref.startsWith(`${side} `)).length;

  return (
    <Dialog open onClose={onCancel} maxWidth="md" fullWidth data-pattern-catalog>
      <DialogTitle>Patterns</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5}>
          {hands.length > 1 ? (
            <Segmented<CatalogHand>
              label="Which hand"
              value={hand}
              options={hands.map((one) => ({ value: one, label: `${HAND_LABELS[one]} (${count(one)})` }))}
              onChange={setHand}
            />
          ) : null}
          <Stack direction="row" spacing={1}>
            {LEVELS.map((one) => (
              <Pill
                key={one.value}
                label={one.label}
                selected={level[hand] === one.value}
                onClick={() => setLevel((now) => ({ ...now, [hand]: one.value }))}
              />
            ))}
          </Stack>
          {shown.map((pattern) => (
            <Box
              key={pattern.ref}
              data-pattern={pattern.ref}
              onClick={() => toggle(pattern.ref)}
              sx={{
                display: "flex",
                gap: 1,
                p: 1,
                borderRadius: 1,
                cursor: "pointer",
                border: 1,
                borderColor: selected.includes(pattern.ref) ? "primary.main" : "divider",
              }}
            >
              <Checkbox size="small" checked={selected.includes(pattern.ref)} sx={{ alignSelf: "flex-start", p: 0.5 }} />
              <Stack spacing={0.5} sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {shortRef(pattern.ref)} · {pattern.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {pattern.line}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {pattern.source}
                  {pattern.bars ? `, bars ${pattern.bars}` : ""}
                </Typography>
                <Box
                  component="img"
                  loading="lazy"
                  alt={pattern.name}
                  src={drawingUrl(pattern)}
                  sx={{ display: "block", maxWidth: "100%", maxHeight: 220, objectFit: "contain", objectPosition: "left", bgcolor: "#fff" }}
                />
              </Stack>
            </Box>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => onDone(selected)} data-testid="catalog-done">
          Use {selected.length} pattern{selected.length === 1 ? "" : "s"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default PatternCatalog;
