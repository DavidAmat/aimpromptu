/**
 * Video to Notes chrome: the four tabs, in the order of the work.
 *
 * A piano roll animation already shows every note, every start and every release,
 * drawn on purpose to be read. This section is where we read the picture instead
 * of listening to the sound — and where what was read is checked against what a
 * person read by hand.
 */

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import { Outlet } from "react-router-dom";
import { TabBar } from "../ui";
import { VIDEO_TABS } from "./routes";

export function VideoLayout() {
  return (
    <Box>
      <Container maxWidth={false} sx={{ pt: 1 }}>
        <TabBar items={VIDEO_TABS} />
      </Container>
      <Outlet />
    </Box>
  );
}

export default VideoLayout;
