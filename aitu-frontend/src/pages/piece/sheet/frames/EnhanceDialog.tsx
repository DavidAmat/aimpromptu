/**
 * **Enhance with AI** (implementation 04, Phase 4; the user's request after the Phase 3 gallery): one dialog, two
 * tabs.
 *
 * - **A stretch** (open when notes or a stretch are selected; implementation 03, Phase 7): both hands, only the right
 *   or only the left (the other hand then stays exactly as it is), and either the user's own words, or **a level**
 *   (implementation 04-3, Phase 4): the AI writes that stretch again in a few seconds, under the pale veil; one step
 *   of undo.
 * - **The whole song** (open when nothing is selected): **Simplify** the left hand, the right hand or both (the rules
 *   of simplicity only: uniform patterns, no quick jumps; the hands stay; batch after batch, one step of undo),
 *   **Write it all again** (the full run of the AI), or **A level** of the whole sheet, the right hand only or the
 *   left hand only, written into a new project of My projects named with the level (the original stays).
 *
 * A level is Easy, Medium or Hard for each hand (the user, 2026-10-30: the same for both by default), with the
 * patterns of the **catalog** (`PatternCatalog`): the patterns approved for that level are selected when the dialog
 * opens, and the user may choose others. The words may name patterns and places ("at frame 112 use hard 3").
 *
 * The cost of each run, about, is read from the backend when the dialog opens. On a version of My library the whole
 * song runs in the edit copy, as **Edit** opens it; a level goes into its new project.
 */

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
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
import { PatternCatalog } from "./PatternCatalog";
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

const RUNS: { value: SongChoice; label: string }[] = [
  { value: "level", label: "A level" },
  { value: "simplify-left", label: "Simplify the left hand" },
  { value: "simplify-right", label: "Simplify the right hand" },
  { value: "simplify-both", label: "Simplify both hands" },
  { value: "all", label: "Write it all again" },
];

function dollars(cost: LlmCost | undefined): string {
  return cost === undefined ? "" : `$${cost.usd.toFixed(2)}`;
}

/** About how long a run takes, as the backend estimates it from what GPT-6.1 Terra measured (implementation 04-3,
 * Phase 5): "about 3 minutes", or "" before the costs arrive. */
function timeOf(cost: LlmCost | undefined): string {
  if (!cost) return "";
  const most = cost.minutes ?? Math.max(1, Math.round((cost.requests * 45) / 60));
  return `about ${most} minute${most === 1 ? "" : "s"}`;
}

function minutes(cost: LlmCost | undefined): string {
  return cost ? `, ${timeOf(cost)}` : "";
}

/** The hands a level writes, the left hand first (as the catalog shows them). */
const handsOf = (hand: LevelHand): CatalogHand[] => (hand === "both" ? ["left", "right"] : [hand]);

export interface EnhanceDialogProps {
  open: boolean;
  audioUuid: string;
  /** The tab it opens on. */
  tab: EnhanceTab;
  /** The selection the stretch tab writes again, its frames, and its hand when it is one hand; `null`: nothing. */
  stretch: { what: string; hand: StretchHand; start: number; end: number } | null;
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
  const [words, setWords] = useState("");
  const [run, setRun] = useState<SongChoice>(enhanced ? "simplify-left" : "all");
  const [levels, setLevels] = useState<Record<CatalogHand, LevelName>>({ right: "easy", left: "easy" });
  /** The patterns the user chose for each hand; `null`: the patterns approved for its level. */
  const [chosen, setChosen] = useState<Record<CatalogHand, string[] | null>>({ right: null, left: null });
  const [browsing, setBrowsing] = useState(false);
  const [costs, setCosts] = useState<LlmCosts | null>(null);
  const [catalog, setCatalog] = useState<LevelCatalog | null>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    sheetApi
      .llmCosts(audioUuid, controller.signal, stretch ? { start: stretch.start, end: stretch.end } : undefined)
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
  const level = onStretchTab ? how === "level" : run === "level";
  const levelHand: LevelHand = onStretchTab ? hand : songHand;
  const hands = handsOf(levelHand);
  const picked = (side: CatalogHand): string[] => chosen[side] ?? catalog?.defaults[side][levels[side]] ?? [];
  const patterns = useMemo(() => hands.flatMap((side) => chosen[side] ?? catalog?.defaults[side][levels[side]] ?? []), [hands, chosen, catalog, levels]);
  const choice: LevelChoice = { right: levels.right, left: levels.left, hand: levelHand, patterns, words: words.trim() };

