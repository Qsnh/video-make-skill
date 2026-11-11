#!/bin/bash
set -e
dest=${1:?usage: init.sh <working dir>}
skill=$(cd "$(dirname "$0")/.." && pwd)
if [ -e "$dest" ] && [ -n "$(ls -A "$dest" 2>/dev/null)" ]; then
  echo "$dest is not empty" >&2
  exit 1
fi
mkdir -p "$dest/tools"
cp -R "$skill/template/." "$dest/"
for f in "$skill"/scripts/*; do
  [ "$(basename "$f")" = init.sh ] || cp "$f" "$dest/tools/"
done
cd "$dest"
npm i --no-audit --no-fund --silent playwright-core@1.64.1
echo "ready: $dest"
