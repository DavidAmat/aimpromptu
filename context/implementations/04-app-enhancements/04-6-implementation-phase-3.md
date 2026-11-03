# 04-6, Phase 3: the model of the LLM in one place, the frontend

Plan: [`04-6-plan.md`](04-6-plan.md) section 4.2. Branch `feat/04-6-run-safety-and-model`. Only `aitu-frontend/`
changed (no backend edit, so no running AI run could stop); no browser check ran during an edit.

## 1. What was built

- **`src/api/sheet.ts`**: `AI_MODELS` removed; `AiModel` is `string`; new `AiModelChoice` (`value`, `label`).
  `LlmCosts` adds `models: AiModelChoice[]` and `model: AiModel` (what `GET /llm/costs` answers since Phase 2).
  `BatchQuery.model` is optional (none: the setting's). `src/api/index.ts` exports `AiModelChoice`, no longer
  `AI_MODELS`.
- **`EnhanceDialog.tsx`**: `model` is the user's choice, `null` at the start (no `"gpt-6.1-terra"` any more).
  `asked` is that choice while `costs.models` offers it, else `null`; the selector shows `asked ?? costs.model`
  (`""` until the costs arrive) and lists `costs.models`. A run and `GET /llm/batches` send `model` only when the
  user chose one: a run left on the setting's names none and the backend uses `AITU_LLM_MODEL`. The dialog is made
  again at each opening, so each opening starts on the setting's model. The module docstring and `timeOf` no longer
  name a model.
- **Comments** that said "Sonnet" now say "the AI": `api/sheet.ts` (6), `api/pieces.ts`, `api/projects.ts`,
  `useFramesSheet.ts`, `FramesSheetView.tsx`, `FramesSheetPage.tsx` ("the AI's (Sonnet 5.5 today)" → "the AI's").
  `git grep -i -E "sonnet|gpt-6|terra|claude" -- aitu-frontend/src`: nothing.
- **The browser checks**:
  - `check-enhance-dialog.mjs` names no model. It reads `GET /llm/costs` of its copy: the selector shows
    `costs.model` first; its options are the labels of `costs.models`, in order; it picks the first other model
    and checks that the cost shown equals the backend's own `GET /llm/batches?...&model=<it>` (before: "Sonnet 5.5
    costs more than Terra"); Write the level sends that model. With one model only, it says so and expects no
    `model` in the body.
  - `check-ai-history.mjs`: the stand-in log's model is `MODEL = 'stand-in-model'` (the history does not show it).
  - The live walks (`check-flow`, `check-frames-sheet`, `check-frames-edit`, `check-journey`, `time-flow`): "Sonnet"
    in comments and check labels → "the AI"; `time-flow`'s `firstSonnet` → `firstAi` (column "first AI segment"),
    `check-flow`'s screenshot `16-sheet-sonnet-working` → `16-sheet-ai-working`. No file refers to the old names.
    Not run: they spend credits.

## 2. Findings

- **There is no `npm run typecheck`** in `aitu-frontend/package.json` (Phase 1's report says it passed; the plan
  names it). The type check is `npx tsc -b`, the first step of `npm run build`. The plan's section 5 now says so.
- **The `simplify-*` keys and the `staff` comment "(Simplify or a stretch of one hand)"** stay for Phase 4.

## 3. Checks

- `npx tsc -b`: passes. `npx eslint` on the changed files of `src/`: passes. `node --check` on every script.
- `npm run check:enhance-dialog`: **all passed** (the setting's model `gpt-6.1-terra` by default; the options
  "GPT-6.1 Terra | GPT-6.1 Sol | Sonnet 5.5"; GPT-6.1 Sol $0.55 = the backend's $0.55; the level copy sent
  `"model": "gpt-6.1-sol"`; the later runs, after a new opening, sent no model; no request reached the AI).
  Screenshot `08-batches` checked: the selector shows "GPT-6.1 Sol".
- `npm run check:ai-history`: **all passed** (it takes no `--out`).
