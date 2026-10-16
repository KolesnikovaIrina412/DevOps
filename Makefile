.PHONY: help setup run test quality migrate backup restore verify deploy

ifeq ($(OS),Windows_NT)
    VENV_BIN = .venv/Scripts
    PYTHON = python
    CP = copy
    NULL = NUL
else
    VENV_BIN = .venv/bin
    PYTHON = python3
    CP = cp
    NULL = /dev/null
endif

help:
	@echo "Available commands:"
	@echo ""
	@echo "Local development:"
	@echo "  make setup     - initial setup (venv, dependencies, .env)"
	@echo "  make run       - run the application locally"
	@echo "  make test      - run tests with coverage report"
	@echo "  make quality   - run linter (flake8) and SAST (bandit)"
	@echo "  make migrate   - apply Alembic migrations (as DB owner)"
	@echo "  make verify    - full local check (test + quality + migrate)"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy    - deploy the application on the server"
	@echo ""
	@echo "Database (db-server):"
	@echo "  make backup    - create a database backup"
	@echo "  make restore   - restore the database from a backup"
	@echo ""
	@echo "Common:"
	@echo "  make help      - this help"


setup:
	@echo "[setup] Creating virtual environment..."
	$(PYTHON) -m venv .venv
	@echo "[setup] Installing dependencies..."
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "[setup] Setting up .env..."
	@if [ ! -f .env ]; then $(CP) .env.example .env && echo "  Created .env from .env.example (edit it!)"; fi
	@echo "[setup] Done."

run:
	@echo "[run] Starting application..."
	$(VENV_BIN)/python app.py

test:
	@echo "[test] Running tests with coverage..."
	$(VENV_BIN)/pytest
	@echo "[test] HTML report: htmlcov/index.html"

quality:
	@echo "[quality] flake8..."
	$(VENV_BIN)/flake8 . --max-line-length=120 --exclude=.venv,tests,__pycache__,migrations
	@echo "[quality] bandit..."
	$(VENV_BIN)/bandit -r . -x ./.venv,./tests,./migrations -q
	@echo "[quality] Done."

# DDL-миграции требуют прав владельца схемы (postgres).
# Используем MIGRATION_DATABASE_URL из .env, а если он не задан — DATABASE_URL.
# .env не читается make автоматически, поэтому подгружаем его через `set -a`.
migrate:
	@echo "[migrate] Applying Alembic migrations..."
	@set -a; . ./.env; set +a; \
	 : "$${DATABASE_URL:?DATABASE_URL is not set in .env}"; \
	 DATABASE_URL="$${MIGRATION_DATABASE_URL:-$$DATABASE_URL}" $(VENV_BIN)/alembic upgrade head
	@echo "[migrate] Current version:"
	@set -a; . ./.env; set +a; \
	 DATABASE_URL="$${MIGRATION_DATABASE_URL:-$$DATABASE_URL}" $(VENV_BIN)/alembic current

verify: test quality migrate
	@echo ""
	@echo "==========================================="
	@echo "  All checks passed successfully."
	@echo "==========================================="


deploy:
	@bash scripts/deploy.sh

backup:
	@bash scripts/backup.sh

restore:
	@DUMP="$(DUMP)" DB="$(DB)" bash scripts/restore.sh