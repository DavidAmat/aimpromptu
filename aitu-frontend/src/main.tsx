import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import { WorkingArtifactProvider } from "./state/WorkingArtifactProvider";
import { theme } from "./ui/theme";
import "./index.css";

/**
 * A data router with one route that matches every address, and `App` declaring the real routes
 * inside it as before.
 *
 * The data router is what makes `useBlocker` work: the flow page asks before it lets a reader
 * leave a tab with unsaved changes, whichever link they used (implementation 08, plan section
 * 7.3). `<BrowserRouter>` cannot block a navigation. Nothing else changes: every page still
 * reads its address with the same hooks.
 */
const router = createBrowserRouter([
  {
    path: "*",
    element: (
      <WorkingArtifactProvider>
        <App />
      </WorkingArtifactProvider>
    ),
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Light until the theme choice of the user menu exists (Phase 4); the dark scheme is defined. */}
    <ThemeProvider theme={theme} defaultMode="light">
      <CssBaseline />
      <RouterProvider router={router} />
    </ThemeProvider>
  </StrictMode>,
);
