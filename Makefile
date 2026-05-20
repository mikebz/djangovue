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

# Default Django env values for local commands.
# CI can override these values via workflow env blocks.
SECRET_KEY ?= dev-secret-key-change-me
DEBUG ?= 1
ALLOWED_HOSTS ?= localhost,127.0.0.1
DJANGO_ENV := SECRET_KEY=$(SECRET_KEY) DEBUG=$(DEBUG) ALLOWED_HOSTS=$(ALLOWED_HOSTS)

UV_BIN := $(shell command -v uv 2>/dev/null)
ifeq ($(UV_BIN),)
PYTHON_RUN := .venv/bin/python
RUFF_RUN := .venv/bin/ruff
BLACK_RUN := .venv/bin/black
else
PYTHON_RUN := uv run python
RUFF_RUN := uv run ruff
BLACK_RUN := uv run black
endif

ensure-python-tools:
	@if [ -n "$(UV_BIN)" ] || [ -x .venv/bin/python ]; then \
		exit 0; \
	fi
	@echo "Missing Python toolchain: install uv or create .venv first." >&2
	@echo "Try: make install" >&2
	@exit 1

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
	@if [ -n "$(UV_BIN)" ]; then \
		uv sync --extra dev; \
	else \
		python3 -m venv .venv; \
		.venv/bin/pip install --upgrade pip; \
		.venv/bin/pip install -e .[dev]; \
	fi

run: ## Start Django development server
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py runserver

migrate: ## Run Django migrations
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py migrate

makemigrations: ## Create new Django migrations
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py makemigrations

shell: ## Start Django shell
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py shell

test: ## Run Django tests
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py test

test-all: ## Run all unit/integration tests
	$(MAKE) check
	$(MAKE) test
	$(MAKE) e2e

lint: ## Run code linter (ruff)
	$(MAKE) ensure-python-tools
	$(RUFF_RUN) check .
	$(RUFF_RUN) format --check .
	$(BLACK_RUN) --check .

lint-all: lint ## Run all lint checks

lint-fix: ## Run linter with auto-fix
	$(MAKE) ensure-python-tools
	$(RUFF_RUN) check --fix .

format: ## Format code with black
	$(MAKE) ensure-python-tools
	$(RUFF_RUN) format .
	$(BLACK_RUN) .

format-check: ## Check code formatting without making changes
	$(MAKE) ensure-python-tools
	$(RUFF_RUN) format --check .
	$(BLACK_RUN) --check .

check: ## Run Django system checks
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py check

status: ## Show project status and environment info
	@echo "$(BLUE)Project Status:$(RESET)"
	@echo "Python version: $$($(PYTHON_RUN) --version)"
	@echo "UV version: $$(if [ -n \"$(UV_BIN)\" ]; then uv --version; else echo \"not installed\"; fi)"
	@echo "Django version: $$($(PYTHON_RUN) -c 'import django; print(django.get_version())')"
	@echo "Virtual environment: $$(if [ -d .venv ]; then echo "✓ Active (.venv)"; else echo "✗ Not found"; fi)"
	@echo "Dependencies: $$(if [ -f uv.lock ]; then echo "✓ Locked (uv.lock)"; else echo "✗ Not locked"; fi)"
	@echo "Node.js: $$(if command -v node >/dev/null 2>&1; then echo "✓ $$(node --version)"; else echo "✗ Not installed"; fi)"
	@echo "NPM packages: $$(if [ -d node_modules ]; then echo "✓ Installed"; else echo "✗ Not installed"; fi)"

collectstatic: ## Collect static files
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py collectstatic --noinput

superuser: ## Create Django superuser
	$(MAKE) ensure-python-tools
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py createsuperuser

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
	$(DJANGO_ENV) $(PYTHON_RUN) manage.py migrate
	$(DJANGO_ENV) $(PYTHON_RUN) scripts/e2e_template_check.py
	$(DJANGO_ENV) ./scripts/e2e_server_smoke.sh

verify: ## Run the same lint, checks, tests, and e2e used in CI
	$(MAKE) lint
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
