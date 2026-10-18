"""The conversation of a request (implementation 02, Phase 14, asked by the user on 2026-10-18).

A request's page is laid out like a pull request: a timeline of comments and events, and comments
on a stretch of the proposed sheet. ``request_comments`` gets four columns, all added, nothing
copied:

* ``kind``: ``comment`` (every row so far), ``review``, ``sentAgain`` or ``withdrawn``;
* ``item_id``: the item a comment is about;
* ``parent_id``: the comment a reply answers;
* ``details``: JSON, the stretch of a comment or the decisions of a review.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-18 11:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("request_comments", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(16), nullable=False, server_default="comment")
        )
        batch_op.add_column(sa.Column("item_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("details", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "kind_allowed", "kind IN ('comment', 'review', 'sentAgain', 'withdrawn')"
        )
        batch_op.create_foreign_key(
            "fk_request_comments_item", "request_items", ["item_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            "fk_request_comments_parent",
            "request_comments",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_request_comments_parent_id", ["parent_id"])


def downgrade() -> None:
    op.execute("DELETE FROM request_comments WHERE kind != 'comment' OR parent_id IS NOT NULL")
    with op.batch_alter_table("request_comments", recreate="always") as batch_op:
        batch_op.drop_index("ix_request_comments_parent_id")
        batch_op.drop_constraint("fk_request_comments_parent", type_="foreignkey")
        batch_op.drop_constraint("fk_request_comments_item", type_="foreignkey")
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.drop_column("details")
        batch_op.drop_column("parent_id")
        batch_op.drop_column("item_id")
        batch_op.drop_column("kind")
