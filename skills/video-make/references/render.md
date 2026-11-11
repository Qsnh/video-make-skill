# 渲染

## 准备

- `bash scripts/init.sh <dir>` 已在工作目录装好 `playwright-core`；渲染用本机 Google Chrome（`channel: "chrome"`），不用下载 Playwright 自带浏览器。
- 启动参数 `--force-color-profile=srgb --font-render-hinting=none`，输出按 bt709 标记，颜色和网页一致。

## 单帧和抽帧

```bash
node tools/render.mjs --timeline=build/timeline.json --stills=2,8.5,20
node tools/render.mjs --timeline=build/timeline.json --png=build/f.png --at=12.3
bash tools/contact.sh build/stills build/sheets
```

第一条把每个时间点存成 `build/stills/t0002.00.png` 这样的文件（先删掉目录里旧的 `t*.png`），第二条只出一帧，第三条把抽帧按 4 张一组拼成 `build/sheets/sheetNN.png`（先删旧的 sheet）。

整片渲染前一定先抽帧看一遍，比渲完再返工快得多。

## 整片

```bash
bash tools/render-par.sh build/timeline.json build/narration.wav dist/video.mp4 8
```

- 把总帧数平均分给 N 个 Chrome 进程，各自 seek + 截图 + 管道进 ffmpeg（libx264、crf 16、yuv420p、30fps），再无损拼接。
- 实测：8 进程渲 5,400–6,400 帧（3–3.5 分钟）约 80–90 秒。
- 混入配音：测出 narration 的积分响度，补增益到 -14 LUFS，`alimiter` 防削波，AAC 192k，`+faststart`。
- 环境变量：`HTML`（默认 `comp/index.html`）、`FPS`（默认 30）、`LUFS`（默认 -14）。
- 某个分段失败时脚本会打印各段日志末尾并退出；页面 JS 报错（`pageerror`）会让该段直接失败。

## 验收

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact dist/video.mp4
```

- 时长 = `timeline.json` 的 `duration`（误差一帧内）。
- `render-par.sh` 最后一行打印的输出响度在 -14 LUFS 左右。
- 在每个章节分界附近再抽一两帧确认切换正常。
- 文件大小参考：3–4 分钟 crf 16 约 11–16MB。

## 发给用户

- 聊天工具限制附件大小（常见 30MB）。超过时先发预览版：

  ```bash
  ffmpeg -i dist/video.mp4 -c:v libx264 -crf 22 -tune animation -preset medium -c:a copy -movflags +faststart dist/preview.mp4
  ```

  4.5 分钟约 16MB；同时告诉用户高清版的路径。
- 大文件发送可能报超时但其实已送达，重发后提醒用户可能收到两份。

## 背景音乐

配音视频默认只有人声，不加音乐和音效，除非用户要求。用户要音乐时：

- 平台内的音乐库对企业号有限制（例如商用曲库、剪辑软件的商用授权只覆盖本平台），优先用代码合成的原创配乐。
- 用 numpy 合成方波/脉冲波时要减掉直流分量（`2·duty−1`），否则每个音符都会"咚"一下；用 `showspectrumpic` 看频谱确认。
- 配乐 `volume=-8dB`，对人声做 sidechain 压缩（ratio 2、threshold 0.08），让配乐比人声低 10–14dB；人声下面不要有主旋律。
- agent 听不见：按各轨 RMS 在同一尺度上测量来平衡，最后请用户听。
