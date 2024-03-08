before_commit: check lint pytest

check:
	poetry check

install:
	poetry install --sync

lint:
	ruff format
	ruff check --fix

pytest:
	pytest --cov=./ --cov-report term-missing:skip-covered
