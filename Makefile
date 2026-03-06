.DEFAULT_GOAL := help

.PHONY: help venv install hooks lint lint-fix format test precommit ci clean

help:
	@echo "Targets:"
	@echo "  make venv        - Create .venv using uv"
	@echo "  make install     - Install dev deps into .venv"
	@echo "  make hooks       - Install pre-commit git hooks"
	@echo "  make lint        - Run ruff checks"
	@echo "  make lint-fix    - Run ruff with auto-fix"
	@echo "  make format      - Run black formatter"
	@echo "  make test        - Run pytest"
	@echo "  make precommit   - Run all pre-commit hooks"
	@echo "  make ci          - Lint + test"
	@echo "  make clean       - Remove local build artifacts"

venv:
	uv venv

install: venv
	uv pip install -e ".[dev]"

hooks: install
	uv run pre-commit install

lint: install
	uv run ruff check .

lint-fix: install
	uv run ruff check --fix .

format: install
	uv run black .

test: install
	uv run pytest

precommit: install
	uv run pre-commit run --all-files

ci: lint test

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info

