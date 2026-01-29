# ============================================================================
# Makefile - Development Commands
# ============================================================================
# This Makefile provides convenient shortcuts for common development tasks

.PHONY: help install install-dev format lint type-check test coverage clean pre-commit-install pre-commit-run all-checks

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================
help: ## Show this help message
	@echo "Bioloupe Development Commands"
	@echo "=============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation
# ============================================================================
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# ============================================================================
# Code Quality
# ============================================================================
format: ## Format code with Black and isort
	@echo "Running Black..."
	black src/ tests/
	@echo "Running isort..."
	isort src/ tests/
	@echo "✓ Code formatting complete!"

format-check: ## Check code formatting without making changes
	@echo "Checking Black formatting..."
	black --check src/ tests/
	@echo "Checking isort formatting..."
	isort --check-only src/ tests/
	@echo "✓ Format check complete!"

lint: ## Run linting with Flake8
	@echo "Running Flake8..."
	flake8 src/ tests/
	@echo "✓ Linting complete!"

lint-ruff: ## Run linting with Ruff (faster alternative)
	@echo "Running Ruff..."
	ruff check src/ tests/
	@echo "✓ Ruff linting complete!"

type-check: ## Run static type checking with MyPy
	@echo "Running MyPy..."
	mypy src/
	@echo "✓ Type checking complete!"

security: ## Run security checks with Bandit
	@echo "Running Bandit..."
	bandit -r src/ -c pyproject.toml
	@echo "✓ Security scan complete!"

# ============================================================================
# Testing
# ============================================================================
test: ## Run tests with pytest
	@echo "Running tests..."
	pytest
	@echo "✓ Tests complete!"

test-fast: ## Run tests without coverage
	@echo "Running tests (fast mode)..."
	pytest --no-cov
	@echo "✓ Fast tests complete!"

test-verbose: ## Run tests with verbose output
	@echo "Running tests (verbose)..."
	pytest -vv
	@echo "✓ Verbose tests complete!"

coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated!"
	@echo "Open htmlcov/index.html to view detailed coverage report"

coverage-report: ## Open coverage report in browser
	@echo "Opening coverage report..."
	xdg-open htmlcov/index.html 2>/dev/null || open htmlcov/index.html 2>/dev/null || echo "Please open htmlcov/index.html manually"

# ============================================================================
# Pre-commit
# ============================================================================
pre-commit-install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Pre-commit hooks installed!"

pre-commit-run: ## Run pre-commit on all files
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files
	@echo "✓ Pre-commit checks complete!"

pre-commit-update: ## Update pre-commit hooks
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate
	@echo "✓ Pre-commit hooks updated!"

# ============================================================================
# Combined Checks
# ============================================================================
all-checks: format lint type-check security test ## Run all quality checks
	@echo "✓ All checks passed!"

ci-checks: format-check lint type-check security test ## Run CI checks (no auto-format)
	@echo "✓ All CI checks passed!"

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove generated files and caches
	@echo "Cleaning up..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	@echo "✓ Cleanup complete!"

clean-all: clean ## Remove all generated files including venv
	rm -rf .venv
	rm -rf venv
	@echo "✓ Deep cleanup complete!"

# ============================================================================
# Development Server
# ============================================================================
dev: ## Run development server
	python run.py

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

# ============================================================================
# Database
# ============================================================================
migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-downgrade: ## Downgrade database by one migration
	alembic downgrade -1

# ============================================================================
# Quick Start
# ============================================================================
setup: install-dev pre-commit-install ## Complete development setup
	@echo "✓ Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Configure your environment variables"
	@echo "  2. Run 'make docker-up' to start services"
	@echo "  3. Run 'make migrate' to setup database"
	@echo "  4. Run 'make dev' to start development server"
	@echo "  5. Run 'make test' to verify everything works"
