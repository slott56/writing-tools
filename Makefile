.PHONY: test docs build

test:
	uvx tox run

type:
	uvx ty check src

docs:
	cd docs && make html

build:
	uv build

