/**
 * The lyrics of the new sheet on the page (implementation 03, Phase 8): the old sheet's Lyrics tab and its piece
 * helpers (`lyricsPieces.ts`) work on as they were, through a small adapter.
 *
 * - **The pieces on the sheet** are stored in the sheet itself (`sheet.f1`, `lyric` lines): every change the tab or a
 *   drag on the sheet makes is one edit, written at once as one step of undo. The tab speaks the old sheet's units
 *   (frames as columns, the size and the lift in pixels); the sheet's are frames and staff spaces.
 * - **The pasted words and the pool** are kept with the part as before (`PUT /time/{uuid}/lyrics`, in
 *   `project.json`): **Save lyrics** saves them, and they outlive a new transcription.
 */

import { useCallback, useEffect, useMemo, useState, type SetStateAction } from "react";
import { timeScoreApi, type FramesSheet, type LyricLine, type ReadingEdit, type SheetLyric } from "../../../../api";
import { said } from "../../../library/shared";
import { backToPool, landingOf, movePiece, placePiece } from "../lyricsPieces";

/** Pixels of the old sheet's words per staff space of the new one: its 12 px default is the new 1.4. */
const PX_PER_SPACE = 12 / 1.4;
const FRAME_MS = 40;

function toLine(piece: SheetLyric): LyricLine {
  return {
    fromColumn: piece.start,
    toColumn: piece.end,
    text: piece.text,
    ...(piece.size === null ? {} : { fontSize: Math.round(piece.size * PX_PER_SPACE) }),
    ...(piece.lift ? { offsetY: -piece.lift * PX_PER_SPACE } : {}),
  };
}

function toPiece(line: LyricLine): SheetLyric {
  return {
    start: line.fromColumn,
    end: line.toColumn,
    text: line.text,
    size: line.fontSize == null ? null : line.fontSize / PX_PER_SPACE,
    lift: line.offsetY ? Math.round((-line.offsetY / PX_PER_SPACE) * 2) / 2 : 0,
  };
}

/** What a change of the pieces did, for the step's label. */
function describe(before: readonly LyricLine[], after: readonly LyricLine[]): string {
  if (after.length > before.length) return after.length - before.length === 1 ? "Place a lyrics piece" : "Split a lyrics piece";
  if (after.length < before.length) {
    const words = new Set(before.map((line) => line.text));
    return after.some((line) => !words.has(line.text)) ? "Merge lyrics pieces" : "Take lyrics off the sheet";
  }
  const changed = after.find((line, at) => line !== before[at]);
  const was = changed ? before.find((line) => line.fromColumn === changed.fromColumn) : undefined;
  if (changed && was && changed.text !== was.text) return "Words of a lyrics piece";
  if (changed && was && changed.fontSize !== was.fontSize) return "Size of a lyrics piece";
  return "Move a lyrics piece";
}

