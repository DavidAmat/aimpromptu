"""Requests to the Public Library (implementation 02, Phase 14, plan section 16).

Two allowed values are added, nothing else changes:

* ``projects.layer = 'request'``: the copy of a project a request sends, made when the request is
  sent, so later edits in the author's library do not change what the master user reviews. It is
  in ``.database/requests/<projectId>/``; its author and the master user read it, nobody writes it.
* ``requests.kind = 'playlist'``: a songs playlist of the Private Library made public (the user,
  2026-10-16: the app context promotes "a given private song or a given private playlist").

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16 18:00:00
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", recreate="always") as batch_op:
        batch_op.drop_constraint("layer_allowed", type_="check")
        batch_op.create_check_constraint(
            "layer_allowed", "layer IN ('vault', 'private', 'public', 'request')"
        )
    with op.batch_alter_table("requests", recreate="always") as batch_op:
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.create_check_constraint(
            "kind_allowed", "kind IN ('metadata', 'userVersion', 'fixedVersion', 'playlist')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM projects WHERE layer = 'request'")
    op.execute("DELETE FROM requests WHERE kind = 'playlist'")
    with op.batch_alter_table("projects", recreate="always") as batch_op:
        batch_op.drop_constraint("layer_allowed", type_="check")
        batch_op.create_check_constraint("layer_allowed", "layer IN ('vault', 'private', 'public')")
    with op.batch_alter_table("requests", recreate="always") as batch_op:
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.create_check_constraint(
            "kind_allowed", "kind IN ('metadata', 'userVersion', 'fixedVersion')"
        )
