# video-make-skill

把"用代码做配音视频"的完整流程做成一个 Agent Skill：文案 → AI 配音（TTS）→ 逐句语音识别校验 → 时间轴和字幕 → HTML 动画 → 逐帧渲染成 MP4 → 封面和发布文案。

这些步骤和经验来自一个系列教程视频（B站横屏 3–4 分钟教程、抖音/小红书/视频号竖屏短片）的实际制作，踩过的坑都写进了文档。

## 包含什么

```
skills/video-make/
├── SKILL.md              流程总览、命令速查、最常见的错误
├── references/
│   ├── script.md         选题、标题、文案长度和结构、审批、事实核查、平台合规
│   ├── voice.md          MiMo TTS、语速、配音文本写法、ASR 校验、重录
│   ├── timeline.md       音频拼接、时间轴、字幕切分和对齐
│   ├── composition.md    HTML + WAAPI 合成的页面契约、时间锚点、坑、视觉风格
│   ├── capture.md        真实界面截图（mock 接口）、中文 Chrome 报错页、Docker 复现终端输出
│   ├── render.md         抽帧检查、多进程渲染、响度、预览版、背景音乐
│   └── publish.md        B站/抖音封面安全区、发布文案、章节时间戳
├── scripts/              init.sh、tts.py、speed.sh、asr.py、takes.py、textnorm.py、build_audio.py、
│                         align_chunks.py、render.mjs、render-par.sh、contact.sh、icons.mjs、bili_kw.py
└── template/             可直接跑通的 30 秒演示项目（4 个章节、字幕、章节条、4:3 和 9:16 封面）
```

## 安装

Claude Code：

```bash
git clone https://github.com/Qsnh/video-make-skill.git
cp -R video-make-skill/skills/video-make ~/.claude/skills/
```

其他支持 Agent Skills 的工具，把 `skills/video-make` 放进对应的 skills 目录即可。

## 依赖

- ffmpeg
- Node.js 18+，本机安装的 Google Chrome
- Python 3，`pip install requests openai-whisper`（首次运行会下载 whisper `small` 模型）
- 小米 MiMo TTS 的 API Key：`export MIMO_API_KEY=...`，或 `export MIMO_ENV_FILE=~/.config/mimo.env`（文件里写 `MIMO_API_KEY=...`，可选 `MIMO_VOICE`、`MIMO_MODEL`）。换别家 TTS 时只需改 `scripts/tts.py`，保证每句输出一个 WAV。

## 跑一遍演示

```bash
bash skills/video-make/scripts/init.sh /tmp/demo-video
cd /tmp/demo-video
python3 audio/make_script.py
python3 tools/tts.py audio/lines.json audio/raw
bash tools/speed.sh audio/raw audio/clips 1.3
python3 tools/asr.py audio/clips --en
python3 tools/build_audio.py audio/clips build audio/script.json
python3 tools/align_chunks.py audio/clips build/timeline.json audio/script.json
node tools/render.mjs --timeline=build/timeline.json --stills=1.5,5.6,9,31
bash tools/contact.sh build/stills build/sheets
bash tools/render-par.sh build/timeline.json build/narration.wav dist/video.mp4 8
node tools/render.mjs --html=comp/cover-4x3.html --width=1440 --height=1080 --png=dist/cover-bili.png
```

在 Apple Silicon Mac 上，演示项目 31 秒 935 帧用 8 个进程渲染约 15 秒，输出 1920×1080 30fps、-14 LUFS。
