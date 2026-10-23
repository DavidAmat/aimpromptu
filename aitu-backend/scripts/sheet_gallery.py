"""The Phase 2 gallery of the new sheet: passages of My library as F1 text and as notes.

Implementation 03, Phase 2, task 7. Each case is a passage of a library song (about 4 seconds) written
by the algorithm of the new sheet (``propose_frames``), shown as its F1 frames text and drawn as notes,
with one sentence that says what to look at: figures, grace notes and alteraciones. Some cases also
draw a variant: figures from the raw length (no cap at the next onset), or rule 4 replaced by a
becuadro.

The engine of the new sheet is Phase 3, so the notes are drawn by Verovio from MEI: one measure per
passage (one per armadura), no meter, an invisible bar line, the gaps as invisible space, and every
note outside the armadura with its own sign (rule 1). Times are kept in proportion where the figures
allow it; the drawing only checks the names, figures, grace notes and beams.

    uv run --with verovio==6.3.0 python scripts/sheet_gallery.py --out DIR

On the host, load ``.env`` first, or the script opens an empty ``.database/``. The page is
``DIR/index.html`` (one file, the drawings inline).
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from aitu_backend.sheet.proposal import frames as algo
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.figures import NAMES
from aitu_backend.sheet.sheet.spelling import key_alter, sign
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription.pipeline import starting_hands

TICKS = 32  # per negra
SPAN = 100  # frames per passage (4 s)

#: (section, part, first frame, title, what to look at, variant)
CASES = [
    (
        "Figures",
        "bef90052",
        3500,
        "Pedaled notes: the figure stops at the next note of the hand",
        "Each note is as long as it sounds, but never longer than the time until the same hand plays again. "
        "Compare with the drawing below it, which takes the raw length: under the pedal the notes become "
        "negras and blancas although the hand plays again at once.",
        "raw",
    ),
    (
        "Figures",
        "4cb9cb38",
        1250,
        "A short chord keeps its own figure, and the rest of the time stays blank",
        "The left hand plays a short chord, a negra, then nothing for 2.4 seconds while the right hand plays. "
        "The chord stays a negra (it does not grow into a redonda to fill the time), and there is no silencio.",
        None,
    ),
    (
        "Figures",
        "1a16a836",
        177,
        "A run of even notes gets one figure",
        "Notes that follow each other at an even pace share one figure, even when their measured lengths "
        "differ a little (7 Years opening).",
        None,
    ),
    (
        "Grace notes",
        "c0edc9b0",
        500,
        "Very short notes just before a longer note become small grace notes",
        "A semicorchea or shorter, two figures or more shorter than the next note of its hand and sounding just "
        "before it, is drawn small (a slashed grace note, two unslashed when there are two).",
        None,
    ),
    (
        "Grace notes",
        "f285e4b7",
        4125,
        "More grace notes",
        "The same rule in another song. A longer run of fast notes stays written at full size.",
        None,
    ),
    (
        "Grace notes",
        "f4c4de9a",
        775,
        "An octave played a little unevenly",
        "The lower note of the octave sounds 80 ms before the upper one and is two figures shorter, so it is "
        "drawn as an acciaccatura of the upper note.",
        None,
    ),
    (
        "Alteraciones",
        "e578f3c0",
        300,
        "Rule 4 in Mi mayor: the key Fa is written Mi#",
        "Mi mayor has Fa# in the armadura. The white key Fa is written Mi# (a sign on a note that is not in "
        "the armadura) instead of Fa becuadro. This is the user's own example.",
        "becuadro",
    ),
    (
        "Alteraciones",
        "a1c30047",
        3125,
        "Rule 4 in La mayor: the key Do is written Si#",
        "La mayor has Do# in the armadura. The white key Do (here inside a Do mayor chord) is written Si#. "
        "The drawing below writes it Do becuadro instead.",
        "becuadro",
    ),
    (
        "Alteraciones",
        "56543911",
        2125,
        "Rule 4 in Sol mayor: the key Fa is written Mi#",
        "Sol mayor has Fa# in the armadura, so the white key Fa is written Mi#. With one sostenido in the "
        "armadura this happens in many pop songs (a Fa mayor chord in Sol mayor).",
        "becuadro",
    ),
    (
        "Alteraciones",
        "fb0b0989",
        None,
        "Rule 4 in Fa mayor: the key Si is written Dob",
        "Fa mayor has Sib in the armadura, so the white key Si is written Dob (the same rule with bemoles).",
        "becuadro",
    ),
    (
        "Alteraciones",
        "2ed0f379",
        3625,
        "A becuadro when the key has no other name with one sign",
        "Si mayor has five sostenidos. The white keys Sol, Re and La have no other name with one sign (it "
        "would be a double sostenido), so they are written with a becuadro, every time.",
        None,
    ),
    (
        "Alteraciones",
        "dff5097c",
        3625,
        "Do mayor: the black keys are Do#, Mib, Fa#, Sol#, Sib",
        "With no armadura, rule 5 gives no answer. The new sheet uses the names that classical scores use "
        "most (research rulebook): Do#, Mib, Fa#, Sol#, Sib.",
        None,
    ),
    (
        "Alteraciones",
        "56543911",
        3250,
        "Every altered note carries its sign, every time",
        "There are no compases, so a sign does not carry over: each Do# (or any note outside the armadura) is "
        "written with its sign each time it appears.",
        None,
    ),
    (
        "Alteraciones",
        "56543911",
        525,
        "A new armadura for a passage",
        "The algorithm changes the armadura when a passage would print many signs in the old one (here Sol "
        "mayor to Do mayor: the becuadro in the middle of the line cancels the Fa#). The LLM will make this "
        "choice in Phase 4.",
        None,
    ),
]


# ------------------------------------------------------------------ the passage


def passage(sheet: Sheet, a: int, b: int) -> Sheet:
    """The notes of columns [a, b), with the clefs and the armadura in force at ``a``."""
    at = frames.key_at(sheet)
    clefs = dict(sheet.clefs)
    for f, st, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if f <= a:
            clefs[st] = c
    inside = [replace(n) for n in sheet.notes if a <= n.frame < b]
    count: dict[int, set[int]] = defaultdict(set)
    for n in inside:
        if n.beam is not None:
            count[n.beam].add(n.frame)
    for n in inside:  # a group with one column left inside would be a beam of one note
        if n.beam is not None and len(count[n.beam]) < 2:
            n.beam = None
    return Sheet(
        notes=inside,
        clefs=clefs,
        clef_changes=[c for c in sheet.clef_changes if a < c[0] < b],
        key=at(a),
        key_changes=[k for k in sheet.key_changes if a < k[0] < b],
        quarter_ms=sheet.quarter_ms,
    ).sort()


def whole_groups(sheet: Sheet, a: int, b: int) -> tuple[int, int]:
    """Columns [a, b) widened so that no beam group is cut, and so that the grace notes of the first note are in."""
    groups: dict[int, list[int]] = defaultdict(list)
    for n in sheet.notes:
        if n.beam is not None:
            groups[n.beam].append(n.frame)
    while True:
        a0, b0 = a, b
        for frames_of in groups.values():
            if any(a <= f < b for f in frames_of):
                a, b = min(a, min(frames_of)), max(b, max(frames_of) + 1)
        before = [n for n in sheet.notes if n.frame < a]
        last = max((n.frame for n in before), default=None)
        if last is not None and all(n.grace for n in before if n.frame == last):
            a = last
        if (a, b) == (a0, b0):
            return a, b


def as_becuadro(sheet: Sheet) -> Sheet:
    """The same passage with rule 4 replaced: the white key keeps its natural name (a becuadro)."""
    at = frames.key_at(sheet)
    out = []
    for n in sheet.notes:
        k = at(n.frame)
        alt = {("E", 1): ("F", 0), ("B", 1): ("C", 0), ("C", -1): ("B", 0), ("F", -1): ("E", 0)}
        if (n.step, n.alter) in alt and key_alter(k, n.step) != n.alter:
            step, alter = alt[(n.step, n.alter)]
            octave = n.octave + (1 if n.step == "B" else -1 if n.step == "C" else 0)
            n = replace(n, step=step, alter=alter, octave=octave)
        out.append(n)
    return replace(sheet, notes=out)


# ------------------------------------------------------------------ MEI


def _space(ticks: int) -> list[str]:
    out = []
    for dur, size in ((1, 128), (2, 64), (4, 32), (8, 16), (16, 8), (32, 4), (64, 2), (128, 1)):
        while ticks >= size:
            out.append(f'<space dur="{dur}"/>')
            ticks -= size
    return out


_ACCID = {"#": "s", "b": "f", "n": "n"}
_ACCID_GES = {1: "s", -1: "f"}


def _note_xml(n: Note, key: int, nid: str | None = None) -> str:
    attrs = [f'pname="{n.step.lower()}"', f'oct="{n.octave - n.ottava}"']
    if n.ottava:
        attrs.append(f'oct.ges="{n.octave}"')
    s = sign(n.step, n.alter, key)
    if s:
        attrs.append(f'accid="{_ACCID[s]}"')
    elif n.alter:
        attrs.append(f'accid.ges="{_ACCID_GES[n.alter]}"')
    if nid:
        attrs.append(f'xml:id="{nid}"')
    return f"<note {' '.join(attrs)}/>"


def _element(ns: list[Note], key: int, nid: str) -> str:
    n0 = ns[0]
    grace = ""
    if n0.grace:
        grace = f' grace="{"acc" if n0.grace == "acc" else "unacc"}"'
    if len(ns) == 1:
        return _note_xml(n0, key, nid).replace("<note ", f'<note dur="{n0.figure}"{grace} ', 1)
    inner = "".join(_note_xml(n, key) for n in sorted(ns, key=lambda n: n.midi))
    return f'<chord xml:id="{nid}" dur="{n0.figure}"{grace}>{inner}</chord>'


_CLEF = {"G2": ("G", 2), "F4": ("F", 4)}


def to_mei(sheet: Sheet) -> str:
    """One passage as MEI: one measure per armadura, both hands, the gaps as invisible space."""
    q = sheet.quarter_ms
    at = frames.key_at(sheet)
    cols: dict[int, dict[int, list[Note]]] = defaultdict(lambda: defaultdict(list))
    for n in sheet.notes:
        if not n.covered:
            cols[n.frame][n.staff].append(n)
    bounds = sorted(f for f, _ in sheet.key_changes)
    frames_all = sorted(set(cols) | set(bounds))
    ms0 = min((n.on_ms for n in sheet.notes), default=0.0)
    # the timeline: ticks from the real time, pushed later where a figure needs more room
    tick: dict[int, int] = {}
    free = {1: 0, 2: 0}
    shift, prev = 0, -1
    ms_of = {f: min(n.on_ms for st in cols[f].values() for n in st) for f in cols}
    for f in frames_all:
        mains = [st for st, ns in cols.get(f, {}).items() if not ns[0].grace]
        base = round((ms_of.get(f, ms0) - ms0) / q * TICKS) if f in ms_of else prev + 1
        need = [free[st] for st in mains] + ([max(free.values())] if f in bounds else [])
        t = max([base + shift, prev + 1] + need)
        shift, prev = t - base, t
        tick[f] = t
        for st in mains:
            free[st] = t + TICKS * 4 // cols[f][st][0].figure
    end = max(free.values())
    layers: dict[int, list[list[str]]] = {1: [[]], 2: [[]]}
    octaves: list[tuple[int, str, str]] = []
    # beam groups as beamSpan with the list of their notes: the invisible spaces between them are not members, so
    # Verovio draws no short beam for a space (the floating "dash" between two stems)
    beams: dict[tuple[int, int], tuple[int, list[str]]] = {}
    for st in (1, 2):
        cursor = 0
        pending: list[str] = []  # grace notes and clef changes before the next main note
        run: list[str] = []
        clef_at = {f: c for f, s, c in sheet.clef_changes if s == st}
        seg = 0

        def flush_run() -> None:
            if run:
                octaves.append((st, run[0], run[-1]))
                run.clear()

        for f in frames_all:
            if f in bounds:
                layers[st][seg] += _space(tick[f] - cursor)
                cursor = tick[f]
                flush_run()
                seg += 1
                layers[st].append([])
            ns = cols.get(f, {}).get(st)
            if not ns:
                continue
            key = at(f)
            nid = f"n{st}_{f}"
            if f in clef_at:
                shape, line = _CLEF[clef_at[f]]
                pending.append(f'<clef shape="{shape}" line="{line}"/>')
            if ns[0].grace:
                pending.append(_element(ns, key, nid))
            else:
                b = ns[0].beam
                if b is not None:
                    beams.setdefault((st, b), (seg, []))[1].append(nid)
                layers[st][seg] += _space(tick[f] - cursor)
                layers[st][seg] += pending + [_element(ns, key, nid)]
                pending = []
                cursor = tick[f] + TICKS * 4 // ns[0].figure
            if ns[0].ottava:
                run.append(nid)
            else:
                flush_run()
        layers[st][seg] += _space(end - cursor)
        flush_run()
    keys = [sheet.key or 0] + [k for _, k in sorted(sheet.key_changes)]

    def keysig(k: int) -> str:
        return "0" if k == 0 else f"{abs(k)}{'s' if k > 0 else 'f'}"

    measures = []
    for i, k in enumerate(keys):
        oct_xml = "".join(
            f'<octave staff="{st}" dis="8" dis.place="above" startid="#{a}" endid="#{b}"/>'
            for st, a, b in octaves
            if any(a in x for x in layers[st][i])
        )
        oct_xml += "".join(
            f'<beamSpan staff="{st}" startid="#{ids[0]}" endid="#{ids[-1]}" '
            f'plist="{" ".join("#" + x for x in ids)}"/>'
            for (st, _), (seg_of, ids) in beams.items()
            if seg_of == i and len(ids) > 1
        )
        if i:
            measures.append(f'<scoreDef keysig="{keysig(k)}"/>')
        staves = "".join(
            f'<staff n="{st}"><layer n="1">{"".join(layers[st][i])}</layer></staff>'
            for st in (1, 2)
        )
        measures.append(f'<measure n="{i + 1}" right="invis">{staves}{oct_xml}</measure>')
    c1, c2 = _CLEF[sheet.clefs.get(1, "G2")], _CLEF[sheet.clefs.get(2, "F4")]
    return (
        '<?xml version="1.0" encoding="UTF-8"?><mei xmlns="http://www.music-encoding.org/ns/mei" '
        'meiversion="5.0"><meiHead><fileDesc><titleStmt><title/></titleStmt><pubStmt/></fileDesc>'
        "</meiHead><music><body><mdiv><score><scoreDef>"
        '<staffGrp symbol="brace" bar.thru="true">'
        f'<staffDef n="1" lines="5" clef.shape="{c1[0]}" clef.line="{c1[1]}" keysig="{keysig(keys[0])}"/>'
        f'<staffDef n="2" lines="5" clef.shape="{c2[0]}" clef.line="{c2[1]}" keysig="{keysig(keys[0])}"/>'
        f"</staffGrp></scoreDef><section>{''.join(measures)}</section></score></mdiv></body></music></mei>"
    )


def render(mei: str) -> str:
    import verovio  # noqa: PLC0415 - only this script needs it (uv run --with verovio)

    tk = verovio.toolkit()
    tk.setOptions(
        {
            "pageWidth": 8000,
            "adjustPageWidth": True,
            "adjustPageHeight": True,
            "scale": 38,
            "header": "none",
            "footer": "none",
            "breaks": "none",
            "svgViewBox": True,
        }
    )
    if not tk.loadData(mei):
        raise ValueError(tk.getLog())
    return tk.renderToSVG(1)


# ------------------------------------------------------------------ the page


def _time(ms: float) -> str:
    return f"{int(ms // 60000)}:{int(ms % 60000 // 1000):02d}"


def build(out: Path) -> None:
    parts = bundle.list_parts(layers=["private"])
    cache: dict[str, tuple] = {}
    sections: dict[str, list[str]] = defaultdict(list)
    index = []
    for no, (section, short, start, title, look, variant) in enumerate(CASES, start=1):
        pid = next(p for p in parts if p.startswith(short))
        if pid not in cache:
            notes = starting_hands(pid)
            project = json.loads((paths.part_dir(pid).parents[1] / "project.json").read_text())
            cache[pid] = (notes, algo.propose_frames(notes), project.get("title", ""))
        notes, prop, song = cache[pid]
        sheet = prop.sheet
        if start is None:  # the first rule 4 note of the song
            at = frames.key_at(sheet)
            start = next(
                n.frame
                for n in sheet.notes
                if (n.step, n.alter) in (("C", -1), ("F", -1), ("E", 1), ("B", 1))
                and key_alter(at(n.frame), n.step) != n.alter
            )
            start = max(0, start - 40)
        start, end = whole_groups(sheet, start, start + SPAN)
        part = passage(sheet, start, end)
        drawings = [("The new sheet", render(to_mei(part)))]
        if variant == "raw":
            raw = replace(sheet, notes=[replace(n) for n in sheet.notes])
            grace_figure = {id(n): n.figure for n in raw.notes if n.grace}
            algo.assign_figures(raw, prop.quarter_ms, cap=False)
            for n in raw.notes:
                n.figure = grace_figure.get(id(n), n.figure)
            algo.beam_groups(raw, prop.quarter_ms)
            drawings.append(
                (
                    "The same notes with the raw length (no cap)",
                    render(to_mei(passage(raw, start, end))),
                )
            )
        if variant == "becuadro":
            drawings.append(
                (
                    "The same notes with a becuadro instead (not rule 4)",
                    render(to_mei(as_becuadro(part))),
                )
            )
        text = f1.write(part, mode="frames").splitlines()
        text = [ln for i, ln in enumerate(text) if not (i == 2 and ln.startswith("[]x"))]
        when = _time(min(n.on_ms for n in part.notes))
        figs = ", ".join(f"{NAMES[k]} {int(round(prop.quarter_ms * 4 / k))} ms" for k in (4, 8, 16))
        anchor = f"c{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a></li>')
        body = "".join(
            f'<figure><figcaption>{html.escape(cap)}</figcaption><div class="svg">{svg}</div></figure>'
            for cap, svg in drawings
        )
        sections[section].append(
            f'<section id="{anchor}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="look">{html.escape(look)}</p>'
            f'<p class="where">{html.escape(song)}, from {when} (columns f{start} to f{end - 1}). '
            f"Reference figure: {figs}.</p>{body}"
            f"<details><summary>F1 text</summary><pre>{html.escape(chr(10).join(text))}</pre></details></section>"
        )
    page = PAGE.replace("{{INDEX}}", "".join(index)).replace(
        "{{SECTIONS}}",
        "".join(
            f"<h2>{html.escape(name)}</h2>{''.join(items)}" for name, items in sections.items()
        ),
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>New sheet: Phase 2 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; --tint: #f6f6f8; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1180px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { margin: 40px 0 8px; font-size: 20px; border-bottom: 1px solid var(--line); }
h3 { font-size: 16px; margin: 28px 0 4px; } .look { margin: 0 0 4px; } .where { color: var(--soft); margin: 0 0 8px; font-size: 13px; }
figure { margin: 8px 0 12px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { height: 170px; width: auto; max-width: none; display: block; }
pre { background: var(--tint); padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 12px; }
summary { cursor: pointer; color: var(--soft); font-size: 13px; } ol { columns: 2; font-size: 14px; }
</style></head><body><main>
<h1>The new sheet: figures, grace notes and alteraciones</h1>
<p>Implementation 03, Phase 2. Passages of My library written by the algorithm of the new sheet: no compases, no
tempo, no puntillos, no silencios. The notes are drawn by Verovio only to check the names, figures and grace notes:
the engine and the spacing of the new sheet come in Phase 3. Hands come from the saved hands and the hand split;
the LLM decides them in Phase 4.</p>
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="the folder of index.html")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
