# Thin Makefile wrappers around scripts/dev.py (works on Linux/macOS and CI).
# On Windows without GNU Make, call the Python task runner directly.

PY ?= python
.PHONY: setup fmt lint type test cov check run cli build package smoke clean

setup:
	$(PY) scripts/dev.py setup

fmt:
	$(PY) scripts/dev.py fmt

lint:
	$(PY) scripts/dev.py lint

type:
	$(PY) scripts/dev.py type

test:
	$(PY) scripts/dev.py test

cov:
	$(PY) scripts/dev.py cov

check:
	$(PY) scripts/dev.py check

run:
	$(PY) scripts/dev.py run

cli:
	$(PY) scripts/dev.py cli $(ARGS)

build:
	$(PY) scripts/dev.py build

package:
	$(PY) scripts/dev.py package $(ARGS)

smoke:
	$(PY) scripts/dev.py smoke

clean:
	$(PY) scripts/dev.py clean
