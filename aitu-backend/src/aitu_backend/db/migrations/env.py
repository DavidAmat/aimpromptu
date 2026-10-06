"""Alembic's entry point. :func:`aitu_backend.db.database.migrate` sets the URL; the command line
(``alembic`` from ``aitu-backend/``, with ``alembic.ini``) reads it from ``.database/``."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from aitu_backend.db.models import Base
from aitu_backend.storage import paths

config = context.config
url = config.get_main_option("sqlalchemy.url") or f"sqlite:///{paths.sqlite_path()}"

# `render_as_batch`: SQLite cannot alter a column in place, so later revisions copy the table.
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
