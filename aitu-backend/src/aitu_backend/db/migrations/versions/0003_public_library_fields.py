"""What the downloaded music library gives and section 8.6 had no place for (implementation 02,
Phase 12, ``context/music-library/reconciliation.md`` section 3).

* ``song_lyrics``: the words of a song (9,104 of the 9,113 downloaded songs have them), kept apart
  from ``songs`` so a list of songs does not read them.
* ``album_artists``: the artists of an album, through artist names as for a song.
* ``album_chart_entries``: the album chart history (129,988 weeks), the source of an album's
  popularity.
* ``albums.release_date`` and ``albums.popularity``.

Only tables and columns are added, so nothing already stored changes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("albums") as batch_op:
        batch_op.add_column(sa.Column("release_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("popularity", sa.Float(), nullable=True))

    op.create_table(
        "album_artists",
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("artist_name_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artist_name_id"], ["artist_names.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("album_id", "artist_name_id"),
    )
    with op.batch_alter_table("album_artists") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_album_artists_artist_name_id"), ["artist_name_id"], unique=False
        )

    op.create_table(
        "song_lyrics",
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("song_id"),
    )

    op.create_table(
        "album_chart_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("chart_source_id", sa.Integer(), nullable=False),
        sa.Column("week", sa.Date(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chart_source_id"], ["chart_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("album_id", "chart_source_id", "week"),
    )
    with op.batch_alter_table("album_chart_entries") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_album_chart_entries_album_id"), ["album_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_album_chart_entries_week"), ["week"], unique=False)


def downgrade() -> None:
    op.drop_table("album_chart_entries")
    op.drop_table("song_lyrics")
    op.drop_table("album_artists")
    with op.batch_alter_table("albums") as batch_op:
        batch_op.drop_column("popularity")
        batch_op.drop_column("release_date")
