"""The metadata of an edit copy is its song's (implementation 04-3, Phase 1, the user on 2026-10-29).

The metadata belongs to a song, never to one version of it. An edit copy (a project of My projects
whose ``based_on`` is a version of My Library) has no rows of its own any more: it shows and changes
its song's. The rows an edit copy has in ``project_tags`` move to its song's ``private_song_tags``
(a row the song already has is kept once) and leave the copy.

Only rows move; no table or column changes. The downgrade leaves them on the song.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-29 23:15:00
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_EDIT_COPIES = """
    SELECT projects.id AS project_id, private_versions.song_id AS song_id
    FROM projects JOIN private_versions ON private_versions.project_id = projects.based_on
    WHERE projects.layer = 'vault'
"""


def upgrade() -> None:
    op.execute(f"""
        INSERT OR IGNORE INTO private_song_tags (song_id, tag_value_id)
        SELECT copies.song_id, project_tags.tag_value_id
        FROM project_tags JOIN ({_EDIT_COPIES}) AS copies
          ON copies.project_id = project_tags.project_id
        """)
    op.execute(f"""
        DELETE FROM project_tags
        WHERE project_id IN (SELECT project_id FROM ({_EDIT_COPIES}))
        """)


def downgrade() -> None:
    pass
