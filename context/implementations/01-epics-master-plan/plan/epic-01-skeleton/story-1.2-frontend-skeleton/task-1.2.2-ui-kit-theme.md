# Task 1.2.2 — UI kit and theme

One component library, standard across all pages. This is a PoC: beautiful and user-friendly, not professional-grade.

## Subtask 1.2.2.1 — Component library

- Standardize on MUI (+ MUI X for data grid / date-time pickers where useful).
- Aceternity UI allowed only for decorative flourishes (landing header, section transitions); every functional control is MUI so behavior stays consistent.
- Create a small `src/ui/` folder with shared wrappers (PageContainer, TabBar, Pill, SectionCard) so pages do not restyle raw MUI each time.

## Subtask 1.2.2.2 — Color palette

Port `context/colors/color-palette.md` to `src/ui/palette.ts` keeping the alias names and dark/light split:

```ts
export const palette = {
  dark:  { Blue: "#4681ff", Green: "#3cdcb4", Gray: "#393939", /* ... */ },
  light: { Blue: "#A2C0FF", Green: "#9DEDD9", Gray: "#9C9C9C", /* ... */ },
};
```

Wire it into the MUI theme. Reserve the semantic uses already decided by the features spec:

- matrix circles one-hand: black (onset), light gray (sustain)
- left hand: dark Green (onset), light Green (sustain)
- right hand: dark Blue (onset), light Blue (sustain)
- pressed piano key highlight: Blue

## Acceptance

Theme applied app-wide; palette imported from one module only (no hardcoded hex in components).
