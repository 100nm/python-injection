before_commit: check lint mypy pytest

check:
	poetry check

install:
	poetry install --sync

lint:
	ruff format
	ruff check --fix

mypy:
	mypy ./

pytest:
	pytest
