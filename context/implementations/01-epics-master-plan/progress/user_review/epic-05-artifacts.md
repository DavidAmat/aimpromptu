# 6 — Artifacts and versioning (Epic 5)

**What this epic did:** saving your work. Versions of a piece as you iterate, and "promoting" a
version into a library you actually play from.

No UI yet — the save and promote buttons belong to Epic 7. But the storage underneath is real, and
**the files it writes are meant to be readable by you in six months**, so it is worth looking at
them now while they are easy to change.

About 10 minutes. Backend running (`make serve`).

---

## 6.1 — Save two versions of a piece

First get a matrix to save. The quickest is the text notation endpoint:

```bash
cd aitu-backend

M=$(curl -s -X POST 127.0.0.1:8765/sequence -H 'Content-Type: application/json' \
  -d '{"sequence":["*Do-4","Do-4","*Re-4","*Mi-4"],"tempoBpm":60,"timeStepSeconds":0.25}')

uv run python -c "
import json, sys
score = json.loads('''$M''')
env = {'tempoBpm': 60, 'timeStepSeconds': 0.25, 'granularity': 'semicorchea',
       'matrixProcessingStep': 'clean', 'sparse': True, 'matrix': score['matrix']}
open('/tmp/env.json','w').write(json.dumps(env))
print('matrix ready')
"
```

Now save it twice, as two versions:

```bash
curl -s -X POST 127.0.0.1:8765/library/playground -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json; env=json.load(open('/tmp/env.json'))
print(json.dumps({'artistName':'Avicii','trackName':'Levels','comment':'first transcription','matrix':env}))")" \
  | python3 -m json.tool | grep folder

curl -s -X POST 127.0.0.1:8765/library/playground -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json; env=json.load(open('/tmp/env.json'))
print(json.dumps({'artistName':'Avicii','trackName':'Levels','comment':'cleaned the intro','parentVersion':'v1_gsc','matrix':env}))")" \
  | python3 -m json.tool | grep folder
```

Expected: `"folder": "v1_gsc"` then `"folder": "v2_gsc"`.

> **Reading a folder name.** `v2_gsc` = version 2, at semicorchea resolution. The version number
> means *the music changed*. Saving the same take at a different resolution keeps the same
> number — you would get `v1_gsc` and `v1_gn` side by side, two views of one performance.
>
> The second save passed `parentVersion` — it records that it came from v1. That is not an undo
> history; it is a pointer. "Back to the original" later means *loading v1*, which still exists
> untouched.

---

## 6.2 — Look at what got written ⭐

**This is the part worth your attention.**

```bash
find data/playground -type f | sort
cat data/playground/avicii/levels/metadata_track.json
```

You should see:

```text
data/playground/avicii/levels/metadata_track.json
data/playground/avicii/levels/v1_gsc/metadata.json
data/playground/avicii/levels/v1_gsc/piano_matrix_v1_gsc.npz
data/playground/avicii/levels/v2_gsc/metadata.json
data/playground/avicii/levels/v2_gsc/piano_matrix_v2_gsc.npz
```

**Read `metadata_track.json` as a person, not a developer.** It is the log of what you did to this
piece. Does it tell you what changed and why? Does the comment field earn its place?

Then read one version's `metadata.json`. It holds everything needed to re-open that exact state:
tempo, resolution, which step of the pipeline it is, which version it came from, which audio it
came from, and an (empty for now) space for lyrics and fingerings.

> **If either file is missing something you would want, say so now.** Changing the shape later
> means migrating files you care about.

---

## 6.3 — Promote to the library

Promoting means "this version is good — I want to play from it."

```bash
curl -s 127.0.0.1:8765/library/promotion-suggestion/avicii/levels | python3 -m json.tool
```

Expected: `{"suggestedName": "Levels - Avicii", "currentPromotions": []}`

> That suggestion is what the dialog will pre-fill when Epic 7 adds the button. **You name
> promotions, you never pick version codes** — "Levels (Chill) - Avicii" is something you can
> choose from a list a year later; `v3_gn` is not.

```bash
curl -s -X POST 127.0.0.1:8765/library/promote -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels","versionFolder":"v1_gsc","promotionName":"Levels (Chill) - Avicii"}' > /dev/null

curl -s -X POST 127.0.0.1:8765/library/promote -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels","versionFolder":"v2_gsc","promotionName":"Levels (Fast) - Avicii"}' \
  | python3 -c "
import json,sys
t=json.load(sys.stdin)
print('live now :', [p['promotionName'] for p in t['promotions'] if p['active']])
print('in history:', [p['promotionName'] for p in t['promotions']])
print('roll back to:', t['rollbackTo'])
"
```

Expected: live `['Levels (Fast) - Avicii']`, history has **both**, roll back to `Levels (Chill) - Avicii`.

> **Nothing was deleted.** The second promotion replaced the first as the one you play, but the
> first is still there, marked inactive.

---

## 6.4 — Roll back

```bash
curl -s -X POST 127.0.0.1:8765/library/rollback -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels"}' \
  | python3 -c "
import json,sys
t=json.load(sys.stdin)
print('live now:', [p['promotionName'] for p in t['promotions'] if p['active']])
print('total kept:', len(t['promotions']))
"
```

Expected: live is `Levels (Chill)` again, total still `2`.

Run the same command a second time → you are back on `Levels (Fast)`. **Rollback is a pointer
moving, so it goes both ways.**

### Two live at once

If you want the same piece in two arrangements — a slow practice version and a full-speed one —
promote with `"asAdditional": true` and both stay live. Try it:

```bash
curl -s -X POST 127.0.0.1:8765/library/promote -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels","versionFolder":"v2_gsc","promotionName":"Levels (Fast) - Avicii","asAdditional":true}' \
  | python3 -c "
import json,sys
print([p['promotionName'] for p in json.load(sys.stdin)['promotions'] if p['active']])
"
```

Expected: **both** names.

---

## 6.5 — It survives a restart

Stop the backend (Ctrl-C), start it again, then:

```bash
curl -s 127.0.0.1:8765/library/tracks | python3 -m json.tool | head -30
cat data/library/tracks/avicii/levels/metadata_library_track.json
```

Everything is still there.

> **Why the library keeps its own copy.** Promoting *copies* the matrix file into the library and
> embeds a snapshot of the version's details. If you later clean out the playground, a piece you
> play from does not break.

Again: **read that file as a person.** It is the record of what you decided was good, and when.

---

## 6.6 — Clean up

```bash
rm -rf data/playground/avicii data/library/tracks/avicii
```

---

## What "working" looks like

- Two saves produce `v1_gsc` and `v2_gsc`, with the second recording the first as its parent.
- The folder tree matches, and both metadata files read like something a human wrote.
- Promotion suggests `Levels - Avicii` and accepts a name you choose.
- Re-promoting replaces but keeps history; rollback goes both ways; `asAdditional` keeps two live.
- Everything survives a restart.

## If it goes wrong

| Symptom | Likely cause |
|---|---|
| `409` on the second save | You passed the same `version` twice — leave it out for a new one |
| `404` on promote | The slugs are lowercase and hyphenated: `avicii`, `levels` |
| `409` on rollback | Only one promotion exists, so there is nothing to go back to |
| Metadata files hard to read | **Tell me** — that is the point of this guide |

That is every epic built so far. Back to the [index](README.md).
