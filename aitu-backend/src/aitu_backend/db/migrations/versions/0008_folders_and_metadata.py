"""Folders and metadata of My projects and My Library (implementation 04-3, Phase 1, plan sections 4.2 and 4.4).

* ``folders``: a folder of one user in one area (``projects``: My projects; ``library``: My Library), with the id of
  its parent folder (``NULL`` at the top). Deleting a folder deletes its child folders.
* ``folder_projects`` and ``folder_songs``: a project or a song in a folder; one item can be in several folders. Two
  tables, because a project id is a uuid and a song id an integer.
* ``private_tag_values``: a secondary key of one user inside a primary key (``tag_categories``). Its own table, so
  that a value a user types never reaches the Public Library's ``tag_values``.
* ``project_tags`` and ``private_song_tags``: the metadata rows of a project or a song.

Only tables are added, so nothing already stored changes.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-29 19:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(16), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("area IN ('projects', 'library')", name="area_allowed"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folders_owner_area", "folders", ["owner_id", "area"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])
    op.create_table(
        "folder_projects",
        sa.Column("folder_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("folder_id", "project_id"),
    )
    op.create_index("ix_folder_projects_project_id", "folder_projects", ["project_id"])
    op.create_table(
        "folder_songs",
        sa.Column("folder_id", sa.Integer(), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("folder_id", "song_id"),
    )
    op.create_index("ix_folder_songs_song_id", "folder_songs", ["song_id"])
    op.create_table(
        "private_tag_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["tag_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "category_id", "value"),
    )
    op.create_index("ix_private_tag_values_owner_id", "private_tag_values", ["owner_id"])
    op.create_table(
        "project_tags",
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("tag_value_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_value_id"], ["private_tag_values.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "tag_value_id"),
    )
    op.create_index("ix_project_tags_tag_value_id", "project_tags", ["tag_value_id"])
    op.create_table(
        "private_song_tags",
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("tag_value_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_value_id"], ["private_tag_values.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("song_id", "tag_value_id"),
    )
    op.create_index("ix_private_song_tags_tag_value_id", "private_song_tags", ["tag_value_id"])


def downgrade() -> None:
    op.drop_table("private_song_tags")
    op.drop_table("project_tags")
    op.drop_table("private_tag_values")
    op.drop_table("folder_songs")
    op.drop_table("folder_projects")
    op.drop_table("folders")
