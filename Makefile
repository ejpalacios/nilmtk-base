.PHONY: isort black mypy test local-ci
isort:
	poetry run isort nilmtk --check-only

black:
	poetry run black nilmtk --check

mypy:
	poetry run mypy nilmtk

test:
	poetry run nosetests -v

test-coverage:
	poetry run nosetests --with-coverage

local-ci: isort black mypy test-coverage
