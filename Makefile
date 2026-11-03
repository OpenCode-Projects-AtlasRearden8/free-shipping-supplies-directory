# Free Shipping Supplies Directory - build/verify targets
# plain make recipes; python3 is the only dependency

PY ?= python3

.PHONY: build links test serve all clean

build:
	$(PY) tools/build.py

links:
	$(PY) tools/linkcheck.py

test:
	$(PY) tools/verify.py

serve:
	$(PY) -m http.server 8123 --directory site

all: build test

clean:
	rm -f site/index.html site/print.html docs/catalog.md data/linkcheck.json docs/link-log.md
