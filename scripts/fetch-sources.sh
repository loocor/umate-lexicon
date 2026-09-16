#!/bin/sh
# Download pinned dumps from data/sources.lock.json into data/sources/downloads/.
set -e
cd "$(dirname "$0")/.."
PYTHONPATH=src python3 -m umate_lexicon fetch "$@"
