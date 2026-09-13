# Prompt — seed the library from YouTube

Hand the block below to the agent that will do the downloading.

---

You are working in the AImpromptu repo. Your job is to replace the current audio library with a new
one, downloaded from YouTube, and to pre-compute the transcription for every piece so nobody has to
wait for it later.

**Read these first, in this order. Do not skip them — they are why this project does things the way
it does, and several of them will contradict an assumption you are about to make.**

1. `context/implementations/01-epics-master-plan/plan/wall-clock-rewrite.md` — the five rules every
   task obeys, and the list of things that are dead and are not coming back.
2. `context/implementations/03-time-based-concept/decisions.md` — the frozen decisions D-01…D-34.
   **D-09 and D-10 constrain this task directly.** A task may not reinterpret a decision.
3. `context/implementations/01-epics-master-plan/plan/checklist.md` — what is built. Epics 1–13 are
   done; Epic 14 (documentation) is the only thing left.
4. `aitu-backend/src/aitu_backend/audio/youtube.py` and `audio/store.py` — how a YouTube download
   becomes a stored piece, and the rule about what may touch `data/audio/`.
5. `aitu-backend/src/aitu_backend/storage/paths.py` — the whole storage tree in one file.
6. `aitu-backend/src/aitu_backend/api/matrix.py` (the `/transcribe` route and `TranscribeRequest`)
   and `transcription/pipeline.py` — how transcription is started and what its defaults are.
7. `Makefile` at the repo root — how to bring the app up (`make serve`; API on 8765, web on 5173).

**The work.**

- `library/01-starting-library.md` is the source list. Parse it into a JSON file — one entry per
  piece with `title`, `artist` and `url` as separate fields — and keep that file; it is the record
  of what the library is supposed to contain. The lines are handwritten and inconsistent (the artist
  is sometimes before the URL, sometimes after, sometimes missing), so read them carefully rather
  than splitting on a delimiter.
- Wipe the existing library first, then download all of them with yt-dlp.
- Run it as a background process, one at a time, with a sleep between downloads. YouTube blocks
  bulk automated downloads; pace it and make the pause long enough to look human. Do not parallelise.
  One failure must not stop the rest — collect failures and report them at the end so they can be
  retried on their own.
- Put each one where the app already expects an ingested piece to be, so it shows up in the
  **Audio library** on the Upload / Input tab without any further step. Go through the existing
  storage layer rather than writing files into `data/` yourself; file 4 above says why.
- Then, also in the background and also paced, run transcription over every downloaded piece with
  the project's default settings, so `events.json` exists for all of them before anyone opens them.
  Transcription is slow (tens of seconds each) and the endpoint is asynchronous — follow the job,
  don't fire and forget.

**Three things to settle with me before you start, not after.**

1. Wiping the library deletes real work. Show me what will be destroyed and wait for me to confirm.
2. One entry says `mr blue sky - ELO (we already have it)` and has no URL — which contradicts the
   wipe. Ask me what to do with it.
3. Read D-09 before you decide what "pre-compute the piano sheet" means. You can precompute
   everything the sheet is derived *from*; whether you can go further than that is the question, and
   the answer is in that decision. Tell me where you think the line is and let me agree with you.

Work in a branch. Report what landed, what failed, and what you did not do.
