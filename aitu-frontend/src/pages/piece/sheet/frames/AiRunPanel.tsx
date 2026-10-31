/**
 * The panel of an AI run (the user, 2026-10-30): at the right of the sheet, where **Enhance with AI** was, it stays
 * open while the AI writes and shows each batch, with the colour and the number the sheet draws it with: waiting,
 * being written, written, or kept as it was (the check refused it). **Stop** asks no more requests (the one the AI
 * is answering ends first); what it wrote stays. Once the run ends, **Revert** puts the part back as it was before
 * the run (one step of undo), and **Close** hides the panel.
 */

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { SheetSegment } from "../../../../api";
import { PillButton } from "../../../../ui";
import { BATCH_COLOURS, ENHANCE_PANEL_WIDTH } from "./batches";
import type { RunSummary } from "./useFramesSheet";

const FRAME_MS = 40;

function clockOf(frame: number): string {
  const seconds = Math.round((frame * FRAME_MS) / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

const STATE_WORDS: Record<SheetSegment["state"], string> = {
  waiting: "Waiting",
  working: "Being written",
  llm: "Written",
  algorithm: "Kept as it was",
};

export interface AiRunPanelProps {
  /** The AI works now. */
  running: boolean;
  /** **Stop** was pressed: the run ends after the request it waits for. */
  stopping: boolean;
  /** The batches of the run, as last seen while it worked. */
  batches: readonly SheetSegment[];
  /** The end of the run, once it ended. */
  summary: RunSummary | null;
  notice: string | null;
  /** **Revert** was done: undo brings the run's result back. */
  reverted: boolean;
  busy: boolean;
  onStop: () => void;
  onRevert: () => void;
  onClose: () => void;
}

export function AiRunPanel({
  running,
  stopping,
  batches,
  summary,
  notice,
  reverted,
  busy,
  onStop,
  onRevert,
  onClose,
}: AiRunPanelProps) {
  const done = batches.filter((batch) => batch.state === "llm" || batch.state === "algorithm").length;
  const title = running
    ? stopping
      ? "Stopping after this batch"
      : "The AI is writing"
    : summary?.stopped
      ? "Stopped"
      : "The AI has finished";
  // Once the run ended, a batch it never reached was not written.
  const stateOf = (batch: SheetSegment) =>
    !running && (batch.state === "working" || batch.state === "waiting") ? "Not written" : STATE_WORDS[batch.state];
  return (
    <Paper
      elevation={12}
      data-ai-run-panel={running ? "running" : "done"}
      sx={{
        position: "fixed",
        top: 16,
        right: 16,
        width: ENHANCE_PANEL_WIDTH,
        maxWidth: "calc(100% - 32px)",
        maxHeight: "calc(100% - 32px)",
        display: "flex",
        flexDirection: "column",
        zIndex: (theme) => theme.zIndex.modal,
        borderRadius: 2,
      }}
    >
      <Stack spacing={1} sx={{ p: 3, pb: 1.5 }}>
        <Typography variant="h6">{title}</Typography>
        {batches.length > 0 ? (
          <>
            <LinearProgress
              variant={running && done === 0 ? "indeterminate" : "determinate"}
              value={(100 * done) / batches.length}
            />
            <Typography variant="body2" color="text.secondary">
              {done} of {batches.length} batches
              {summary?.usd !== undefined ? `, $${summary.usd.toFixed(2)}` : ""}
            </Typography>
          </>
        ) : null}
      </Stack>
      <Box sx={{ overflowY: "auto", px: 3, flex: 1 }} data-ai-run-batches>
        {batches.map((batch, index) => {
          const colour = BATCH_COLOURS[index % BATCH_COLOURS.length];
          return (
            <Stack
              key={`${batch.start}-${batch.end}`}
              direction="row"
              spacing={1.5}
              sx={{ alignItems: "center", py: 0.75, borderBottom: 1, borderColor: "divider" }}
              data-ai-run-batch={index + 1}
              data-state={batch.state}
            >
              <Box
                sx={{
                  width: 26,
                  height: 26,
                  borderRadius: 1,
                  border: `2px solid ${colour}`,
                  bgcolor: `${colour}1f`,
                  color: colour,
                  fontWeight: 700,
                  fontSize: 13,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {index + 1}
              </Box>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {clockOf(batch.start)} - {clockOf(batch.end)}{" "}
                <Typography component="span" variant="caption" color="text.secondary">
                  f{batch.start}-f{batch.end}
                </Typography>
              </Typography>
              <Typography
                variant="body2"
                color={batch.state === "working" && running ? "primary" : "text.secondary"}
                sx={{ fontWeight: batch.state === "working" && running ? 600 : 400 }}
              >
                {stateOf(batch)}
              </Typography>
            </Stack>
          );
        })}
      </Box>
      <Stack spacing={1.5} sx={{ p: 3, pt: 1.5 }}>
        {!running && (notice || reverted) ? (
          <Typography variant="body2" color="text.secondary" data-ai-run-notice>
            {reverted ? "Reverted: the sheet is as it was before the run. Undo brings the AI's work back." : notice}
          </Typography>
        ) : null}
        <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
          {running ? (
            <PillButton kind="danger" onClick={onStop} disabled={stopping} data-testid="ai-run-stop">
              Stop
            </PillButton>
          ) : (
            <>
              {summary?.before !== undefined ? (
                <PillButton kind="secondary" onClick={onRevert} disabled={reverted || busy} busy={busy} data-testid="ai-run-revert">
                  Revert
                </PillButton>
              ) : null}
              <PillButton kind="primary" onClick={onClose} data-testid="ai-run-close">
                Close
              </PillButton>
            </>
          )}
        </Stack>
      </Stack>
    </Paper>
  );
}

export default AiRunPanel;
