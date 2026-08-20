#!/bin/bash
# Publish the FULL commit history to the public mirror, minus secrets and
# minus the wrong-account identity.
#
# HARD GATE: run ONLY on Hao's explicit per-run go-ahead. Never
# autonomously — public pushes are cached/indexed and cannot be recalled.
#
# Filter: .env dropped from every commit; the old OpenAI key scrubbed
# (extracted from local history at runtime, never stored); author
# hlincontacts/haogotmilk -> jappabl's noreply (both gmails attribute to the
# wrong GitHub account; the noreply is structurally bound to jappabl). filter-repo is
# deterministic, so unchanged history keeps identical hashes across syncs.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
KEY=$(git show 0a40e8f:.env 2>/dev/null | grep -o "sk-proj-[A-Za-z0-9_-]*" | head -1)
[ -n "$KEY" ] || { echo "ABORT: key anchor not found in local history"; exit 1; }
T=$(mktemp -d)
git clone -q --no-local . "$T/pub"
cd "$T/pub"
printf '%s==>OPENAI_API_KEY_REDACTED\n' "$KEY" > "$T/replace.txt"
{ printf 'Hao Lin <129558989+jappabl@users.noreply.github.com> <hlincontacts@gmail.com>\n'
  printf 'Hao Lin <129558989+jappabl@users.noreply.github.com> <haogotmilk@gmail.com>\n'; } > "$T/mailmap.txt"
python3 -m git_filter_repo --invert-paths --path .env \
  --replace-text "$T/replace.txt" --mailmap "$T/mailmap.txt" --force >/dev/null

fail=0
# Guard 1: the specific key must be gone from every blob
hits=$(git rev-list --all | while read c; do git grep -lF "$KEY" "$c" 2>/dev/null; done | head -3)
if [ -n "$hits" ]; then echo "ABORT [old-openai-key]:"; echo "$hits"; fail=1; fi
# Guard 2: widened secret patterns across every blob of every commit
for entry in \
  "openai:sk-[A-Za-z0-9_-]{20,}" \
  "anthropic:sk-ant-[A-Za-z0-9_-]{8,}" \
  "github:gh[pousr]_[A-Za-z0-9]{16,}" \
  "github-pat:github_pat_[A-Za-z0-9_]{16,}" \
  "aws-id:AKIA[0-9A-Z]{16}" \
  "pem:BEGIN [A-Z ]*PRIVATE KEY" \
  "slack:xox[baprs]-[A-Za-z0-9-]{10,}" \
  "groq:gsk_[A-Za-z0-9]{16,}" \
  "google:AIza[A-Za-z0-9_-]{16,}"; do
  name="${entry%%:*}"; pat="${entry#*:}"
  hits=$(git rev-list --all | while read c; do
    git grep -lE "$pat" "$c" 2>/dev/null | sed "s/^/[$name] /"; done | sort -u | head -5)
  if [ -n "$hits" ]; then echo "ABORT: secret pattern matched:"; echo "$hits"; fail=1; fi
done
# Guard 3: banned filenames anywhere in history
BANNED='(^|/)(\.env(\..*)?|id_rsa|id_ed25519|credentials|.*\.pem)$'
bad=$(git rev-list --all | while read c; do
  git ls-tree -r --name-only "$c" | grep -E "$BANNED" | sed "s/^/[$c] /"; done | sort -u | head -5)
if [ -n "$bad" ]; then echo "ABORT: banned filename in history:"; echo "$bad"; fail=1; fi
# Guard 4: safety raw material must not appear
raw=$(git ls-tree -r --name-only HEAD | grep -E "strongreject_dataset\.csv|safety.*raw|completions" | head -3 || true)
if [ -n "$raw" ]; then echo "ABORT: safety raw material in snapshot:"; echo "$raw"; fail=1; fi
if [ "$fail" -ne 0 ]; then exit 1; fi

git branch -m main 2>/dev/null || true
git push -qf https://github.com/jappabl/anytime-valid-design-selection.git main
cd / && rm -rf "$T"
echo "public mirror synced (full filtered history)"
