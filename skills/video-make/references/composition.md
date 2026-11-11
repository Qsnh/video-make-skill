# HTML 合成

## 页面契约

`render.mjs` 通过本地 HTTP 打开 `comp/index.html`，注入 `window.TIMELINE`，然后对每一帧调用 `window.__seek(t)` 并截图。页面必须：

1. 用 `el.animate(...)` 建好全部动画并立即 `pause()`。
2. 提供 `window.__seek = (t) => { for (const a of document.getAnimations()) a.currentTime = t * 1000; captionAt(t) }`。
3. 提供 `window.__duration = TIMELINE.duration`。
4. 不依赖真实时间（不用 `setTimeout`、自动播放的 CSS `animation`、`Date.now()`）；需要逐帧计算的效果（计数器、字幕）在 `__seek` 里按 `t` 算。
5. 不抛错：页面 JS 报错（`pageerror`）会让渲染直接失败，比如 `T(i, j)` 引用了不存在的句子或字幕段。

模板 `template/comp/index.html` 已实现以上全部，新视频从它改。

## 时间锚点和章节

```js
const T = (i, j = 0) => S[i].chunks[j].start
const E = (i) => S[i].end
const CHAPTERS = S.flatMap((s, i) => (s.chapter ? [[s.chapter, i]] : []))
const SCENES = ["#s1", "#s2", "#s3", "#s4"]
```

- `T(i, j)`：第 i 句第 j 个字幕段开始；`E(i)`：第 i 句结束。
- 章节从时间轴读（源头是 `make_script.py` 的 `CHAPTERS`），页面里不再手写。章节分界 `CUT` 取上一句结束和本句开始的中点；场景切换、章节条都挂在 `CUT` 上。
- 一个章节一个场景（`<section class="scene">`），`SCENES` 的个数要等于章节数。
- 场景内元素挂在 `T(i, j)` 上，通常提前 0.05–0.1s 出现。只有第一句开始之前的开场动画可以用固定秒数。

## 动画和填充模式

模板里的辅助函数：

| 函数 | 效果 | fill |
|------|------|------|
| `show(el, at)` / `pop(el, at)` / `fadeIn(el, at)` | 位移淡入 / 缩放弹出 / 淡入 | both |
| `hide(el, at)` / `fadeOut(el, at)` | 淡出 | forwards |
| `ring(el, at, until)` | 高亮框出现，可带结束时间 | both + forwards |
| `hidden(el)` | 从 0 秒起保持透明，直到后面的动画接管 | forwards |
| `flash(i, at)` | 章节条第 i 段闪一下 | forwards |
| `anim(el, frames, at, dur, { fill, easing })` | 通用 | 默认 both |

规则：

- **一个元素的第一段动画可以用 `fill: both`**（`show`、`pop`、`fadeIn`），它会在开始前把元素保持在起始状态（透明）。
- **同一元素同一属性的第二段及以后的动画一律用 `fill: forwards`。** 后创建的 `both` 动画会在它开始之前就把属性锁成它的起始值，覆盖前面所有动画，元素会整段消失或提前出现。链式镜头移动、显示→隐藏→再显示都属于这种情况。
- **要先隐藏、之后用 `forwards` 动画显示的元素，先调用 `hidden(el)`，再创建显示动画。** 动画的叠加顺序按创建顺序，后创建的在生效时覆盖先创建的。
- WAAPI 出错时不报错，只会表现为画面不对，所以每个改动都要抽帧看。

## 其他坑

- **重复 id。** 跨场景复制 HTML 时容易出现两个相同 id，`$()` 只拿到第一个，另一个的动画完全不生效。渲染前检查：

  ```bash
  grep -o 'id="[^"]*"' comp/index.html | sort | uniq -d
  ```

