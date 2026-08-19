#!/bin/bash
# Sync the public repo (fresh-history snapshot of HEAD). Local git history
# contains a revoked-key blob and must NEVER be pushed. Run after progress
# lands and README.md is updated.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
MSG=$(git log --format=%s -1)
PUB=$(mktemp -d)
git archive HEAD | tar -x -C "$PUB"
cd "$PUB"
if grep -rq "sk-proj-[A-Za-z0-9]\{8\}" .; then echo "ABORT: key"; exit 1; fi
if grep -rq "sk-[A-Za-z0-9]\{20\}" .; then echo "ABORT: keylike"; exit 1; fi
git init -q && git branch -m main && git add -A
GIT_AUTHOR_NAME="Hao Lin" GIT_COMMITTER_NAME="Hao Lin" \
GIT_AUTHOR_EMAIL="haogotmilk@gmail.com" GIT_COMMITTER_EMAIL="haogotmilk@gmail.com" \
  git commit -q -m "Sync: $MSG"
git push -qf https://github.com/jappabl/anytime-valid-design-selection.git main
cd / && rm -rf "$PUB"
echo "public repo synced: $MSG"
