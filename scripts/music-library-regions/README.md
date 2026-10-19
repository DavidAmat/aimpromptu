# The `spain` and `catalan` sources

The download and the build of the regional lists of the Public Library (implementation 02,
Phase 16). What the sources are and why these: [regional-sources.md](../../context/music-library/regional-sources.md).
Python standard library only; `pdftohtml` (poppler) for the APECAT PDFs.

| File | What it does |
|---|---|
| `download.py <source>` | Saves every page of a source once into `data/music-library-regions/<source>/raw/` beside the repository (`MUSIC_LIBRARY_REGIONS_DIR` moves it), paced, with a `manifest.sqlite`; run again, it asks only for what is missing. `--status` prints what is saved |
| `parse.py` | Reads one saved page (or one PDF's `pdftohtml -xml`) into rows |
| `build.py <source>... \| all` | Writes `<source>/<source>.sqlite` again from `raw/`: charts, songs, entries, totals, notes |
| `test_parse.py` | The readers on small pieces of each format, no network: `python3 scripts/music-library-regions/test_parse.py` |
| `common.py` | The fetcher: the timer, the manifest, the stop on a refusal |

```bash
make regional-download SOURCE=spanishcharts   # also los40, kworb, apecat, wikipedia
make regional-build
make regional-import                          # the public rows: aitu_backend/library/regional_import.py
make regional-import ARGS="--database /path/to/a/copy"
```

The paces: spanishcharts.com 5 s, los40.com 10 s, the others 3 s between two requests.
