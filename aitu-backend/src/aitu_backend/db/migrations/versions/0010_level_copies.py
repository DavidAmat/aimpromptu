"""The level copies of the whole song simplification (implementation 04-3, Phase 4, plan section 5.8).

A level of the whole sheet (easy, medium, hard) is written into a new project of My projects, a copy of the song
named with the level ("99 Red Balloons · Easy"). ``projects.level_of`` names the project it was written from. It is
not ``based_on``: a level copy is not an edit copy, so **Edit** on a version of My Library still opens the user's own
edit copy (the user, 2026-10-30). The metadata of a level copy is the metadata of the song of that project.

Not a foreign key: the original may be deleted while the copy stays. Only a column is added; nothing stored changes.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-30 15:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("level_of", sa.String(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("level_of")
