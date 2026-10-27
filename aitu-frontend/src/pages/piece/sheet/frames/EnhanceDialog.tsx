/**
 * **Enhance with AI** (implementation 04, Phase 4; the user's request after the Phase 3 gallery): one dialog, two
 * tabs.
 *
 * - **A stretch** (open when notes or a stretch are selected; implementation 03, Phase 7): both hands, only the right
 *   or only the left (the other hand then stays exactly as it is), and the user's own words, optional. The AI writes
 *   that stretch again in a few seconds, under the pale veil; one step of undo.
 * - **The whole song** (open when nothing is selected): **Simplify** the left hand, the right hand or both (the rules
 *   of simplicity only: uniform patterns, no quick jumps; the hands stay; batch after batch, one step of undo), or
 *   **Write it all again** (the full run of the AI).
 *
 * The cost of each run, about, is read from the backend when the dialog opens. On a version of My library the whole
 * song runs in the edit copy, as **Edit** opens it.
 */

import { useEffect, useState } from "react";
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
import { sheetApi, type LlmCosts, type SongRun } from "../../../../api";
import { PillButton, Segmented } from "../../../../ui";

/** As the backend takes them (`REQUEST_CHARS`). */
const MAX_WORDS = 1000;

export type EnhanceTab = "stretch" | "song";
export type StretchHand = "both" | "right" | "left";

const TABS = [
  { value: "stretch" as const, label: "A stretch" },
  { value: "song" as const, label: "The whole song" },
];

const HANDS = [
  { value: "both" as const, label: "Both" },
  { value: "right" as const, label: "Right" },
  { value: "left" as const, label: "Left" },
];

const RUNS: { value: SongRun; label: string }[] = [
  { value: "simplify-left", label: "Simplify the left hand" },
  { value: "simplify-right", label: "Simplify the right hand" },
  { value: "simplify-both", label: "Simplify both hands" },
  { value: "all", label: "Write it all again" },
];

function dollars(usd: number | undefined): string {
  return usd === undefined ? "" : `$${usd.toFixed(2)}`;
}

export interface EnhanceDialogProps {
  open: boolean;
  audioUuid: string;
  /** The tab it opens on. */
  tab: EnhanceTab;
  /** The selection the stretch tab writes again, and its hand when it is one hand; `null`: nothing selected. */
  stretch: { what: string; hand: StretchHand } | null;
  /** The AI enhanced this sheet already. */
  enhanced: boolean;
  /** A version of My library: the whole song runs in the edit copy. */
  viaEdit: boolean;
  onStretch: (hand: StretchHand, words: string) => void;
  onSong: (run: SongRun) => void;
  onCancel: () => void;
}

export function EnhanceDialog({ open, audioUuid, tab: opening, stretch, enhanced, viaEdit, onStretch, onSong, onCancel }: EnhanceDialogProps) {
  const [tab, setTab] = useState<EnhanceTab>(opening);
  const [hand, setHand] = useState<StretchHand>(stretch?.hand ?? "both");
  const [words, setWords] = useState("");
  const [run, setRun] = useState<SongRun>(enhanced ? "simplify-left" : "all");
  const [costs, setCosts] = useState<LlmCosts | null>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    sheetApi
      .llmCosts(audioUuid, controller.signal)
      .then(setCosts)
      .catch(() => {
        // Without the cost the dialog still works: it only says less.
      });
    return () => controller.abort();
  }, [open, audioUuid]);

  const onStretchTab = tab === "stretch" && stretch !== null;
  const simplify = run !== "all";
  const confirm = () => (onStretchTab ? onStretch(hand, words.trim()) : onSong(run));
  const other = hand === "right" ? "left" : "right";
  const status = onStretchTab
    ? `${hand === "both" ? "" : `The ${other} hand stays as it is. `}About ${dollars(costs?.stretch.usd) || "one cent"}. Undo takes it back.`
    : [
        viaEdit ? "This opens a copy in Projects, as Edit does, and the AI works there." : "",
        simplify
          ? "Uniform patterns and no quick jumps; the hands stay. Undo takes it back."
          : enhanced
            ? "The AI writes the hands and the reading again, in a few minutes. If it does not finish, the sheet you have now stays."
            : "The AI writes the hands and the reading, part by part, in a few minutes. The hands you have now are kept in the history.",
      ]
        .filter(Boolean)
        .join(" ");

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
                <Typography variant="body2" color="text.secondary" noWrap>
                  {stretch.what}
                </Typography>
              </Stack>
              <TextField
                autoFocus
                fullWidth
                multiline
                minRows={2}
                maxRows={6}
                label="What should the AI change?"
                placeholder="Make the octaves single notes."
                value={words}
                onChange={(event) => setWords(event.target.value.slice(0, MAX_WORDS))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) confirm();
                }}
                slotProps={{ htmlInput: { "data-testid": "stretch-words" } }}
              />
            </>
          ) : (
            <RadioGroup value={run} onChange={(event) => setRun(event.target.value as SongRun)} aria-label="What the AI does">
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
                        {dollars(costs?.[one.value].usd)}
                      </Typography>
                    </Stack>
                  }
                />
              ))}
            </RadioGroup>
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
          {onStretchTab ? "Enhance with AI" : simplify ? "Simplify" : "Write it all again"}
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default EnhanceDialog;
