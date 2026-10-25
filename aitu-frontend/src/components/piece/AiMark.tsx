/**
 * Whether the AI enhanced the sheet of a project or a song (implementation 03, Phase 5), as one small mark before
 * its name: the sparkle of **Enhance with AI**, green and filled once the AI enhanced it, faint and hollow when
 * it could and has not. Always the same width, so the names of a list stay aligned whatever the mark.
 */

import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import type { ReactNode } from "react";
import { semantic } from "../../ui";

export function AiMark({
  enhanced,
  could = true,
  busy,
}: {
  enhanced: boolean;
  /** Has notes the AI could enhance: the hollow mark when it has not. */
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
          <AutoAwesomeIcon sx={{ fontSize: 18, color: semantic.status.success }} aria-label="Enhanced with AI" data-enhanced />
        </Tooltip>
      ) : could ? (
        <Tooltip title="Not enhanced with AI yet">
          <AutoAwesomeOutlinedIcon sx={{ fontSize: 18, color: "text.disabled" }} aria-label="Not enhanced with AI yet" data-not-enhanced />
        </Tooltip>
      ) : null}
    </Box>
  );
}

export default AiMark;
