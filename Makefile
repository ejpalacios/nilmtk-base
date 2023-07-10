.PHONY: isort black mypy test local-ci
isort:
	poetry run isort nilmtk --check-only

black:
	poetry run black nilmtk --check

install-stubs:
	poetry run mypy --install-types --non-interactive nilmtk

mypy:
	poetry run mypy --no-incremental nilmtk

test:
	poetry run nosetests -v

test-coverage:
	poetry run nosetests --with-coverage

local-ci: isort black mypy test-coverage
