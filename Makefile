# Makefile for djangovue project
# Uses UV for Python package management

.PHONY: help install run migrate shell test lint format check clean setup frontend all

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

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
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	uv sync --extra dev

run: ## Start Django development server
	@echo "$(BLUE)Starting Django development server...$(RESET)"
	uv run python manage.py runserver

migrate: ## Run Django migrations
	@echo "$(BLUE)Running Django migrations...$(RESET)"
	uv run python manage.py migrate

makemigrations: ## Create new Django migrations
	@echo "$(BLUE)Creating Django migrations...$(RESET)"
	uv run python manage.py makemigrations

shell: ## Start Django shell
	@echo "$(BLUE)Starting Django shell...$(RESET)"
	uv run python manage.py shell

test: ## Run Django tests
	@echo "$(BLUE)Running tests...$(RESET)"
	uv run python manage.py test

lint: ## Run code linter (ruff)
	@echo "$(BLUE)Running linter...$(RESET)"
	uv run ruff check backend/ djangovue/

lint-fix: ## Run linter with auto-fix
	@echo "$(BLUE)Running linter with auto-fix...$(RESET)"
	uv run ruff check --fix backend/ djangovue/

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(RESET)"
	uv run black backend/ djangovue/

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)Checking code formatting...$(RESET)"
	uv run black --check backend/ djangovue/

check: ## Run Django system checks
	@echo "$(BLUE)Running Django system checks...$(RESET)"
	uv run python manage.py check

status: ## Show project status and environment info
	@echo "$(BLUE)Project Status:$(RESET)"
	@echo "Python version: $$(uv run python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Django version: $$(uv run python -c 'import django; print(django.get_version())')"
	@echo "Virtual environment: $$(if [ -d .venv ]; then echo "✓ Active (.venv)"; else echo "✗ Not found"; fi)"
	@echo "Dependencies: $$(if [ -f uv.lock ]; then echo "✓ Locked (uv.lock)"; else echo "✗ Not locked"; fi)"
	@echo "Node.js: $$(if command -v node >/dev/null 2>&1; then echo "✓ $$(node --version)"; else echo "✗ Not installed"; fi)"
	@echo "NPM packages: $$(if [ -d node_modules ]; then echo "✓ Installed"; else echo "✗ Not installed"; fi)"

collectstatic: ## Collect static files
	@echo "$(BLUE)Collecting static files...$(RESET)"
	uv run python manage.py collectstatic --noinput

superuser: ## Create Django superuser
	@echo "$(BLUE)Creating Django superuser...$(RESET)"
	uv run python manage.py createsuperuser

# Frontend commands
frontend-install: ## Install Node.js dependencies
	@echo "$(BLUE)Installing Node.js dependencies...$(RESET)"
	npm install

frontend-dev: ## Start Vite development server
	@echo "$(BLUE)Starting Vite development server...$(RESET)"
	npm run dev

frontend-build: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(RESET)"
	npm run build

frontend-watch: ## Watch frontend files for changes
	@echo "$(BLUE)Watching frontend files...$(RESET)"
	npm run watch

frontend-preview: ## Preview production build
	@echo "$(BLUE)Starting preview server...$(RESET)"
	npm run preview

# Cleanup commands
clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf frontend/bundles/*

clean-all: clean ## Clean everything including dependencies
	@echo "$(BLUE)Cleaning everything...$(RESET)"
	rm -rf .venv/
	rm -rf node_modules/
	rm -f uv.lock
	rm -f package-lock.json

# Development setup
setup: install frontend-install migrate ## Initial project setup
	@echo "$(GREEN)Project setup complete!$(RESET)"
	@echo "Run '$(YELLOW)make dev$(RESET)' to start development"

dev: migrate frontend-build ## Prepare for development
	@echo "$(GREEN)Development environment ready!$(RESET)"
	@echo "Run '$(YELLOW)make run$(RESET)' to start the server"

dev-full: frontend-build run ## Build frontend and start Django server
	@echo "$(GREEN)Starting full development environment...$(RESET)"

all: setup ## Setup everything and start development server
	@echo "$(GREEN)Starting development server...$(RESET)"
	make run

# Quality assurance
qa: lint-fix format test check ## Run all quality checks and fixes
	@echo "$(GREEN)All quality checks passed!$(RESET)"

# Production commands
prod-build: install frontend-build collectstatic ## Build for production
	@echo "$(GREEN)Production build complete!$(RESET)"

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(RESET)"
	docker build -t djangovue:latest .

docker-run: docker-build ## Build and run Docker container
	@echo "$(BLUE)Running Docker container...$(RESET)"
	docker run --rm -p 8000:8000 djangovue:latest

docker-dev: ## Run development environment in Docker
	@echo "$(BLUE)Starting development environment in Docker...$(RESET)"
	docker-compose up --build
