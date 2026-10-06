/**
 * **Lab**: the video reader's pages (implementation 02, Q-4). The tabs are the order of the work on
 * a video (bring it in, fit the piano, read the frames, turn them into notes), and Examples is
 * where a detection rule is measured before it is trusted.
 *
 * The Lab pages draw with many `ui` colours in canvases and SVGs; on a change of the colour scheme
 * they are drawn again from the start (`key`). They are development tools of the master user.
 */

import Box from "@mui/material/Box";
import { Outlet } from "react-router-dom";
import { PageBody, PageHeader, TabBar, useScheme } from "../ui";
import { LAB_TABS } from "./routes";

export function LabLayout() {
  const scheme = useScheme();
  return (
    <PageBody wide>
      <PageHeader title="Lab">
        <Box sx={{ width: "100%" }}>
          <TabBar items={LAB_TABS} />
        </Box>
      </PageHeader>
      <Box key={scheme} sx={{ pt: 2 }}>
        <Outlet />
      </Box>
    </PageBody>
  );
}

export default LabLayout;
