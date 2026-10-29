/**
 * The Sheet step of a project: the piano sheet of a part (implementation 03).
 *
 * Every screen that shows a sheet draws it through this page: the Sheet step, a version of My
 * library, Play mode, the page of a passage (the Current and the Proposal), From other projects and
 * the requests review. The page itself is `frames/FramesSheetPage`; the backend lays the sheet out
 * and draws it (`GET /sheet/{uuid}`). The old vexflow-v2 sheet was removed in implementation 03,
 * Phase 10.
 */

import type { ReactNode, RefObject } from "react";
import type { SongRun, StepState } from "../../../api";
import type { ScorePlayerControls } from "../../../components/time/ScorePlayer";
import { FramesSheetPage } from "./frames/FramesSheetPage";

/**
 * What the flow page tells the piano sheet when it is the Sheet tab.
 *
 * `state` and `reason` are the backend's answer for the Sheet step (`GET /pieces/{uuid}/status`).
 * `onChanged` is called after a write that can change that answer: a saved reading makes the step
 * ready, **Remove all** makes it missing.
 */
export interface SheetStep {
  audioUuid: string;
  label?: string | undefined;
  state: StepState;
  reason: string | null;
  onChanged: () => void;
  /**
   * A version of the library, opened to look at (Phase 6): the sheet draws and plays and prints;
   * nothing on it opens a toolbox, and there is no Save. It changes through **Edit**.
   */
  readOnly?: boolean;
  /** Drawn on the page of a passage (Record in Sheet, Phase 9): the Current or the Proposal. */
  passage?: PassageView;
  /** Drawn in Play mode (Phase 11): the sheet alone, read only, played from the page's own button. */
  play?: PlayView;
  /**
   * What a stretch marked on a read-only sheet can be used for, besides a copy (Phase 10): a
   * passage of From other projects, a stretch of a song in a playlist.
   */
  stretchAction?: { label: string; onStretch: (fromMs: number, toMs: number) => void };
  /**
   * The parts of a project (Phase 10): **Start a new part here** in the range toolbox. Gets where
   * the marked stretch starts; `false` when it was refused.
   */
  onSplit?: (atMs: number) => Promise<boolean>;
  /**
   * The audio revision of the part when the page opened. In the player's address with the page's
   * own reloads, so audio changed by another page (a promotion, Phase 9) is not the file the
   * browser kept under the old address (Phase 8 learning).
   */
  audioRevision?: number | undefined;
  /** A version of My library: **Enhance with AI** opens the copy that edits it and starts the run there. */
  enhanceInCopy?: (run: SongRun) => void;
  /**
   * The project of the sheet, on the Sheet step (implementation 04-3, Phase 1): the header gets the **info button**,
   * which shows the metadata of the song or the project (`GET /metadata/info/{projectId}`).
   */
  projectId?: string;
}

/**
 * How a sheet is drawn on the page of a passage (plan section 13). The **Current** is the copy of
 * the marked frames, read only, with no bar of its own; the **Proposal** is a take, with every tool
 * of the sheet and its own bar, which carries the passage's actions too. Both are read with the
 * song's reference figure and armadura (the backend's `PassageState`), so the two read alike;
 * neither prints the title lines.
 */
export interface PassageView {
  role: "current" | "proposal";
  /** The window over the take, in frames, and its drag (the Proposal). */
  frameWindow?: { fromColumn: number; toColumn: number };
  onWindowMove?: (fromColumn: number, done: boolean) => void;
  /** The actions of the passage, on the Proposal's bar. */
  barActions?: ReactNode;
  /** The transport, for the page's own play buttons, and whether it is sounding. */
  playerRef?: RefObject<ScorePlayerControls | null>;
  onPlaying?: (playing: boolean) => void;
}

/**
 * How a sheet is drawn in Play mode (plan section 17): no title lines, no scrub bar, no floating
 * bar, nothing that opens a toolbox. The page plays it from its own button and its own keys, keeps
 * the cursor in the middle of the window while it plays, and shows each lyrics piece only while its
 * frames sound. Several sheets can be on one page (the parts of a project, a playlist), each with
 * its own player; the page says which one plays.
 */
export interface PlayView {
  /** The transport, for the page's own play button and keys. */
  playerRef: RefObject<ScorePlayerControls | null>;
  onPlaying?: (playing: boolean) => void;
  /** Where the recording is, on every frame while it plays (Notes Falling reads it). */
  onTime?: (seconds: number | null) => void;
  /** The recording stopped by itself: at the end of the part, or of the stretch. */
  onEnded?: () => void;
  /** The cursor was moved on this sheet by the reader (a drag, a double-click). */
  onSeek?: () => void;
  /** A stretch of a playlist: where it starts and stops, in ms of the part. */
  fromMs?: number | null;
  toMs?: number | null;
  /** Ask the browser for the whole audio file at once (the sheet on show), or only its length. */
  preload?: "auto" | "metadata";
}

/** The piano sheet of a part. */
export function SheetPage({ step }: { step: SheetStep }) {
  return <FramesSheetPage step={step} />;
}

export default SheetPage;
