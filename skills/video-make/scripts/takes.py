import argparse, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tts, whisper
from textnorm import NEUTRAL_PROMPT, score
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("spec", help='JSON file {"<key>": ["text A", "text B"]}, or line indexes like 3,7 to retake lines from audio/lines.json')
ap.add_argument("takes", nargs="?", type=int, default=3)
ap.add_argument("--rate", type=float, default=1.3)
ap.add_argument("--out", default="audio/takes")
args = ap.parse_args()

if re.fullmatch(r"[\d,]+", args.spec):
    lines = json.loads(pathlib.Path("audio/lines.json").read_text())
    spec = {f"{int(i):02d}": [lines[int(i)]] for i in args.spec.split(",")}
else:
    spec = json.loads(pathlib.Path(args.spec).read_text())

out = pathlib.Path(args.out)
out.mkdir(parents=True, exist_ok=True)
jobs = [(key, v, k) for key, texts in spec.items() for v in range(len(texts)) for k in range(args.takes)]


def job(x):
    key, v, k = x
    raw = out / f"{key}-{v}-{k}.raw.wav"
    if not raw.exists():
        tts.synth(spec[key][v], raw)
    fast = out / f"{key}-{v}-{k}.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-filter:a", f"atempo={args.rate}", str(fast)], check=True)


with ThreadPoolExecutor(4) as ex:
    list(ex.map(job, jobs))

model = whisper.load_model("small")


def run(path, lang):
    kw = {"initial_prompt": NEUTRAL_PROMPT} if lang == "zh" else {}
    return model.transcribe(str(path), language=lang, fp16=False, temperature=0, condition_on_previous_text=False, **kw)["text"].strip()


for key, v, k in jobs:
    f = out / f"{key}-{v}-{k}.wav"
    zh = run(f, "zh")
    en = run(f, "en")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout)
    print(f"{key}-{v}-{k} {score(spec[key][v], zh):.2f} {dur:.2f}s {zh}\n      EN {en}", flush=True)
