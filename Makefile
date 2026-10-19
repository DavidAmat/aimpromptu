# AImpromptu — both services from the repo root.
#
# In containers, on the Ubuntu machine (implementation 08, Phase 3). This is the usual way:
#
#   make up             build if needed, start the backend (GPU) and the frontend, wait for both
#   make down           stop both
#   make logs           follow both logs
#   make ps             what is running
#   make test-backend   the backend tests, inside the backend image (ARGS="-k pmn" to filter)
#   make shell-backend  a shell in the running backend container
#   make build          rebuild both images (after a change of uv.lock, package-lock.json or
#                       vexflow-v2)
#
# `.database/` (implementation 02, plan section 8.7), on the host (they need tar with zstd):
#
#   make db-backup      .database-YYYYMMDD-HHMMSS.tar.zst beside .database/, safe while the app runs
#   make db-restore FILE=.database-....tar.zst   into an empty .database/
#   make db-check       the tables against the bundles and the audio store (HASHES=1: hash every file)
#   make db-reindex     the rows of the projects and the audio again, from the bundles on disk
#
# Natively, without containers:
#
#   make serve        start the backend and the frontend, print where they are
#   make stop         shut both down
#   make logs-native  follow both logs
#   make status       what is running
#
# Both ways use the same two ports, 5173 and 8765, so `make up` stops the native servers first.
#
# `serve` starts them in the background and returns your terminal, so closing it
# does not kill them — `make stop` does. Logs go to .run/ and are followed with
# `make logs-native`.
#
# The frontend port is pinned with --strictPort on purpose. Vite's default is to
# hop to the next free port when 5173 is taken, which is friendly right up until
# you have two copies of the app running and are reading the wrong one. Failing
# loudly is better; run `make stop` or `make serve WEB_PORT=5174`.

.PHONY: serve stop restart status logs-native logs-web logs-api _start _report \
	up down logs ps build test-backend shell-backend _database db-backup db-restore db-check db-reindex \
	public-import popularity-check regional-download regional-build regional-import \
	popularity-collect popularity-fit popularity-infer popularity-refresh genres-measure genres-import

WEB_PORT ?= 5173
API_HOST ?= $(or $(AITU_HOST),127.0.0.1)
API_PORT ?= $(or $(AITU_PORT),8765)

RUN_DIR := .run
WEB_LOG := $(RUN_DIR)/web.log
API_LOG := $(RUN_DIR)/api.log
WEB_PID := $(RUN_DIR)/web.pid
API_PID := $(RUN_DIR)/api.pid

# Seconds to wait for a server to answer before giving up and showing its log.
TIMEOUT ?= 60

serve: stop _start _report

_start:
	@mkdir -p $(RUN_DIR)
	@echo "starting backend  → http://$(API_HOST):$(API_PORT)"
	@cd aitu-backend && nohup uv run python -m uvicorn aitu_backend.main:app \
		--host $(API_HOST) --port $(API_PORT) --reload \
		> ../$(API_LOG) 2>&1 & echo $$! > $(API_PID)
	@echo "starting frontend → http://localhost:$(WEB_PORT)"
	@cd aitu-frontend && nohup npm run dev -- --port $(WEB_PORT) --strictPort \
		> ../$(WEB_LOG) 2>&1 & echo $$! > $(WEB_PID)

# Wait for both to actually answer, then show the frontend's own banner. A URL
# printed before the server is listening is a URL you click too early.
_report:
	@printf "waiting for the backend "; \
	for i in $$(seq 1 $(TIMEOUT)); do \
		if curl -fsS "http://$(API_HOST):$(API_PORT)/health" >/dev/null 2>&1; then \
			printf " up\n"; break; \
		fi; \
		if [ $$i -eq $(TIMEOUT) ]; then \
			printf " FAILED\n\n--- $(API_LOG) ---\n"; tail -30 $(API_LOG); exit 1; \
		fi; \
		printf "."; sleep 1; \
	done
	@printf "waiting for the frontend"; \
	for i in $$(seq 1 $(TIMEOUT)); do \
		if grep -q "ready in\|Local:" $(WEB_LOG) 2>/dev/null; then printf " up\n"; break; fi; \
		if grep -qi "error\|EADDRINUSE" $(WEB_LOG) 2>/dev/null; then \
			printf " FAILED\n\n--- $(WEB_LOG) ---\n"; tail -30 $(WEB_LOG); exit 1; \
		fi; \
		if [ $$i -eq $(TIMEOUT) ]; then \
			printf " FAILED\n\n--- $(WEB_LOG) ---\n"; tail -30 $(WEB_LOG); exit 1; \
		fi; \
		printf "."; sleep 1; \
	done
	@echo ""
	@echo "──────────────── vite ────────────────"
	@sed -n '/VITE/,/^$$/p' $(WEB_LOG) | sed '/^$$/d' || true
	@echo "──────────────────────────────────────"
	@echo ""
	@echo "  app       http://localhost:$(WEB_PORT)"
	@echo "  api       http://$(API_HOST):$(API_PORT)"
	@echo "  api docs  http://$(API_HOST):$(API_PORT)/docs"
	@echo ""
	@echo "  make logs-native   follow both      make stop   shut down"
	@echo ""

