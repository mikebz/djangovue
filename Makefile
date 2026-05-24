# Makefile for djangovue project
# Uses UV for Python package management

.PHONY: help install run migrate shell test test-all e2e lint lint-all format format-check check verify clean setup frontend all

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Load defaults from .env.example, then let .env override when present.
# Neither file is ever created as a side effect.
ENV_FILES := .env.example $(wildcard .env)
-include $(ENV_FILES)

# Export all KEY=VALUE entries found in loaded env files.
ENV_KEYS := $(shell sed -nE 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/\1/p' $(ENV_FILES) | sort -u)
export $(ENV_KEYS)

ensure-python-tools:
	@if command -v uv >/dev/null 2>&1; then \
		exit 0; \
	else \
		echo "uv is required to run Python commands in this project." >&2; \
		echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2; \
		exit 1; \
	fi

help: ## Show this help message
	@echo "$(BLUE)Django + Vue Development Commands$(RESET)"
	@echo ""
	@echo "$(GREEN)Python/Django:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(install|run|migrate|shell|test|lint|format|check|clean|setup|status)"
	@echo ""
	@echo "$(GREEN)Frontend:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(frontend-|build|watch|preview)"
	@echo ""
	@echo "$(GREEN)Compound commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(all|dev)"
	@echo ""
	@echo "$(BLUE)UV Commands:$(RESET)"
	@echo "  uv run python manage.py <command>  # Run Django commands"
	@echo "  uv add <package>                   # Add production dependency"
	@echo "  uv add --dev <package>             # Add development dependency"

install: ## Install Python dependencies
	$(MAKE) ensure-python-tools
	uv sync --extra dev

run: ## Start Django development server
	$(MAKE) ensure-python-tools
	uv run python manage.py runserver

migrate: ## Run Django migrations
	$(MAKE) ensure-python-tools
	uv run python manage.py migrate

makemigrations: ## Create new Django migrations
	$(MAKE) ensure-python-tools
	uv run python manage.py makemigrations

shell: ## Start Django shell
	$(MAKE) ensure-python-tools
	uv run python manage.py shell

test: ## Run Django tests
	$(MAKE) ensure-python-tools
	uv run python manage.py test

test e2e: export DJANGO_VITE_DEV_MODE := 0

test-all: ## Run all unit/integration tests
	$(MAKE) check
	$(MAKE) test
	$(MAKE) e2e

lint: ## Run code linter (ruff)
	$(MAKE) ensure-python-tools
	uv run ruff check .
	uv run ruff format --check .
	uv run black --check .

lint-all: lint ## Run all lint checks

lint-fix: ## Run linter with auto-fix
	$(MAKE) ensure-python-tools
	uv run ruff check --fix .

format: ## Format code with black
	$(MAKE) ensure-python-tools
	uv run ruff format .
	uv run black .

format-check: ## Check code formatting without making changes
	$(MAKE) ensure-python-tools
	uv run ruff format --check .
	uv run black --check .

check: ## Run Django system checks
	$(MAKE) ensure-python-tools
	uv run python manage.py check

typecheck: ## Run static type checking with mypy
	$(MAKE) ensure-python-tools
	uv run python -m mypy

status: ## Show project status and environment info
	@echo "$(BLUE)Project Status:$(RESET)"
	@echo "Python version: $$(uv run python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Django version: $$(uv run python -c 'import django; print(django.get_version())')"
	@echo "Virtual environment: $$(if [ -d .venv ]; then echo "✓ Present (.venv)"; else echo "✗ Not found"; fi)"
	@echo "Dependencies: $$(if [ -f uv.lock ]; then echo "✓ Locked (uv.lock)"; else echo "✗ Not locked"; fi)"
	@echo "Node.js: $$(if command -v node >/dev/null 2>&1; then echo "✓ $$(node --version)"; else echo "✗ Not installed"; fi)"
	@echo "NPM packages: $$(if [ -d node_modules ]; then echo "✓ Installed"; else echo "✗ Not installed"; fi)"

collectstatic: ## Collect static files
	$(MAKE) ensure-python-tools
	uv run python manage.py collectstatic --noinput

superuser: ## Create Django superuser
	$(MAKE) ensure-python-tools
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

dev: migrate frontend-build ## Prepare for development

dev-full: frontend-build run ## Build frontend and start Django server

all: setup ## Setup everything and start development server
	make run

# Quality assurance
qa: lint-fix format test check ## Run all quality checks and fixes

e2e: frontend-build ## Run end-to-end checks (template render + server boot)
	$(MAKE) ensure-python-tools
	uv run python manage.py migrate
	uv run python scripts/e2e_template_check.py
	./scripts/e2e_server_smoke.sh

verify: ## Run the same lint, checks, tests, and e2e used in CI
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) check
	$(MAKE) test
	$(MAKE) e2e

frontend-build: ## Build frontend for production
	npm run build
	if [ ! -d "frontend/dist" ]; then \
		echo "Frontend build failed - no dist directory found"; \
		exit 1; \
	fi
	if [ ! -f "frontend/dist/.vite/manifest.json" ]; then \
		echo "Frontend build failed - no manifest.json found"; \
		exit 1; \
	fi

# Production commands
prod-build: install frontend-build collectstatic ## Build for production

docker-build: ## Build Docker image
	docker build -t djangovue:latest .

docker-run: docker-build ## Build and run Docker container
	docker run --rm -p 8000:8000 djangovue:latest

docker-dev: ## Run development environment in Docker
	docker-compose up --build
