# Video Composition API Makefile

.PHONY: help install install-dev test lint format run dev build up down logs clean

# Variables
PYTHON := python
PIP := pip
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DEV := docker-compose -f docker-compose.dev.yml

help: ## Show this help message
@echo "Video Composition API - Available commands:"
@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
$(PIP) install -r requirements.txt -r requirements-dev.txt
pre-commit install

test: ## Run tests
pytest tests/ -v --cov=./ --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
pytest tests/ -v

lint: ## Run linting checks
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
mypy .

format: ## Format code
black .
isort .

format-check: ## Check code formatting
black --check .
isort --check-only .

run: ## Run the API locally
$(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dev: ## Run development environment with Docker
$(DOCKER_COMPOSE_DEV) up --build

build: ## Build production Docker image
docker build -t video-composition-api .

up: ## Start production environment
$(DOCKER_COMPOSE) up -d

up-build: ## Build and start production environment
$(DOCKER_COMPOSE) up --build -d

down: ## Stop all services
$(DOCKER_COMPOSE) down
$(DOCKER_COMPOSE_DEV) down

logs: ## View logs from all services
$(DOCKER_COMPOSE) logs -f

logs-api: ## View API logs only
$(DOCKER_COMPOSE) logs -f api

shell: ## Open a shell in the API container
$(DOCKER_COMPOSE) exec api bash

db-shell: ## Open a database shell
$(DOCKER_COMPOSE) exec postgres psql -U postgres -d video_composition

redis-cli: ## Open Redis CLI
$(DOCKER_COMPOSE) exec redis redis-cli

clean: ## Clean up development environment
$(DOCKER_COMPOSE) down -v
$(DOCKER_COMPOSE_DEV) down -v
docker system prune -f

clean-all: ## Clean up everything including images
$(DOCKER_COMPOSE) down -v --rmi all
$(DOCKER_COMPOSE_DEV) down -v --rmi all
docker system prune -af

migrate: ## Run database migrations (if using Alembic)
alembic upgrade head

migrate-create: ## Create new migration
alembic revision --autogenerate -m "$(MESSAGE)"

backup-db: ## Backup PostgreSQL database
$(DOCKER_COMPOSE) exec postgres pg_dump -U postgres video_composition > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore PostgreSQL database (specify BACKUP_FILE)
$(DOCKER_COMPOSE) exec -T postgres psql -U postgres video_composition < $(BACKUP_FILE)

security-check: ## Run security checks
safety check
bandit -r . -f json

docs: ## Generate documentation
@echo "API documentation available at http://localhost:8000/docs when running"

# Development quality checks
pre-commit: format lint test ## Run all pre-commit checks

# CI/CD related
ci-test: ## Run tests in CI environment
pytest tests/ -v --cov=./ --cov-report=xml

# Environment setup
setup-dev: install-dev ## Setup development environment
@echo "Creating .env file from example..."
@if not exist .env copy .env.example .env
@echo "Development environment setup complete!"
@echo "Edit .env file with your configuration before running 'make dev'"

# Quick start
quickstart: setup-dev dev ## Setup and start development environment
