# 1 — Skeleton (Epic 1)

**What this epic did:** built the empty rooms of the house. Every page exists and every URL works,
but most pages just say which epic will fill them. The point is that the *shape* is right.

About 5 minutes. Both services running (see [setup](00-setup.md)).

---

## 1.1 — Walk every page

Open **http://localhost:5173**. You land on **Playground → Upload / Input**.

Click through the top bar and the Playground tabs, in this order:

| Click | URL you should land on | What you should see |
|---|---|---|
| *(start)* | `/playground/input` | The input tab (already real — Epics 3 and 6) |
| **Matrix** | `/playground/matrix` | Blue box: "Coming in Epic 7 (Matrix tab)" |
| **Piano Roll** | `/playground/piano-roll` | Blue box naming Epic 8 |
| **Notes Falling** | `/playground/notes-falling` | Blue box naming Epic 8, Story 8.4 |
| **Music Notation** | `/playground/notation` | Blue box naming Epic 9 |
| **YouTube to Audio** (top) | `/youtube` | A real page — URL field, Download button |
| **Piano Library** (top) | `/library` | Two blue boxes naming Epic 10 |

**What you are checking:** the tab you clicked is the one that highlights, and the URL in the
address bar matches. Every unbuilt page tells you *which epic owns it* rather than showing an
error or a blank.

---

## 1.2 — The working piece is remembered

This is the one piece of real behaviour in this epic, and it matters for everything later.

Look just under the Playground tabs. There is a grey strip:

> Working piece: **none loaded** · `60 BPM` · `semicorchea` · `clean`

Now:

1. Click **Matrix**, then **Piano Roll**, then back to **Upload / Input**.
   → The strip must still say the same thing. It does not reset when you change tabs.
2. Press **⌘R** to reload the whole page.
   → It must *still* say the same thing.

> **What happens behind the scenes.** The "working piece" lives in one place shared by all five
> Playground tabs, and a copy is kept in the browser's session storage. That is why switching tabs
> or reloading does not lose which piece you are working on. Once you load an audio in guide 2,
> those pills will show its name, and the tabs will all be looking at the same piece.

---

## 1.3 — Two small things

**Not-found page.** Type `http://localhost:5173/nonsense` in the address bar.
→ "Page not found" with a button back to the Playground. Not a blank screen, not a crash.

**API status chip.** Go to the backend terminal and press **Ctrl-C** to stop it. Reload the
frontend.
→ The chip top-right turns red: **API offline**. Restart with `make serve` and reload — green again.

---

## 1.4 — The API's own documentation

Open **http://127.0.0.1:8765/docs**.

Expand **matrix → GET /matrix/{audio_uuid}**, click **Try it out**, type anything as the uuid, and
**Execute**.

→ You get a `404` saying no audio with that uuid. Now expand **notation →
GET /notation/{artifact_id}** and do the same.

→ You get a `501` reading *"Not implemented yet — the VexFlow score format builder is delivered by
Epic 9 (Music notation)."*

> **Why this is deliberate.** Every endpoint the finished app will need already exists at its final
> URL. The frontend can be wired against real addresses now, and each unbuilt one tells you exactly
> which epic will fill it. Nothing has to be re-plumbed later.

---

## What "working" looks like

- Every one of the eight routes loads and highlights its own tab.
- Unbuilt pages name their epic.
- The working-piece strip survives tab switches **and** a page reload.
- The API chip reflects reality.

## If it goes wrong

| Symptom | Likely cause |
|---|---|
| A tab does not highlight | Route mismatch — note which one and tell me |
| Working piece resets on reload | Session storage blocked (private browsing?) |
| Everything unstyled / light background | The theme failed to load; check the browser console |
| `/docs` shows fewer than six groups | The backend did not fully start — check its terminal |

Next: [2 — Audio I/O](epic-03-audio-io.md)