export function useFramesLyrics(
  audioUuid: string,
  sheet: FramesSheet | null,
  apply: (change: ReadingEdit) => Promise<boolean>,
  onRefused: (why: string) => void,
) {
  const lines = useMemo(() => (sheet?.lyrics ?? []).map(toLine), [sheet?.lyrics]);
  const frameCount = sheet && sheet.columns.length > 0 ? sheet.columns[sheet.columns.length - 1].frame + 50 : 1;

  // ------------------------------------------------------------------ the pasted words and the pool

  const [saved, setSaved] = useState<{ forPart: string; text: string | null; pool: string[] } | null>(null);
  const [poolNow, setPoolNow] = useState<{ forPart: string; pool: readonly string[] } | null>(null);
  const [draft, setDraft] = useState<{ forPart: string; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    timeScoreApi
      .lyrics(audioUuid, controller.signal)
      .then((found) => setSaved({ forPart: audioUuid, text: found?.text ?? null, pool: found?.pool ?? [] }))
      .catch(() => setSaved({ forPart: audioUuid, text: null, pool: [] }));
    return () => controller.abort();
  }, [audioUuid]);
  const savedHere = saved && saved.forPart === audioUuid ? saved : null;
  const pool = useMemo(
    () => (poolNow && poolNow.forPart === audioUuid ? poolNow.pool : (savedHere?.pool ?? [])),
    [poolNow, audioUuid, savedHere],
  );
  const savedPool = savedHere?.pool ?? [];
  const poolUnsaved = pool.length !== savedPool.length || pool.some((text, at) => text !== savedPool[at]);
  const pasted = draft && draft.forPart === audioUuid ? draft.text : (savedHere?.text ?? "");
  const setPool = useCallback(
    (next: SetStateAction<readonly string[]>) =>
      setPoolNow((current) => {
        const now = current && current.forPart === audioUuid ? current.pool : (savedHere?.pool ?? []);
        return { forPart: audioUuid, pool: typeof next === "function" ? next(now) : next };
      }),
    [audioUuid, savedHere],
  );
  const setPasted = useCallback((text: string) => setDraft({ forPart: audioUuid, text }), [audioUuid]);
  const save = useCallback(
    async (text: string) => {
      setSaving(true);
      try {
        const kept = await timeScoreApi.saveLyrics(audioUuid, text, pool);
        setSaved({ forPart: audioUuid, text: kept.text, pool: kept.pool ?? [] });
        setPoolNow(null);
        setDraft({ forPart: audioUuid, text: kept.text ?? "" });
      } catch (caught) {
        onRefused(said(caught, "Could not save the lyrics."));
      } finally {
        setSaving(false);
      }
    },
    [audioUuid, pool, onRefused],
  );

  // ------------------------------------------------------------------ the pieces on the sheet

  const [pickedNow, setPickedNow] = useState<{ forPart: string; starts: readonly number[] }>({ forPart: audioUuid, starts: [] });
  const picked = useMemo(
    () =>
      pickedNow.forPart === audioUuid ? pickedNow.starts.filter((start) => lines.some((line) => line.fromColumn === start)) : [],
    [pickedNow, audioUuid, lines],
  );
  const setPicked = useCallback(
    (next: SetStateAction<readonly number[]>) =>
      setPickedNow((current) => ({
        forPart: audioUuid,
        starts: typeof next === "function" ? next(current.forPart === audioUuid ? current.starts : []) : next,
      })),
    [audioUuid],
  );

  /** The pieces as the tab wants them now: one edit of the sheet, named by what changed. */
  const write = useCallback(
    async (after: readonly LyricLine[], label?: string) => {
      const pieces = after.map(toPiece);
      return apply({ action: "lyrics", value: { pieces, label: label ?? describe(lines, after) } });
    },
    [apply, lines],
  );
  const setLines = useCallback(
    (next: SetStateAction<readonly LyricLine[]>) => {
      const after = typeof next === "function" ? next(lines) : next;
      if (after !== lines) void write(after);
    },
    [lines, write],
  );

  /** A piece dragged on the sheet: moved, made longer or shorter, lifted. */
  const move = useCallback(
    (change: { start: number; nextStart: number; nextEnd: number; lift: number }) => {
      const piece = lines.find((line) => line.fromColumn === change.start);
      if (!piece) return;
      const lift = Math.max(-4, (piece.offsetY ? -piece.offsetY / PX_PER_SPACE : 0) + change.lift);
      const moved = movePiece(lines, {
        fromColumn: change.start,
        toColumn: piece.toColumn,
        nextFromColumn: Math.max(0, change.nextStart),
        nextToColumn: Math.max(change.nextStart + 1, change.nextEnd),
        offsetY: -lift * PX_PER_SPACE,
      });
      if ("refused" in moved) {
        onRefused(moved.refused);
        return;
      }
      void write(moved.ok, change.lift !== 0 && change.nextStart === change.start ? "Lift a lyrics piece" : "Move a lyrics piece");
      setPicked([Math.max(0, change.nextStart)]);
    },
    [lines, write, onRefused, setPicked],
  );

  /** The piece of the pool being dragged, by its place in the pool. */
  const [dragging, setDragging] = useState<number | null>(null);
  const draggedText = dragging !== null ? (pool[dragging] ?? null) : null;
  const landing = useMemo(
    () =>
      draggedText === null
        ? null
        : (frame: number) => {
            const found = landingOf(lines, draggedText, frame, FRAME_MS, frameCount);
            return { start: found.fromColumn, end: found.toColumn, free: found.free };
          },
    [draggedText, lines, frameCount],
  );
  const dropPool = useCallback(
    (frame: number) => {
      setDragging(null);
      if (draggedText === null) return;
      const placed = placePiece(lines, draggedText, frame, FRAME_MS, frameCount);
      if ("refused" in placed) {
        onRefused(placed.refused);
        return;
      }
      void write(placed.ok, "Place a lyrics piece");
    },
    [draggedText, lines, frameCount, onRefused, write],
  );

  /** The picked pieces taken off the sheet (Delete): their words stay in the pool. */
  const removePicked = useCallback(() => {
    if (picked.length === 0) return;
    const after = backToPool(lines, pool, picked);
    setPool(after.pool);
    setPicked([]);
    void write(after.lyrics, picked.length === 1 ? "Take a lyrics piece off the sheet" : "Take lyrics off the sheet");
  }, [picked, lines, pool, setPool, setPicked, write]);

  return {
    lines,
    pool,
    setPool,
    picked,
    setPicked,
    setLines,
    pasted,
    setPasted,
    savedText: savedHere?.text ?? null,
    poolUnsaved,
    saving,
    save,
    onPoolDrag: setDragging,
    landing,
    dropPool,
    move,
    removePicked,
  };
}
