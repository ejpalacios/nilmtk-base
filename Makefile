.PHONY: isort black mypy test local-ci clean

PACKAGE := nilmtk
TEST := tests

## Create virtual environment
.venv/bin/activate: pyproject.toml
	poetry install

## Export requirements file
requirements.txt: pyproject.toml
	poetry export -o requirements.txt -f requirements.txt --without-hashes --without dev --without test

isort: .venv/bin/activate
	poetry run isort $(PACKAGE) $(TEST) --check-only

black: .venv/bin/activate
	poetry run black $(PACKAGE) $(TEST) --check

mypy: .venv/bin/activate
	poetry run mypy $(PACKAGE) $(TEST) --install-types --non-interactive

test: .venv/bin/activate
	poetry run pytest --cov=$(PACKAGE) -v

## Run local CI
local-ci: isort black mypy test

## Clean files
clean:
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf .venv

