sources = django_urlconfchecks

.PHONY: test format lint unittest coverage pre-commit clean
test: format lint unittest

format:
	uv run ruff format $(sources) tests
	uv run ruff check --select I --fix $(sources) tests

lint:
	uv run ruff check $(sources) tests
	uv run ty check $(sources) tests

unittest:
	uv run pytest

coverage:
	uv run pytest --cov=$(sources) --cov-branch --cov-report=term-missing tests

pre-commit:
	pre-commit run --all-files

clean:
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf .tox dist site
	rm -rf coverage.xml .coverage
