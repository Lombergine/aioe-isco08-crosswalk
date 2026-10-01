# macOS ships python3 but no `python`. Override with: make PYTHON=python3.12 test
PYTHON ?= python3

.PHONY: all build figure validate test clean

all: build figure validate test

build:
	$(PYTHON) src/build_crosswalk.py

figure:
	$(PYTHON) src/make_figure.py

# Fetches the ILO WP140 scores over the network, then checks the crosswalk
# against a measure built natively on ISCO-08.
validate:
	$(PYTHON) src/validate_external.py
	$(PYTHON) src/make_validation_figure.py

test:
	$(PYTHON) -m pytest tests/ -q

clean:
	rm -rf out/*.csv out/*.json docs/*.png src/__pycache__ tests/__pycache__ .pytest_cache
