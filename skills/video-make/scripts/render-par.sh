#!/bin/bash
set -e
here=$(cd "$(dirname "$0")" && pwd)
tl=${1:?usage: render-par.sh build/timeline.json build/narration.wav dist/video.mp4 [workers]}
narration=${2:?narration wav}
out=${3:?output mp4}
n=${4:-8}
fps=${FPS:-30}
html=${HTML:-comp/index.html}
lufs=${LUFS:--14}
dur=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['duration'])" "$tl")
total=$(python3 -c "import sys;print(round(float(sys.argv[1])*int(sys.argv[2])))" "$dur" "$fps")
seg=build/seg
rm -rf "$seg"; mkdir -p "$seg" "$(dirname "$out")"
step=$(( (total + n - 1) / n ))
pids=()
for ((k=0; k<n; k++)); do
  s=$((k*step)); e=$(( (k+1)*step )); [ $e -gt $total ] && e=$total
  node "$here/render.mjs" --html="$html" --timeline="$tl" --fps=$fps --start=$s --end=$e --out=$seg/p$k.mp4 > $seg/p$k.log 2>&1 &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait $p || fail=1; done
if [ $fail -ne 0 ]; then tail -n 5 $seg/p*.log; exit 1; fi
for ((k=0; k<n; k++)); do echo "file 'p$k.mp4'" >> $seg/list.txt; done
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $seg/list.txt -c copy $seg/video.mp4
i=$(ffmpeg -hide_banner -nostats -i "$narration" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | tail -1 | awk '{print $2}')
gain=$(python3 -c "import sys;print(round(float(sys.argv[1]) - float(sys.argv[2]), 2))" "$lufs" "$i")
ffmpeg -hide_banner -loglevel error -y -i $seg/video.mp4 -i "$narration" -map 0:v -map 1:a -c:v copy -af "volume=${gain}dB,alimiter=limit=0.89:level=disabled" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$out"
echo "frames=$total in=$i gain=$gain out=$(ffmpeg -hide_banner -nostats -i "$out" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | tail -1 | awk '{print $2}') LUFS"
