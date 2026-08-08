/**
 * MUI theme built from `palette.ts`. Imported once, in `main.tsx`.
 *
 * **The app is light, always.** Not "light by default" — the mode is pinned and
 * there is no `prefers-color-scheme` branch anywhere, so a Mac or a Chrome in
 * dark mode cannot re-tint it. `color-scheme: light` (set below, in `index.css`
 * and as a meta tag in `index.html`) completes the lock: without it the browser
 * still darkens the parts it owns rather than us — scrollbars, native form
 * controls, and whole pages under Chrome's Auto Dark Mode.
 *
 * Why light at all: sheet music is black on white, and so is a piano matrix. A
 * struck note is `grays.ink` and a held one `grays.silver`; on a dark ground the
 * struck note disappeared into the background, which is exactly the distinction
 * the Matrix tab exists to show.
 */

import { createTheme } from "@mui/material/styles";
import { grays, palette, semantic, surface } from "./palette";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: palette.dark.Blue, light: palette.light.Blue, contrastText: grays.white },
    secondary: { main: palette.dark.Green, light: palette.light.Green, contrastText: grays.ink },
    info: { main: semantic.status.info },
    success: { main: semantic.status.success },
    warning: { main: semantic.status.warning },
    error: { main: semantic.status.error },
    background: { default: surface.page, paper: surface.panel },
    text: { primary: surface.text, secondary: surface.mutedText },
    divider: surface.line,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: ['"Inter"', "system-ui", "Avenir", "Helvetica", "Arial", "sans-serif"].join(","),
    h1: { fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.02em" },
    h2: { fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.01em" },
    h3: { fontSize: "1.15rem", fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        // `colorScheme` is the declaration the browser itself reads; it is what
        // keeps scrollbars and native controls light under a dark OS.
        ":root": { colorScheme: "light" },
        body: { backgroundColor: surface.page, color: surface.text },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, minHeight: 44 },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none" },
      },
    },
  },
});

export default theme;
