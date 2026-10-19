"""A popularity inferred from YouTube views (implementation 02, Phase 17, Q-10;
``context/music-library/popularity.md`` section 6).

* ``song_signals``: what a public song has outside the charts, one row per song: its official
  video on YouTube (the id, where the id came from, the kind of channel, the upload date, the views)
  and its all-time Spotify streams (kworb.net), with the day they were read. The views are read
  again within 30 days (the YouTube API Developer Policies).
* ``song_region_popularity``: a fourth basis, ``inferred``, for a song no chart of the region
  lists, and ``inferred_on``, the day it was worked out. A chart value always replaces it.

Only a table, a column and an allowed value are added, so nothing already stored changes.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-19 14:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "song_signals",
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(16), nullable=True),
        sa.Column("found_by", sa.String(16), nullable=True),
        sa.Column("channel", sa.String(8), nullable=True),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("views", sa.BigInteger(), nullable=True),
        sa.Column("streams", sa.BigInteger(), nullable=True),
        sa.Column("read_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("song_id"),
    )
    with op.batch_alter_table("song_region_popularity", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("inferred_on", sa.Date(), nullable=True))
        batch_op.drop_constraint("basis_allowed", type_="check")
        batch_op.create_check_constraint(
            "basis_allowed", "basis IN ('weeks', 'number_ones', 'estimated', 'inferred')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM song_region_popularity WHERE basis = 'inferred'")
    with op.batch_alter_table("song_region_popularity", recreate="always") as batch_op:
        batch_op.drop_column("inferred_on")
        batch_op.drop_constraint("basis_allowed", type_="check")
        batch_op.create_check_constraint(
            "basis_allowed", "basis IN ('weeks', 'number_ones', 'estimated')"
        )
    op.drop_table("song_signals")
