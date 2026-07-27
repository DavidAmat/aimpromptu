import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { WorkingArtifactProvider } from "./state/WorkingArtifactProvider";
import { theme } from "./ui/theme";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <WorkingArtifactProvider>
          <App />
        </WorkingArtifactProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
