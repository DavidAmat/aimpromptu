# AImpromptu — both services from the repo root.
#
#   make serve    start the backend and the frontend, print where they are
#   make stop     shut both down
#   make logs     follow both logs
#   make status   what is running
#
# `serve` starts them in the background and returns your terminal, so closing it
# does not kill them — `make stop` does. Logs go to .run/ and are followed with
# `make logs`.
#
# The frontend port is pinned with --strictPort on purpose. Vite's default is to
# hop to the next free port when 5173 is taken, which is friendly right up until
# you have two copies of the app running and are reading the wrong one. Failing
# loudly is better; run `make stop` or `make serve WEB_PORT=5174`.

.PHONY: serve stop restart status logs logs-web logs-api _start _report

WEB_PORT ?= 5173
API_HOST ?= 127.0.0.1
API_PORT ?= 8765

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
	@echo "  make logs   follow both      make stop   shut down"
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

logs:
	@tail -f $(WEB_LOG) $(API_LOG)

logs-web:
	@tail -f $(WEB_LOG)

logs-api:
	@tail -f $(API_LOG)
