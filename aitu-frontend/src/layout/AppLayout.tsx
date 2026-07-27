/** App chrome: brand bar, top-level section tabs, then the routed page. */

import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { Link, Outlet } from "react-router-dom";
import { TabBar } from "../ui";
import { ROUTES, TOP_SECTIONS } from "./routes";
import BackendStatus from "./BackendStatus";

export function AppLayout() {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 3 }}>
          <Typography
            component={Link}
            to={ROUTES.playgroundInput}
            variant="h2"
            sx={{ textDecoration: "none", color: "primary.main", flexShrink: 0 }}
          >
            AImpromptu
          </Typography>
          <Box sx={{ flexGrow: 1 }}>
            <TabBar items={TOP_SECTIONS} />
          </Box>
          <BackendStatus />
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Outlet />
      </Box>
    </Box>
  );
}

export default AppLayout;
