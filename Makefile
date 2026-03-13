.PHONY: test docs build

test:
	pytest -vv

docs:
	cd docs && make html

build:
	uv build
