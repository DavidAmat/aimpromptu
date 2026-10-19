"""A popularity inferred from YouTube views (and Spotify streams) for a song no chart lists
(implementation 02, Phase 17; ``context/music-library/popularity.md`` section 6).

**The fit.** The songs that have both a chart popularity (``weeks``: a chart with places) and an
official video (:mod:`signals`) are the sample. Each candidate relation is fitted on four fifths of
the songs and measured on the fifth left out, five times (a song's regions stay in the same fifth),
as the mean difference in points from its chart popularity, and by how well it keeps the charts'
order (a rank correlation).

::

    python -m aitu_backend.library.inferred collect [--songs ID ...] [--no-search] [--no-streams]
    python -m aitu_backend.library.inferred fit [--out DIR]

``collect`` reads the signals (:mod:`signals`) of the songs named, or of every public song that has
a free video id, into ``song_signals``; ``fit`` writes the scatter plots and the errors of every
candidate into ``--out`` and changes nothing.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import Region, Song, SongRegion, SongRegionPopularity, SongSignal
from aitu_backend.library import popularity
from aitu_backend.library import signals as signals_module

__all__ = ["CANDIDATES", "Candidate", "Row", "evaluate", "plots", "sample_rows", "store_signals"]

REGIONS = ("worldwide", "spain", "catalan")
#: The decades with a term of their own; earlier ones are the base, later ones count as the 2020s.
TERM_DECADES = (1980, 1990, 2000, 2010, 2020)
#: The kinds of official channel with a term of their own; ``artist`` is the base.
TERM_CHANNELS = ("vevo", "topic", "label")


@dataclass(frozen=True)
class Row:
    """One song in one region: its chart popularity and its signals."""

    song_id: int
    region: str
    popularity: float
    basis: str
    year: int | None
    views: int
    published: date
    read_on: date
    streams: int | None = None
    #: ``artist``, ``topic``, ``vevo`` or ``label`` (:func:`signals.channel_kind`).
    channel: str = "artist"

    @property
    def years_online(self) -> float:
        """The years the video has been on YouTube, at least a quarter."""
        return max(0.25, (self.read_on - self.published).days / 365.25)

    @property
    def log_views(self) -> float:
        return math.log10(max(self.views, 1))

    @property
    def log_views_per_year(self) -> float:
        return math.log10(max(self.views, 1) / self.years_online)

    @property
    def upload_delay(self) -> float:
        """The years between the song and its upload (0 when the song has no year)."""
        return max(0.0, float(self.published.year - self.year)) if self.year else 0.0

    @property
    def log_streams(self) -> float | None:
        return math.log10(max(self.streams, 1)) if self.streams else None


# --------------------------------------------------------------------------- candidates


def _design(rows: Sequence[Row], feature: str, terms: bool, streams: bool) -> np.ndarray:
    columns: list[list[float]] = [[1.0] * len(rows), [getattr(r, feature) for r in rows]]
    if terms:
        for region in REGIONS[1:]:
            columns.append([1.0 if r.region == region else 0.0 for r in rows])
        # One term per decade from the 80s; the 70s and before (no song of the sample is older)
        # are the base. A song with no year counts in its video's decade.
        for decade in TERM_DECADES:
            columns.append([1.0 if _decade(r) == decade else 0.0 for r in rows])
        for kind in TERM_CHANNELS:
            columns.append([1.0 if r.channel == kind else 0.0 for r in rows])
        columns.append([min(r.upload_delay, 30.0) for r in rows])
    if streams:
        columns.append([r.log_streams or 0.0 for r in rows])
        columns.append([0.0 if r.log_streams else 1.0 for r in rows])
    return np.array(columns, dtype=float).T


def _decade(row: Row) -> int:
    year = row.year or row.published.year
    return min(max(year - year % 10, TERM_DECADES[0] - 10), TERM_DECADES[-1])


@dataclass(frozen=True)
class Candidate:
    """A relation between the signals and the popularity, fitted on rows, then applied."""

    key: str
    name: str
    fit: Callable[[Sequence[Row]], Callable[[Sequence[Row]], np.ndarray]]


def _linear(feature: str, terms: bool = False, streams: bool = False) -> Callable:
    def fit(train: Sequence[Row]) -> Callable[[Sequence[Row]], np.ndarray]:
        x = _design(train, feature, terms, streams)
        y = np.array([r.popularity for r in train])
        coefficients, *_ = np.linalg.lstsq(x, y, rcond=None)

        def apply(rows: Sequence[Row]) -> np.ndarray:
            return np.clip(_design(rows, feature, terms, streams) @ coefficients, 0.0, 100.0)

        apply.coefficients = coefficients  # type: ignore[attr-defined]
        return apply

    return fit


def _monotonic(feature: str) -> Callable:
    """One curve per region that only goes up with the feature (an isotonic regression)."""

    def fit(train: Sequence[Row]) -> Callable[[Sequence[Row]], np.ndarray]:
        from sklearn.isotonic import IsotonicRegression  # noqa: PLC0415 - the fit only

        curves = {}
        for region in REGIONS:
            mine = [r for r in train if r.region == region]
            if len(mine) < 10:
                mine = list(train)
            curve = IsotonicRegression(y_min=0.0, y_max=100.0, out_of_bounds="clip")
            curve.fit([getattr(r, feature) for r in mine], [r.popularity for r in mine])
            curves[region] = curve

        def apply(rows: Sequence[Row]) -> np.ndarray:
            return np.array(
                [float(curves[r.region].predict([getattr(r, feature)])[0]) for r in rows]
            )

        return apply

    return fit


def _boosted(streams: bool) -> Callable:
    """Gradient boosted trees on every signal: not a formula, a measure of how much the signals
    can say at most."""

    def features(rows: Sequence[Row], streams: bool) -> np.ndarray:
        return np.array(
            [
                [
                    r.log_views,
                    r.log_views_per_year,
                    r.year or np.nan,
                    r.upload_delay,
                    REGIONS.index(r.region),
                    ("artist", "vevo", "topic", "label").index(r.channel),
                    *([r.log_streams or np.nan] if streams else []),
                ]
                for r in rows
            ]
        )

    def fit(train: Sequence[Row]) -> Callable[[Sequence[Row]], np.ndarray]:
        from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: PLC0415

        model = HistGradientBoostingRegressor(
            max_iter=300,
            learning_rate=0.05,
            min_samples_leaf=40,
            categorical_features=[4, 5],
            random_state=17,
        )
        # A column with no value at all cannot be binned: no song of the sample has streams.
        use = streams and any(r.streams for r in train)
        model.fit(features(train, use), [r.popularity for r in train])
        return lambda rows: np.clip(model.predict(features(rows, use)), 0.0, 100.0)

    return fit


def _median(train: Sequence[Row]) -> Callable[[Sequence[Row]], np.ndarray]:
    medians = {
        region: float(np.median([r.popularity for r in train if r.region == region] or [0.0]))
        for region in REGIONS
    }
    return lambda rows: np.array([medians[r.region] for r in rows])


CANDIDATES = (
    Candidate("median", "The region's median (no signal: the error to beat)", _median),
    Candidate("views", "A line on the log of the views", _linear("log_views")),
    Candidate(
        "per_year", "A line on the log of the views per year online", _linear("log_views_per_year")
    ),
    Candidate(
        "terms",
        "A line on the log of the views per year, with a term per region, decade and kind of channel, and the years before the upload",
        _linear("log_views_per_year", terms=True),
    ),
    Candidate(
        "monotonic",
        "A curve that only rises with the views per year, one per region",
        _monotonic("log_views_per_year"),
    ),
    Candidate(
        "streams",
        "The line with terms, and the log of the Spotify streams (kworb) where a song has them",
        _linear("log_views_per_year", terms=True, streams=True),
    ),
    Candidate("boosted", "Boosted trees on the views (a ceiling, not a formula)", _boosted(False)),
    Candidate(
        "boosted_streams",
        "Boosted trees on the views and the streams (a ceiling, not a formula)",
        _boosted(True),
    ),
)


#: The candidate the user chose on 2026-10-19 (Story 17.2): its weights are ``popularity.INFERRED``.
CHOSEN = "streams"


def chosen_weights(rows: Sequence[Row]) -> popularity.InferredWeights:
    """The weights of :data:`CHOSEN` fitted on every row, as ``popularity.inferred`` reads them."""
    apply = next(one for one in CANDIDATES if one.key == CHOSEN).fit(rows)
    c = [round(float(v), 3) for v in apply.coefficients]  # type: ignore[attr-defined]
    decades = len(TERM_DECADES)
    return popularity.InferredWeights(
        intercept=c[0],
        per_year=c[1],
        spain=c[2],
        catalan=c[3],
        decades=tuple(zip(TERM_DECADES, c[4 : 4 + decades])),
        channels=tuple(zip(TERM_CHANNELS, c[4 + decades : 7 + decades])),
        delay=c[7 + decades],
        streams=c[8 + decades],
        no_streams=c[9 + decades],
    )


# --------------------------------------------------------------------------- measuring


def folds(rows: Sequence[Row], k: int = 5, seed: int = 17) -> list[int]:
    """The fifth of each row: by song, so a song's regions are left out together."""
    songs = sorted({r.song_id for r in rows})
    order = np.random.default_rng(seed).permutation(len(songs))
    fold_of = {songs[i]: int(n % k) for n, i in enumerate(order)}
    return [fold_of[r.song_id] for r in rows]


