/**
 * The design tokens: every colour, size and radius of the app around the music
 * (implementation 02, plan section 7.2).
 *
 * The app is black, white and grey. Colour is spent in one place only, the music
 * itself (the two hands, the selection, the piano roll), and those colours live in
 * `palette.ts`, not here. The MUI theme (`theme.ts`) is built from these tokens, and
 * pages read them through the theme (`text.secondary`, `divider`, ...). Drawing code
 * that cannot read the theme (a canvas, an SVG) imports `ui`.
 *
 * There are two schemes, light and dark. The piano sheet is a page of paper and
 * stays white in both (`paper`), and the piano roll keeps its own colours
 * (`palette.ts`). The user chooses the scheme in the user menu (Phase 4):
 * `applyScheme` copies it into `ui` in place, and the components that draw with
 * `ui` re-render through `useScheme()` (`scheme.tsx`).
 */

export interface Tokens {
  /** The page. */
  bg: string;
  /** The sidebar. */
  bgSidebar: string;
  /** Hover of rows and icon buttons, the selected row. */
  bgHover: string;
  /** Borders and dividers. */
  line: string;
  /** A line that must stay visible on its own: an axis, a lane edge. */
  lineStrong: string;
  /** Text. */
  text: string;
  /** Secondary text and icons. */
  text2: string;
  /** Disabled, placeholders. */
  text3: string;
  /** The one primary button of a screen: its fill, and the text on it. */
  primary: string;
  onPrimary: string;
  /** Only inside a confirmation of a destructive action. */
  danger: string;
  /** The piano sheet, white in both schemes. */
  paper: string;
}

export const lightTokens: Tokens = {
  bg: "#FFFFFF",
  bgSidebar: "#F9F9F9",
  bgHover: "#ECECEC",
  line: "#E5E5E5",
  lineStrong: "#C7C7C7",
  text: "#0D0D0D",
  text2: "#5D5D5D",
  text3: "#8F8F8F",
  primary: "#000000",
  onPrimary: "#FFFFFF",
  danger: "#D92D20",
  paper: "#FFFFFF",
};

export const darkTokens: Tokens = {
  bg: "#212121",
  bgSidebar: "#171717",
  bgHover: "#2F2F2F",
  line: "#3A3A3A",
  lineStrong: "#5A5A5A",
  text: "#ECECEC",
  text2: "#B4B4B4",
  text3: "#8F8F8F",
  primary: "#FFFFFF",
  onPrimary: "#000000",
  danger: "#F97066",
  paper: "#FFFFFF",
};

/** The scheme in use, for drawing code that cannot read the theme. Changed in place. */
export const ui: Tokens = { ...lightTokens };

export type SchemeName = "light" | "dark";

/** Make `ui` the tokens of a scheme. Components re-render through `useScheme()`. */
export function applyScheme(scheme: SchemeName): void {
  Object.assign(ui, scheme === "dark" ? darkTokens : lightTokens);
}

/** The type scale (plan section 7.3), in pixels. */
export const fontSize = {
  meta: 13,
  body: 14,
  input: 16,
  title: 20,
  play: 28,
} as const;

export const fontFamily = ['"Geist"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"].join(", ");

/** Heights and widths that more than one component must agree on. */
export const size = {
  button: 36,
  buttonToolbox: 32,
  icon: 20,
  sidebar: 260,
  sidebarClosed: 64,
} as const;

export const radius = {
  /** Text fields and selects. */
  input: 12,
  /** Floating things: toolboxes, floating bars, menus, dialogs. */
  float: 16,
  /** Buttons: fully rounded. */
  pill: 999,
  /** Rows and small surfaces. */
  row: 8,
} as const;

/** The one shadow of the app, for floating things only. */
export const shadow = {
  float: "0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.06)",
} as const;
