/**
 * The MUI theme, built from `tokens.ts` (implementation 02, plan sections 7.2 and 7.3). Imported
 * once, in `main.tsx`.
 *
 * Black, white and grey: one black primary button per screen, white secondary buttons with a grey
 * border, icon buttons with no border and a grey hover, pill buttons, 12 px inputs, and a 16 px
 * radius with the one soft shadow for anything that floats (menus, dialogs, toolboxes). Lists and
 * tables are flat. The colours of the music are not here: they are in `palette.ts`.
 *
 * Both schemes are defined, as CSS variables, so a component styled through the theme follows the
 * scheme by itself. The app opens in the light one (`main.tsx`); the choice of theme arrives with
 * the user menu in Phase 4.
 */

import { createTheme, type Theme } from "@mui/material/styles";
import { darkTokens, fontFamily, fontSize, lightTokens, radius, shadow, size, type Tokens } from "./tokens";

declare module "@mui/material/styles" {
  interface TypeBackground {
    /** The sidebar of the shell. */
    sidebar: string;
  }
}

function schemePalette(t: Tokens) {
  return {
    primary: { main: t.primary, contrastText: t.onPrimary },
    secondary: { main: t.text2, contrastText: t.bg },
    error: { main: t.danger },
    background: { default: t.bg, paper: t.bg, sidebar: t.bgSidebar },
    text: { primary: t.text, secondary: t.text2, disabled: t.text3 },
    divider: t.line,
    action: { hover: t.bgHover, selected: t.bgHover },
  };
}

/** The palette of the scheme in use, as CSS variables. */
const vars = (theme: Theme) => (theme.vars ?? theme).palette;

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "data-scheme" },
  colorSchemes: {
    light: { palette: schemePalette(lightTokens) },
    dark: { palette: schemePalette(darkTokens) },
  },
  shape: { borderRadius: radius.row },
  typography: {
    fontFamily,
    fontSize: fontSize.body,
    htmlFontSize: 16,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 600,
    h1: { fontSize: fontSize.title, fontWeight: 600, lineHeight: 1.3, letterSpacing: "-0.01em" },
    h2: { fontSize: fontSize.title, fontWeight: 600, lineHeight: 1.3, letterSpacing: "-0.01em" },
    h3: { fontSize: fontSize.body + 2, fontWeight: 600, lineHeight: 1.4 },
    body1: { fontSize: fontSize.body },
    body2: { fontSize: fontSize.body },
    caption: { fontSize: fontSize.meta },
    button: { textTransform: "none", fontWeight: 500, fontSize: fontSize.body },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontFamily },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: radius.pill,
          minHeight: size.button,
          paddingInline: 16,
          color: vars(theme).text.primary,
          "&.MuiButton-colorError": { color: vars(theme).error.main },
          "&:hover": { backgroundColor: vars(theme).action.hover },
        }),
        sizeSmall: { minHeight: size.buttonToolbox, paddingInline: 12 },
        contained: ({ theme }) => ({
          backgroundColor: vars(theme).primary.main,
          color: vars(theme).primary.contrastText,
          "&:hover": { backgroundColor: vars(theme).primary.main, opacity: 0.85 },
          // The danger colour, only inside the confirmation of a destructive action.
          "&.MuiButton-colorError": { backgroundColor: vars(theme).error.main, color: "#FFFFFF" },
          "&.Mui-disabled": { backgroundColor: vars(theme).action.hover, color: vars(theme).text.disabled },
        }),
        outlined: ({ theme }) => ({
          borderColor: vars(theme).divider,
          backgroundColor: vars(theme).background.paper,
          "&:hover": { borderColor: vars(theme).divider, backgroundColor: vars(theme).action.hover },
        }),
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          color: vars(theme).text.secondary,
          borderRadius: radius.pill,
          "&:hover": { backgroundColor: vars(theme).action.hover },
        }),
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          textTransform: "none",
          fontWeight: 500,
          color: vars(theme).text.secondary,
          borderColor: vars(theme).divider,
          "&.Mui-selected, &.Mui-selected:hover": {
            backgroundColor: vars(theme).action.selected,
            color: vars(theme).text.primary,
          },
        }),
      },
    },
    MuiToggleButtonGroup: {
      styleOverrides: {
        root: { borderRadius: radius.pill },
        grouped: {
          "&:first-of-type": { borderTopLeftRadius: radius.pill, borderBottomLeftRadius: radius.pill },
          "&:last-of-type": { borderTopRightRadius: radius.pill, borderBottomRightRadius: radius.pill },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: radius.input,
          "& .MuiOutlinedInput-notchedOutline": { borderColor: vars(theme).divider },
          "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: vars(theme).text.disabled },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: vars(theme).text.primary,
            borderWidth: 1.5,
          },
        }),
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: ({ theme }) => ({ "&.Mui-focused": { color: vars(theme).text.primary } }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none" },
        outlined: { borderRadius: radius.input },
      },
    },
    MuiPopover: {
      styleOverrides: {
        paper: { borderRadius: radius.float, boxShadow: shadow.float },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: { borderRadius: radius.float, boxShadow: shadow.float, minWidth: 180 },
        list: { padding: 6 },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: { borderRadius: radius.row, minHeight: 36, fontSize: fontSize.body },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: radius.float, boxShadow: shadow.float },
      },
    },
    MuiDialogTitle: {
      styleOverrides: { root: { fontSize: fontSize.title - 2, fontWeight: 600 } },
    },
    MuiDialogActions: {
      styleOverrides: { root: { padding: "8px 24px 20px", gap: 8 } },
    },
    MuiTooltip: {
      defaultProps: { arrow: false, enterDelay: 300 },
      styleOverrides: {
        tooltip: { fontSize: fontSize.meta - 1, fontWeight: 500, borderRadius: radius.row, padding: "6px 10px" },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: radius.pill, fontWeight: 500 },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: { minHeight: 40 },
        indicator: ({ theme }) => ({ backgroundColor: vars(theme).text.primary, height: 2 }),
      },
    },
    MuiTab: {
      styleOverrides: {
        root: ({ theme }) => ({
          textTransform: "none",
          fontWeight: 500,
          minHeight: 40,
          minWidth: 0,
          paddingInline: 12,
          color: vars(theme).text.secondary,
          "&.Mui-selected": { color: vars(theme).text.primary },
        }),
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: radius.input,
          border: `1px solid ${vars(theme).divider}`,
          backgroundColor: vars(theme).background.paper,
          color: vars(theme).text.primary,
          alignItems: "center",
        }),
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: ({ theme }) => ({ height: 3, borderRadius: 2, backgroundColor: vars(theme).divider }),
        bar: ({ theme }) => ({ backgroundColor: vars(theme).text.primary }),
      },
    },
    MuiCircularProgress: {
      defaultProps: { color: "inherit" },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: ({ theme }) => ({
          "&.Mui-checked": { color: vars(theme).background.paper },
          "&.Mui-checked + .MuiSwitch-track": { backgroundColor: vars(theme).text.primary, opacity: 1 },
        }),
      },
    },
    MuiDivider: {
      styleOverrides: { root: ({ theme }) => ({ borderColor: vars(theme).divider }) },
    },
  },
});

export default theme;
