# Requests and the review

The Public Library changes only by **requests** that the master user reviews, as the app context
says: "every private library is a kind of feature branch, and in order to publish something into
the public library, we need to open a request, so the master user needs to review it". This page
says what a request can ask, how it is sent, how the review decides it, and what an accepted
request writes. It also covers a **shared library**, the other way a user's work reaches another
user. Built in implementation 02, Phase 14.

## 1. The four kinds

The app context keeps the requests separate: one for the metadata of a public song, one for a user
version, one for a fixed version. The user added a fourth on 2026-10-16: a songs playlist.

| Kind | What it asks | Where it is sent from |
|---|---|---|
| **Version** (`userVersion`) | A version of My library becomes the user's version of a public song, in **Other versions** (the app context's `user_versions/<user>/<version name>/`). A version of the same name replaces the user's own | **Publish** in a version's `⋯` (My library → a song) |
| **Metadata** | A change of a public song (title, year, artists, genres, regions, tags) or of a public artist (a new name, more names); or a new song | **Suggest a change** on a public song or artist; **Propose a song** on Public songs |
| **Fixed version** (`fixedVersion`) | The user's accepted version becomes Hard, Medium, Easy, or a new name of that song only | **Ask for a fixed version** on the user's own version, on the public song |
| **Playlist** | A songs playlist of My library becomes a public playlist | **Publish** in a playlist's `⋯` |

A request is made of **items**, one per proposed change: a new artist, a new song, a change of
metadata, a piano sheet (the project), a version pointer, a playlist. Each item gets its own
decision, which is what lets the master user accept part of a request.

**No private id reaches the Public Library** (app context): a song or an artist that the Public
Library does not have is proposed by its name, as its own item, and gets a public id only when it is
accepted. A song proposed with a new artist names it by a reference inside the request.

## 2. Sending a request

**Publish** asks three things, in one dialog (plan section 16.2):

1. **Public song**: the Public Library's songs, searched from the song's own title. A song that
   already stands for a public song (pulled from it, or saved on it) starts on it. When it is not
   there, **Propose this song** opens its fields; each artist is a public artist chosen from the
   suggestions, or a new one ("A new artist" under the field).
2. **Version name**: the simple form of the version's own name: lowercase letters, digits and
   hyphens, at most 24 characters (plan section 15.2). "Easy (left hand)" is offered as
   `easy-left-hand`. A name the user already has on that song says it replaces it.
3. **Send request**, with an optional note for the reviewer.

**The project is copied when the request is sent**, so later edits in the user's library do not
change what is reviewed. The copy is a project of its own layer, `request`
(`.database/requests/<projectId>/`): its author and the master user read it, nobody writes it, and
it is kept with the request as the record of the review. No audio bytes are copied (P-3).

A request is refused at once when it would break a rule a review checks: a version without its
piano sheet, a version name that is not a simple name, more than two genres, a new artist or song
that the Public Library already has (choose it instead), a metadata change that changes nothing,
the same version already asked in a request that waits, a fixed version of someone else's version.

A **playlist** keeps only its songs that have a public version: one pulled from the Public Library,
or one the user published from that project. The dialog names the songs left out.

## 3. The review

**Admin → Review** lists the open requests, oldest first, with their kind and who sent them; **All**
shows every request. The number beside **Review** in the sidebar is the open requests.

A request's page is laid out like a pull request (the user, 2026-10-18): the title, the status as
a pill, one line saying who asks for what, and two tabs, each with its own address.

**Conversation** (`/requests/:id`) is the request's timeline, on one line down the left:

- the first box is the request as it was sent: the author's note, then what each item proposes;
- each **comment** is a box with its author, "Author" or "Reviewer", and its time; the author and
  the master user both write, at any time, in the box at the end;
- a comment **on a stretch of the sheet** draws that stretch above its words, as it was when the
  comment was written, with its own Play. It is a project of just that stretch (a copy of its
  notes, marks and audio ranges, no audio bytes), kept with the request. Once the request is sent
  again with another sheet, the comment says "Outdated";
