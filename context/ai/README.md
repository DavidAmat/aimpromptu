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
| **A stretch** | A stretch of the song, both hands or one, with the user's words | The dialog with notes or a stretch selected, the tab **A stretch** | `stretch-and-simplify.md` (Phase 10 writes it) |
| **Simplify** a hand | The easier version of one hand, or both, over the song | The tab **The whole song**, as a level of that hand | `stretch-and-simplify.md` (Phase 10) |
| **A level** | A passage, or the whole song, at **Easy**, **Medium** or **Hard**, with patterns | The tab **The whole song** or **A stretch**, with a level chosen | `levels.md` (Phase 11), `level-run.md` (Phase 12) |
| **The history of runs** | The log of each level run, the first batch first, a batch written again | The button **History of AI runs** in the sheet's buttons | `run-history.md` (Phase 13) |

The names in the table are the labels of the app. A page not yet written is named in code style, with the phase
that writes it.

## The model and the cost

- Every run uses **GPT-6.1 Terra** at medium effort, unless the user chooses another model in the dialog. The choices
  are GPT-6.1 Terra, GPT-6.1 Sol and Sonnet 5.5 (the dialog is the only place that names them).
- The keys are read from the environment or from the repository's `.env`: `OPENAI_API_KEY` for the OpenAI models,
  `ANTHROPIC_API_KEY` for Sonnet. A run is refused when the key of its model is missing ("This AI is not set up on
  this machine").
- The dialog shows the cost and the time of a run before it starts, about: the requests of the run, in US dollars and
  in minutes. The estimate is made from the song (its windows, its batches) and the measured cost of a request.
- The user chooses **batches** in the dialog: the song is written in that many parts, of about the same time.

The code and the numbers: [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md).

## The AI mark

The lists of projects show a small mark before the name of a song. It is the logo of AImpromptu:

- **green**: the AI enhanced the sheet of the song;
- **faint grey**: the AI could enhance it (it has notes) and has not;
- a spinner in its place while a job works on the song.

The mark has the same width whatever its state, so the names of a list stay aligned. It is `components/piece/AiMark.tsx`.

## Words the app uses

- **the AI** is the word on the page. The model's name is shown only in the dialog's model choice.
- **Enhance with AI** opens the dialog. **Enhance it again with AI** is its label once the part was enhanced.
- The states of a batch: **Waiting**, **Being written**, **Written**, **Kept as it was** (the check refused every reply).

## Pages of this folder

- [whole-run.md](whole-run.md): the whole run, its panel, **Stop** and **Revert**.

The other pages of the folder are written by the phases of the documentation refresh (see
[implementations/05-documentation-refresh](../implementations/05-documentation-refresh/05-plan.md)): the stretch and
Simplify, the levels, the level run and the history of runs.

## Where to look deeper

- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md): the jobs, the model
  client, the windows, the prompts and the routes
- [context/02-tech-stack.md](../02-tech-stack.md): the AI client and the model, in the stack
- [context/frontend/projects.md](../frontend/projects.md): the Sheet step and the lists where the AI mark shows
