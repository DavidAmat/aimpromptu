# The AI in the app

The AI writes and rewrites the sheet of a part. The user starts it from **Enhance with AI** on the Sheet step, and
every run is a background job: the page shows the sheet as it changes, and the user can stop a run or take it back.
The AI decides the hands, the beams, the clefs and the octaves of the sheet; the app computes the figures, the grace
notes and the spelling. A run may also leave out or add notes (for the rules of simplicity and for a level); each
such run is one step of undo.

Read this page first, then the page of the run you need.

## The kinds of run

| Run | What it writes | Where the user starts it | Page |
|---|---|---|---|
| **Write it all again** (the whole run) | The hands and the reading of the whole song | **Enhance with AI** or **Enhance it again with AI**, the tab **The whole song** | [whole-run.md](whole-run.md) |
| **A stretch** | A stretch of the song, both hands or one, with the user's words | The dialog with notes or a stretch selected, the tab **A stretch** | [stretch.md](stretch.md) |
| **A level** | A passage, or the whole song, at **Easy**, **Medium** or **Hard**, with patterns | The tab **The whole song** or **A stretch**, with a level chosen | [levels.md](levels.md), [level-run.md](level-run.md) |
| **The history of runs** | The log of each level run, the first batch first, a batch written again | The button **History of AI runs** in the sheet's buttons | [run-history.md](run-history.md) |

The names in the table are the labels of the app. A page not yet written is named in code style, with the phase
that writes it.

## The model and the cost

- **The model of the LLM is one setting**, `AITU_LLM_MODEL` (in `.env`; `compose.yaml` passes it to the backend).
  Every run the user starts without choosing a model uses it. When the setting is empty, the model is the default of
  `aitu_backend/config.py` (`DEFAULT_LLM_MODEL`, `gpt-6.1-terra` today). This is the only page of the docs that
  names a model: every other page says "the LLM" (the code) or "the AI" (the app) and links here.
- **The choices of the dialog's Model selector** are one table of the backend, `aitu_backend/llm_models.py`
  (`TABLE`): for each model its label, its provider (OpenAI or Anthropic), its effort, its prices, and its cost and
  time measured against the model the estimates were measured with. The page reads the list from
  `GET /sheet/{uuid}/llm/costs` (`models`, the setting's model first, and `model`) and keeps none of its own. A model
  in the setting that the table does not hold is still offered first, named by its name.
- **A model never measured**: its cost in the estimate comes from its prices; its time is the measured model's. With no
  price at all, the estimate is the measured model's, and the cost of its requests counts as $0 (a warning in the
  backend log), so a new model never stops a run.
- The keys are read from the environment or from the repository's `.env`: `OPENAI_API_KEY` for the OpenAI models
  (required), `ANTHROPIC_API_KEY` for the Anthropic ones. A run is refused when the key of its model is missing ("This
  AI is not set up on this machine").
- The dialog shows the cost and the time of a run before it starts, about: the requests of the run, in US dollars and
  in minutes. The estimate is made from the song (its windows, its batches), the measured cost of a request, and the
  model's ratio.
- The user chooses **batches** in the dialog: the song is written in that many parts, of about the same time.

The code and the numbers: [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md).

## The AI mark

The lists of projects show a small mark before the name of a song. It is the logo of AImpromptu:

- **green**: the AI enhanced the sheet of the song;
- **faint grey**: the AI could enhance it (it has notes) and has not;
- a spinner in its place while a job works on the song.

The mark has the same width whatever its state, so the names of a list stay aligned. It is `components/piece/AiMark.tsx`.

## Words the app uses

- **the AI** is the word on the page. The model's name is shown only in the dialog's model choice. The docs of the
  code say **the LLM**.
- **Enhance with AI** opens the dialog. **Enhance it again with AI** is its label once the part was enhanced.
- The states of a batch: **Waiting**, **Being written**, **Written**, **Kept as it was** (the check refused every reply).

## Pages of this folder

- [whole-run.md](whole-run.md): the whole run, its panel, **Stop** and **Revert**.
- [stretch.md](stretch.md): a stretch of the sheet with the user's words.
- [levels.md](levels.md): the levels, the catalog of patterns, the chords of the song, the level copy.
- [level-run.md](level-run.md): a level run: the plan, the batches, the rules, the check, Strict and Suggested.
- [run-history.md](run-history.md): the history of AI runs: the log, the first batch first, an answer to the AI, a batch written again, Go on.

## Where to look deeper

- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md): the jobs, the model
  client, the windows, the prompts and the routes
- [context/02-tech-stack.md](../02-tech-stack.md): the AI client and the model, in the stack
- [context/frontend/projects.md](../frontend/projects.md): the Sheet step and the lists where the AI mark shows
