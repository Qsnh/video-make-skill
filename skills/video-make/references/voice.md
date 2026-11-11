# 配音和校验

## MiMo TTS

- 接口：`POST https://api.xiaomimimo.com/v1/chat/completions`，请求头 `api-key`，模型 `mimo-v2.5-tts`。
- 导演提示放 `user` 消息，要读的文本放 `assistant` 消息，`audio: {format: "wav", voice: "<音色>"}`。
- `tools/tts.py` 读取：`MIMO_API_KEY`（或 `MIMO_ENV_FILE` 指向的 `KEY=VALUE` 文件）、`MIMO_VOICE`（默认 `冰糖`）、`MIMO_MODEL`；导演提示读工作目录下的 `audio/direction.txt`，没有这个文件时用脚本内置的通用提示。
- 一句一次请求，4 并发；偶发 `SSLEOFError`/5xx/429 自动重试 4 次。已存在的 `raw/NN.wav` 会跳过。

导演提示由三段组成，可以写在一行里：

```
【角色】知识类视频的 UP 主，年轻女生，专业、亲切、条理清楚。
【场景】给做网站和运维的观众讲一期三分钟左右的教程，主题是……。英文的配置项和命令照常读出来。
【指导】语速适中、吐字清晰……讲到日期和数字时稍微放慢……提到产品时平实自然，不要有广告腔；句末收得干净。
```

每期只改【场景】。不要写"语速偏快、逗号几乎不停顿"：变速后吞字，还出现过把导演提示念进音频末尾。

## 语速

- 用自然语速合成，再用 `tools/speed.sh raw clips 1.3`（ffmpeg `atempo`，不变调）统一加速。1.15x 用户仍嫌慢，1.3x 是默认。
- 句间停 0.1s，章节间停 0.5s（`make_script.py` 自动设置）。
- 短视频还要再压时长时，用 `silenceremove` 限制句内停顿，而不是加大倍速。
- ASR、重录一律针对变速后的 clip；有些英文词在 1.3x 下才会糊。`takes.py --rate` 要和 `speed.sh` 用同一个倍速。

## 配音文本怎么写

字幕保持原样，只改送给 TTS 的文本：

| 情况 | 写法 |
|------|------|
| 数字 | 写成读法：`四四三`、`三零一`、`二零二八年`、`一点二五点一`、`四十五天` |
| 字母缩写 | 拆开加空格：`H T T P S`、`C U R L`、`C NAME`；但 `Zero SSL` 连写反而清楚，逐个试 |
| 难读的品牌名 | `Nginx`→`Engine X`；有官方读法的按用户指定的读（例如 `1Panel`→`One Panel`） |
| 配置项、命令 | 首字母大写更清楚：`Server Name`、`Return 三零一`、`HTTP 2 On`；符号读出来：`acme 点 S H`、`Full Chain 点 P E M`、`杠 T` |
| 句首英文/字母 | 句首最容易含糊，前面垫一个词：`先看/再看/最后是/所以/这条/第三种是` |
| 连读吞字 | 加逗号断开：`acme 点 sh，续期后` |
| 怎么都读不好 | 换中文说法，英文只放画面：`Invalid`→`无效`，`Chrome`→`浏览器`；`Shell`、`certbot` 这类词尽量避开 |

一个难读的词在整期里出现次数越少越好，其余用代称（"面板""这个工具"）。

## 常见故障

- 句末多出一段乱语（约 3%–7% 的句子），表现为时长明显偏长、识别结果多出一截。
- 吞掉最后一个音节，或句首第一个词含糊。
- 同一句多次合成质量差异很大，重录往往比改写快。

所以每一句都要识别校验，不能抽查。

## ASR 校验

```bash
python3 tools/asr.py audio/clips --en
python3 tools/asr.py audio/clips --only 3,7 --en
```

每句输出：

- 第一行：文件名、时长、plain 分数（和期望文本的相似度，数字统一成阿拉伯数字后比较）。
- `want`：期望的 TTS 文本。
- `plain`：只带中性提示"以下是普通话的句子。"的识别。这个提示让输出变成简体，但不会把读错的词纠正过来。
- `prime`：用 `asr-prompt.txt` 术语表做提示的识别。
- `en`：英文模式识别。中文句子在英文模式下常被整句翻译成英文，只看里面有没有出现那个英文术语。

识别设置：whisper `small`，`temperature=0`，`condition_on_previous_text=False`。模型下载慢，`~/.cache/whisper/small.pt` 要保留。

**只对单句 clip 做识别。** 整段混音识别会把英文术语认错，不能用来判断。

### 判定

先看 plain 分数：0.9 以上且时长正常的，扫一眼即可；0.9 以下的逐句对比。

| 情况 | 结论 |
|------|------|
| plain 和期望一致，或只差同音字（步/部、公钥/功耀）、标点 | 通过 |
| plain 把英文术语认成别的，`en` 里出现了这个术语 | 通过 |
| plain 把英文术语认成读法相近的拼写（`Engine X`→`NGX`） | 通过 |
| plain 多出一截、少了字、少了最后一个音节 | 重录 |
| plain 和 `en` 都没认出术语，只有 `prime` 认对 | 不能判通过：重录 3 条，有 plain 或 `en` 认得出的就换上；都认不出，保留 plain 分数最高的那条，交付时报出时间点请用户听 |
| 年份被写成别的年份（`二零二九`→`2019`） | 用同时列出两种读法的提示复查（"二零一九年，二零二九年"），能区分就通过 |

`prime` 只用来排除"这个词 whisper 根本不认识"的可能，不能用来在几条 take 之间做选择：它会把读错的也纠正对，也可能把对的改错（例如把"字幕"改成"刺目"）。句尾有音乐时，whisper 会编出"字幕by…"之类的句子，忽略。

## 重录

```bash
python3 tools/takes.py 3,7 3
python3 tools/takes.py audio/var.json 2
```

第一条按 `lines.json` 原文给第 3、7 句各录 3 条；第二条按 spec 文件录改写版本。`audio/var.json`：

```json
{"12b": ["像免费的 Let's Encrypt，从明年起……", "所以 Let's Encrypt 从明年起……"]}
```

- 输出 `audio/takes/<key>-<改写序号>-<take序号>.raw.wav`（原速）和 `.wav`（已变速），打印 zh 分数和英文模式结果。
- 原速文件按文件名缓存，存在就不再合成。数字模式的 key 就是句号（`03`）；改了某句文本后再用数字模式重录，先删掉 `audio/takes/03-*`。spec 里的 key 不要和句号重名，每次换新文本就换新 key（`12b`、`12c`）。
- 选中后：把 `.raw.wav` 复制成 `audio/raw/NN.wav`（用 `cp`，不要保留旧时间戳）；如果用的是改写版，同步改 `make_script.py` 里该句的 TTS 文本和字幕读法并重新运行；然后 `speed.sh`（会自动重做比 raw 旧的 clip）→ `build_audio.py` → `align_chunks.py`。
- 15 条以上都读不好的词，放弃这个词，换说法。
- agent 听不见声音：实在拿不准的句子，交付时报出时间点请用户听。
