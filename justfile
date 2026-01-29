set shell := ["powershell.exe", "-Command"]

# List all available commands
default:
    @just --list

# Lint, format and sort imports (using ruff)
lint:
    @Write-Host "Linting, formatting and sorting imports..." -ForegroundColor Cyan
    poetry run ruff check --fix .
    poetry run ruff format .
    @Write-Host "Linting and formatting completed." -ForegroundColor Green

# Check for linting, formatting and typing issues without fixing
check:
    poetry run ruff check .
    poetry run ruff format --check .
    poetry run mypy src

# Run tests
test:
    poetry run pytest

# Run tests with coverage report
test-cov:
    poetry run pytest --cov=django_wallets --cov-report=term-missing --cov-report=html

# Run type checking with mypy
type-check:
    poetry run mypy src

# Run all checks: lint (including import sort), type-check, and test
all: lint type-check test

# Run tests across multiple environments using tox
tox:
    poetry run tox

# Clean up all cached files and build artifacts
clean:
    @Write-Host "Cleaning up cached files and build artifacts..." -ForegroundColor Cyan
    Get-ChildItem -Path . -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse
    Get-ChildItem -Path . -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    if (Test-Path ".pytest_cache") { Remove-Item -Path .pytest_cache -Force -Recurse }
    if (Test-Path ".ruff_cache") { Remove-Item -Path .ruff_cache -Force -Recurse }
    if (Test-Path ".mypy_cache") { Remove-Item -Path .mypy_cache -Force -Recurse }
    if (Test-Path ".tox") { Remove-Item -Path .tox -Force -Recurse }
    if (Test-Path ".coverage") { Remove-Item -Path .coverage -Force }
    if (Test-Path "htmlcov") { Remove-Item -Path htmlcov -Force -Recurse }
    if (Test-Path "dist") { Remove-Item -Path dist -Force -Recurse }
    if (Test-Path "build") { Remove-Item -Path build -Force -Recurse }
    @Write-Host "Cleanup completed successfully." -ForegroundColor Green

# Install dependencies
install:
    poetry install

# Make migrations for the app
migrations:
    poetry run python manage.py makemigrations

# Run migrations
migrate:
    poetry run python manage.py migrate

# Print the current version of the package
version:
    @$env:PYTHONPATH="src"; poetry run python -c "import django_wallets; print(django_wallets.__version__)"
