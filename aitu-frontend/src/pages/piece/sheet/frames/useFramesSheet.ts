/**
 * The new sheet of a part as the page holds it (implementation 03, Phase 5): read for the page's width, read again
 * at each step of Sonnet's job, and Sonnet started by itself on a new transcription.
 *
 * While Sonnet writes, the backend sends an `event: sheet` message on the job's stream each time the sheet changes
 * (the reference figure, then each window) and `event: done` at the end; each one asks for the sheet again. A
 * stream opened late, or again after a reload, first receives every message already sent: the reads that follow
 * one another closely are joined into one.
 *
 * An edit (Phase 6) is one request whose answer is the sheet drawn again: `edit` puts it on the page in place of the
 * one it had, and holds further edits until it is back.
 *
 * A stretch the AI writes again with the user's words (Phase 7) is a job like a whole run: the page follows it the
 * same way, and the job's last message says when no answer was accepted (`notice`: the stretch stays as it was).
 * So is **Simplify** (implementation 04, Phase 4): its last message says how many notes the AI added and left out.
 * So is a **level** of a range (implementation 04-3, Phase 4): its last message says when no batch was accepted.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { sheetApi, type FramesSheet, type LevelRequest, type SheetEdited, type StretchRequest } from "../../../../api";
import { said } from "../../../library/shared";

/** Messages closer than this are read as one. */
const JOIN_MS = 250;

type Hand = "left" | "right" | "both";

/** The end of a job, as its last message sums it up. */
interface Summary {
  stretch?: string;
  simplify?: string;
  hand?: Hand;
  added?: number;
  leftOut?: number;
  level?: string;
  levelName?: string;
  batches?: number;
  total?: number;
  /** The run stopped because the account of the AI has no credits left (``openai``). */
  credits?: string;
}

const HAND_WORDS: Record<Hand, string> = { left: "the left hand", right: "the right hand", both: "both hands" };

function notes(count: number): string {
  return `${count} note${count === 1 ? "" : "s"}`;
}

/** What the page says when a stretch or Simplify ends without the result the user expects; `null`: nothing. */
function endNotice(summary: Summary): string | null {
  if (summary.stretch === "failed") return "The AI could not write this stretch again. It stays as it was.";
  if (summary.stretch === "stale") return "The notes changed while the AI worked. The stretch stays as it was.";
  const where = summary.hand ? ` in ${HAND_WORDS[summary.hand]}` : "";
  if (summary.simplify === "none") return `The AI found nothing to simplify${where}.`;
  if (summary.simplify === "failed") return "The AI could not simplify the sheet. It stays as it was.";
  if (summary.simplify === "stale") return "The notes changed while the AI worked. The sheet stays as it was.";
  if (summary.credits) {
    const done =
      summary.level === "ok" && summary.batches ? `The AI wrote ${summary.batches} of ${summary.total} parts; the others stay as they were. ` : "The sheet stays as it was. ";
    return `${done}The AI has no credits left: add credits to the OpenAI account (platform.openai.com, Billing), then run it again.`;
  }
  if (summary.level === "failed") return "The AI could not write this level. The sheet stays as it was.";
  if (summary.level === "stale") return "The notes changed while the AI worked. The sheet stays as it was.";
  if (summary.level === "ok" && summary.total && summary.batches !== undefined && summary.batches < summary.total) {
    return `The AI wrote ${summary.batches} of ${summary.total} parts at the level; the others stay as they were.`;
  }
  if (summary.simplify === "ok") {
    const parts = [summary.added ? `added ${notes(summary.added)}` : "", summary.leftOut ? `left out ${notes(summary.leftOut)}` : ""];
    return `The AI ${parts.filter(Boolean).join(" and ")}${where}.`;
  }
  return null;
}

export interface FramesSheetState {
  sheet: FramesSheet | null;
  error: string | null;
  /** Start the AI on the part: **Enhance with AI**. */
  run: () => Promise<void>;
  starting: boolean;
  /** Send one edit; its answer (the sheet drawn again) replaces the sheet. `null` when it failed or another is out. */
  edit: (call: () => Promise<SheetEdited>) => Promise<SheetEdited | null>;
  /** An edit is on its way. */
  editing: boolean;
  /** What went wrong with the last edit, said for the page; cleared by the next one. */
  editError: string | null;
  /** Ask the AI to write a stretch again with the user's words (Phase 7). */
  enhanceStretch: (stretch: StretchRequest) => Promise<void>;
  /** Ask the AI to write a range again at a level (implementation 04-3, Phase 4). */
  level: (request: LevelRequest) => Promise<void>;
  /** Ask the AI to simplify one hand, or both, over the whole song (implementation 04, Phase 4). */
  simplify: (hand: Hand) => Promise<void>;
  /** A quiet word after the AI could not write a stretch again; cleared by the next edit or request. */
  notice: string | null;
}