def predict_left_out(candidate: Candidate, rows: Sequence[Row], k: int = 5) -> np.ndarray:
    """Each row's prediction by the candidate fitted without its fifth."""
    which = folds(rows, k)
    found = np.zeros(len(rows))
    for fold in range(k):
        train = [r for r, f in zip(rows, which) if f != fold]
        test = [i for i, f in enumerate(which) if f == fold]
        apply = candidate.fit(train)
        found[test] = apply([rows[i] for i in test])
    return found


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    """How well one order follows the other: 1 the same, 0 none (ties at their mean rank)."""
    from scipy.stats import spearmanr  # noqa: PLC0415

    return float(spearmanr(a, b).statistic) if np.ptp(a) > 0 else 0.0


def bands(value: float) -> str:
    low = min(int(value // 20), 4) * 20
    return f"{low} to {low + 20}"


def evaluate(rows: Sequence[Row], candidates: Sequence[Candidate] = CANDIDATES) -> list[dict]:
    """The mean error in points of each candidate on the songs left out: all, per region, per
    band of the chart popularity, and the share within 10 points."""
    truth = np.array([r.popularity for r in rows])
    found = []
    for candidate in candidates:
        guess = predict_left_out(candidate, rows)
        error = np.abs(guess - truth)
        found.append(
            {
                "key": candidate.key,
                "name": candidate.name,
                "error": float(error.mean()),
                "within_10": float((error <= 10).mean()),
                "order": _spearman(guess, truth),
                "regions": {
                    region: float(error[[r.region == region for r in rows]].mean())
                    for region in REGIONS
                    if any(r.region == region for r in rows)
                },
                "bands": {
                    band: float(error[[bands(r.popularity) == band for r in rows]].mean())
                    for band in sorted({bands(r.popularity) for r in rows})
                },
                "guess": guess,
            }
        )
    return found


# --------------------------------------------------------------------------- the plots


_COLOURS = {"worldwide": "#4C6EF5", "spain": "#E8590C", "catalan": "#2B8A3E"}


def plots(rows: Sequence[Row], results: list[dict], out: Path) -> list[Path]:
    """The scatter plots of the report, as PNG files in ``out``."""
    import matplotlib  # noqa: PLC0415 - the fit only

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    out.mkdir(parents=True, exist_ok=True)
    written = []

    def scatter(name: str, feature: Callable[[Row], float | None], label: str) -> None:
        figure, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
        for axis, region in zip(axes, REGIONS):
            mine = [r for r in rows if r.region == region and feature(r) is not None]
            axis.scatter(
                [feature(r) for r in mine],
                [r.popularity for r in mine],
                s=6,
                alpha=0.35,
                color=_COLOURS[region],
                linewidths=0,
            )
            axis.set_title(f"{region} ({len(mine)} songs)")
            axis.set_xlabel(label)
            axis.grid(alpha=0.25)
        axes[0].set_ylabel("Chart popularity")
        figure.tight_layout()
        path = out / f"{name}.png"
        figure.savefig(path, dpi=110)
        plt.close(figure)
        written.append(path)

    scatter("01-popularity-views", lambda r: r.log_views, "log10 of the views")
    scatter(
        "02-popularity-views-per-year",
        lambda r: r.log_views_per_year,
        "log10 of the views per year online",
    )
    scatter(
        "03-popularity-streams", lambda r: r.log_streams, "log10 of the Spotify streams (kworb)"
    )

    shown = [one for one in results if one["key"] != "median"]
    figure, axes = plt.subplots(1, len(shown), figsize=(4 * len(shown), 4.2), sharey=True)
    truth = [r.popularity for r in rows]
    for axis, one in zip(axes, shown):
        axis.scatter(
            truth,
            one["guess"],
            s=5,
            alpha=0.3,
            c=[_COLOURS[r.region] for r in rows],
            linewidths=0,
        )
        axis.plot([0, 100], [0, 100], color="#868E96", linewidth=1)
        axis.set_title(f"{one['key']}: {one['error']:.1f} points", fontsize=10)
        axis.set_xlabel("Chart popularity")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Inferred, on songs left out")
    figure.tight_layout()
    path = out / "04-inferred-against-chart.png"
    figure.savefig(path, dpi=110)
    plt.close(figure)
    written.append(path)
    return written


# --------------------------------------------------------------------------- the database


def store_signals(db: DbSession, found: dict[int, signals_module.Signal]) -> int:
    """Write what was found into ``song_signals``, one row per song (written again when read
    again); a song with neither a video nor streams gets no row. The number of rows written."""
    rows = []
    for song_id, one in found.items():
        if one.video is None and one.streams is None:
            continue
        read = one.video.read_at if one.video else one.streams_read_at
        rows.append(
            {
                "song_id": song_id,
                "video_id": one.video.id if one.video else None,
                "found_by": one.found_by,
                "channel": one.channel_kind,
                "published_on": one.video.published if one.video else None,
                "views": one.video.views if one.video else None,
                "streams": one.streams,
                "read_on": (read or signals_module._now()).date(),
            }
        )
    ids = [row["song_id"] for row in rows]
    for start in range(0, len(ids), 500):
        db.execute(delete(SongSignal).where(SongSignal.song_id.in_(ids[start : start + 500])))
    if rows:
        db.execute(insert(SongSignal), rows)
    return len(rows)


def chart_values(db: DbSession, basis: str = "weeks") -> list[tuple[int, str, float]]:
    """``(song, region, popularity)`` of every song with a chart value of this basis: the
    worldwide one of the songs of the US chart (``songs.popularity``), and the others'
    ``song_region_popularity``."""
    found: list[tuple[int, str, float]] = []
    if basis == "weeks":
        found += [
            (int(song_id), "worldwide", float(value or 0.0))
            for song_id, value in db.execute(
                select(Song.id, Song.popularity)
                .join(SongRegion, SongRegion.song_id == Song.id)
                .join(Region, Region.id == SongRegion.region_id)
                .where(Song.scope == "public", Region.code == "worldwide")
            )
        ]
    found += [
        (int(song_id), str(code), float(value))
        for song_id, code, value in db.execute(
            select(SongRegionPopularity.song_id, Region.code, SongRegionPopularity.popularity)
            .join(Region, Region.id == SongRegionPopularity.region_id)
            .where(SongRegionPopularity.basis == basis)
        )
    ]
    return found


def sample_rows(db: DbSession, basis: str = "weeks") -> list[Row]:
    """The sample: every song with a chart value of this basis and an official video."""
    stored = {
        one.song_id: one
        for one in db.scalars(select(SongSignal).where(SongSignal.views.is_not(None)))
    }
    years = dict(db.execute(select(Song.id, Song.year).where(Song.scope == "public")).all())
    rows = []
    for song_id, region, value in chart_values(db, basis):
        one = stored.get(song_id)
        if one is None or one.published_on is None or one.views is None:
            continue
        rows.append(
            Row(
                song_id=song_id,
                region=region,
                popularity=value,
                basis=basis,
                year=years.get(song_id),
                views=int(one.views),
                published=one.published_on,
                read_on=one.read_on,
                streams=int(one.streams) if one.streams else None,
                channel=one.channel or "artist",
            )
        )
    return rows


def report_lines(results: list[dict], rows: Sequence[Row]) -> list[str]:
    counts = {region: sum(1 for r in rows if r.region == region) for region in REGIONS}
    lines = [
        f"sample: {len(rows)} songs and regions {counts}, "
        f"{sum(1 for r in rows if r.streams)} with streams",
        "candidate        error  order  within 10  " + "  ".join(f"{r:>9}" for r in REGIONS),
    ]
    for one in results:
        lines.append(
            f"{one['key']:15} {one['error']:6.1f}  {one['order']:5.2f}  {100 * one['within_10']:7.0f} %  "
            + "  ".join(f"{one['regions'].get(r, float('nan')):9.1f}" for r in REGIONS)
        )
    return lines


# --------------------------------------------------------------------------- inferring


#: Signals read longer ago than this are read again before a value is worked out from them, so no
#: view count is kept past the 30 days of the YouTube API Developer Policies.
FRESH_DAYS = signals_module.STATS_DAYS - 5


@dataclass
class Report:
    pairs: int = 0
    read: int = 0
    written: dict[str, int] = field(default_factory=dict)
    without_video: int = 0
    removed: int = 0
    refreshed: int = 0
    gone: int = 0

    def lines(self) -> list[str]:
        return [
            f"{self.pairs} songs and regions with no chart value; signals read for {self.read}",
            f"inferred values written: {self.written}; {self.without_video} with no official video",
            f"inferred values removed (a chart lists the song now, or no video): {self.removed}",
            f"views read again: {self.refreshed}; videos no longer on YouTube: {self.gone}",
        ]


def targets(db: DbSession) -> list[tuple[int, str]]:
    """Every public song and region with no chart value: a song of `spain` or `catalan` that no
    chart of the region scores, and ``worldwide`` for a song on no chart at all (no region)."""
    regions = dict(db.execute(select(Region.code, Region.id)).all())
    codes = {v: k for k, v in regions.items()}
    charted = {
        (int(song_id), codes[region_id])
        for song_id, region_id in db.execute(
            select(SongRegionPopularity.song_id, SongRegionPopularity.region_id).where(
                SongRegionPopularity.basis != "inferred"
            )
        )
    }
    listed: dict[int, set[str]] = {}
    for song_id, region_id in db.execute(select(SongRegion.song_id, SongRegion.region_id)):
        listed.setdefault(int(song_id), set()).add(codes[region_id])
    found = [
        (song_id, region)
        for song_id, regions_of in listed.items()
        for region in sorted(regions_of)
        if region != popularity.WORLDWIDE and (song_id, region) not in charted
    ]
    for (song_id,) in db.execute(select(Song.id).where(Song.scope == "public")):
        if int(song_id) not in listed:
            found.append((int(song_id), popularity.WORLDWIDE))
    return sorted(found)


def _write(db: DbSession, pairs: list[tuple[int, str]], report: Report, today: date) -> None:
    """Work out the value of each pair from its stored signals; a pair with no official video
    has none."""
    regions = dict(db.execute(select(Region.code, Region.id)).all())
    stored = {
        one.song_id: one
        for one in db.scalars(
            select(SongSignal).where(SongSignal.song_id.in_({s for s, _ in pairs}))
        )
    }
    years = dict(
        db.execute(select(Song.id, Song.year).where(Song.id.in_({s for s, _ in pairs}))).all()
    )
    for song_id, region in pairs:
        one = stored.get(song_id)
        db.execute(
            delete(SongRegionPopularity).where(
                SongRegionPopularity.song_id == song_id,
                SongRegionPopularity.region_id == regions[region],
                SongRegionPopularity.basis == "inferred",
            )
        )
        if one is None or one.views is None or one.published_on is None:
            report.without_video += 1
            continue
        value = popularity.inferred(
            region=region,
            year=years.get(song_id),
            views=int(one.views),
            published=one.published_on,
            read_on=one.read_on,
            channel=one.channel,
            streams=int(one.streams) if one.streams else None,
        )
        db.add(
            SongRegionPopularity(
                song_id=song_id,
                region_id=regions[region],
                popularity=value,
                basis="inferred",
                inferred_on=today,
            )
        )
        report.written[region] = report.written.get(region, 0) + 1


def infer(
    db: DbSession,
    client: signals_module.Client,
    song_ids: list[int] | None = None,
    search: bool = True,
    streams: bool = True,
    today: date | None = None,
) -> Report:
    """Give every song with no chart value in a region (or only these songs) its inferred value:
    its signals read first when it has none or they are older than :data:`FRESH_DAYS` (free
    video ids, then a search while the day's searches last), then the formula. An inferred value
    no longer wanted (a chart lists the song now) is removed."""
    today = today or date.today()
    report = Report()
    pairs = targets(db)
    if song_ids is None:
        wanted = set(pairs)
        for song_id, region_id, code in db.execute(
            select(SongRegionPopularity.song_id, SongRegionPopularity.region_id, Region.code)
            .join(Region, Region.id == SongRegionPopularity.region_id)
            .where(SongRegionPopularity.basis == "inferred")
        ):
            if (int(song_id), str(code)) not in wanted:
                db.execute(
                    delete(SongRegionPopularity).where(
                        SongRegionPopularity.song_id == song_id,
                        SongRegionPopularity.region_id == region_id,
                    )
                )
                report.removed += 1
    else:
        chosen = set(song_ids)
        pairs = [pair for pair in pairs if pair[0] in chosen]
    report.pairs = len(pairs)
    stale = today - timedelta(days=FRESH_DAYS)
    fresh = {
        int(song_id)
        for (song_id,) in db.execute(select(SongSignal.song_id).where(SongSignal.read_on >= stale))
    }
    unread = sorted({s for s, _ in pairs} - fresh)
    if unread:
        found = signals_module.collect(db, client, unread, search, streams)
        store_signals(db, found)
        report.read = len(unread)
    db.flush()
    _write(db, pairs, report, today)
    return report


def refresh(db: DbSession, client: signals_module.Client, today: date | None = None) -> Report:
    """Read again the views of every kept video read more than :data:`FRESH_DAYS` days ago (1 unit
    for 50 videos), forget those no longer on YouTube, and work out the inferred values again."""
    today = today or date.today()
    report = Report()
    stale = list(
        db.scalars(
            select(SongSignal).where(
                SongSignal.video_id.is_not(None),
                SongSignal.read_on < today - timedelta(days=FRESH_DAYS),
            )
        )
    )
    videos = client.videos((str(one.video_id) for one in stale), days=0)
    for one in stale:
        video = videos.get(str(one.video_id))
        if video is None:
            one.video_id = one.found_by = one.channel = None
            one.views = None
            one.published_on = None
            report.gone += 1
        else:
            one.views = video.views
            report.refreshed += 1
        one.read_on = today
    db.flush()
    pairs = [pair for pair in targets(db)]
    report.pairs = len(pairs)
    _write(db, pairs, report, today)
    return report


# --------------------------------------------------------------------------- command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--database", type=Path, default=None, help="another .database/ folder")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="read the signals into song_signals")
    collect.add_argument("--songs", type=int, nargs="*", default=None)
    collect.add_argument("--no-search", action="store_true")
    collect.add_argument("--no-streams", action="store_true")
    fit = commands.add_parser("fit", help="measure the candidates, write the plots")
    fit.add_argument("--out", type=Path, default=Path("phase-17-fit"))
    infer_ = commands.add_parser("infer", help="give the songs with no chart value theirs")
    infer_.add_argument("--songs", type=int, nargs="*", default=None)
    infer_.add_argument("--no-search", action="store_true")
    infer_.add_argument("--no-streams", action="store_true")
    commands.add_parser("refresh", help="read the views again before 30 days pass")
    args = parser.parse_args(argv)
    if args.database is not None:
        os.environ["AITU_DATABASE_DIR"] = str(args.database.resolve())

    from aitu_backend.db.database import session  # noqa: PLC0415 - after AITU_DATABASE_DIR

    if args.command == "collect":
        answers = signals_module.Answers(signals_module.default_folder() / "answers.sqlite")
        client = signals_module.Client(answers)
        with session() as db:
            free = signals_module.free_videos(db, client)
            wanted = args.songs if args.songs is not None else sorted(free)
            found = signals_module.collect(
                db, client, wanted, not args.no_search, not args.no_streams, free
            )
            written = store_signals(db, found)
        videos = sum(1 for one in found.values() if one.video)
        streams = sum(1 for one in found.values() if one.streams)
        print(
            f"{len(wanted)} songs: {videos} with an official video, {streams} with streams;"
            f" {written} rows written; asked {dict(client.asked)}"
        )
        answers.close()
        return 0
    if args.command in ("infer", "refresh"):
        answers = signals_module.Answers(signals_module.default_folder() / "answers.sqlite")
        client = signals_module.Client(answers)
        with session() as db:
            if args.command == "infer":
                report = infer(db, client, args.songs, not args.no_search, not args.no_streams)
            else:
                report = refresh(db, client)
        print("\n".join(report.lines()) + f"\nasked {dict(client.asked)}")
        answers.close()
        return 0
    with session() as db:
        rows = sample_rows(db)
    results = evaluate(rows)
    print("\n".join(report_lines(results, rows)))
    for path in plots(rows, results, args.out):
        print(f"  {path}")
    print(f"the weights of {CHOSEN!r} on every row: {chosen_weights(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
