# 封面和发布文案

B站视频默认也会发到抖音等平台，所以 B站 和抖音两套封面一起出；用户明确只发一个平台时只出那一套。

## 尺寸和安全区

| 平台 | 画布 | 安全区 | 原因 |
|------|------|--------|------|
| B站 | 1440×1080（4:3） | 中间 16:9 横带，y 135–945 | 同一张图在首页推荐裁成 4:3、在个人空间裁成 16:9 |
| 抖音 | 1080×1920（9:16） | 中间 3:4 区域，y 240–1680 | 主页列表裁成 3:4 |
| 抖音合集 | 1080×1080，≤5MB | 居中 | — |

模板 `comp/cover-4x3.html`、`comp/cover-9x16.html`，地址加 `?guide` 会画出安全区虚线，检查完去掉再出图：

```bash
node tools/render.mjs "--html=comp/cover-4x3.html?guide" --width=1440 --height=1080 --png=build/cover-guide.png
node tools/render.mjs --html=comp/cover-4x3.html --width=1440 --height=1080 --png=dist/cover-bili.png
node tools/render.mjs --html=comp/cover-9x16.html --width=1080 --height=1920 --png=dist/cover-douyin.png
```

## 封面内容

- 一个大标题（搜索关键词）+ 一张体现本期结构的图：步骤 1-2-3、几类方案各一格、关键数字（如 398 → 200 → 47 天）、一个典型报错行。
- 封面要覆盖本期讲的每一类内容，不能只挑几个。
- 不加"一张选型表"这类总结性标签；抖音封面不写集数。
- 不放网址、二维码。
- 缩到 200px 宽看一眼，标题仍要能读：`ffmpeg -y -i dist/cover-bili.png -vf scale=200:-1 build/thumb.png`，再用 Read 看 `build/thumb.png`。
- 合集封面只放品牌标志 + 合集名，不列各集目录。用户给的表单截图没写是哪个平台时，先问清楚。

## 发布文案（dist/copy.txt）

```
【B站】
标题：<搜索关键词式标题>
分区：<分区>
标签：<8–10 个关键词>

简介：
<一两句说明本期内容；素材来源（如"终端画面是本地实际运行的输出，域名用 example.com 代替"）>

00:00 开场
00:16 <章节名：具体内容>
……

要点：
· <3–5 条，每条一句>

<产品一句话说明，平实陈述，不讲价格>

【抖音】
<一段话：问题 + 本期讲清什么>
#话题1 #话题2 …
```

- 章节时间戳取章节分界（上一句结束和章节首句开始的中点），四舍五入到秒，直接从时间轴算：

  ```bash
  node -e 'const S=require("./build/timeline.json").sentences;S.forEach((s,i)=>{if(!s.chapter)return;const c=Math.round(i?(S[i-1].end+s.start)/2:0);console.log(`${String(Math.floor(c/60)).padStart(2,"0")}:${String(c%60).padStart(2,"0")} ${s.chapter}`)})'
  ```

  简介里的章节名可以比章节条上的更长、更具体。
- 平台名只出现在对应平台的文案里；小红书不发带产品推广的版本。
