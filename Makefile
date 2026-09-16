PYTHON ?= python3
export PYTHONPATH := src

.PHONY: test pipeline fetch verify-sources pipeline-locked eval emit inventory

test:
	$(PYTHON) -m pytest

pipeline:
	$(PYTHON) -m umate_lexicon pipeline --fixtures

fetch:
	$(PYTHON) -m umate_lexicon fetch

verify-sources:
	$(PYTHON) -m umate_lexicon verify-sources

pipeline-locked:
	$(PYTHON) -m umate_lexicon pipeline

eval:
	$(PYTHON) -m umate_lexicon eval

emit:
	$(PYTHON) -m umate_lexicon emit --out dist/rime

inventory:
	$(PYTHON) -m umate_lexicon inventory
