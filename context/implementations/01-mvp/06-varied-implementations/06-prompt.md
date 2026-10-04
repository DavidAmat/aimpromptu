You are working on the sheet of the Playground's Rhythm page. Read
@context/language/communication-implementation-plans.md,
@context/09-coding-conventions.md, @context/04-local-development.md,
@context/frontend/annotations.md, @context/frontend/rendering.md,
@context/implementations/03-time-based-concept/decisions.md,
@context/implementations/03-time-based-concept/contract.md,
@documentation/services/frontend/grid-notation.md,
@documentation/services/backend/rhythm-and-annotations.md,
@aitu-frontend/src/pages/playground/RhythmPage.tsx and
@aitu-frontend/src/components/time/TimeScoreView.tsx.

Build undo and redo for every edit a reader makes on the sheet: Command-Z takes the
last one back, Shift-Command-Z puts it back, and the two are also buttons beside
"Write the sheet". Every edit that lives in the page's own state (key, octave
brackets, trills, words, small stretches, spacing, fingers, figure overrides, beam
breaks, notes taken off, grace notes, the decorative-notes switch) must be undoable
in one step; an edit that writes to the recording (a hand swap, a re-record) must
either be undoable through the backend or say plainly that it is not. Write an
implementation plan first, in the folder and format the other implementations use,
and raise anything that goes against the frozen decisions before building.

We have started a new folder: `context/implementations/06-varied-implementations` put the report of what you changed in a file there.

Also, another thing that I want you to do is: currently, we should have a way to control the spacing between the set of lines. We have a set of pentagrammas indicating the right and left hand, both joined with the { curly bracket. When we look at two lines (two sets of curly brackets) spacing, it is a lot, it has a lot of white space, some sheets have high notes so it is good to have some space so that notes from one line do not get mixed to another line (the left hand line low frequency notes may collide with high frequency notes of the right hand line) . So my proposal is to have a kind of small slider next to the Key Signature of the sheet to control this