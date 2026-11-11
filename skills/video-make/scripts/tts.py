import argparse, base64, json, os, pathlib, shutil, time
import requests
from concurrent.futures import ThreadPoolExecutor

ENDPOINT = "https://api.xiaomimimo.com/v1/chat/completions"
DEFAULT_DIRECTION = (
    "【角色】知识类视频的 UP 主，年轻女生，专业、亲切、条理清楚。"
    "【场景】给观众讲一期三分钟左右的教程视频。英文术语和命令照常读出来。"
    "【指导】语速适中、吐字清晰，像在跟朋友把一件事讲明白；讲到日期和数字时稍微放慢、读清楚；讲风险时语气认真但不夸张；提到产品时平实自然，不要有广告腔；句末收得干净。"
)


def env_file_value(key):
    path = os.environ.get("MIMO_ENV_FILE")
    if not path or not pathlib.Path(path).expanduser().exists():
        return None
    for line in pathlib.Path(path).expanduser().read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def setting(key, default=None):
    return os.environ.get(key) or env_file_value(key) or default


def api_key():
    key = setting("MIMO_API_KEY")
    if not key:
        raise SystemExit("MIMO_API_KEY is not set (export it, or point MIMO_ENV_FILE at a KEY=VALUE file)")
    return key


def direction():
    p = pathlib.Path("audio/direction.txt")
    return p.read_text().strip() if p.exists() else DEFAULT_DIRECTION


class Retryable(Exception):
    pass


def _synth(text, out, voice, direction_text):
    resp = requests.post(
        ENDPOINT,
        headers={"api-key": api_key(), "Content-Type": "application/json"},
        json={
            "model": setting("MIMO_MODEL", "mimo-v2.5-tts"),
            "messages": [
                {"role": "user", "content": direction_text},
                {"role": "assistant", "content": text},
            ],
            "audio": {"format": "wav", "voice": voice},
        },
        timeout=180,
    )
    if resp.status_code == 429 or resp.status_code >= 500:
        raise Retryable(f"{resp.status_code} {resp.text[:200]}")
    if resp.status_code != 200:
        raise SystemExit(f"{resp.status_code} {resp.text[:500]}")
    data = resp.json()["choices"][0]["message"]["audio"]["data"]
    pathlib.Path(out).write_bytes(base64.b64decode(data))


def synth(text, out, voice=None, direction_text=None, tries=4):
    voice = voice or setting("MIMO_VOICE", "冰糖")
    direction_text = direction_text or direction()
    for k in range(tries):
        try:
            return _synth(text, out, voice, direction_text)
        except (requests.exceptions.RequestException, Retryable):
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


def load_manifest(outdir, lines):
    path = outdir / "manifest.json"
    if path.exists():
        return json.loads(path.read_text())
    return {f.stem: lines[int(f.stem)] for f in outdir.glob("*.wav") if f.stem.isdigit() and int(f.stem) < len(lines)}


def sync(lines, outdir, only=None):
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(outdir, lines)
    stash = outdir / "old"
    stash.mkdir(exist_ok=True)
    by_text = {}
    for name, text in manifest.items():
        f = outdir / f"{name}.wav"
        if f.exists():
            kept = stash / f"{name}.wav"
            shutil.move(str(f), kept)
            by_text.setdefault(text, kept)
    new_manifest, todo, reused = {}, [], []
    for i, text in enumerate(lines):
        name = f"{i:02d}"
        target = outdir / f"{name}.wav"
        if text in by_text:
            if manifest.get(name) == text:
                shutil.copy2(by_text[text], target)
            else:
                shutil.copyfile(by_text[text], target)
                reused.append(i)
            new_manifest[name] = text
        elif only is None or i in only:
            todo.append(i)
    used = {by_text[t] for t in lines if t in by_text}
    for f in stash.glob("*.wav"):
        if f in used:
            f.unlink()
    if not any(stash.iterdir()):
        stash.rmdir()

    def job(i):
        synth(lines[i], outdir / f"{i:02d}.wav")
        print(i, "synthesized", flush=True)

    try:
        with ThreadPoolExecutor(4) as ex:
            for i in ex.map(lambda i: (job(i), i)[1], todo):
                new_manifest[f"{i:02d}"] = lines[i]
    finally:
        (outdir / "manifest.json").write_text(json.dumps(dict(sorted(new_manifest.items())), ensure_ascii=False, indent=1))
    if reused:
        print("moved to new index:", reused)
    missing = [i for i in range(len(lines)) if f"{i:02d}" not in new_manifest]
    if missing:
        print("not synthesized:", missing)


def adopt(lines, outdir, index, take):
    manifest = load_manifest(outdir, lines)
    shutil.copyfile(take, outdir / f"{index:02d}.wav")
    manifest[f"{index:02d}"] = lines[index]
    (outdir / "manifest.json").write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=1))
    print(f"{index:02d} <- {take}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", help="audio/lines.json")
    ap.add_argument("outdir", help="audio/raw")
    ap.add_argument("--only", help="comma separated indexes to synthesize; others are only re-linked")
    ap.add_argument("--adopt", nargs=2, metavar=("INDEX", "TAKE_WAV"), help="use a take as line INDEX (run make_script.py first if the text changed)")
    args = ap.parse_args()
    lines = json.loads(pathlib.Path(args.lines).read_text())
    outdir = pathlib.Path(args.outdir)
    if args.adopt:
        adopt(lines, outdir, int(args.adopt[0]), args.adopt[1])
    else:
        sync(lines, outdir, {int(x) for x in args.only.split(",")} if args.only else None)
