/**
 * **Enhance with AI** (implementation 04, Phase 4; reworked on the user's request of 2026-10-30): one dialog, two tabs
 * that work the same way.
 *
 * - **A stretch** (open when notes or a stretch are selected; implementation 03, Phase 7): both hands, only the right
 *   or only the left (the other hand then stays exactly as it is), and either **a level** or the user's own words: the
 *   AI writes that stretch again under the pale veil; one step of undo.
 * - **The whole song** (open when nothing is selected): **a level** of the whole sheet, the right hand only or the left
 *   hand only, written into a new project of My projects named with the level (the original stays); or **Write it all
 *   again** (the AI writes the hands and the reading of the whole song). Simplifying a hand is a level of that hand;
 *   the older Simplify run without a level is no longer offered here.
 *
 * A level is Easy, Medium or Hard for each hand rewritten (the same for both by default). Under it, the **gallery of
 * patterns** of those hands (`PatternGallery`), inside the dialog: the patterns approved for the level are ticked, the
 * user may tick others, and the words may name them and places ("at frame 112 use hard 3").
 *
 * The cost and the time of each run, about, are read from the backend when the dialog opens. On a version of My
 * library, Write it all again runs in the edit copy, as **Edit** opens it; a level goes into its new project.
 */

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  sheetApi,
  type LevelCatalog,
  type LevelChoice,
  type LevelHand,
  type LevelName,
  type LlmCost,
  type LlmCosts,
  type SongRun,
} from "../../../../api";
import { PillButton, Segmented } from "../../../../ui";
import { PatternGallery, type GalleryLevel } from "./PatternCatalog";
import { shortRef, type CatalogHand } from "./patterns";

/** As the backend takes them (`REQUEST_CHARS`). */
const MAX_WORDS = 1000;

export type EnhanceTab = "stretch" | "song";
export type StretchHand = "both" | "right" | "left";
/** What the dialog runs on the whole song: one of today's runs, or a level. */
export type SongChoice = SongRun | "level";

const TABS = [
  { value: "stretch" as const, label: "A stretch" },
  { value: "song" as const, label: "The whole song" },
];

const HANDS = [
  { value: "both" as const, label: "Both" },
  { value: "right" as const, label: "Right" },
  { value: "left" as const, label: "Left" },
];

const SONG_HANDS = [
  { value: "both" as const, label: "The whole sheet" },
  { value: "right" as const, label: "Right hand only" },
  { value: "left" as const, label: "Left hand only" },
];

type How = "words" | "level";
const HOW = [
  { value: "words" as const, label: "Your words" },
  { value: "level" as const, label: "A level" },
];

