#!/bin/bash
# Publish the FULL commit history to the public mirror, minus secrets and
# minus the yesssorno-linked identity:
#   - .env dropped from every commit (real API key lived there)
#   - the key string scrubbed from any other blob (extracted from local
#     history at runtime — never stored in this script or any tracked file)
#   - author/committer rewritten hlincontacts@gmail.com -> haogotmilk@gmail.com
#     (hlincontacts is linked to the wrong GitHub account)
# git-filter-repo is deterministic: unchanged history keeps identical hashes
# across syncs, so force-push only appends new commits in effect.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
KEY=$(git show 0a40e8f:.env 2>/dev/null | grep -o "sk-proj-[A-Za-z0-9_-]*" | head -1)
[ -n "$KEY" ] || { echo "ABORT: key anchor not found in local history"; exit 1; }
T=$(mktemp -d)
git clone -q --no-local . "$T/pub"
cd "$T/pub"
printf '%s==>OPENAI_API_KEY_REDACTED\n' "$KEY" > "$T/replace.txt"
printf 'Hao Lin <haogotmilk@gmail.com> <hlincontacts@gmail.com>\n' > "$T/mailmap.txt"
python3 -m git_filter_repo --invert-paths --path .env \
  --replace-text "$T/replace.txt" --mailmap "$T/mailmap.txt" --force >/dev/null
# hard guards before anything leaves the machine
git rev-list --all | while read c; do git grep -lF "$KEY" "$c" 2>/dev/null; done | grep -q . && { echo "ABORT: key survived filter"; exit 1; }
git log --all --format='%ae%n%ce' | grep -q "hlincontacts" && { echo "ABORT: identity survived filter"; exit 1; }
git branch -m main 2>/dev/null || true
git push -qf https://github.com/jappabl/anytime-valid-design-selection.git main
cd / && rm -rf "$T"
echo "public mirror synced (full filtered history)"
