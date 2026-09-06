PYTHON ?= python3
export PYTHONPATH := src

.PHONY: test pipeline eval emit

test:
	$(PYTHON) -m pytest

pipeline:
	$(PYTHON) -m umate_lexicon pipeline --fixtures

eval:
	$(PYTHON) -m umate_lexicon eval

emit:
	$(PYTHON) -m umate_lexicon emit --out dist/rime