export function useFramesSheet(
  audioUuid: string,
  /** The staff width to draw for, in staff spaces; `null` until the page is measured. */
  width: number | null,
  {
    autoStart,
    onChanged,
  }: {
    /** Whether this page may start Sonnet by itself (the Sheet step of a project; never Play mode). */
    autoStart: boolean;
    /** Sonnet started or ended: the steps of the project may have changed. */
    onChanged?: () => void;
  },
): FramesSheetState {
  const [loaded, setLoaded] = useState<{ uuid: string; sheet: FramesSheet } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [starting, setStarting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const changed = useRef(onChanged);
  useEffect(() => {
    changed.current = onChanged;
  }, [onChanged]);

  useEffect(() => {
    if (width === null) return;
    const controller = new AbortController();
    sheetApi
      .get(audioUuid, width, controller.signal)
      .then((sheet) => {
        setLoaded({ uuid: audioUuid, sheet });
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(said(caught, "The sheet could not be drawn."));
      });
    return () => controller.abort();
  }, [audioUuid, width, reload]);

  const sheet = loaded && loaded.uuid === audioUuid ? loaded.sheet : null;
  const jobId = sheet?.llm.state === "running" ? sheet.llm.jobId : null;

  // Follow Sonnet's job: read the sheet again at each of its messages.
  useEffect(() => {
    if (!jobId) return;
    const source = new EventSource(sheetApi.progressUrl(jobId));
    let timer: number | null = null;
    const again = () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        timer = null;
        setReload((value) => value + 1);
      }, JOIN_MS);
    };
    source.addEventListener("sheet", again);
    source.addEventListener("done", (event) => {
      source.close();
      again();
      changed.current?.();
      try {
        const summary = JSON.parse((event as MessageEvent<string>).data ?? "{}") as Summary;
        const word = endNotice(summary);
        if (word) setNotice(word);
      } catch {
        // A message without a summary: nothing to say.
      }
    });
    return () => {
      source.close();
      if (timer !== null) window.clearTimeout(timer);
    };
  }, [jobId]);

  const run = useCallback(async () => {
    setStarting(true);
    try {
      await sheetApi.runLlm(audioUuid);
      setReload((value) => value + 1);
      changed.current?.();
    } catch (caught) {
      setError(said(caught, "The AI could not be started."));
    } finally {
      setStarting(false);
    }
  }, [audioUuid]);

  // A new transcription goes to Sonnet by itself, once per page.
  const started = useRef<string | null>(null);
  const auto = autoStart && sheet?.llm.auto === true;
  useEffect(() => {
    if (!auto || started.current === audioUuid) return;
    started.current = audioUuid;
    void run();
  }, [auto, audioUuid, run]);

  const enhanceStretch = useCallback(
    async (stretch: StretchRequest) => {
      setNotice(null);
      setEditError(null);
      try {
        await sheetApi.enhanceStretch(audioUuid, stretch);
        setReload((value) => value + 1);
        changed.current?.();
      } catch (caught) {
        setEditError(said(caught, "The AI could not be asked."));
      }
    },
    [audioUuid],
  );

  const simplify = useCallback(
    async (hand: Hand) => {
      setNotice(null);
      setEditError(null);
      try {
        await sheetApi.simplify(audioUuid, hand);
        setReload((value) => value + 1);
        changed.current?.();
      } catch (caught) {
        setEditError(said(caught, "The AI could not be asked."));
      }
    },
    [audioUuid],
  );

  const level = useCallback(
    async (request: LevelRequest) => {
      setNotice(null);
      setEditError(null);
      try {
        await sheetApi.level(audioUuid, request);
        setReload((value) => value + 1);
        changed.current?.();
      } catch (caught) {
        setEditError(said(caught, "The AI could not be asked."));
      }
    },
    [audioUuid],
  );

  const edit = useCallback(
    async (call: () => Promise<SheetEdited>) => {
      if (editing) return null;
      setEditing(true);
      setEditError(null);
      setNotice(null);
      try {
        const answer = await call();
        setLoaded({ uuid: audioUuid, sheet: answer });
        return answer;
      } catch (caught) {
        setEditError(said(caught, "The change could not be made."));
        return null;
      } finally {
        setEditing(false);
      }
    },
    [audioUuid, editing],
  );

  return { sheet, error, run, starting, edit, editing, editError, enhanceStretch, simplify, level, notice };
}
