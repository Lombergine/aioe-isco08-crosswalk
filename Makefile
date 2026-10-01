.PHONY: all build figure test clean

all: build figure test

build:
	python src/build_crosswalk.py

figure:
	python src/make_figure.py

test:
	python -m pytest tests/ -q

clean:
	rm -rf out/*.csv out/*.json docs/*.png src/__pycache__ tests/__pycache__ .pytest_cache
