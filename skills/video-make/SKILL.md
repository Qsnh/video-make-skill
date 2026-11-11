---
name: video-make
description: Use when making a narrated explainer, tutorial or product promo video from code (B站 横屏教程, 抖音/小红书/视频号 竖屏短视频) — AI 配音 TTS、字幕、HTML 动画逐帧渲染成 MP4、视频封面、章节时间戳、发布文案; also when TTS mispronounces terms, captions drift from the voice, frame rendering breaks, or a cover gets cropped.
---

# 用代码做配音视频

## 概览

一条视频 = 定稿文案 → 逐句 TTS → 逐句 ASR 校验 → 时间轴 → HTML 动画 → 逐帧截图 → ffmpeg 合成。

**核心原则：时间轴来自音频。** 先把每一句配好、校验好，测出每个字幕段的真实起止时间，再把所有画面动画挂在这些时间点上。画面不写死秒数，配音改了重跑时间轴即可；渲染是对页面逐帧 `__seek(t)` 截图，结果确定、可重复。

适用：讲解/教程（2–5 分钟）、产品宣传短片（20–40 秒）、带字幕和章节条的知识视频。
不适用：真人出镜剪辑、需要实拍素材的视频、纯音乐 MV。

## 流程

每一步都有关口，前一步没过不要往下走。

| # | 步骤 | 产出 | 关口 | 参考 |
|---|------|------|------|------|
| 0 | 初始化 | 工作目录 | `bash scripts/init.sh <dir>` 成功 | 下文 |
| 1 | 选题、核实、文案 | `script.md`、`audio/make_script.py` | 事实已核实（要实验的先跑）；**用户明确同意文案**，才能开始配音 | references/script.md |
| 2 | 配音 | `audio/raw/NN.wav` → `audio/clips/NN.wav`（1.3x） | 每句 ASR 过一遍，问题句重录 | references/voice.md |
| 3 | 时间轴 | `build/narration.wav`、`build/timeline.json` | 字幕切分对上语音 | references/timeline.md |
| 4 | 素材 | 真实界面截图、真实终端输出 | 和口播一致，示例域名用 example.com | references/capture.md |
| 5 | 合成 | `comp/index.html` | 抽帧拼图逐张看过 | references/composition.md |
| 6 | 渲染 | `dist/video.mp4` | 时长 = 时间轴，响度 -14 LUFS | references/render.md |
| 7 | 封面、文案 | `dist/cover-bili.png`、`dist/cover-douyin.png`、`dist/copy.txt` | 封面在各平台裁切安全区内 | references/publish.md |
| 8 | 交付、清理 | 发给用户；归档源文件 | 用户确认已保存后才清理 | 下文 |

## 初始化

`bash scripts/init.sh ~/work/<项目>/video-<期名>` 把 `template/` 复制成工作目录、把 `scripts/` 复制到 `tools/`、装好 playwright-core。模板是一条能直接跑通的 30 秒演示，开工前替换这些示例内容：

- `script.md`、`audio/make_script.py`：本期文案；章节只在 `make_script.py` 的 `CHAPTERS` 里定义一次，章节间停顿、章节条、章节时间戳都从它推导。
- `audio/direction.txt`：TTS 导演提示的【场景】。
- `asr-prompt.txt`：本期术语表（规范写法，必要时附读法）。
- `comp/index.html` 的场景和动画、`comp/cover-*.html` 的封面内容。

## 常用命令

在工作目录里执行：

