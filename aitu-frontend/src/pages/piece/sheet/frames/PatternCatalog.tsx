/**
 * The **gallery of patterns** inside **Enhance with AI** (implementation 04-3, Phase 4; plan section 5.10; inside the
 * dialog since the user's request of 2026-10-30): the patterns numbered inside each hand and level ("left hand, medium
 * 2"), each drawn by the app's engine from its F1 text. Only the hands the run rewrites are shown (the left hand first,
 * with a button per hand when both are rewritten), with pills by level that open on the hand's level. The user ticks
 * the patterns the level run uses; only those go into the AI's prompt, and the words may name them ("medium 2").
 */

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { CatalogPattern, LevelCatalog } from "../../../../api";
import { Pill, Segmented } from "../../../../ui";
import { drawingUrl, shortRef, type CatalogHand } from "./patterns";

export type GalleryLevel = CatalogPattern["level"];

const LEVELS: { value: GalleryLevel; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
  { value: "super hard", label: "Super hard" },
];

const HAND_LABELS: Record<CatalogHand, string> = { left: "Left hand", right: "Right hand" };

export interface PatternGalleryProps {
  catalog: LevelCatalog;
  /** The hands the run rewrites, in the order shown (the left hand first). */
  hands: CatalogHand[];
  /** The hand shown, and the level shown for each hand (the pills). */
  hand: CatalogHand;
  shownLevels: Record<CatalogHand, GalleryLevel>;
  onHand: (hand: CatalogHand) => void;
  onLevel: (hand: CatalogHand, level: GalleryLevel) => void;
  /** The refs ticked, of every hand. */
  selected: string[];
  onToggle: (ref: string) => void;
  /** Tick every pattern of the hand shown at the level of its pill; untick every pattern of that hand; tick the
   * patterns approved for the hand's level again (as the dialog opens). */
  onSelectAll: (hand: CatalogHand, refs: string[]) => void;
  onDeselectAll: (hand: CatalogHand) => void;
  onApproved: (hand: CatalogHand) => void;
}

export function PatternGallery({
  catalog,
  hands,
  hand,
  shownLevels,
  onHand,
  onLevel,
  selected,
  onToggle,
  onSelectAll,
  onDeselectAll,
  onApproved,
}: PatternGalleryProps) {
  const shown = catalog.patterns.filter((one) => one.hand === hand && one.level === shownLevels[hand]);
  const count = (side: CatalogHand) => selected.filter((ref) => ref.startsWith(`${side} `)).length;

  return (
    <Stack spacing={1} data-pattern-gallery>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        <Typography variant="subtitle2">Patterns</Typography>
        {hands.length > 1 ? (
          <Segmented<CatalogHand>
            label="The patterns of which hand"
            value={hand}
            options={hands.map((one) => ({ value: one, label: `${HAND_LABELS[one]} (${count(one)})` }))}
            onChange={onHand}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">
            {HAND_LABELS[hand]} ({count(hand)})
          </Typography>
        )}
        <Stack direction="row" spacing={0.75}>
          {LEVELS.map((one) => (
            <Pill key={one.value} label={one.label} selected={shownLevels[hand] === one.value} onClick={() => onLevel(hand, one.value)} />
          ))}
        </Stack>
        <Stack direction="row" spacing={0.5} data-pattern-bulk>
          <Button size="small" onClick={() => onSelectAll(hand, shown.map((one) => one.ref))} disabled={shown.every((one) => selected.includes(one.ref))}>
            Select all
          </Button>
          <Button size="small" onClick={() => onDeselectAll(hand)} disabled={count(hand) === 0}>
            Deselect all
          </Button>
          <Button size="small" onClick={() => onApproved(hand)}>
            Approved
          </Button>
        </Stack>
      </Stack>
      <Box
        sx={{ maxHeight: 380, overflowY: "auto", pr: 0.5, display: "flex", flexDirection: "column", gap: 1 }}
        data-pattern-list
      >
        {shown.map((pattern) => (
          <Box
            key={pattern.ref}
            data-pattern={pattern.ref}
            onClick={() => onToggle(pattern.ref)}
            sx={{
              display: "flex",
              gap: 1,
              p: 1,
              borderRadius: 1,
              cursor: "pointer",
              border: 1,
              borderColor: selected.includes(pattern.ref) ? "primary.main" : "divider",
              flexShrink: 0,
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
                sx={{ display: "block", maxWidth: "100%", maxHeight: 200, objectFit: "contain", objectPosition: "left", bgcolor: "#fff" }}
              />
            </Stack>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}

export default PatternGallery;