const LEVELS: { value: LevelName; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

type SongHow = "level" | "all";
const SONG_HOW = [
  { value: "level" as const, label: "A level" },
  { value: "all" as const, label: "Write it all again" },
];

function dollars(cost: LlmCost | undefined): string {
  return cost === undefined ? "" : `$${cost.usd.toFixed(2)}`;
}

/** About how long a run takes, as the backend estimates it from what GPT-6.1 Terra measured (implementation 04-3,
 * Phase 5): "about 3 minutes", or "" before the costs arrive. */
function timeOf(cost: LlmCost | undefined): string {
  if (!cost) return "";
  const most =
    cost.minutes ?? Math.max(1, Math.round((cost.requests * 45) / 60));
  return `about ${most} minute${most === 1 ? "" : "s"}`;
}

function minutes(cost: LlmCost | undefined): string {
  return cost ? `, ${timeOf(cost)}` : "";
}

/** The hands a level writes, the left hand first (as the catalog shows them). */
const handsOf = (hand: LevelHand): CatalogHand[] =>
  hand === "both" ? ["left", "right"] : [hand];

export interface EnhanceDialogProps {
  open: boolean;
  audioUuid: string;
  /** The tab it opens on. */
  tab: EnhanceTab;
  /** The selection the stretch tab writes again, its frames, and its hand when it is one hand; `null`: nothing. */
  stretch: {
    what: string;
    hand: StretchHand;
    start: number;
    end: number;
  } | null;
  /** The AI enhanced this sheet already. */
  enhanced: boolean;
  /** A version of My library: the whole song runs in the edit copy. */
  viaEdit: boolean;
  onStretch: (hand: StretchHand, words: string) => void;
  /** A level of the selected stretch. */
  onStretchLevel: (choice: LevelChoice) => void;
  onSong: (run: SongRun) => void;
  /** A level of the whole sheet: a new project. */
  onSongLevel: (choice: LevelChoice) => void;
  onCancel: () => void;
}

export function EnhanceDialog({
  open,
  audioUuid,
  tab: opening,
  stretch,
  enhanced,
  viaEdit,
  onStretch,
  onStretchLevel,
  onSong,
  onSongLevel,
  onCancel,
}: EnhanceDialogProps) {
  const [tab, setTab] = useState<EnhanceTab>(opening);
  const [hand, setHand] = useState<StretchHand>(stretch?.hand ?? "both");
  const [how, setHow] = useState<How>("words");
  const [songHand, setSongHand] = useState<LevelHand>("both");
  // A sheet the AI has not written yet is first written whole; then a level is the usual run.
  const [songHow, setSongHow] = useState<SongHow>(enhanced ? "level" : "all");
  const [words, setWords] = useState("");
  const [levels, setLevels] = useState<Record<CatalogHand, LevelName>>({
    right: "easy",
    left: "easy",
  });
  /** The patterns the user chose for each hand; `null`: the patterns approved for its level. */
  const [chosen, setChosen] = useState<Record<CatalogHand, string[] | null>>({
    right: null,
    left: null,
  });
  /** What the gallery shows: the hand, and the level of each hand (it follows the hand's level). */
  const [galleryHand, setGalleryHand] = useState<CatalogHand>("left");
  const [shownLevels, setShownLevels] = useState<
    Record<CatalogHand, GalleryLevel>
  >({ right: "easy", left: "easy" });
  const [costs, setCosts] = useState<LlmCosts | null>(null);
  const [catalog, setCatalog] = useState<LevelCatalog | null>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    sheetApi
      .llmCosts(
        audioUuid,
        controller.signal,
        stretch ? { start: stretch.start, end: stretch.end } : undefined,
      )
      .then(setCosts)
      .catch(() => {
        // Without the cost the dialog still works: it only says less.
      });
    sheetApi
      .levelCatalog(controller.signal)
      .then(setCatalog)
      .catch(() => {
        // Without the catalog a level uses the patterns approved for it (the backend's defaults).
      });
    return () => controller.abort();
  }, [open, audioUuid, stretch]);

  const onStretchTab = tab === "stretch" && stretch !== null;
  const level = onStretchTab ? how === "level" : songHow === "level";
  const levelHand: LevelHand = onStretchTab ? hand : songHand;
  const hands = handsOf(levelHand);
  const shownHand = hands.includes(galleryHand) ? galleryHand : hands[0];
  const picked = (side: CatalogHand): string[] =>
    chosen[side] ?? catalog?.defaults[side][levels[side]] ?? [];
  const patterns = useMemo(
    () =>
      hands.flatMap(
        (side) => chosen[side] ?? catalog?.defaults[side][levels[side]] ?? [],
      ),
    [hands, chosen, catalog, levels],
  );
  const choice: LevelChoice = {
    right: levels.right,
    left: levels.left,
    hand: levelHand,
    patterns,
    words: words.trim(),
  };

  const setLevel = (side: CatalogHand, value: LevelName) => {
    setLevels((now) => ({ ...now, [side]: value }));
    setShownLevels((now) => ({ ...now, [side]: value }));
    setGalleryHand(side);
  };
  const toggle = (ref: string) => {
    const side = ref.split(" ")[0] as CatalogHand;
    const now = picked(side);
    setChosen((all) => ({
      ...all,
      [side]: now.includes(ref)
        ? now.filter((one) => one !== ref)
        : [...now, ref],
    }));
  };

  const confirm = () => {
    if (onStretchTab) {
      if (level) onStretchLevel(choice);
      else onStretch(hand, words.trim());
    } else if (level) onSongLevel(choice);
    else onSong("all");
  };
  const other = hand === "right" ? "left" : "right";
  const levelKey: `level-${LevelHand}` | `level-stretch-${LevelHand}` =
    onStretchTab ? `level-stretch-${levelHand}` : `level-${levelHand}`;
  const levelCost = costs?.[levelKey];
  const status = onStretchTab
    ? `${hand === "both" ? "" : `The ${other} hand stays as it is. `}About ${level ? `${dollars(levelCost) || "a few cents"}${minutes(levelCost)}` : `${dollars(costs?.stretch) || "one cent"}${minutes(costs?.stretch)}`}. Undo takes it back.`
    : level
      ? `A new project in My projects, named with the level. This sheet stays as it is. About ${dollars(levelCost)}${minutes(levelCost)}.`
      : [
          viaEdit
            ? "This opens a copy in Projects, as Edit does, and the AI works there."
            : "",
          enhanced
            ? `The AI writes the hands and the reading again, in ${timeOf(costs?.all) || "a few minutes"}. If it does not finish, the sheet you have now stays.`
            : `The AI writes the hands and the reading, part by part, in ${timeOf(costs?.all) || "a few minutes"}. The hands you have now are kept in the history.`,
          costs?.all ? `About ${dollars(costs.all)}.` : "",
        ]
          .filter(Boolean)
          .join(" ");

  const wordsField = (
    <TextField
      autoFocus={onStretchTab && !level}
      fullWidth
      multiline
      minRows={level ? 1 : 2}
      maxRows={6}
      label={level ? "Your words (optional)" : "What should the AI change?"}
      placeholder={
        level ? "At frame 112 use medium 2." : "Make the octaves single notes."
      }
      value={words}
      onChange={(event) => setWords(event.target.value.slice(0, MAX_WORDS))}
      onKeyDown={(event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey))
          confirm();
      }}
      slotProps={{ htmlInput: { "data-testid": "stretch-words" } }}
    />
  );

  const levelControls = (
    <Stack spacing={1.5} data-level-controls>
      {hands
        .slice()
        .reverse()
        .map((side) => (
          <Stack
            key={side}
            direction="row"
            spacing={1.5}
            sx={{ alignItems: "center" }}
          >
            <Typography variant="body2" sx={{ width: 84 }}>
              {side === "right" ? "Right hand" : "Left hand"}
            </Typography>
            <Segmented<LevelName>
              label={`The level of the ${side} hand`}
              value={levels[side]}
              options={LEVELS}
              onChange={(value) => setLevel(side, value)}
            />
          </Stack>
        ))}
      <Typography variant="body2" color="text.secondary" data-level-patterns>
        {hands
          .map(
            (side) =>
              `${side === "right" ? "Right" : "Left"}: ${picked(side).map(shortRef).join(", ") || "-"}`,
          )
          .join(" · ")}
      </Typography>
      {wordsField}
    </Stack>
  );

  // Under the cost and the time, so those stay in sight while the user scrolls the patterns.
  const gallery =
    level && catalog ? (
      <PatternGallery
        catalog={catalog}
        hands={hands}
        hand={shownHand}
        shownLevels={shownLevels}
        onHand={setGalleryHand}
        onLevel={(side, value) =>
          setShownLevels((now) => ({ ...now, [side]: value }))
        }
        selected={hands.flatMap(picked)}
        onToggle={toggle}
      />
    ) : null;

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      maxWidth="md"
      fullWidth
      data-enhance-dialog
    >
      <DialogTitle>
        {enhanced ? "Enhance it again with AI" : "Enhance with AI"}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <Segmented<EnhanceTab>
            label="What the AI works on"
            value={onStretchTab ? "stretch" : "song"}
            options={TABS.map((one) =>
              one.value === "stretch" && stretch === null
                ? {
                    ...one,
                    disabled: true,
                    tooltip: "Select notes or a stretch first",
                  }
                : one,
            )}
            onChange={setTab}
          />
          {onStretchTab ? (
            <>
              <Stack
                direction="row"
                spacing={1.5}
                sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
              >
                <Segmented<StretchHand>
                  label="Which hand"
                  value={hand}
                  options={HANDS}
                  onChange={setHand}
                />
                <Segmented<How>
                  label="How"
                  value={how}
                  options={HOW}
                  onChange={setHow}
                />
                <Typography variant="body2" color="text.secondary" noWrap>
                  {stretch.what}
                </Typography>
              </Stack>
              {level ? levelControls : wordsField}
            </>
          ) : (
            <>
              <Stack
                direction="row"
                spacing={1.5}
                sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
              >
                <Segmented<SongHow>
                  label="What the AI does"
                  value={songHow}
                  options={SONG_HOW}
                  onChange={setSongHow}
                />
                {level ? (
                  <Segmented<LevelHand>
                    label="Which hands"
                    value={songHand}
                    options={SONG_HANDS}
                    onChange={setSongHand}
                  />
                ) : null}
              </Stack>
              {level ? levelControls : null}
            </>
          )}
          <Typography
            variant="body2"
            color="text.secondary"
            data-enhance-status
          >
            {status}
          </Typography>
          {gallery}
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel}>
          Cancel
        </PillButton>
        <PillButton
          kind="primary"
          onClick={confirm}
          data-testid={onStretchTab ? "stretch-confirm" : "song-confirm"}
        >
          {level
            ? "Write the level"
            : onStretchTab
              ? "Enhance with AI"
              : "Write it all again"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default EnhanceDialog;
