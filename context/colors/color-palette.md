# Colour palette

The app is black, white and grey, and colour is spent in one place only: **the music itself**
(the two hands, the selection, the piano roll, the waveform). Everything around the music (the page,
the sidebar, text, lines, buttons) comes from the design tokens, so the piano sheet and the piano
roll are the most colourful things on any screen. This is the direction of implementation 02 (plan
section 7, [`02-plan.md`](../implementations/02-private-web-app/02-plan.md)).

Two files hold every colour, and no component writes a hex value:

| File | Holds |
|---|---|
| `aitu-frontend/src/ui/tokens.ts` | The tokens of the page, light and dark, and the type scale, radii and shadow. The MUI theme (`theme.ts`) is built from them |
| `aitu-frontend/src/ui/palette.ts` | The colours of the music: the aliases below, the greys of the drawn notes and keys, and their meanings (`semantic`) |

## 1. The tokens

| Token | Light | Dark | Used for |
|---|---|---|---|
| `bg` | `#FFFFFF` | `#212121` | The page |
| `bgSidebar` | `#F9F9F9` | `#171717` | The sidebar |
| `bgHover` | `#ECECEC` | `#2F2F2F` | Hover of rows and icon buttons, the selected row |
| `line` | `#E5E5E5` | `#3A3A3A` | Borders and dividers |
| `lineStrong` | `#C7C7C7` | `#5A5A5A` | A line that must stay visible on its own: an axis, a lane edge |
| `text` | `#0D0D0D` | `#ECECEC` | Text |
| `text2` | `#5D5D5D` | `#B4B4B4` | Secondary text, icons |
| `text3` | `#8F8F8F` | `#8F8F8F` | Disabled, placeholders |
| `primary` / `onPrimary` | `#000000` / `#FFFFFF` | `#FFFFFF` / `#000000` | The one primary button of a screen |
| `danger` | `#D92D20` | `#F97066` | Only inside the confirmation of a destructive action |
| `paper` | `#FFFFFF` | `#FFFFFF` | The piano sheet, white in both schemes |

### 1.1 Choosing the scheme

Since implementation 02, Phase 4 the user menu offers **Light**, **Dark** and **System** (the
device's own setting). The app opens in the light one until the user chooses, and MUI keeps the
choice in the browser (`localStorage`, `mui-mode`), so each browser remembers its own.

Everything styled through the MUI theme follows a change at once, because the theme keeps both
schemes as CSS variables. Drawing code (a canvas, an SVG) cannot read those variables, so it reads
`ui` from `tokens.ts` instead, and follows a change in three steps:

1. `SchemeSync` (`ui/scheme.tsx`, placed in `main.tsx`) reads MUI's mode.
2. It calls `applyScheme`, which copies the light or the dark tokens into `ui` in place, before
   the page renders.
3. Every component that draws with `ui` calls `useScheme()`, so it renders again with the new
   colours. Nothing is remounted, so a page with unsaved changes keeps them. The Lab pages, which
   use many `ui` colours, are redrawn from the start instead.

**Two things do not change with the scheme.** The piano sheet stays white paper in both schemes
(`paper`, plan P-8), because it is the page that is printed. The piano roll keeps its own dark panel
and the colours of section 2.

## 2. The colours of the music

The aliases are the user's own, and a conversation about "dark Green" or "light Blue" maps one to
one onto `palette.ts`:

| Alias | Dark | Light |
|---|---|---|
| Blue | `#4681ff` | `#A2C0FF` |
| Pink | `#ff6495` | `#FFB1CA` |
| Lavender | `#816eff` | `#C0B6FF` |
| Yellow | `#ffc83c` | `#FFE39D` |
| Green | `#3cdcb4` | `#9DEDD9` |
| Orange | `#ff8b32` | `#FFC598` |
| Brown | `#664E3C` | `#B2A69D` |
| Red | `#FE6060` | `#FEAFAF` |
| Cyan | `#00E7E7` | `#B2F7F7` |
| Gray | `#393939` | `#9C9C9C` |

What they mean on screen (`semantic` in `palette.ts`):

| Meaning | Colour |
|---|---|
| Right hand | dark Blue for an onset, light Blue for a sustain |
| Left hand | dark Green for an onset, light Green for a sustain |
| A note with no hand, a note marked to come off | Red |
| The selection in the piano roll | Lavender |
| The playhead | Pink |
| The waveform, its selection, its cursor | light Blue, dark Lavender, dark Pink |
| A step out of date, an unsaved step (the dot of the step tabs) | dark Orange |

The piano roll visualization has its own dark panel (`semantic.roll`), so the rectangles are the
brightest thing on it.

## 3. Where to look deeper

- [`../frontend/README.md`](../frontend/README.md): the app shell and the shared components
- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md):
  every shared component of `src/ui/`
