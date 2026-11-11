import json, re, subprocess, sys, pathlib

LEAD = 0.06
TAIL = 0.14
INTRO = 0.3
OUTRO = 2.0


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out.strip())


def silences(path, min_len):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=noise=-40dB:d={min_len}", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    total = duration(path)
    while len(ends) < len(starts):
        ends.append(total)
    return list(zip(starts, ends)), total


def speech_bounds(path):
    gaps, total = silences(path, 0.05)
    start, end = 0.0, total
    if gaps and gaps[0][0] <= 0.01:
        start = gaps[0][1]
    if gaps and gaps[-1][1] >= total - 0.01:
        end = gaps[-1][0]
    return start, end


def weight(text):
    text = re.sub(r"[\s，。？、！,.?：；“”/·'-]", "", text)
    total = 0.0
    for run in re.findall(r"[A-Za-z]+|[^A-Za-z]", text):
        if run[0].isascii() and run[0].isalpha():
            total += len(run) * 0.8 if run.isupper() else max(1, round(len(run) / 2.5))
        else:
            total += 1
    return total


def chunk_times(chunks, start, end, gaps):
    pairs = [(c, c) if isinstance(c, str) else (c[0], c[1]) for c in chunks]
    total = sum(weight(say) for _, say in pairs)
    bounds, acc, used = [], 0, set()
    for _, say in pairs[:-1]:
        acc += weight(say)
        expected = start + (end - start) * acc / total
        best = None
        for i, (gs, ge) in enumerate(gaps):
            mid = (gs + ge) / 2
            if i in used or not (start < mid < end):
                continue
            if abs(mid - expected) <= 0.8 and (best is None or abs(mid - expected) < abs(best[1] - expected)):
                best = (i, mid)
        if best:
            used.add(best[0])
            bounds.append(best[1])
        else:
            bounds.append(expected)
    edges = [start] + sorted(bounds) + [end]
    return [{"text": text, "say": say, "start": round(edges[i], 3), "end": round(edges[i + 1], 3)} for i, (text, say) in enumerate(pairs)]


def main(voice_dir, out_dir, script_path):
    voice_dir, out_dir = pathlib.Path(voice_dir), pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    script = json.loads(pathlib.Path(script_path).read_text())
    cursor = INTRO
    inputs, filters, sentences = [], [], []
    for i, line in enumerate(script):
        clip = voice_dir / f"{i:02d}.wav"
        s, e = speech_bounds(clip)
        cut_start, cut_end = max(0.0, s - LEAD), min(duration(clip), e + TAIL)
        offset = cursor - cut_start
        inner, _ = silences(clip, 0.12)
        gaps = [(a + offset, b + offset) for a, b in inner if a > s + 0.05 and b < e - 0.05]
        speech_start, speech_end = s + offset, e + offset
        sentence = {"start": round(speech_start, 3), "end": round(speech_end, 3), "chunks": chunk_times(line["chunks"], speech_start, speech_end, gaps)}
        if line.get("chapter"):
            sentence["chapter"] = line["chapter"]
        sentences.append(sentence)
        inputs += ["-i", str(clip)]
        filters.append(f"[{i}]atrim={cut_start:.3f}:{cut_end:.3f},asetpts=PTS-STARTPTS,adelay={int(round(cursor * 1000))}:all=1[a{i}]")
        cursor += cut_end - cut_start + float(line.get("gap_after", 0))
    total = round(cursor - TAIL + OUTRO, 3)
    mix = "".join(f"[a{i}]" for i in range(len(script)))
    graph = ";".join(filters) + f";{mix}amix=inputs={len(script)}:normalize=0,apad,atrim=0:{total},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-ac", "2", str(out_dir / "narration.wav")], check=True)
    timeline = {"duration": total, "sentences": sentences}
    (out_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2))
    print(json.dumps({"duration": total, "lines": len(sentences)}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