| 命令 | 作用 |
|------|------|
| `python3 audio/make_script.py` | 生成 `audio/script.json` 和 `audio/lines.json` |
| `python3 tools/tts.py audio/lines.json audio/raw` | 逐句配音；按文本复用已有音频，改稿后直接重跑 |
| `bash tools/speed.sh audio/raw audio/clips 1.3` | 变速不变调 |
| `python3 tools/asr.py audio/clips --en` | 逐句识别：plain / 术语提示 / 英文模式 |
| `python3 tools/takes.py 3,7 3` | 第 3、7 句各录 3 条并打分 |
| `python3 tools/takes.py audio/var.json 2` | 同一句的几种改写各录 2 条 |
| `python3 tools/tts.py audio/lines.json audio/raw --adopt 3 audio/takes/03-0-1.raw.wav` | 采用某条 take |
| `python3 tools/build_audio.py audio/clips build audio/script.json` | 拼接配音，生成时间轴 |
| `python3 tools/align_chunks.py audio/clips build/timeline.json audio/script.json` | 字幕段对齐到实际读音 |
| `node tools/render.mjs --timeline=build/timeline.json --stills=2,8.5,20` | 抽帧到 `build/stills`（每次先清空） |
| `bash tools/contact.sh build/stills build/sheets` | 2x2 拼图，用 Read 看图 |
| `bash tools/render-par.sh build/timeline.json build/narration.wav dist/video.mp4 8` | 8 进程并行渲染整片并混音 |
| `node tools/render.mjs --html=comp/cover-4x3.html --width=1440 --height=1080 --png=dist/cover-bili.png` | 出封面 |
| `python3 tools/bili_kw.py "nginx 配置ssl证书" "宝塔 https"` | 选题：B站关键词前 6 条播放量 |

依赖：ffmpeg、Node 18+、本机 Google Chrome、Python 3 + `requests` + `openai-whisper`（`small` 模型）。TTS 用小米 MiMo，Key 从环境变量 `MIMO_API_KEY` 或 `MIMO_ENV_FILE` 指向的文件读取，都没有就问用户要；换别家 TTS 只要保证每句一个 WAV。

## 最容易出错的地方

- **没审批就配音。** 文案先发用户；"继续/开始/可以"算同意。为了读音改了措辞，交付时逐条告诉用户。
- **字幕和配音写成一份。** 字幕给人看（`Nginx`、`443`、`1.3`），配音给 TTS 读（`Engine X`、`四四三`、`一点三`）。`make_script.py` 里用 `P(字幕, 读法)` 分开写，各段读法拼起来要等于整句 TTS 文本。
- **只听整段混音。** 整段识别会把英文术语认错，必须逐句识别。选 take 只看 plain 分数和 `--en` 结果；带术语提示的 prime 会把读错的也"纠正"对，判定规则见 voice.md。
- **把秒数写死在动画里。** 第一句开始之后的动画一律写 `T(句, 段)`；变速、重录后时间都会变。
- **页面开头空着。** 卡片出现后 2–3 秒还是空的，看起来像卡住了；内容在本章第一个字幕段就要出来。
- **同一元素多段 `fill: both` 动画、重复 id。** WAAPI 不报错，元素会整段消失或停在错误状态，见 composition.md。
- **用 `file://` 打开页面渲染。** CSS mask 等会失效；`render.mjs` 自带本地 HTTP 服务。
- **封面被平台裁掉。** B站一张图同时裁 4:3 和 16:9，抖音 9:16 会被裁成 3:4，内容只放安全区。
- **违规导流。** 画面、封面、文案里不放指向真实站点的网址、二维码、联系方式，不写"可以看看/搜一下"；`example.com` 这类保留示例域名可以出现在演示界面和终端里。跨平台发布的视频不拿某个内容平台当示例；宣传片不讲价格。
- **先报成功再看结果。** 发进度消息要等命令跑完、看到输出之后。

## 交付和清理

1. 交付：成片、B站 4:3 封面、抖音 9:16 封面、`dist/copy.txt`（标题、标签、简介、章节时间戳）。B站视频默认也会发到抖音等平台，所以竖版封面和抖音文案一起出；用户明确只发一个平台时只出那一套。列出所有为读音改过的措辞，以及没把握的时间点请用户听一下。
2. 文件超过聊天工具上限（常见 30MB）时，先发 `crf 22` 预览版，并说明高清版位置。大文件发送超时重发后，提醒用户可能收到两份。
3. 用户确认素材已保存后：把可复用源文件（`comp/` 及用到的素材、`audio/make_script.py`、变体 spec、`script.md`、`copy.txt`、`direction.txt`、`asr-prompt.txt`、截图脚本、`lab/`）归档到用户的模板库（没有约定就问用户放哪，例如 `~/work/<项目>/video-template/<期名>/`），`diff -r` 逐个比对一致后，再删工作目录、临时浏览器 profile、容器、开发服务器（按 PID 杀，先确认命令行）和只为截图装的前端依赖。whisper 模型缓存和 Docker 镜像保留。
