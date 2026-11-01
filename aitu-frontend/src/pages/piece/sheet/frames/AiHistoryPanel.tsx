/**
 * The history of the AI runs of this sheet (implementation 04-5, the user, 2026-10-31): at the right of the sheet,
 * the runs latest first; a click opens one (`AiRunDetail`): the rules the AI followed, each batch with its
 * explanation, and an answer to the AI with **Write this batch again**. Level runs made before the history have no
 * conversation stored: they show their plan and what they declared.
 */

import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { sheetApi, type AiRunShort } from "../../../../api";
import { PillButton } from "../../../../ui";
import { AiRunDetail } from "./AiRunDetail";
import { runTitle } from "./patterns";
import { ENHANCE_PANEL_WIDTH } from "./batches";

const STATE_WORDS: Record<string, string> = {
  running: "The AI is writing",
  waiting: "Waiting for you after batch 1",
  done: "Finished",
  stopped: "Stopped",
  failed: "Not written",
};

export interface AiHistoryPanelProps {
  audioUuid: string;
  /** An AI run goes on this sheet now. */
  busy: boolean;
  /** Changes when a run ends: the list is read again. */
  refresh: number;
  /** The run to open first (the run the user just made). */
  opening?: string | null;
  onStarted: () => void;
  onClose: () => void;
}

export function AiHistoryPanel({ audioUuid, busy, refresh, opening = null, onStarted, onClose }: AiHistoryPanelProps) {
  const [runs, setRuns] = useState<AiRunShort[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(opening);

  useEffect(() => {
    const controller = new AbortController();
    sheetApi
      .aiRuns(audioUuid, controller.signal)
      .then((next) => {
        setRuns(next);
        setError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError("The history could not be read.");
      });
    return () => controller.abort();
  }, [audioUuid, refresh]);

  const open = runs?.find((one) => one.id === openId) ?? null;

  return (
    <Paper
      elevation={12}
      data-ai-history
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
      <Stack direction="row" spacing={1} sx={{ p: 3, pb: 1.5, alignItems: "center" }}>
        {open ? (
          <IconButton size="small" aria-label="Back to the history" onClick={() => setOpenId(null)}>
            <ArrowBackRounded fontSize="small" />
          </IconButton>
        ) : null}
        <Typography variant="h6" sx={{ flex: 1 }}>
          History of AI runs
        </Typography>
      </Stack>
      <Box sx={{ overflowY: "auto", px: 3, flex: 1 }}>
        {error ? (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        ) : runs === null ? (
          <CircularProgress size={20} />
        ) : open?.log ? (
          <AiRunDetail audioUuid={audioUuid} runId={open.id} busy={busy} refresh={refresh} onStarted={onStarted} />
        ) : open ? (
          <Stack spacing={1} data-ai-run-old>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {runTitle(open)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              This run was made before the history kept the AI's explanations. Its plan and what it declared:
            </Typography>
            {[...(open.plan ?? []), ...(open.declared ?? [])].map((line, index) => (
              <Typography key={index} variant="caption" sx={{ fontFamily: "monospace" }}>
                {line}
              </Typography>
            ))}
          </Stack>
        ) : runs.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No AI run on this sheet yet.
          </Typography>
        ) : (
          runs.map((one) => (
            <Stack
              key={one.id}
              spacing={0.25}
              onClick={() => setOpenId(one.id)}
              data-history-run={one.id}
              sx={{ py: 1, borderBottom: 1, borderColor: "divider", cursor: "pointer", "&:hover": { bgcolor: "action.hover" } }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {runTitle(one)}
              </Typography>
              {one.words ? (
                <Typography variant="body2" color="text.secondary" noWrap>
                  {one.words}
                </Typography>
              ) : null}
              <Typography variant="caption" color="text.secondary">
                {one.created ? new Date(one.created).toLocaleString() : ""} · {STATE_WORDS[one.state] ?? one.state} ·{" "}
                {one.batches.filter((batch) => batch.status === "ok").length} of {one.total} batches · $
                {one.usd.toFixed(2)}
              </Typography>
            </Stack>
          ))
        )}
      </Box>
      <Stack direction="row" sx={{ p: 3, pt: 1.5, justifyContent: "flex-end" }}>
        <PillButton kind="primary" onClick={onClose} data-testid="ai-history-close">
          Close
        </PillButton>
      </Stack>
    </Paper>
  );
}

export default AiHistoryPanel;
