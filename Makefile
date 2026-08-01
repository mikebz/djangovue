# Makefile for djangovue project
# A task runner: every recipe shells out to uv (Python) or npm (frontend).

.DEFAULT_GOAL := help
.NOTPARALLEL:

# .env.example provides defaults; a local .env overrides individual keys.
ENV_FILES := .env.example $(wildcard .env)
-include $(ENV_FILES)

ENV_KEYS := $(shell sed -nE 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/\1/p' $(ENV_FILES) | sort -u)
export $(ENV_KEYS)

# Targets that shell out to uv all depend on the guard below. `run` and `e2e` name
# it in their own rules instead, so it is checked before the frontend is built.
UV_TARGETS := install migrate makemigrations shell lint lint-fix format \
              check typecheck test status collectstatic superuser
$(UV_TARGETS): ensure-uv

# Targets that must render templates against the built manifest rather than
# the Vite dev server. Prerequisites inherit this, so frontend-build sees it too.
run e2e check test: export DJANGO_VITE_DEV_MODE := 0

.PHONY: help ensure-uv setup install run migrate makemigrations shell superuser \
        collectstatic status test e2e check lint lint-fix format typecheck verify \
        frontend-install frontend-dev frontend-watch frontend-preview frontend-build \
        prod-build docker-build docker-run docker-dev clean clean-all

help: ## Show this help message
	@printf "Django + Vue commands\n\n"
	@grep -E '^[a-zA-Z_-]+:.*## ' $(firstword $(MAKEFILE_LIST)) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'

ensure-uv:
	@command -v uv >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2; exit 1; }

# Setup
setup: install frontend-install migrate ## Initial project setup

install: ## Install Python dependencies
	uv sync --extra dev

# Django
run: ensure-uv frontend-build ## Start Django with built frontend assets on a single port
	@echo "Django binds to 0.0.0.0:8000."
	@echo "In a dev container or Codespaces, open the forwarded port URL from the Ports tab."
	@echo "From inside the container, the app is available at http://127.0.0.1:8000/."
	uv run manage runserver 0.0.0.0:8000

migrate: ## Run Django migrations
	uv run manage migrate

makemigrations: ## Create new Django migrations
	uv run manage makemigrations

shell: ## Start Django shell
	uv run manage shell

superuser: ## Create Django superuser
	uv run manage createsuperuser

collectstatic: ## Collect static files
	uv run manage collectstatic --noinput

status: ## Show project status and environment info
	@echo "Project status"
	@echo "Python version: $$(uv run python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Django version: $$(uv run python -c 'import django; print(django.get_version())')"
	@echo "Virtual environment: $$(test -d .venv && echo present || echo missing)"
	@echo "Dependencies: $$(test -f uv.lock && echo locked || echo missing)"
	@echo "Node.js: $$(command -v node >/dev/null 2>&1 && node --version || echo missing)"
	@echo "NPM packages: $$(test -d node_modules && echo installed || echo missing)"

# Checks
check: ## Run Django system checks
	uv run manage check

test: ## Run Django tests
	uv run manage test

e2e: ensure-uv frontend-build ## Run end-to-end checks (template render + server boot)
	uv run manage migrate
	uv run python scripts/e2e_template_check.py
	./scripts/e2e_server_smoke.sh

lint: ## Run code linter (ruff)
	uv run ruff check .
	uv run ruff format --check .
	uv run black --check .

lint-fix: ## Run linter with auto-fix
	uv run ruff check --fix .

format: ## Format code with black
	uv run ruff format .
	uv run black .

typecheck: ## Run static type checking with mypy
	uv run mypy

# Builds the frontend up front: `check` and `test` render templates against the
# manifest, so on a clean checkout they fail without it (CI builds separately).
verify: ensure-uv frontend-build ## Run lint, checks, tests, and e2e used in CI
	$(MAKE) lint typecheck check test e2e

# Frontend
frontend-install: ## Install Node.js dependencies
	npm ci

frontend-dev: ## Start Vite development server
	npm run dev

frontend-watch: ## Watch frontend files for changes
	npm run watch

frontend-preview: ## Preview production build
	npm run preview

BUILD_ARTIFACTS := frontend/dist frontend/dist/.vite/manifest.json

frontend-build: ## Build frontend for production
	npm run build
	@for artifact in $(BUILD_ARTIFACTS); do \
		test -e "$$artifact" || { echo "Frontend build failed - no $$artifact found" >&2; exit 1; }; \
	done

# Production
prod-build: install frontend-build collectstatic ## Build for production

docker-build: ## Build Docker image
	docker build -t djangovue:latest .

docker-run: docker-build ## Build and run Docker container
	docker run --rm -p 8000:8000 djangovue:latest

docker-dev: ## Run development environment in Docker
	docker-compose up --build

# Cleanup
clean: ## Clean up generated files
	find . -type d \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} +
	rm -rf frontend/bundles/*

clean-all: clean ## Clean everything including dependencies
	rm -rf .venv/ node_modules/
	rm -f uv.lock package-lock.json
