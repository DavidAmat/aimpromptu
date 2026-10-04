# 6 — Piano Roll and Notes Falling (Epic 8)

**What this epic did:** made the matrix playable over a full 88-key piano in two views.

About 20 minutes. Reuse the slow `Do Re Mi Fa Sol` recording from guide 3.

---

## 6.1 — Piano Roll

Open **Playground → Piano Roll**.

You should see the whole piano rotated vertically at the left and five rectangles forming a
staircase from C4 to G4. Dashed vertical guides are numbered by frame. If the piece has real source
audio, a faint waveform sits behind the rectangles on exactly the same time axis.

Click **Play** with **Transcribed piano** selected:

- the timeline follows playback without a horizontal scrollbar fight;
- a rectangle becomes light blue as it sounds;
- the matching piano key becomes opaque blue for the note's whole duration;
- frame and timestamp advance together.

While a white key is blue, inspect its neighbouring black keys: they must remain fully visible
above the white highlight. The intended order is white base → pressed white → normal black →
pressed black.

Pause, seek to `00:02`, change speed to 0.5×, and resume. Change BPM or Resolution; the view should
reload from the raw matrix without re-transcribing.

Click **Open this frame in Matrix**. Matrix should open with that frame visible.

---

## 6.2 — Original/transcribed A/B ⭐

Select a short range around the scale with **From (s)** and **To (s)**.

1. Select **Original audio**, Restart, Play.
2. Watch the key highlights while listening to your recording.
3. Select **Transcribed piano**, Restart, Play.

The note landings should occur at the same moments. Differences are transcription-quality
feedback, not a player timing difference. Imported JSON has no audio, so Original audio is
correctly disabled for that source.

---

## 6.3 — Notes Falling

Open **Notes Falling**. Rectangles approach the horizontal piano from above. The caption says how
many frames/seconds fit in the future window; only those notes are mounted.

Click Play. Each rectangle tip must reach the blue landing line exactly when the note sounds. The
key turns blue, the rectangle becomes light blue, and the part crossing below the line disappears
as if the piano swallowed it.

Every sounding key is the same blue, whether it has just been struck or is still ringing. A green
"struck" colour was tried on 2026-07-27 and removed.

### 6.3a — The note labels ⭐

Look at what is written inside the rectangles, especially in a busy passage.

- A long note carries its full Spanish name at full size: `Sol#-3`.
- A shorter one keeps the full name in **smaller** type before giving anything up.
- A short one drops the octave and switches to English: `G#3`, then `G#`.
- A very short one carries **nothing** — deliberately.
- Every label is centred, and **no label may cross its own border.** Text spilling out over the
  neighbouring notes is the bug this step exists to catch; if you see it, note the note name and
  the resolution you were on.

Rectangle outlines should be a firm black, thick enough to separate two adjacent notes at a glance.

---

## 6.4 — Drag a correction

In either view, drag one rectangle to another key and/or time.

- Dashed key landing guides with Spanish names appear while dragging.
- The dropped rectangle gets an orange outline.
- **Save (1)** appears, but Matrix is still unchanged.
- Cancel restores it immediately.

Repeat the drag and Save. Open Matrix and play it: the note should now be at the new key/frame with
its original duration.

---

## What “working” looks like

- Both orientations show the same 88-key piano and correct blue pressed overlays; normal black
  keys always remain above pressed white keys.
- Roll rectangles align with piano lanes and frame guides; the watermark aligns with time.
- Original and synthesized sources share transport, range, speed and highlighting.
- Falling notes land exactly on sound and are clipped below the piano line.
- Drag edits stage, cancel and save; saved changes appear in Matrix.

## If it goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| Original audio disabled | The source is imported JSON | Load a real transcribed recording |
| No piano sound | Browser audio needs a user gesture | Click Play and check system volume |
| Rectangle/key mismatch | Coordinate-table bug | Note the visible key name and report it |
| Falling notes jump | BPM/resolution changed mid-play | Restart; controls rebuild from selection start |
| Save rejects a drag | The move collides with an illegal sustain or the edge | Move it earlier or to an empty lane |

Back to [5 — Matrix](epic-07-matrix-tab.md) · [guide index](README.md)
