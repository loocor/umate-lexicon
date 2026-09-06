#!/bin/sh
# Copy this factory to /Volumes/External/GitHub/umate-lexicon
# when the creating agent is sandboxed to the VoiMate workspace.
set -e
SRC="${1:-/tmp/umate-lexicon}"
DEST="/Volumes/External/GitHub/umate-lexicon"
if [ ! -d "$SRC" ]; then
  echo "missing source: $SRC" >&2
  exit 1
fi
mkdir -p "$DEST"
rsync -a --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'data/store/*.sqlite' \
  "$SRC"/ "$DEST"/
echo "placed $DEST"
