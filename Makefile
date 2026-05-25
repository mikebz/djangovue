# Makefile for djangovue project
# Uses uv for Python package management

.PHONY: help install run migrate makemigrations shell test e2e lint lint-fix format check typecheck verify clean setup frontend-install frontend-dev frontend-watch frontend-preview collectstatic superuser clean-all frontend-build prod-build docker-build docker-run docker-dev status

.DEFAULT_GOAL := help

ENV_FILES := .env.example $(wildcard .env)
-include $(ENV_FILES)

ENV_KEYS := $(shell sed -nE 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/\1/p' $(ENV_FILES) | sort -u)
export $(ENV_KEYS)

ensure-python-tools:
	@command -v uv >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2; exit 1; }

help: ## Show this help message
	@printf "Django + Vue commands\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ensure-python-tools ## Install Python dependencies
	uv sync --extra dev

run: export DJANGO_VITE_DEV_MODE := 0
run: ensure-python-tools frontend-build ## Start Django with built frontend assets on a single port
	@echo "Django binds to 0.0.0.0:8000."
	@echo "In a dev container or Codespaces, open the forwarded port URL from the Ports tab."
	@echo "From inside the container, the app is available at http://127.0.0.1:8000/."
	uv run python manage.py runserver 0.0.0.0:8000

migrate: ensure-python-tools ## Run Django migrations
	uv run python manage.py migrate

makemigrations: ensure-python-tools ## Create new Django migrations
	uv run python manage.py makemigrations

shell: ensure-python-tools ## Start Django shell
	uv run python manage.py shell

e2e: export DJANGO_VITE_DEV_MODE := 0
e2e: ensure-python-tools frontend-build ## Run end-to-end checks (template render + server boot)
	uv run python manage.py migrate
	uv run python scripts/e2e_template_check.py
	./scripts/e2e_server_smoke.sh

lint: ensure-python-tools ## Run code linter (ruff)
	uv run ruff check .
	uv run ruff format --check .
	uv run black --check .

lint-fix: ensure-python-tools ## Run linter with auto-fix
	uv run ruff check --fix .

format: ensure-python-tools ## Format code with black
	uv run ruff format .
	uv run black .

check: export DJANGO_VITE_DEV_MODE := 0
check: ensure-python-tools ## Run Django system checks
	uv run python manage.py check

typecheck: ensure-python-tools ## Run static type checking with mypy
	uv run python -m mypy

test: export DJANGO_VITE_DEV_MODE := 0
test: ensure-python-tools ## Run Django tests
	uv run python manage.py test

verify: ## Run lint, checks, tests, and e2e used in CI
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) check
	$(MAKE) test
	$(MAKE) e2e

status: ensure-python-tools ## Show project status and environment info
	@echo "Project status"
	@echo "Python version: $$(uv run python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Django version: $$(uv run python -c 'import django; print(django.get_version())')"
	@echo "Virtual environment: $$(test -d .venv && echo present || echo missing)"
	@echo "Dependencies: $$(test -f uv.lock && echo locked || echo missing)"
	@echo "Node.js: $$(command -v node >/dev/null 2>&1 && node --version || echo missing)"
	@echo "NPM packages: $$(test -d node_modules && echo installed || echo missing)"

collectstatic: ensure-python-tools ## Collect static files
	uv run python manage.py collectstatic --noinput

superuser: ensure-python-tools ## Create Django superuser
	uv run python manage.py createsuperuser

# Frontend commands
frontend-install: ## Install Node.js dependencies
	npm ci

frontend-dev: ## Start Vite development server
	npm run dev

frontend-watch: ## Watch frontend files for changes
	npm run watch

frontend-preview: ## Preview production build
	npm run preview

# Cleanup commands
clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf frontend/bundles/*

clean-all: clean ## Clean everything including dependencies
	rm -rf .venv/
	rm -rf node_modules/
	rm -f uv.lock
	rm -f package-lock.json

# Development setup
setup: install frontend-install migrate ## Initial project setup

# Production commands
frontend-build: ## Build frontend for production
	npm run build
	@if [ ! -d "frontend/dist" ]; then \
		echo "Frontend build failed - no dist directory found"; \
		exit 1; \
	fi
	@if [ ! -f "frontend/dist/.vite/manifest.json" ]; then \
		echo "Frontend build failed - no manifest.json found"; \
		exit 1; \
	fi

prod-build: install frontend-build collectstatic ## Build for production

docker-build: ## Build Docker image
	docker build -t djangovue:latest .

docker-run: docker-build ## Build and run Docker container
	docker run --rm -p 8000:8000 djangovue:latest

docker-dev: ## Run development environment in Docker
	docker-compose up --build
