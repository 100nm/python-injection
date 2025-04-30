before_commit: lint mypy pytest

install:
	uv sync

update:
	uv lock --upgrade
	uv sync

lint:
	uv run ruff format
	uv run ruff check --fix

mypy:
	uv run mypy ./

pytest:
	uv run pytest
