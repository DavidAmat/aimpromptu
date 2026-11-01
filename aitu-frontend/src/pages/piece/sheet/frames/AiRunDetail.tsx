/**
 * One AI run of the history (implementation 04-5, the user, 2026-10-31): what was asked, the rules the AI set for
 * the run, and each batch with the AI's explanation in simple words, the check's refusals and the user's answers.
 * Under a batch, the user can answer the AI ("No, I want this") and **Write this batch again**. A run that waits after
 * its first batch offers **Go on with the other batches**. The panel of a run shows it when the first batch is
 * written; the history of AI runs shows it when a run is opened.
 */

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { sheetApi, type AiRun, type AiRunTalk } from "../../../../api";
import { PillButton } from "../../../../ui";
import { BATCH_COLOURS } from "./batches";
import { runTitle, shortRef } from "./patterns";

const FRAME_MS = 40;
const MAX_ANSWER = 1000;

function clockOf(frame: number): string {
  const seconds = Math.round((frame * FRAME_MS) / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

const STATUS_WORDS: Record<string, string> = {
  ok: "Written",
  failed: "Kept as it was",
  error: "Not written",
  open: "Being written",
};

function BatchBlock({
  talk,
  colour,
  canAnswer,
  sending,
  onAgain,
}: {
  talk: AiRunTalk;
  colour: string;
  canAnswer: boolean;
  sending: boolean;
  onAgain: (words: string) => void;
}) {
  const [answer, setAnswer] = useState("");
  return (
    <Stack spacing={0.75} sx={{ py: 1.25, borderBottom: 1, borderColor: "divider" }} data-run-batch={talk.k + 1}>
      <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
        <Box
          sx={{
            width: 24,
            height: 24,
            borderRadius: 1,
            border: `2px solid ${colour}`,
            bgcolor: `${colour}1f`,
            color: colour,
            fontWeight: 700,
            fontSize: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          {talk.k + 1}
        </Box>
        <Typography variant="body2" sx={{ flex: 1 }}>
          {clockOf(talk.start)} - {clockOf(talk.end)}{" "}
          <Typography component="span" variant="caption" color="text.secondary">
            f{talk.start}-f{talk.end}
          </Typography>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {STATUS_WORDS[talk.status] ?? talk.status}
        </Typography>
      </Stack>
      {talk.explain.map((line, index) => (
        <Typography key={index} variant="body2" sx={{ bgcolor: "action.hover", borderRadius: 1, px: 1, py: 0.5 }} data-run-explain>
          {line}
        </Typography>
      ))}
      {talk.rules.map((line, index) => (
        <Typography key={index} variant="body2" color="text.secondary">
          Rule for the next batches: {line}
        </Typography>
      ))}
      {talk.errors.length ? (
        <Typography variant="caption" color="text.secondary" data-run-refused>
          The check refused {talk.errors.length} {talk.errors.length === 1 ? "answer" : "answers"} of the AI:{" "}
          {talk.errors.map((errors) => errors.join(" ")).join(" · ")}
        </Typography>
      ) : null}
      {(talk.answers ?? []).map((one, index) => (
        <Typography key={index} variant="body2" color="primary" data-run-answer>
          You: {one.words}
        </Typography>
      ))}
      {canAnswer ? (
        <Stack spacing={0.75}>
          <TextField
            size="small"
            multiline
            maxRows={5}
            placeholder="Answer the AI: No, I want this…"
            value={answer}
            onChange={(event) => setAnswer(event.target.value.slice(0, MAX_ANSWER))}
            slotProps={{ htmlInput: { "data-testid": `run-answer-${talk.k + 1}` } }}
          />
          <Stack direction="row" sx={{ justifyContent: "flex-end" }}>
            <PillButton
              kind="secondary"
              disabled={!answer.trim() || sending}
              onClick={() => onAgain(answer.trim())}
              data-testid={`run-again-${talk.k + 1}`}
            >
              Write this batch again
            </PillButton>
          </Stack>
        </Stack>
      ) : null}
    </Stack>
  );
}

export interface AiRunDetailProps {
  audioUuid: string;
  runId: string;
  /** An AI run goes on this sheet now: nothing new can start. */
  busy: boolean;
  /** Changes when the run may have changed (the end of a job): the run is read again. */
  refresh?: number;
  /** A job was started (a batch written again, the other batches). */
  onStarted: () => void;
  /** Only the batches written (the panel of a run waiting after its first batch). */
  compact?: boolean;
}

export function AiRunDetail({ audioUuid, runId, busy, refresh = 0, onStarted, compact = false }: AiRunDetailProps) {
  const [run, setRun] = useState<AiRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    sheetApi
      .aiRun(audioUuid, runId, controller.signal)
      .then((next) => {
        setRun(next);
        setError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError("This run could not be read.");
      });
    return () => controller.abort();
  }, [audioUuid, runId, refresh]);

  if (error) return <Typography variant="body2" color="error">{error}</Typography>;
  if (!run) return <CircularProgress size={20} />;

  const waiting = run.state === "waiting";
  const left = run.request.windows.length - run.batches.length;
  const start = async (call: () => Promise<unknown>) => {
    setSending(true);
    try {
      await call();
      onStarted();
    } catch {
      setError("The AI could not be asked.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Stack spacing={1} data-ai-run={run.id} data-state={run.state}>
      {!compact ? (
        <>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {runTitle(run.request)}
          </Typography>
          {run.request.words ? (
            <Typography variant="body2" color="text.secondary">
              Your words: {run.request.words}
            </Typography>
          ) : null}
          <Typography variant="caption" color="text.secondary">
            {new Date(run.created).toLocaleString()} · ${run.usd.toFixed(2)}, {run.requests} requests
          </Typography>
        </>
      ) : null}
      {run.rules.length ? (
        <Stack spacing={0.25} data-run-rules>
          <Typography variant="subtitle2" component="p">
            The rules the AI follows
          </Typography>
          {run.rules.map((rule, index) => (
            <Typography key={index} variant="body2" color="text.secondary">
              {rule.ref ? `${shortRef(rule.ref)}: ` : ""}
              {rule.text}
            </Typography>
          ))}
        </Stack>
      ) : null}
      <Box>
        {run.batches.map((talk) => (
          <BatchBlock
            key={talk.k}
            talk={talk}
            colour={BATCH_COLOURS[talk.k % BATCH_COLOURS.length]}
            canAnswer={!busy && talk.status !== "open" && run.state !== "running"}
            sending={sending}
            onAgain={(words) => void start(() => sheetApi.runBatchAgain(audioUuid, run.id, talk.k, words))}
          />
        ))}
      </Box>
      {waiting && left > 0 ? (
        <Stack spacing={1} sx={{ pt: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Check batch 1 on the sheet. If it is good, the AI writes the other {left} batches in the same way.
          </Typography>
          <Stack direction="row" sx={{ justifyContent: "flex-end" }}>
            <PillButton
              kind="primary"
              disabled={busy || sending}
              onClick={() => void start(() => sheetApi.continueRun(audioUuid, run.id))}
              data-testid="run-continue"
            >
              Go on with the other {left} batches
            </PillButton>
          </Stack>
        </Stack>
      ) : null}
    </Stack>
  );
}

export default AiRunDetail;
