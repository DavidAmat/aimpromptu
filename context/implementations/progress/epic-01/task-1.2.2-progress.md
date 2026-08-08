# Task 1.2.2 — UI kit and theme · progress report

Status: **done**. Date: 2026-07-26.

> Ordering note: this task was implemented **before** Task 1.2.1, not after. The app shell has
> to render *something*, and everything it renders is MUI reading the theme — building the shell
> first would have meant restyling it immediately. No requirement changed; only the order.

## Summary

**Dependencies added** — `@mui/material@^9.2`, `@mui/icons-material`, `@mui/x-data-grid`,
`@emotion/react`, `@emotion/styled`. (`react-router-dom@^7.18` came with Task 1.2.1.)

**`src/ui/palette.ts`** — the `dark`/`light` × 10-alias table from
`context/colors/color-palette.md`, ported verbatim with the alias names preserved, plus:

- `grays` — the extra gray spectrum the palette doc explicitly allows, named rather than inlined
  (`ink`, `charcoal`, `slate`, `silver`, `mist`, `paper`, `white`).
- `semantic` — the product meanings already decided by the features spec:

  | Meaning | Onset | Sustain |
  |---------|-------|---------|
  | `matrixOneHand` | `grays.ink` (black) | `grays.silver` (light gray) |
  | `leftHand` | dark Green `#3cdcb4` | light Green `#9DEDD9` |
  | `rightHand` | dark Blue `#4681ff` | light Blue `#A2C0FF` |

  plus `pressedKey` (dark Blue), `steps` (one color per processing step), `status`
  (info/success/warning/error) and `waveform` (body/selection/cursor).
- `handColors(hand)` — the lookup the matrix grid and roll views will call.

**`src/ui/theme.ts`** — `createTheme` fed entirely from `palette.ts`. Dark mode is the default:
the matrix grid, piano roll and falling views read better on a dark ground, and the brand "dark"
shades are the saturated ones meant to sit on it. Also sets `borderRadius: 10`, the Inter type
scale, `textTransform: none` on buttons and tabs.

> **Reversed on 2026-07-27.** The app is now light, and pinned so a dark OS or browser cannot
> re-tint it. The reasoning above was never checked against the semantic colors: a struck matrix
> note is `grays.ink` and the background was `grays.ink` too, so it was invisible. See
> [`task-1.2.2-followup-light-mode.md`](task-1.2.2-followup-light-mode.md) — which also introduces
> the `surface` tokens that stop a view from assuming a ground again.

**`src/ui/` wrappers**, so no page restyles raw MUI:

| Component | Role |
|-----------|------|
| `PageContainer` | title + subtitle + actions + content, `wide` for full-bleed pages |
| `SectionCard` | outlined surface with an optional header row; `flush` for grids/canvases |
| `Pill` | selectable chip, accent color from `palette.ts` — the Epic 7 step pills |
| `TabBar` | router-aware tab strip (longest matching path prefix wins) |
| `Placeholder` | "coming in Epic N" block, so every unbuilt route still says who owns it |

`src/ui/index.ts` re-exports all of them plus `palette`, `grays`, `semantic`, `handColors`, `theme`.

**`src/index.css`** was stripped of its hardcoded `color`/`background` (`#2c261d` / `#f3eee5`)
— they fought the theme and violated the no-hex rule. It now carries document resets only;
`CssBaseline` plus the theme own everything visual.

## Errors found and how they were solved

1. **MUI v9 dropped system props from `Stack` and `Typography`.** `justifyContent`, `alignItems`
   and `fontWeight` as direct props are now type errors (`TS2769`, five files). All moved into
   `sx`. Worth knowing for every later epic: **in MUI v9, layout props live in `sx`.**
2. **Aceternity UI not installed.** The task allows it for decoration only and nothing decorative
   exists yet; adding an unused dependency (it also pulls in Tailwind, which this app does not use)
   would have been noise. Deferred until a page actually wants a flourish — the rule that
   functional controls stay MUI is what matters and is recorded in the frontend README.

## Deviations from the task file

- Task order swapped with 1.2.1 (see the note at the top).
- Added `Placeholder` to `src/ui/` beyond the four wrappers named in the task; the shell needs it
  on every route.
- MUI X is installed (`@mui/x-data-grid`) but not yet used — Epic 7's matrix grid is its first
  customer.

## Verification

```
npx tsc -b        # clean
npm run lint      # clean
npx vite build    # 479 modules, 417 kB / 134 kB gzipped
```

`grep -rn "#[0-9a-fA-F]\{6\}" src --include=*.tsx` returns nothing: the only hex literals in the
app are in `palette.ts`.

## Manual trial for the supervisor

`npm run dev`, then check: dark ground throughout, blue "AImpromptu" wordmark, tab underline in
brand Blue, the three BPM/granularity/step pills in the Playground bar outlined in Blue.
If any surface still looks cream/beige, something is importing `App.css` again.

> Superseded by the light-mode follow-up: the ground is now **light** throughout. Everything else in
> this check still applies.

## For the next worker

- Import colors from `../ui` (`semantic`, `palette`, `handColors`) — never a hex literal.
- Layout props go in `sx`, not as direct props (MUI v9).
- If a page needs a new shared shape, add it to `src/ui/` rather than styling MUI inline twice.
