#!/usr/bin/env bash
# Publish a rendered post folder to the gh-pages branch and print its public URLs.
# Usage: bash publish.sh out/<slug>
set -euo pipefail
SRC="$(cd "$1" && pwd)"
SLUG="$(basename "$SRC")"
BASE="https://ajayoneness.github.io/codeaj-social"
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
git commit -q -m "post: $SLUG" || true
git push -q origin gh-pages

URLS=()
for f in $(ls posts/$SLUG | grep -E '\.(jpg|mp4)$' | sort); do URLS+=("$BASE/posts/$SLUG/$f"); done
# wait for the GitHub Pages build of this commit (github.io itself is not reachable from the sandbox)
SHA="$(git rev-parse HEAD)"
ok=0
for i in $(seq 1 60); do
  read -r st sha < <(gh api repos/ajayoneness/codeaj-social/pages/builds/latest -q '.status+" "+.commit' 2>/dev/null || echo "none none")
  if [ "$st" = "built" ] && [ "$sha" = "$SHA" ]; then ok=1; break; fi
  [ "$st" = "errored" ] && break
  sleep 10
done
sleep 20  # CDN propagation
cd "$ROOT"; git worktree remove --force "$WT"
printf '%s\n' "${URLS[@]}"
[ $ok = 1 ] || { echo "WARNING: some URLs not live yet" >&2; exit 2; }
