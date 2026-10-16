/**
 * **Side by side** (implementation 02, Phase 14, plan section 16.3): the Public Library's version
 * now on the left (or nothing, for a new one) and the proposed one on the right, both as read-only
 * piano sheets that play. Each side has its own Play button; starting one stops the other. A
 * window narrower than 1200 px puts the two one under the other.
 *
 * Each sheet is the Sheet step's own page in the role of a passage's **Current** (Phase 9): drawn
 * and played as it is edited, with no toolbox and no bar. A project of several parts shows its
 * first part here; **Open in Play mode** plays them all.
 */

import { useCallback, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useNavigate } from "react-router-dom";
import type { ProjectSide } from "../../api";
import type { ScorePlayerControls } from "../../components/time/ScorePlayer";
import { ROUTES } from "../../layout/routes";
import { IconAction } from "../../ui";
import SheetPage from "../piece/sheet/SheetPage";

type Which = "current" | "proposed";

function Side({
  label,
  side,
  empty,
  playing,
  onToggle,
  playerRef,
  onPlaying,
}: {
  label: string;
  side: ProjectSide | null;
  empty: string;
  playing: boolean;
  onToggle: () => void;
  playerRef: React.RefObject<ScorePlayerControls | null>;
  onPlaying: (now: boolean) => void;
}) {
  const navigate = useNavigate();
  const part = side?.kept ? side.parts[0] : undefined;
  return (
    <Box sx={{ minWidth: 0, flex: 1 }} data-testid={`compare-${label === "Now" ? "current" : "proposed"}`}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", minHeight: 40, mb: 1 }}>
        <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{label}</Typography>
        {side ? (
          <Typography noWrap sx={{ fontSize: 13, color: "text.secondary", minWidth: 0 }}>
            “{side.name}”, by {side.creator}
            {side.parts.length > 1 ? `, ${side.parts.length} parts` : ""}
          </Typography>
        ) : null}
        <Box sx={{ flex: 1 }} />
        {part && side ? (
          <>
            <IconAction
              title={playing ? "Pause" : `Play ${label === "Now" ? "the version now" : "the proposal"}`}
              icon={playing ? <PauseIcon /> : <PlayArrowIcon />}
              onClick={onToggle}
              data-testid={`compare-play-${label === "Now" ? "current" : "proposed"}`}
            />
            <IconAction
              title="Open in Play mode"
              icon={<OpenInFullIcon fontSize="small" />}
              onClick={() => navigate(ROUTES.play(side.projectId))}
            />
          </>
        ) : null}
      </Stack>
      <Box
        sx={(theme) => ({
          border: 1,
          borderColor: "divider",
          borderRadius: 2,
          backgroundColor: (theme.vars ?? theme).palette.background.default,
          overflow: "hidden",
          minHeight: 160,
        })}
      >
        {part ? (
          <SheetPage
            key={part}
            step={{
              audioUuid: part,
              state: "ready",
              reason: null,
              onChanged: () => undefined,
              passage: { role: "current", playerRef, onPlaying },
            }}
          />
        ) : (
          <Typography sx={{ fontSize: 14, color: "text.secondary", p: 2 }}>
            {side && !side.kept ? "This project is no longer kept." : empty}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export function CompareSheets({
  current,
  proposed,
  empty = "Nothing yet: this is a new version",
}: {
  current: ProjectSide | null;
  proposed: ProjectSide | null;
  empty?: string;
}) {
  const currentPlayer = useRef<ScorePlayerControls | null>(null);
  const proposedPlayer = useRef<ScorePlayerControls | null>(null);
  const [playing, setPlaying] = useState<Which | null>(null);
  const report = useCallback(
    (which: Which) => (now: boolean) => setPlaying((was) => (now ? which : was === which ? null : was)),
    [],
  );
  const reportCurrent = useCallback((now: boolean) => report("current")(now), [report]);
  const reportProposed = useCallback((now: boolean) => report("proposed")(now), [report]);
  const toggle = (which: Which) => {
    const other: Which = which === "current" ? "proposed" : "current";
    const player = (one: Which) => (one === "current" ? currentPlayer : proposedPlayer);
    if (playing === other) player(other).current?.toggle();
    player(which).current?.toggle();
  };

  return (
    <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ alignItems: "stretch" }}>
      <Side
        label="Now"
        side={current}
        empty={empty}
        playing={playing === "current"}
        onToggle={() => toggle("current")}
        playerRef={currentPlayer}
        onPlaying={reportCurrent}
      />
      <Side
        label="Proposed"
        side={proposed}
        empty="The proposal is not kept."
        playing={playing === "proposed"}
        onToggle={() => toggle("proposed")}
        playerRef={proposedPlayer}
        onPlaying={reportProposed}
      />
    </Stack>
  );
}

export default CompareSheets;
