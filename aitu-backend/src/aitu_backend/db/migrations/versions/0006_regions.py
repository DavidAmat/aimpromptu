"""The `spain` and `catalan` regions (implementation 02, Phase 16, Q-9;
``context/music-library/regional-sources.md``).

* ``regions``: the rows ``spain`` and ``catalan``.
* ``song_region_popularity``: a song's all-time popularity in a region other than ``worldwide``,
  with what it rests on (weekly places, number ones only, or an estimate from totals) and the
  chart it comes from. ``songs.popularity`` stays the worldwide one.
* ``song_keys`` and ``artist_keys``: more than one identity per public row. A song found on four
  regional lists keeps the key of each, so a later import finds the same row by any of them.

Only tables and rows are added, so nothing already stored changes.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-19 01:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

REGIONAL = (("spain", "Spain"), ("catalan", "Catalan"))


def upgrade() -> None:
    connection = op.get_bind()
    for code, name in REGIONAL:
        found = connection.execute(
            sa.text("SELECT id FROM regions WHERE code = :code"), {"code": code}
        )
        if found.first() is None:
            connection.execute(
                sa.text("INSERT INTO regions (code, name) VALUES (:code, :name)"),
                {"code": code, "name": name},
            )

    op.create_table(
        "song_region_popularity",
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("popularity", sa.Float(), nullable=False),
        sa.Column("basis", sa.String(16), nullable=False),
        sa.Column("chart_source_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("basis IN ('weeks', 'number_ones', 'estimated')", name="basis_allowed"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.ForeignKeyConstraint(["chart_source_id"], ["chart_sources.id"]),
        sa.PrimaryKeyConstraint("song_id", "region_id"),
    )
    op.create_table(
        "song_keys",
        sa.Column("key", sa.String(400), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key"),
    )
    with op.batch_alter_table("song_keys") as batch_op:
        batch_op.create_index(batch_op.f("ix_song_keys_song_id"), ["song_id"], unique=False)
    op.create_table(
        "artist_keys",
        sa.Column("key", sa.String(400), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key"),
    )
    with op.batch_alter_table("artist_keys") as batch_op:
        batch_op.create_index(batch_op.f("ix_artist_keys_artist_id"), ["artist_id"], unique=False)


def downgrade() -> None:
    op.drop_table("artist_keys")
    op.drop_table("song_keys")
    op.drop_table("song_region_popularity")
    connection = op.get_bind()
    for code, _name in REGIONAL:
        ids = [
            row[0]
            for row in connection.execute(
                sa.text("SELECT id FROM regions WHERE code = :code"), {"code": code}
            )
        ]
        for region_id in ids:
            connection.execute(
                sa.text("DELETE FROM song_regions WHERE region_id = :id"), {"id": region_id}
            )
            connection.execute(
                sa.text("UPDATE chart_sources SET region_id = NULL WHERE region_id = :id"),
                {"id": region_id},
            )
            connection.execute(sa.text("DELETE FROM regions WHERE id = :id"), {"id": region_id})
