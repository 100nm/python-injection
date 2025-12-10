before_commit: lint mypy pyright pytest

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

pyright:
	uv run pyright

pytest:
	uv run pytest

mkdocs:
	uv run mkdocs serve
