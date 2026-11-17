import argparse, base64, json, os, pathlib, shutil, subprocess, time, uuid
import requests
from concurrent.futures import ThreadPoolExecutor

MIMO_ENDPOINT = "https://api.xiaomimimo.com/v1/chat/completions"
DOUBAO_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
DEFAULT_DIRECTION = (
    "【角色】知识类视频的 UP 主，年轻女生，专业、亲切、条理清楚。"
    "【场景】给观众讲一期三分钟左右的教程视频。英文术语和命令照常读出来。"
    "【指导】语速适中、吐字清晰，像在跟朋友把一件事讲明白；讲到日期和数字时稍微放慢、读清楚；讲风险时语气认真但不夸张；提到产品时平实自然，不要有广告腔；句末收得干净。"
)


def env_file_value(key):
    for var in ("TTS_ENV_FILE", "MIMO_ENV_FILE"):
        path = os.environ.get(var)
        if not path or not pathlib.Path(path).expanduser().exists():
            continue
        for line in pathlib.Path(path).expanduser().read_text().splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def setting(key, default=None):
    return os.environ.get(key) or env_file_value(key) or default


def direction():
    p = pathlib.Path("audio/direction.txt")
    return p.read_text().strip() if p.exists() else DEFAULT_DIRECTION


class Retryable(Exception):
    pass


def check(resp, note=""):
    if resp.status_code == 200:
        return
    if resp.status_code == 429 or resp.status_code >= 500 or "concurrency" in resp.text:
        raise Retryable(f"{resp.status_code} {resp.text[:200]}{note}")
    raise SystemExit(f"{resp.status_code} {resp.text[:500]}{note}")


def synth_mimo(text, out, voice, direction_text):
    key = setting("MIMO_API_KEY")
    if not key:
        raise SystemExit("MIMO_API_KEY is not set (export it, or point TTS_ENV_FILE at a KEY=VALUE file)")
    resp = requests.post(
        MIMO_ENDPOINT,
        headers={"api-key": key, "Content-Type": "application/json"},
        json={
            "model": setting("MIMO_MODEL", "mimo-v2.5-tts"),
            "messages": [
                {"role": "user", "content": direction_text or direction()},
                {"role": "assistant", "content": text},
            ],
            "audio": {"format": "wav", "voice": voice or setting("MIMO_VOICE", "冰糖")},
        },
        timeout=180,
    )
    check(resp)
    data = resp.json()["choices"][0]["message"]["audio"]["data"]
    pathlib.Path(out).write_bytes(base64.b64decode(data))


def doubao_auth():
    if setting("DOUBAO_API_KEY"):
        return {"X-Api-Key": setting("DOUBAO_API_KEY")}
    if setting("DOUBAO_APP_ID") and setting("DOUBAO_ACCESS_KEY"):
        return {"X-Api-App-Id": setting("DOUBAO_APP_ID"), "X-Api-Access-Key": setting("DOUBAO_ACCESS_KEY")}
    raise SystemExit("DOUBAO_API_KEY is not set (new console API Key; old console: DOUBAO_APP_ID + DOUBAO_ACCESS_KEY)")


def json_stream(body):
    dec, i = json.JSONDecoder(), 0
    while True:
        while i < len(body) and body[i].isspace():
            i += 1
        if i == len(body):
            return
        obj, i = dec.raw_decode(body, i)
        yield obj


def synth_doubao(text, out, voice, direction_text):
    params = {
        "text": text,
        "speaker": voice or setting("DOUBAO_VOICE", "zh_female_vv_uranus_bigtts"),
        "audio_params": {"format": "mp3", "sample_rate": 24000, "bit_rate": 160000},
    }
    context = direction_text or setting("DOUBAO_CONTEXT")
    if context:
        params["additions"] = json.dumps({"context_texts": [context]}, ensure_ascii=False)
    resp = requests.post(
        setting("DOUBAO_ENDPOINT", DOUBAO_ENDPOINT),
        headers={
            **doubao_auth(),
            "X-Api-Resource-Id": setting("DOUBAO_RESOURCE_ID", "seed-tts-2.0"),
            "X-Api-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        },
        json={"req_params": params},
        timeout=180,
    )
    note = f" (logid {resp.headers.get('X-Tt-Logid', '-')})"
    check(resp, note)
    body = resp.content.decode("utf-8", "replace")
    audio = bytearray()
    try:
        for msg in json_stream(body):
            code = msg.get("code", 0)
            if code not in (0, 20000000):
                err = f"{code} {msg.get('message')}{note}"
                if str(code).startswith("5") or "concurrency" in str(msg.get("message")):
                    raise Retryable(err)
                raise SystemExit(err)
            if msg.get("data"):
                audio += base64.b64decode(msg["data"])
    except ValueError:
        raise SystemExit(f"unexpected response: {body[:300]}{note}")
    if not audio:
        raise Retryable(f"no audio in response{note}")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "mp3", "-i", "pipe:0", str(out)], input=bytes(audio), check=True)


PROVIDERS = {"mimo": synth_mimo, "doubao": synth_doubao}


def provider():
    name = setting("TTS_PROVIDER", "mimo").lower()
    if name not in PROVIDERS:
        raise SystemExit(f"TTS_PROVIDER must be one of: {', '.join(PROVIDERS)} (got {name})")
    return PROVIDERS[name]


def synth(text, out, voice=None, direction_text=None, tries=4):
    fn = provider()
    for k in range(tries):
        try:
            return fn(text, out, voice, direction_text)
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
