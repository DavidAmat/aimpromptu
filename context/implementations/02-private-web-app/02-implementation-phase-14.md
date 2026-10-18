# 02: Phase 14 report: Requests, the Admin panel and sharing

Plan: [`02-plan.md`](02-plan.md) sections 6.3, 9.3, 15.2, 15.4 and 16, and section 20, Phase 14.
Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-14`, made from `master` at
`ac45f0c` (Phase 13 merged after the user's ok, 2026-10-16). Built 2026-10-16 on the Ubuntu machine,
while another project held about 10 GB of the GPU: the backend tests ran on the CPU and no check
that transcribes was run (nothing of the transcription changed).

The page this phase writes is [`../../music-library/requests.md`](../../music-library/requests.md);
this report is the detail behind it.

# 1. Summary

| Story | Result |
|---|---|
| 14.1 Requests | Four kinds (the plan's three and **Playlist**, the user's answer), each made of items with their own decision. **Publish** on a version of My library (and on a playlist), **Suggest a change** on a public song or artist, **Propose a song** on Public songs, **Ask for a fixed version** on the user's own version. The project is copied when sent, into a layer of its own (`request`). **Requests** lists them; **Withdraw**; **Change and send again** |
| 14.2 Review | **Admin → Review** (open requests, oldest first; **All**). A request's page is laid out like a pull request (the user's ask of 2026-10-18, section 11): **Conversation** (the timeline; comments of the author and the master user; a comment on a marked stretch of the sheet draws that stretch; replies; the reviews) and **Sheet** (the whole proposed sheet; **Proposed** and **Now**). **Review** opens **Finish your review**: a decision per item (Accept, with the name changeable; Ask for a change; Refuse). What is accepted is written in one transaction; the author is the creator of the version |
| 14.3 Sharing | **Share my library** (user menu, Shared page), **My library → Shared**, a shared song (Play, open read only, **Add to my library**). The counts beside **Requests** and **Review** |
| 14.4 Documentation | `requests.md` (new); the other pages of section 9 |

Checks (section 7): backend 1,132 tests on the CPU, only the 3 known CPU failures; the 13 new tests
pass; `check:requests` (new, 40 checks) and the browser checks of the pages it touches pass; lint,
build and `check-links.py` pass; `make db-check` reports no problem.

# 2. The decision asked at the start

**A fourth kind of request, for a playlist.** The app context promotes "a given private song or a
given private playlist" to the Public Library; the plan's three kinds have no playlist, so no public
playlist could ever be made. Asked before any code, because it changes the allowed kinds of the
`requests` table. **Answer (2026-10-16): add it** (the recommendation). A playlist keeps only its
songs that have a public version (pulled from the Public Library, or published by the user from
that project); the dialog names the ones left out.

Two other points were read from the app context rather than asked, because it answers them:

- **What is accepted is written at once**, even when another item asks for changes: "One can accept
  a given song or a given artist into the music library, but not accept the piano sheet version".
- **The master user may change a name on accepting**: "the master user will revisit what this will
  be (this new version name) and will either accept it or change it".

# 3. The design

## 3.1 Where the copy of a request lives

The plan copies the project when a request is sent. The master user must read that copy, but has no
right over a user's private projects (section 9.3, Phase 4). So the copy has a **layer of its own**,
`request`, in `.database/requests/<projectId>/`, owned by the author: the author and the master user
read it, nobody writes it (`auth/rights.py`). Every route keyed by a part (the sheet, the audio,
Play mode) works on it unchanged.

Rejected: the copy in the `public` layer with a special rule (every user could read it by its id, and
"public" would mean two things); the copy in the author's vault (the master user cannot read it).

The copies are **kept with the request**, as the record of what was reviewed: no audio bytes are
copied (P-3), so a copy is its notes and sheet only. A copy replaced by **Change and send again** is
deleted.

## 3.2 Revision `0004`, and the real database

Revision `0004` adds two allowed values and nothing else: `projects.layer = 'request'` and
`requests.kind = 'playlist'` (both tables copied by batch mode, like `0002`). It was checked on a
temporary database first: the models and the migration agree, and it goes down to `0003` and up
again.

`make db-backup` came first (`/mnt/ssd2/aimpromptu/.database-20261016-174602.tar.zst`, 1.27 GB). The
backend did not migrate when the file appeared, because `database.HEAD_REVISION` still said `0003`
(a database at that revision is opened without Alembic). Once it said `0004`, the reload moved the
real database. Checked read only afterwards: revision `0004`, the same 45 projects, 46 parts, 49
audio references and 32 library versions, `foreign_key_check` empty, `integrity_check` ok.

## 3.3 Items, references and the transaction (`library/requests.py`)

A request is made of items: `newArtist`, `newSong`, `metadata`, `project`, `versionPointer`,
`playlist`. A new artist or song carries a `ref`; a song names its artists by `{publicId}` or
`{ref}`, a project its song the same way. So nothing private ever becomes a public id, as the app
context asks.

**Sending** (`create`) checks in one read what a review would refuse, then copies the project, then
writes the request; if the write fails the copy is deleted.

**Deciding** (`decide`) takes a decision for every waiting item and only those. It checks the
dependencies (an accepted item whose `ref` points at an item not accepted is refused, with "Accept its
new artist first, or ask for a change"), copies each accepted project into `public/`
(`public.copy_to_public`), and then writes every row in **one session**: new artists and songs in
that order, metadata, the version pointers (`public.point_version`), the playlist, the decisions and
the status. If the rows fail, the public copies are deleted. Replaced public projects are deleted
after the commit, when nothing uses them.

`library/public.place_version` (Phase 13) was split into those two steps, and still exists for the
tests and the fixture.

**A user version replaced** by a better one of the same name keeps its likes and its place in the
public playlists: they move to the new project. A fixed version points at the **same** project as the
user version it comes from (a pointer, as the app context says), so it does not move.

**Links back**: the author's own song (and the artists named with a `privateId`) get `public_id` on
acceptance, so the next **Publish** starts on the public song and **Save to library** files under it.

## 3.4 Changes asked, and sent again

When an item asks for changes, the request is `changesAsked` and the author's **Requests** shows a
number. **Change and send again** opens the dialog that sent it, filled from `proposal`: the backend
rebuilds the proposal from the items, naming the accepted ones by the public rows they made (an
accepted new artist comes back as a public artist). Sending replaces every item not accepted. This
keeps one path for sending and sending again.

## 3.5 Sharing (`library/shares.py`)

The rights check already let a user read a library shared with them (Phase 4). This phase adds the
lists and the copy: **Add to my library** copies the chosen versions under the reader's own song (by
its public song, or title and first artist, or a new one), named "<version> (<owner>)", with
`origin.sharedVersion` so a version is not added twice.

The project page needed one change: it treated any library project as the reader's own (**Edit**,
back to the owner's song). `GET /projects/{id}` now says `mine`; a shared version shows **Play** only
and goes back to the shared song.

## 3.6 The pages

| Page | Notes |
|---|---|
| **Publish** (`PublishDialog`) | The public song searched from the song's own title (or the linked one); **Propose this song** opens `SongFieldsForm`: title, artists (each a public artist from the suggestions, or "A new artist"), year, genres (two at most), regions, tags. The version name in its simple form (`easy-left-hand`); "Replaces your “easy”" when it does |
| **Suggest a change** | A public song: the same form, filled as it is. An artist: a new name, names to add |
| **Requests**, **Review** | One `DataTable` page in two roles |
| A request (`RequestPage`) | The status in words, then each item; the decision controls under each waiting item; **Decision** at the end (a note and **Send decision**). Text items keep the width of a page of lists; an item with sheets takes the window |
| Side by side (`CompareSheets`) | Two `SheetPage`s in the role of a passage's **Current**, as on the passage page (Phase 9): read only, played from their own button, one stops the other |
| Shared, a shared song | `DataTable` and `ListRow`, as My library |

`/public/lists` gives the forms the 13 genres, the regions and the tag categories (the facets only
list values in use).

# 4. Tests

| File | Tests | What |
|---|---|---|
| `test_requests.py` (new) | 12 | Three users through `/auth`. A version sent: the publish info, a name refused, the same request twice refused, the copy in the layer `request` (read by the author and the master user, `404` for another user, `403` to every write), the request `404` for another user, Review and the counts, every item needing a decision, accepted (the creator, the public copy, the record kept). A better version of the same name replaces the own one and keeps its likes. A new song and artist: too many genres and a known artist refused; a song accepted without its artist refused; the artist and song accepted (with a title changed), the piano sheet refused with a comment; reviewed requests cannot be withdrawn or sent again. Changes asked and sent again: the proposal names the accepted artist publicly, the old copy deleted, the version name changed on accepting, the author's song linked. Withdraw. Metadata of a song (nothing changed refused, genres and a tag, the facets) and of an artist (a name of another artist refused, a new name and a name added, the credit keeps its name). A new song alone. A fixed version: only one's own, twice refused, the same project, the creator, **Default** on it, pulled by another user. A playlist: the song with no public version left out, published with a changed title. Sharing: read only, the master user not included, **Add to my library** once, sharing stopped. The simple form of a name. The fixture's removals |

`test_rights.py` already checked row 4 (a request); the new layer is checked in `test_requests.py`.

# 5. The browser check `check:requests`

`aitu-frontend/scripts/check-requests.mjs` (`npm run check:requests`) drives two windows: the master
user, and a **temporary user** it makes (`check-<time>`). Nothing of a real library changes: the
temporary user gets its version by **Add to my library** from the master user's library shared with
it, and what the check accepts into the Public Library (a user version and a fixed version of the
public "7 Years", a new song and a new artist) is removed at the end by new commands of
`library/public_fixture.py` (`remove-song`, `remove-artist`, `remove-user`). The check refuses to
run if "7 Years" already has a public version.

It walks: **Share my library**; **Shared**, the song, **Add to my library**, the version read only;
**Publish** with the public song chosen; the request page with side by side; **Propose a song** with
a new artist; **Review** (the count, oldest first); the artist accepted and a change asked on the
song; the user's count; **Change and send again**; accepted; the version request (the proposed sheet
drawn, **Play**), accepted; **Ask for a fixed version**, accepted; a change withdrawn; the rights;
390 px and dark. **35 checks passed** in the first layout, no console error and no failed request; nothing left behind
(the user, the public rows, the share). Run seven times in all; the last two into
[`screenshots/phase-14/`](screenshots/phase-14/). One run of the seven failed at "the proposal plays":
Play answers once the browser has enough of the 4-minute recording, and on the busy machine that
took more than the 15 s the script waited (the screenshot showed the player still at 0). The step
now waits up to 60 s; the two runs after passed.

# 6. Speed

Nothing of the sheet or the transcription changed. A decision with a piano sheet copies one project
(its notes and sheet; no audio): under a second in the check, including the reload of the page.
The two sheets of side by side load like a passage page's two sheets (Phase 9).

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held the GPU) | 1,132 tests: the 3 known CPU failures (`test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU); every other test passed. Phase 13: 1,120 |
| `test_requests.py` (new) | 13 passed (12, and the conversation's after section 11), with `test_public`, `test_library`, `test_rights`, `test_database`, `test_passages`, `test_paste` after the change of section 11 |
| `black`, `flake8`, `mypy` on the new and changed backend modules | clean |
| The migration against the models; down to `0003` and up | no difference |
| `tsc -b`, `npm run lint`, `npm run build` | clean |
| `check:requests` (new) | 35 checks passed in the first layout; **40** in the layout of section 11, twice, into [`screenshots/phase-14/`](screenshots/phase-14/); nothing left behind |
| `check:library`, `check:public`, `check:play`, `check:projects`, `check:compose` (the library song and playlist pages, the public pages, the project page and Play mode changed) | 27, 38, 32, 26, 24 checks passed, run one at a time |
| `make db-check` on the real `.database/` | no problem (45 projects, as before the checks), after the migration and after every check |
| `scripts/docs/check-links.py` | passes |
| Checks that transcribe (`check:passage`, `check:flow` live, `time:flow`) | not run: the GPU was held, and nothing of the transcription changed |

# 8. The 13 checks of the 09 guidelines

Run on the new pages and dialogs, with the screenshots of [`screenshots/phase-14/`](screenshots/phase-14/).

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Send your work to the Public Library, and let the master user decide each part of it |
| 2 | Every sentence a label, control or fact | Only the empty states, the left-out songs of a playlist, and the confirmation of **Withdraw** |
| 3 | Words above the first content | A request: its title, then one line (status in words, kind, who, when) |
| 4 | Very wide | The conversation at most 1,180 px with its items column; the Sheet tab takes the window (shot 11); the tables are sized by their content (shot 07) |
| 5 | Narrow (390 px, shots 16, 17) | 0 px of sideways scroll; the items column above the timeline; a stretch's sheet wraps its lines |
| 6 | Longest, shortest, none | Long titles cut (full on hover); "Nothing yet: this is a new version" on the empty side; "Nobody shares a library with you yet"; "Nothing to review"; a project no longer kept says so |
| 7 | Buttons say what happens | "Publish", "Send request", "Send again", "Send decision", "Withdraw request", "Change and send again", "Accept", "Ask for a change", "Refuse", "Propose this song", "Add an artist" |
| 8 | Helper lines | "From the Public Library" / "A new artist" under an artist; "One or two" under Genres; "Replaces your “easy”…"; the name rule only when a name breaks it |
| 9 | Loading, empty, partial, error | Skeletons; the backend's own words for a refusal ("Accept its new artist first, or ask for a change"); **Send decision** disabled until every item has a decision, with a tooltip saying so |
| 10 | Tab through it | Decisions are toggle buttons; switches have names ("Share with anna"); every icon button has a tooltip |
| 11 | Internal names | None of `item`, `payload`, `ref`, `userVersion`, `scope`: "Version", "Metadata", "Fixed version", "Playlist", "Piano sheet", "New artist" |
| 12 | First-time user | "Publish", "Requests", "Review", "Shared", "Share my library" |
| 13 | Anti-patterns | No cards, no badges: the decision is a word beside the item's title; colour stays out |

| Shot | Page |
|---|---|
| 01 | Share my library |
| 02, 03 | Shared; the shared song added |
| 04 | **Publish** |
| 05 | The request sent: its Conversation |
| 06 | **Propose a song** |
| 07, 08 | Review; **Finish your review** |
| 09, 10 | My requests with changes asked; **Change and send again** |
| 11 | The Sheet tab: **Comment on this stretch** |
| 12 | The Conversation: the request as sent, the comment on a stretch with the stretch drawn and a reply, a comment |
| 13 | **Ask for a fixed version** |
| 14 | The public song with Hard and Other versions by the user |
| 15 | A request withdrawn |
| 16, 17, 18 | 390 px (a request, Review); dark |

# 9. Open points

- **A sheet on the request page draws the sheet's passage header** ("negra = 176 ms · ≈342 BPM") and
  its scrub bar, as every Sheet step and the passage page do since Phases 2 and 9; the read-only
  sheet of the Sheet tab shows its title line ("Untitled" when the sheet has none). Not changed here.
- **The full backend run** (1,132) was before section 11; after it, the request tests and their
  neighbours were run (all pass), not the whole suite again.
- **A merge of public artists or songs by request** is not built (section 16.1 does not name it), so
  Phase 12's open point (a merge must keep both import keys) stays open.
- **New regions by request** (`spain`, `catalan`) wait for Q-5: a request chooses among the regions
  that exist.
- **The master user cannot move Default** away from Hard; nothing in section 16 asks for it.
- **A user is never deleted** in the app (only disabled); the check removes its temporary user with
  `public_fixture remove-user`, which is a host command, not a page.

# 10. Learnings for later phases

- **The user reads a review page as a pull request**: a timeline of comments and events, the
  changes in a tab of their own, comments anchored to a stretch. Two columns with one often empty
  waste the page (section 11).

- **`database.HEAD_REVISION` decides whether the backend migrates**: a new revision file is not
  enough, the constant must name it. Write both together, after `make db-backup`.
- **A layer is the simplest rights rule**: the copy a request sends needed "author and master user
  read, nobody writes", and a layer of its own gave that to every existing route at once.
- **A controlled switch flips after the backend answers**: a browser script clicks it and waits for
  the state, rather than `check()`.
- **Play waits for the recording**: a script that presses Play must allow for a slow start on a
  busy machine (60 s here), or it fails while the page is right.
- **Escape after choosing in a multiple Autocomplete closes the dialog**, because the list already
  closed on the choice: a script should not press it.

# 11. The request page laid out like a pull request (asked 2026-10-18)

**What the user saw.** The first layout put, under each item, the version now and the proposal in
two columns, and the notes as a plain list at the end. For a new version the left column was empty,
so half the page was white, and the notes did not read like a conversation.

**What the user asked.** The page should read like a pull request on GitHub: a **Conversation** tab
with the timeline, the comments and the decisions, and a tab with the full sheet. The reviewer
should be able to mark a stretch of the sheet and comment on it, and the conversation should show
that stretch with the comment, as GitHub shows the lines a comment is about.

**What was built.**

| Part | How |
|---|---|
| Conversation (`/requests/:id`) | `Conversation.tsx`: one line down the left; the first box is the request as sent (the note, then what each item proposes, `ItemBody`); comment boxes with the author, "Author" or "Reviewer", the time; review boxes with each item's decision and words; "sent it again" and "withdrew it" as events; **Comment** at the end for the author and the master user. Beside it, the items with their decisions, the kind and the dates |
| A comment on a stretch | On the Sheet tab, marking a stretch offers **Comment on this stretch** (the read-only sheet's `stretchAction`, Phase 10). The backend keeps a project of just that stretch (`requests._excerpt`: `paste.read_passage` then `paste.paste` into a project of kind `passage` in the layer `request`, owned by the author; no audio bytes), so the Conversation draws it as it was, with its own Play, even after the request is sent again ("Outdated" then). At most two minutes |
| Replies | One level, as on a pull request: a reply to a reply joins the thread |
| Sheet (`/requests/:id/sheet`) | `RequestSheet.tsx`: the whole proposed sheet at the page's width, read only; **Proposed** and **Now** switch when the Public Library has a version it would replace; one part at a time. A request with no piano sheet has **Changes** there |
| Review | **Review** in the header opens **Finish your review** (`ReviewDialog.tsx`), the decisions as before |
| Revision `0005` | `request_comments.kind` (`comment`, `review`, `sentAgain`, `withdrawn`), `item_id`, `parent_id`, `details` (JSON). Added only; the real database moved after `make db-backup` (`/mnt/ssd2/aimpromptu/.database-20261018-111419.tar.zst`), checked read only afterwards (revision `0005`, the one comment of anna's request kept as a `comment`, integrity ok). A request decided before `0005` has no review row: the conversation draws one from its items' decisions |
| Route | `POST /requests/{id}/comments` (`endpoints.md` §7.4) |
| Removed | `CompareSheets.tsx` (the two columns) |

**Choices made without asking**, each the pull request's own way: a comment on a stretch is posted
at once (GitHub's "Add single comment"; a batch of pending comments would add a state to explain);
the author and the master user both comment and reply at any time; one level of replies.

**Checks.** `test_requests.py` has one more test (the conversation: a comment on a stretch and its
project, its rights, replies, refusals, the events), and two tests read the events. `check:requests`
now walks the Conversation and Sheet tabs, a comment on a marked stretch, its drawing and Play, a
reply and a comment by the author, and **Finish your review**: 40 checks, twice.
