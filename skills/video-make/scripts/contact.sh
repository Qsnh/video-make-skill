#!/bin/bash
set -e
src=${1:?usage: contact.sh build/stills build/sheets}
out=${2:?output dir}
mkdir -p "$out"
rm -f "$out"/sheet*.png
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$src/*.png" -vf "scale=960:-1,tile=2x2:padding=4:color=white" "$out/sheet%02d.png"
ls "$out"/sheet*.png
