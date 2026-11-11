import json, pathlib

P = lambda caption, say: [caption, say]

CHAPTERS = [("开场", 0), ("写文案", 2), ("配音", 4), ("渲染", 5)]

L = [
 ("这条视频，从文案到成片，全程用代码做出来。", ["这条视频，从文案到成片", "全程用代码做出来"]),
 ("一共三步：写文案、配音、渲染。", ["一共三步", "写文案、配音、渲染"]),

 ("第一步写文案，一句一行，字幕和配音分开写。", ["第一步写文案，一句一行", "字幕和配音分开写"]),
 ("比如 Engine X 和一点三倍速，字幕照常写，配音要写成读法。", [P("比如 Nginx 和 1.3 倍速", "比如 Engine X 和一点三倍速"), "字幕照常写，配音要写成读法"]),

 ("第二步，逐句配音，再用语音识别把每一句都听一遍，读错的就重录。", ["第二步，逐句配音", "再用语音识别把每一句都听一遍", "读错的就重录"]),

 ("第三步，网页动画跟着时间轴逐帧截图，最后合成视频。", ["第三步，网页动画跟着时间轴逐帧截图", "最后合成视频"]),
 ("觉得有用，点个关注。", ["觉得有用，点个关注"]),
]

starts = {i: name for name, i in CHAPTERS}
out = []
for i, (tts, chunks) in enumerate(L):
    item = {"tts": tts, "chunks": chunks, "gap_after": 0.5 if i + 1 in starts else 0.1}
    if i in starts:
        item["chapter"] = starts[i]
    out.append(item)
here = pathlib.Path(__file__).parent
(here / "script.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
(here / "lines.json").write_text(json.dumps([x["tts"] for x in out], ensure_ascii=False, indent=1))
print(len(out), "lines", sum(len(x["tts"]) for x in out), "chars", len(CHAPTERS), "chapters")
