# 时间轴和字幕

## build_audio.py

```bash
python3 tools/build_audio.py audio/clips build audio/script.json
```

- 用 `silencedetect`（-40dB）找每句的有声起止，前留 0.06s、后留 0.14s，开头空 0.3s，结尾留 2s 给最后一屏。
- 按 `gap_after` 依次排开，`amix` 混成 `build/narration.wav`，并 `loudnorm` 到 -14 LUFS。
- 生成 `build/timeline.json`：

```json
{
  "duration": 31.165,
  "sentences": [
    {"start": 0.36, "end": 3.98, "chapter": "开场", "chunks": [
      {"text": "字幕段", "say": "读法", "start": 0.36, "end": 2.39}
    ]}
  ]
}
```

- `chapter` 只出现在章节首句上。
- 字幕段的初始切分：按读法的字数加权估算位置（英文按音节、大写缩写按字母数），再吸附到 ±0.8s 内最近的句内停顿。

## align_chunks.py

```bash
python3 tools/align_chunks.py audio/clips build/timeline.json audio/script.json
```

- 用 whisper 词级时间戳（以该句 TTS 文本作提示）把每个字幕段的边界对到实际读到的位置，再吸附到附近的停顿。比只按停顿吸附准：有一期按停顿切的边界差了 0.8s。
- 识别文本与读法相似度低于 0.9，或对齐后某段短于 0.6s 时，自动保留按停顿切的时间，打印 `keep pause times`。英文多的句子常走这条路，这些句子抽帧时重点看字幕。
- 输出每句的切分结果 `起始时间:字幕段 [相似度]`，扫一眼有没有明显不合理的。
- 它直接改写 `timeline.json`。重跑 `build_audio.py` 会覆盖对齐结果，所以每次重建音频后都要再跑一次。
- 某句切得仍然不好时，回到 `make_script.py` 调整这一句的字幕段（换切分点、拆成两句），不要手改 `timeline.json`，下次重建就丢了。

## 字幕规则

- 一屏一段，中文 20 字左右以内；画布 1920 宽时字幕框 1440px、42px 字号，超长自动缩到 30px。
- 在逗号、顿号处切；不要把一个术语切到两屏。
- 字幕段里的数字、英文写规范形式（`1.25.1`、`nginx -t`、`fullchain.pem`），读法只出现在 `say` 里。
- 字幕在段开始前 0.04s 淡入；两段之间的短暂停顿（<0.35s）保留上一段，避免闪烁；最后一段说完就消失。

## 改动后的重跑顺序

| 改了什么 | 重跑 |
|----------|------|
| 某句重录（文本不变） | 把选中的 take 复制成 `raw/NN.wav` → `speed.sh` → `build_audio.py` → `align_chunks.py` → 抽帧 |
| 改了某句的 TTS 文本 | 改 `make_script.py` 并运行 → 删 `audio/raw/NN.wav`（`tts.py` 会跳过已存在的文件）→ `tts.py` → `speed.sh` → `asr.py --only NN` → `build_audio.py` → `align_chunks.py` |
| 只改字幕文字（读法不变） | 改 `make_script.py` 并运行 → `build_audio.py` → `align_chunks.py` |
| 改章节划分 | 改 `CHAPTERS` 并运行 `make_script.py` → `build_audio.py` → `align_chunks.py`；页面里场景数（`SCENES`）要和章节数一致 |
| 增删句子 | 音频按句号存放，插入点之后的编号全部错位：把 `raw/` 里插入点之后的文件按新编号改名（从后往前改），删掉 `clips/` 重新 `speed.sh`，新句子 `tts.py` 补录；页面里所有 `T(i, j)`、`E(i)` 的句号同步调整 |
| 改倍速 | 清空 `clips/` → `speed.sh` → `asr.py` → `build_audio.py` → `align_chunks.py` |
| 只改画面 | 直接抽帧/渲染 |

变速或重录后，所有按固定间隔错开的动画（如 `T(4, 0) + i * 0.45`）要对照新的字幕段长度复查，段变短后动画可能跑到下一段去。
