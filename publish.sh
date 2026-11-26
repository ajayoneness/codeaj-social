#!/usr/bin/env bash
# Publish a rendered post folder to the gh-pages branch and print its public URLs.
# Usage: bash publish.sh out/<slug>
set -euo pipefail
SRC="$(cd "$1" && pwd)"
SLUG="$(basename "$SRC")"
ROOT="$(git rev-parse --show-toplevel)"
WT="$(mktemp -d)"

cd "$ROOT"
git fetch -q origin gh-pages 2>/dev/null || true
if git show-ref -q --verify refs/remotes/origin/gh-pages; then
  git worktree add -q -B gh-pages "$WT" origin/gh-pages
else
  git worktree add -q --orphan -b gh-pages "$WT"
  touch "$WT/.nojekyll"; echo '{"posts": [], "weekly_notes": []}' > "$WT/history.json"
fi
mkdir -p "$WT/posts/$SLUG"
cp "$SRC"/*.jpg "$SRC"/*.mp4 "$SRC"/spec.json "$WT/posts/$SLUG/" 2>/dev/null || true
cd "$WT"
git add -A
git -c user.name="CodeAj Agent" -c user.email="noreply@anthropic.com" commit -q -m "post: $SLUG" || true
git -c push.negotiate=true push -q origin gh-pages 2>&1 | grep -v -i negotiat || true

SHA="$(git rev-parse HEAD)"
# jsDelivr serves files from the public repo with correct content types (image/jpeg, video/mp4).
# Pinning to the commit SHA makes the URL live immediately. Fallback: raw.githubusercontent.com.
echo "# primary (use these)"
for f in $(ls posts/$SLUG | grep -E '\.(jpg|mp4)$' | sort); do
  echo "https://cdn.jsdelivr.net/gh/ajayoneness/codeaj-social@$SHA/posts/$SLUG/$f"
done
echo "# fallback"
for f in $(ls posts/$SLUG | grep -E '\.(jpg|mp4)$' | sort); do
  echo "https://raw.githubusercontent.com/ajayoneness/codeaj-social/$SHA/posts/$SLUG/$f"
done
sleep 15
cd "$ROOT"; git worktree remove --force "$WT"