- **公共样式的类名冲突。** 基础样式里的通用类（如固定高度的 `.row`）会把自定义布局撑坏，新组件用独立类名。
- **空卡片。** 卡片出现后 2–3 秒内容还没出来，看着像卡住了；本章第一个字幕段就要有内容。
- **容器和徽章。** 装不同宽度徽章、要来回切换的槽位，本身不能是徽章，否则宽度跟着跳。
- **固定间隔错开的动画。** 变速或重录后对照新的字幕段长度复查。
- **`file://`。** CSS mask 等在 file 协议下失效，始终经 `render.mjs` 的本地 HTTP 打开。
- **颜色变量。** 背景变量如果是渐变（模板的 `--page`），不能拿来当文字颜色。

## 截图镜头

展示真实界面截图时，用一个固定尺寸的"镜头"容器放大局部：

```js
const camT = (x, y, w, view = 1000) => { const s = view / w; return `translate(${-x * s}px, ${-y * s}px) scale(${s})` }
```

- 截图是 2 倍图（`deviceScaleFactor: 2`），在页面里按截图时的 CSS 视口宽度显示（1180px 视口截的图就设 `width: 1180px`），这样截图时记录的元素坐标可以直接用。
- 结构是三层：镜头容器（固定尺寸，`overflow: hidden`）→ 画布层（`position: relative; transform-origin: 0 0`，动画的 `transform` 加在这一层）→ 截图 `img` 和若干高亮框（都绝对定位在画布层里）。`camT(x, y, w)` 把截图里从 (x, y) 开始、宽 w 的区域放大到镜头宽度 `view`，高亮框跟着画布层一起缩放平移。
- 高亮框的 `left/top/width/height` 直接取截图时记录的 `*.boxes.json`（见 capture.md）；裁剪过的截图要先减去裁剪起点。不要目测坐标。
- 连续镜头移动按上面的规则，第二段起用 `fill: "forwards"`。

## 视觉风格

- 产品相关的视频，画面风格贴近产品自己的设计系统（颜色、圆角、字重、图标库），用它的 design tokens。
- 不要伪造产品外壳（假侧边栏菜单、假头像栏）。进度用顶部章节条：按章节时长分段、带标签和分隔线、已播放部分填充、底部进度线、当前章节标签加深。
- 浅色页面不要纯白（刺眼），用很浅的灰底叠一层淡色渐变，上面放白卡片；1px 浅灰边框、大圆角、基本不用阴影；字重只用 400/500；绿/橙/红只出现在小徽章上。
- 深色版：`<html class="dark">`，模板已带一套深色变量。
- 1920×1080 画布：正文 24px，页面标题 54px，字幕 42px（8px 描边 + `paint-order: stroke fill`）。
- 图标：`npm i --no-save lucide-react` 后运行 `node tools/icons.mjs node_modules/lucide-react/dist/esm/icons shield-check timer`，覆盖生成 `comp/icons.js`（模板自带一个空的，并已引用）。页面里写 `<svg class="ic" data-i="shield-check" viewBox="0 0 24 24"></svg>`。lucide 的别名文件（如 `history`）会被跳过，改用正式名。

### 宣传短片（深色科技风）

- 结构：开场就是品牌，然后一个功能接一个功能；除非用户要求，不用痛点开场。
- 只用品牌自有元素：logo 几何拆成可动画的 SVG、品牌色、像素块转场、`steps()` 节奏。
- 避免"AI 味"：不用紫色渐变、发光、粒子、毛玻璃。
- 先发分镜给用户确认，再出关键帧，再做整片。

## 大文件组织

画面很多时把页面拆成 `head-base.css.txt`（公共样式）+ `<期名>-body.html`（本期内容和脚本），用一个 `assemble.py` 拼成 `index.html`：

```python
import pathlib
d = pathlib.Path(__file__).parent
(d / "index.html").write_text((d / "head-base.css.txt").read_text() + (d / "ep-body.html").read_text())
```

## 抽帧检查

```bash
node tools/render.mjs --timeline=build/timeline.json --stills=1.5,5.6,9,13.5,20,31
bash tools/contact.sh build/stills build/sheets
```

每章至少取两帧（刚进入、讲到一半），加上每个高亮、切换的时间点，以及 align 时标了 `keep pause times` 的句子。逐张用 Read 看：空卡片、文字溢出、元素重叠、高亮框错位、字幕和画面不同步、按钮文字和背景同色。
