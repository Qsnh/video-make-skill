import json, pathlib, re, sys, difflib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import whisper
from build_audio import speech_bounds, silences

ZH_NUM = {"零": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
MIN_RATIO = 0.9
MIN_CHUNK = 0.6


def norm(s):
    s = s.lower()
    s = re.sub(r"[\s，。？、！,.?：；:“”\"'_\-（）()·]", "", s)
    return s


def unify(s):
    return "".join(ZH_NUM.get(c, c) for c in s)


def main(clip_dir, timeline_path, script_path):
    clip_dir = pathlib.Path(clip_dir)
    tl = json.loads(pathlib.Path(timeline_path).read_text())
    script = json.loads(pathlib.Path(script_path).read_text())
    model = whisper.load_model("small")
    for i, (sent, line) in enumerate(zip(tl["sentences"], script)):
        chunks = sent["chunks"]
        if len(chunks) < 2:
            continue
        clip = clip_dir / f"{i:02d}.wav"
        s, e = speech_bounds(clip)
        offset = sent["start"] - s
        say = [norm(c["say"]) for c in chunks]
        target = unify("".join(say))
        r = model.transcribe(str(clip), language="zh", fp16=False, temperature=0, condition_on_previous_text=False, word_timestamps=True, initial_prompt=line["tts"])
        chars = []
        for seg in r["segments"]:
            for w in seg.get("words", []):
                t = unify(norm(w["word"]))
                if not t:
                    continue
                n = len(t)
                for k, ch in enumerate(t):
                    chars.append((ch, w["start"] + (w["end"] - w["start"]) * k / n))
        asr = "".join(c for c, _ in chars)
        sm = difflib.SequenceMatcher(None, target, asr, autojunk=False)
        mapping = {}
        for a, b, size in sm.get_matching_blocks():
            for k in range(size):
                mapping[a + k] = b + k
        gaps, _ = silences(clip, 0.08)
        bounds = []
        pos = 0
        for j, c in enumerate(chunks[:-1]):
            pos += len(unify(say[j]))
            idx = next((mapping[q] for q in range(pos, min(pos + 4, len(target))) if q in mapping), None)
            if idx is None:
                bounds.append(c["end"])
                continue
            t = chars[idx][1]
            near = [(abs((ga + gb) / 2 - t), (ga + gb) / 2) for ga, gb in gaps if abs((ga + gb) / 2 - t) < 0.3 or ga - 0.05 <= t <= gb + 0.05]
            if near:
                t = min(near)[1]
            bounds.append(round(t + offset, 3))
        edges = [sent["start"]] + bounds + [sent["end"]]
        old = [c["end"] - c["start"] for c in chunks]
        new = [edges[j + 1] - edges[j] for j in range(len(chunks))]
        ratio = sm.ratio()
        if ratio < MIN_RATIO or any(n < min(MIN_CHUNK, o) for n, o in zip(new, old)):
            print(i, f"keep pause times [{ratio:.2f}]", " | ".join(f"{c['start']:.2f}:{c['text']}" for c in chunks), flush=True)
            continue
        for j, c in enumerate(chunks):
            c["start"] = edges[j]
            c["end"] = edges[j + 1]
        print(i, " | ".join(f"{c['start']:.2f}:{c['text']}" for c in chunks), f"[{ratio:.2f}]", flush=True)
    pathlib.Path(timeline_path).write_text(json.dumps(tl, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage: align_chunks.py audio/clips build/timeline.json audio/script.json")
    main(*sys.argv[1:4])
