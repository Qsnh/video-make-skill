import argparse, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import whisper
from textnorm import NEUTRAL_PROMPT, score

ap = argparse.ArgumentParser()
ap.add_argument("clips", nargs="+", help="a clip directory (NN.wav per line) or individual wav files")
ap.add_argument("--lines", default="audio/lines.json")
ap.add_argument("--only", help="comma separated line indexes")
ap.add_argument("--prompt", help="initial_prompt text; defaults to asr-prompt.txt when it exists")
ap.add_argument("--en", action="store_true", help="also transcribe with language=en to judge English terms")
args = ap.parse_args()

prompt = args.prompt
if prompt is None and pathlib.Path("asr-prompt.txt").exists():
    prompt = pathlib.Path("asr-prompt.txt").read_text().strip()
lines = json.loads(pathlib.Path(args.lines).read_text()) if pathlib.Path(args.lines).exists() else None
model = whisper.load_model("small")


def run(path, **kw):
    return model.transcribe(str(path), fp16=False, temperature=0, condition_on_previous_text=False, **kw)["text"].strip()


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout)


targets = []
for c in args.clips:
    p = pathlib.Path(c)
    if p.is_dir():
        for f in sorted(p.glob("*.wav")):
            if f.stem.isdigit():
                targets.append((int(f.stem), f))
    else:
        targets.append((int(p.stem) if p.stem.isdigit() else None, p))
if args.only:
    keep = {int(x) for x in args.only.split(",")}
    targets = [(i, f) for i, f in targets if i in keep]

for i, f in targets:
    want = lines[i] if lines is not None and i is not None and i < len(lines) else None
    plain = run(f, language="zh", initial_prompt=NEUTRAL_PROMPT)
    out = [f"{f.name} {duration(f):.2f}s"]
    if want:
        out[0] += f"  plain {score(want, plain):.2f}"
        out.append(f"   want  {want}")
    out.append(f"   plain {plain}")
    if prompt:
        out.append(f"   prime {run(f, language='zh', initial_prompt=prompt)}")
    if args.en:
        out.append(f"   en    {run(f, language='en')}")
    print("\n".join(out), flush=True)
