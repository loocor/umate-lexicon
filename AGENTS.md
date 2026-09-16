# umate-lexicon agent notes

- This repo lives at `VoiMate/Lexicon` for local work, but keeps an
  independent git history. Do not copy VoiMate keyboard sources here.
  Do not copy rime-ice files here.
- Canonical data is the SQLite lemma store, not `*.dict.yaml`.
- Primary key is `(surface, pinyin_plain)`.
- Emit Rime YAML only at the end of the pipeline. Keyboard compilation
  of dictionaries is forbidden; Host compiles binaries.
- LLM calls, if any, must use the structured verifier in
  `umate_lexicon.verify.llm`. They must not invent lemmas.
- New ingest adapters need a license id, a fixture, and a test.
- Run `python -m pytest` from the repo root (`PYTHONPATH=src`).
- GitHub-facing text is English. Internal design notes may be Chinese
  under `docs/zh/`.

- Full dumps are pinned in `data/sources.lock.json`. Fetch with
  `python -m umate_lexicon fetch`. Do not invent hashes. Hash mismatch
  is a hard failure; do not fall back to fixtures.
