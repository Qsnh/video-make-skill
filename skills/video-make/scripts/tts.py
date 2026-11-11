import base64, json, os, pathlib, sys, time
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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("usage: tts.py audio/lines.json audio/raw [indexes]")
    lines = json.loads(pathlib.Path(sys.argv[1]).read_text())
    outdir = pathlib.Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    only = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(len(lines))

    def job(i):
        target = outdir / f"{i:02d}.wav"
        if target.exists():
            return
        synth(lines[i], target)
        print(i, "ok", flush=True)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(job, only))
