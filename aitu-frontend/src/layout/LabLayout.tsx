/**
 * **Lab**: the video reader's pages (implementation 02, Q-4). The tabs are the order of the work on
 * a video (bring it in, fit the piano, read the frames, turn them into notes), and Examples is
 * where a detection rule is measured before it is trusted.
 */

import Box from "@mui/material/Box";
import { Outlet } from "react-router-dom";
import { PageBody, PageHeader, TabBar } from "../ui";
import { LAB_TABS } from "./routes";

export function LabLayout() {
  return (
    <PageBody wide>
      <PageHeader title="Lab">
        <Box sx={{ width: "100%" }}>
          <TabBar items={LAB_TABS} />
        </Box>
      </PageHeader>
      <Box sx={{ pt: 2 }}>
        <Outlet />
      </Box>
    </PageBody>
  );
}

export default LabLayout;