  const confirm = () => {
    if (onStretchTab) {
      if (level) onStretchLevel(choice);
      else onStretch(hand, words.trim());
    } else if (run === "level") onSongLevel(choice);
    else onSong(run);
  };
  const other = hand === "right" ? "left" : "right";
  const levelKey: `level-${LevelHand}` | `level-stretch-${LevelHand}` = onStretchTab ? `level-stretch-${levelHand}` : `level-${levelHand}`;
  const levelCost = costs?.[levelKey];
  const status = onStretchTab
    ? `${hand === "both" ? "" : `The ${other} hand stays as it is. `}About ${level ? `${dollars(levelCost) || "a few cents"}${minutes(levelCost)}` : `${dollars(costs?.stretch) || "one cent"}${minutes(costs?.stretch)}`}. Undo takes it back.`
    : run === "level"
      ? `A new project in My projects, named with the level. This sheet stays as it is. About ${dollars(levelCost)}${minutes(levelCost)}.`
      : [
          viaEdit ? "This opens a copy in Projects, as Edit does, and the AI works there." : "",
          run !== "all"
            ? `Uniform patterns and no quick jumps; the hands stay. ${timeOf(costs?.[run]) ? `It takes ${timeOf(costs?.[run])}. ` : ""}Undo takes it back.`
            : enhanced
              ? `The AI writes the hands and the reading again, in ${timeOf(costs?.all) || "a few minutes"}. If it does not finish, the sheet you have now stays.`
              : `The AI writes the hands and the reading, part by part, in ${timeOf(costs?.all) || "a few minutes"}. The hands you have now are kept in the history.`,
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
      placeholder={level ? "At frame 112 use hard 3." : "Make the octaves single notes."}
      value={words}
      onChange={(event) => setWords(event.target.value.slice(0, MAX_WORDS))}
      onKeyDown={(event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) confirm();
      }}
      slotProps={{ htmlInput: { "data-testid": "stretch-words" } }}
    />
  );

  const levelControls = (
    <Stack spacing={1.25} data-level-controls>
      {hands
        .slice()
        .reverse()
        .map((side) => (
          <Stack key={side} direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Typography variant="body2" sx={{ width: 84 }}>
              {side === "right" ? "Right hand" : "Left hand"}
            </Typography>
            <Segmented<LevelName>
              label={`The level of the ${side} hand`}
              value={levels[side]}
              options={LEVELS}
              onChange={(value) => setLevels((now) => ({ ...now, [side]: value }))}
            />
          </Stack>
        ))}
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }} data-level-patterns>
          {hands.map((side) => `${side === "right" ? "Right" : "Left"}: ${picked(side).map(shortRef).join(", ") || "-"}`).join(" · ")}
        </Typography>
        <PillButton kind="quiet" disabled={!catalog} onClick={() => setBrowsing(true)} data-testid="open-catalog">
          Patterns
        </PillButton>
      </Stack>
      {wordsField}
    </Stack>
  );

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth data-enhance-dialog>
      <DialogTitle>{enhanced ? "Enhance it again with AI" : "Enhance with AI"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <Segmented<EnhanceTab>
            label="What the AI works on"
            value={onStretchTab ? "stretch" : "song"}
            options={TABS.map((one) =>
              one.value === "stretch" && stretch === null ? { ...one, disabled: true, tooltip: "Select notes or a stretch first" } : one,
            )}
            onChange={setTab}
          />
          {onStretchTab ? (
            <>
              <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                <Segmented<StretchHand> label="Which hand" value={hand} options={HANDS} onChange={setHand} />
                <Segmented<How> label="How" value={how} options={HOW} onChange={setHow} />
                <Typography variant="body2" color="text.secondary" noWrap>
                  {stretch.what}
                </Typography>
              </Stack>
              {level ? levelControls : wordsField}
            </>
          ) : (
            <>
              <RadioGroup value={run} onChange={(event) => setRun(event.target.value as SongChoice)} aria-label="What the AI does">
                {RUNS.map((one) => (
                  <FormControlLabel
                    key={one.value}
                    value={one.value}
                    control={<Radio size="small" />}
                    data-testid={`song-run-${one.value}`}
                    sx={{ mr: 0, "& .MuiFormControlLabel-label": { flex: 1 } }}
                    label={
                      <Stack direction="row" sx={{ justifyContent: "space-between", gap: 2 }}>
                        <span>{one.label}</span>
                        <Typography component="span" variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {dollars(one.value === "level" ? costs?.[`level-${songHand}`] : costs?.[one.value])}
                        </Typography>
                      </Stack>
                    }
                  />
                ))}
              </RadioGroup>
              {run === "level" ? (
                <>
                  <Segmented<LevelHand> label="Which hands" value={songHand} options={SONG_HANDS} onChange={setSongHand} />
                  {levelControls}
                </>
              ) : null}
            </>
          )}
          <Typography variant="body2" color="text.secondary" data-enhance-status>
            {status}
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={confirm} data-testid={onStretchTab ? "stretch-confirm" : "song-confirm"}>
          {level ? "Write the level" : onStretchTab ? "Enhance with AI" : run === "all" ? "Write it all again" : "Simplify"}
        </PillButton>
      </DialogActions>
      {browsing && catalog ? (
        <PatternCatalog
          catalog={catalog}
          hands={hands}
          levels={levels}
          selected={hands.flatMap(picked)}
          onCancel={() => setBrowsing(false)}
          onDone={(selected) => {
            setBrowsing(false);
            setChosen((now) => {
              const next = { ...now };
              for (const side of hands) next[side] = selected.filter((ref) => ref.startsWith(`${side} `));
              return next;
            });
          }}
        />
      ) : null}
    </Dialog>
  );
}

export default EnhanceDialog;
