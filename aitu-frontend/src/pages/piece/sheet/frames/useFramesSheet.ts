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
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { sheetApi, type FramesSheet, type SheetEdited } from "../../../../api";
import { said } from "../../../library/shared";

/** Messages closer than this are read as one. */
const JOIN_MS = 250;

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
    source.addEventListener("done", () => {
      source.close();
      again();
      changed.current?.();
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

  const edit = useCallback(
    async (call: () => Promise<SheetEdited>) => {
      if (editing) return null;
      setEditing(true);
      setEditError(null);
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

  return { sheet, error, run, starting, edit, editing, editError };
}