- each comment takes **replies** (one level, as on a pull request): **Reply…** under it;
- the events: a **review** (a box with each item's decision and its words, and the master user's
  note: "asked for changes", "accepted", "refused", "reviewed"), "sent it again" (with the
  author's note), "withdrew it".

Beside it, a narrow column lists the items with their decisions, the kind and the dates.

**Sheet** (`/requests/:id/sheet`) is the whole proposed sheet at the page's width, read only, with
its player. When the Public Library has a version it would replace (the user's own version of that
name, or the fixed version of that name), **Proposed** and **Now** switch between the two. A
project of several parts shows one part at a time. **Mark a stretch** of the proposed sheet, then
**Comment on this stretch**: the comment goes to the Conversation. A request with no piano sheet
(metadata, a playlist) has **Changes** there instead:

| Item | What it shows |
|---|---|
| New artist | Its name |
| New song | Its fields; a new artist marked "(new)" |
| Metadata of a song | Each field now and proposed, the changed ones in bold |
| Metadata of an artist | The name now and proposed; the names to add |
| Playlist | Its songs and versions; the songs left out |

The master user's **Review** (on a request waiting for review) opens **Finish your review**, as a
pull request's "Review changes": each item waiting gets **Accept**, **Ask for a change** (with what
to change) or **Refuse** (with a reason, if wanted). On **Accept** the master user can change the
name ("will either accept it or change it", app context): an artist's name, a song's title, a
version name, a playlist's title. **Send decision** needs a decision for every item waiting, and
writes what is accepted; the review then appears in the Conversation.

The first layout (Phase 14, 2026-10-16) put the version now and the proposal side by side in two
columns under each item. The user found the empty column and the plain list of notes wasteful, and
asked for the pull request's layout instead (2026-10-18).

**An item cannot be accepted without what it needs**: a new song without its new artist, a piano
sheet without its new song. The backend refuses the decision and says which.

## 4. What an accepted request writes

Everything accepted in one decision is written **in one transaction** (plan section 16.3):

- a new artist: a public artist with its one name; a new song: a public song with its artists,
  year, genres, regions (`worldwide` when none), tags, popularity 0 until a chart has it;
- a metadata change: the song's or artist's fields as proposed; an artist keeps the name a song is
  credited with;
- a piano sheet: the copy that was reviewed is copied again into `public/`, and becomes the
  author's user version of that name; the author's name is its creator. A version that replaces
  the author's own keeps its likes and its place in public playlists;
- a fixed version: the pointer (Hard, Medium, Easy or the new name) points at the author's user
  version, the same project; the author is its creator;
- a playlist: a public playlist, credited to the author;
- the author's own song and artists named in the request now stand for the public ones
  (`public_id`), so the next **Publish** starts on the public song.

The project copy is made first; when the transaction fails, the copy is deleted again.

## 5. Statuses

| Status | When |
|---|---|
| Waiting for review (`open`) | Sent, or sent again |
| Changes asked | An item asks for a change. What was accepted in that decision is already written. The author's **Requests** shows a number until they act |
| Accepted, Refused, Partly accepted | Every item has its final decision |
| Withdrawn | The author took it back before it was reviewed. What was accepted stays |

**Change and send again** opens the dialog that sent the request, filled as it was: the accepted
items stay, and are named by the public rows they made (an accepted artist is now "From the Public
Library"); the other items are replaced by the new proposal. The request waits for review again.

## 6. A shared library

The owner shares their **whole** Private Library, read only, with the users they choose: **Share my
library** in the user menu, or on **My library → Shared** (plan section 15.4). The other user sees
it under **Shared**: the owner's songs, each with its versions. They play a version, open its sheet
read only (and copy a passage from it, as from any library), and **Add to my library** copies the
chosen versions into their own library, named "<version> (<owner>)", under their own song for it.
When sharing stops, the shared songs disappear from them; what they added stays theirs. The master
user has no extra right: a library nobody shared with them stays private to them too
([08-security.md](../08-security.md)).

## 7. Not built

| Thing | Why |
|---|---|
| A merge of two public artists or songs by request | Section 16.1 does not name it; a merge must keep both keys of the import (Phase 12's open point) |
| A new region by request (`spain`, `catalan`) | Q-5 is still open: a region can be chosen among those that exist |
| Deleting a public song or artist by request | Not asked; the next import would make it again (Phase 12) |
| The master user changing **Default** | The pointer stays on Hard; nothing in section 16 asks for it |

## Where to look deeper

- The routes: [`endpoints.md`](../../documentation/services/backend/endpoints.md) §7.4 and §7.5
- The tables and the `requests/` folder: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) sections 1 and 6
- Who reads and writes what: [08-security.md](../08-security.md)
- The Public Library a request writes into: [ontology.md](ontology.md)
- The plan: [02-plan.md](../implementations/02-private-web-app/02-plan.md) sections 15.4 and 16
- The code: `aitu-backend/src/aitu_backend/library/requests.py`, `library/shares.py`,
  `api/requests.py`, `api/shares.py`; `aitu-frontend/src/pages/requests/`,
  `pages/library/SharedPage.tsx`, `SharedSongPage.tsx`
