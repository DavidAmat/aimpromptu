/** App chrome: brand bar, top-level section tabs, then the routed page. */

import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import { Link, Outlet } from "react-router-dom";
import { TabBar } from "../ui";
import { ROUTES, TOP_SECTIONS } from "./routes";
import BackendStatus from "./BackendStatus";

export function AppLayout() {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 3 }}>
          {/* The official logo (`public/logo-final-2.svg`), drawn at the height of the bar. */}
          <Box
            component={Link}
            to={ROUTES.pieceRoot}
            aria-label="AImpromptu, open the working piece"
            sx={{ display: "flex", alignItems: "center", flexShrink: 0 }}
          >
            <Box component="img" src="/logo-final-2.svg" alt="AImpromptu" sx={{ height: 34, width: "auto", display: "block" }} />
          </Box>
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