# Two ways of stopping, because either alone leaves something behind. The PID
# files catch the process trees we started (npm forks vite, uvicorn --reload
# forks a worker, and killing only the parent orphans the child). The port sweep
# catches anything from an earlier run whose PID file is stale or gone.
stop:
	@if [ -f $(WEB_PID) ] || [ -f $(API_PID) ]; then echo "stopping…"; fi
	@for f in $(WEB_PID) $(API_PID); do \
		[ -f $$f ] || continue; \
		pid=$$(cat $$f 2>/dev/null); \
		if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
			for child in $$(pgrep -P $$pid 2>/dev/null); do kill $$child 2>/dev/null || true; done; \
			kill $$pid 2>/dev/null || true; \
		fi; \
		rm -f $$f; \
	done
	@sleep 1
	@for port in $(WEB_PORT) $(API_PORT); do \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pids" ]; then kill $$pids 2>/dev/null || true; fi; \
	done
	@sleep 1
	@for port in $(WEB_PORT) $(API_PORT); do \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pids" ]; then kill -9 $$pids 2>/dev/null || true; fi; \
	done

restart: serve

status:
	@for entry in "frontend:$(WEB_PORT)" "backend:$(API_PORT)"; do \
		name=$${entry%%:*}; port=$${entry##*:}; \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "  $$name  running on $$port (pid $$(echo $$pids | tr '\n' ' '))"; \
		else \
			echo "  $$name  not running"; \
		fi; \
	done

logs-native:
	@tail -f $(WEB_LOG) $(API_LOG)

logs-web:
	@tail -f $(WEB_LOG)

logs-api:
	@tail -f $(API_LOG)

# ------------------------------------------------------------------ containers
#
# `.env` is optional and Compose reads it itself. The Makefile needs only the cache folder from it,
# and reads that one line: including the whole file would let an empty `WEB_PORT=` blank out the
# default above. The ids are passed so the images write files as the host user, not as root.

export UID := $(shell id -u)
export GID := $(shell id -g)
CACHE_DIR := $(or $(AITU_CACHE_DIR),$(shell sed -n 's/^AITU_CACHE_DIR=//p' .env 2>/dev/null),/mnt/ssd2/aimpromptu/home)
DATABASE_DIR := $(shell sed -n 's/^AITU_DATABASE_DIR=//p' .env 2>/dev/null)
export AITU_DATABASE_DIR := $(DATABASE_DIR)
COMPOSE := docker compose

# The cache folder must exist before Docker mounts it, or Docker creates it as root.
# --renew-anon-volumes: the frontend keeps its node_modules in an anonymous volume, and without the
# flag a rebuilt image would still see the old packages.
# The database folder must exist before Docker mounts it, or Docker creates it as root.
# On this machine it is AITU_DATABASE_DIR in .env (/mnt/ssd2/aimpromptu/.database), not a link
# inside the repository.
up: stop _database
	@mkdir -p "$(CACHE_DIR)"
	$(COMPOSE) up -d --build --renew-anon-volumes --wait
	@echo ""
	@echo "  app       http://localhost:$(WEB_PORT)   (from the Mac: http://ubuntu:$(WEB_PORT); sign in)"
	@echo "  api       http://127.0.0.1:$(API_PORT)   (on this machine; the page uses /api)"
	@echo ""
	@echo "  make logs   follow both      make down   stop both"
	@echo ""

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

_database:
	@if [ -n "$(AITU_DATABASE_DIR)" ]; then mkdir -p "$(AITU_DATABASE_DIR)"; else mkdir -p .database; fi

test-backend: _database
	$(COMPOSE) run --rm --no-deps backend python -m pytest $(ARGS)

shell-backend:
	$(COMPOSE) exec backend bash

# ------------------------------------------------------------------- .database

# `--no-sync`: the local environment keeps the extras it was made with (the engines).
DB_TOOLS := cd aitu-backend && uv run --no-sync python -m aitu_backend.db.tools

db-backup:
	$(DB_TOOLS) backup

db-restore:
	@test -n "$(FILE)" || (echo "usage: make db-restore FILE=.database-YYYYMMDD-HHMMSS.tar.zst"; exit 1)
	$(DB_TOOLS) restore $(abspath $(FILE))

db-check:
	$(DB_TOOLS) check $(if $(HASHES),--hashes,)

db-reindex:
	$(DB_TOOLS) reindex

# ------------------------------------------------------------- the Public Library

# The downloaded music library into public rows (implementation 02, Phase 12; run for real in
# Phase 13). On the host: the download is beside the repository, not in the containers.
# `ARGS="--database DIR"` writes into another .database/ folder (a copy); `--no-seed`.
public-import:
	cd aitu-backend && uv run --no-sync python -m aitu_backend.library.public_import $(ARGS)

# The `spain` and `catalan` regions (Phase 16, context/music-library/regional-sources.md). The
# download is paced and resumable (`SOURCE=spanishcharts`, `los40`, `kworb`, `apecat`, `wikipedia`);
# the build reads the saved pages into one database per source; the import writes the public rows
# and each song's popularity per region (`ARGS="--database DIR"`: a copy). All three on the host.
regional-download:
	python3 scripts/music-library-regions/download.py $(SOURCE)

regional-build:
	python3 scripts/music-library-regions/build.py all

regional-import:
	cd aitu-backend && uv run --no-sync python -m aitu_backend.library.regional_import $(ARGS)

# The inferred popularity (Phase 17, context/music-library/popularity.md section 6), on the host,
# with the keys of `.env`. Collect reads each song's official video and Spotify streams into
# song_signals (`SONGS="12 34"`, else every song with a free video id; within the day's quota);
# fit measures the candidate relations and writes the plots (`OUT=DIR`), and writes nothing else.
# infer gives every song with no chart value in a region its inferred popularity (`SONGS="..."`:
# only those; the searches it needs stop at the day's 100, run it again the next day); refresh
# reads every kept view count again before 30 days pass (the YouTube policy): run it monthly.
# `ARGS="--database DIR"`: a copy.
popularity-collect:
	cd aitu-backend && set -a && . ../.env && set +a && \
		uv run --no-sync python -m aitu_backend.library.inferred $(ARGS) collect $(if $(SONGS),--songs $(SONGS))

popularity-fit:
	cd aitu-backend && set -a && . ../.env && set +a && \
		uv run --no-sync python -m aitu_backend.library.inferred $(ARGS) fit $(if $(OUT),--out $(OUT))

popularity-infer:
	cd aitu-backend && set -a && . ../.env && set +a && \
		uv run --no-sync python -m aitu_backend.library.inferred $(ARGS) infer $(if $(SONGS),--songs $(SONGS))

popularity-refresh:
	cd aitu-backend && set -a && . ../.env && set +a && \
		uv run --no-sync python -m aitu_backend.library.inferred $(ARGS) refresh

# The genres and tags from Wikidata (Phase 18, context/music-library/genres.md): the measure reads
# QLever's copy of Wikidata (every answer kept in data/music-library-genres/) and prints the counts
# and the proposed map; writes nothing. The import writes at most two genres a song and the film
# tags as public rows, safe to run again; a song an accepted request named is left alone
# (`ARGS="--database DIR"`: a copy). On the host.
genres-measure:
	cd aitu-backend && uv run --no-sync python -m aitu_backend.library.genres $(ARGS) measure $(if $(OUT),--out $(OUT))

genres-import:
	cd aitu-backend && uv run --no-sync python -m aitu_backend.library.genres $(ARGS) import

# The objective criteria of the popularity (Q-6), for the plan's weights and the app's, measured on
# the downloaded chart history; writes nothing.
popularity-check:
	cd aitu-backend && uv run --no-sync python -m aitu_backend.library.popularity check
