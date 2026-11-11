#!/bin/bash
set -e
in=$1; out=$2; rate=${3:-1.3}
mkdir -p "$out"
for f in "$in"/*.wav; do
  n=$(basename "$f")
  [ -f "$out/$n" ] && [ "$out/$n" -nt "$f" ] && continue
  ffmpeg -hide_banner -loglevel error -y -i "$f" -filter:a "atempo=$rate" "$out/$n"
done
