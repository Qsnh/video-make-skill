#!/bin/bash
set -e
in=${1:?usage: speed.sh audio/raw audio/clips [rate]}
out=${2:?output dir}
rate=${3:-1.3}
mkdir -p "$out"
for f in "$out"/*.wav; do
  [ -e "$f" ] || continue
  [ -f "$in/$(basename "$f")" ] || rm -f "$f"
done
for f in "$in"/*.wav; do
  n=$(basename "$f")
  [ -f "$out/$n" ] && [ "$out/$n" -nt "$f" ] && continue
  ffmpeg -hide_banner -loglevel error -y -i "$f" -filter:a "atempo=$rate" "$out/$n"
done
