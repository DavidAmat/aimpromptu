/**
 * Whether the AI enhanced the sheet of a project or a song (implementation 03, Phase 5), as one small mark before
 * its name: the logo of AImpromptu (implementation 04, prompt 04-2), green once the AI enhanced it, faint grey when
 * it could and has not. Always the same width, so the names of a list stay aligned whatever the mark.
 */

import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import type { ReactNode } from "react";
import { Logo, semantic } from "../../ui";

export function AiMark({
  enhanced,
  could = true,
  busy,
}: {
  enhanced: boolean;
  /** Has notes the AI could enhance: the faint mark when it has not. */
  could?: boolean;
  /** Shown in place of the mark: a job working on it now (a spinner). */
  busy?: ReactNode;
}) {
  return (
    <Box sx={{ width: 18, display: "grid", placeItems: "center", flexShrink: 0 }}>
      {busy ? (
        busy
      ) : enhanced ? (
        <Tooltip title="Enhanced with AI">
          <Box sx={{ display: "grid", color: semantic.status.success }} aria-label="Enhanced with AI" data-enhanced>
            <Logo height={18} />
          </Box>
        </Tooltip>
      ) : could ? (
        <Tooltip title="Not enhanced with AI yet">
          <Box sx={{ display: "grid", color: "text.disabled" }} aria-label="Not enhanced with AI yet" data-not-enhanced>
            <Logo height={18} />
          </Box>
        </Tooltip>
      ) : null}
    </Box>
  );
}

export default AiMark;
