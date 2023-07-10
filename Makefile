.PHONY: isort black mypy test local-ci
isort:
	poetry run isort nilmtk --check-only

black:
	poetry run black nilmtk --check

mypy:
	poetry run mypy nilmtk

test:
	poetry run nosetests -v

local-ci: isort black mypy
