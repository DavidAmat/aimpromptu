/**
 * MUI theme built from `palette.ts`. Imported once, in `main.tsx`.
 *
 * Dark mode is the app default: the matrix grid, piano roll and falling views
 * all read better on a dark ground, and the brand "dark" shades are the
 * saturated ones meant to sit on it.
 */

import { createTheme } from "@mui/material/styles";
import { grays, palette, semantic } from "./palette";

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: palette.dark.Blue, light: palette.light.Blue, contrastText: grays.ink },
    secondary: { main: palette.dark.Green, light: palette.light.Green, contrastText: grays.ink },
    info: { main: semantic.status.info },
    success: { main: semantic.status.success },
    warning: { main: semantic.status.warning },
    error: { main: semantic.status.error },
    background: { default: grays.ink, paper: grays.charcoal },
    text: { primary: grays.paper, secondary: palette.light.Gray },
    divider: palette.dark.Gray,
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
        body: { backgroundColor: grays.ink },
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
