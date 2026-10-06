import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./state/AuthProvider";
import { WorkingArtifactProvider } from "./state/WorkingArtifactProvider";
import { SchemeSync } from "./ui/scheme";
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
      <AuthProvider>
        <WorkingArtifactProvider>
          <App />
        </WorkingArtifactProvider>
      </AuthProvider>
    ),
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Light unless the user chose Dark or System in the user menu; MUI keeps the choice. */}
    <ThemeProvider theme={theme} defaultMode="light">
      <CssBaseline />
      <SchemeSync>
        <RouterProvider router={router} />
      </SchemeSync>
    </ThemeProvider>
  </StrictMode>,
);
