"""A project may be a passage being re-recorded (implementation 02, Phase 9, plan section 13).

**Record this passage** keeps its work in projects of their own, hidden from every list: the
passage (a copy of the marked frames of a part, the *Current*) and each take recorded for it. They
are ordinary bundles of the owner's Personal Vault, so the steps of a project (the audio, the
transcription, the hands, the sheet) work on a take unchanged; ``kind = 'passage'`` is what keeps
them out of the Projects page and the lists of audio.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 10:00:00
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", recreate="always") as batch_op:
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.create_check_constraint(
            "kind_allowed", "kind IN ('song', 'integratedPlaylist', 'passage')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM projects WHERE kind = 'passage'")
    with op.batch_alter_table("projects", recreate="always") as batch_op:
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.create_check_constraint("kind_allowed", "kind IN ('song', 'integratedPlaylist')")
