# 素材：截图和真实输出

画面里的界面、报错页、终端输出都用真实的，不手画。拿不到真实的，就做成卡片并标"示例"。

## 产品界面（mock 接口）

起前端开发服务器，用 playwright 拦截接口返回演示数据，截图：

```js
import { chromium } from "playwright-core"
import { writeFileSync } from "node:fs"
const browser = await chromium.launch({ channel: "chrome" })
const ctx = await browser.newContext({ viewport: { width: 1180, height: 800 }, deviceScaleFactor: 2, locale: "zh-CN", colorScheme: "light" })
await ctx.addInitScript((u) => localStorage.setItem("app-auth", JSON.stringify({ token: "demo", user: u })), { id: "1", email: "demo@example.com" })
const page = await ctx.newPage()
const seen = new Set()
await page.route((url) => url.pathname.startsWith("/api/"), (route) => {
  const url = new URL(route.request().url())
  seen.add(url.pathname)
  const body = url.pathname.endsWith("/certs") ? { items: [{ id: "1", domain: "example.com" }], total: 1 } : {}
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
})
await page.goto("http://127.0.0.1:5173/certs", { waitUntil: "networkidle" })
if (await page.getByRole("dialog").count()) await page.keyboard.press("Escape")
await page.mouse.move(0, 0)
const boxes = { deploy: await page.getByRole("button", { name: "部署" }).boundingBox() }
await page.screenshot({ path: "comp/assets/certs.png" })
writeFileSync("comp/assets/certs.boxes.json", JSON.stringify(boxes, null, 1))
console.log([...seen].join("\n"))
await browser.close()
```

- 打印 `seen` 看页面实际请求了哪些接口，逐个补 mock；登录态、弹窗、引导浮层都要处理掉（每日弹窗、客服二维码等先关）。
- 视口 1180px 左右 + `deviceScaleFactor: 2`：侧栏会自动收起，文字放进视频后仍然清楚。页面太宽时，裁剪局部或把几条横条叠起来（如对话框标题 + 记录行），不要整页缩小。
- 截图时把要高亮的元素的 `boundingBox()` 存进同名的 `*.boxes.json`（`{"名字": {"x", "y", "width", "height"}}`，单位是截图时视口的 CSS 像素，和 2 倍图的物理像素差一倍）。合成时按 composition.md 的"截图镜头"换算成高亮框位置。
- 演示数据：域名用 `example.com` 及其子域、`demo-*.com`；日期相对当前时间生成；状态码的含义先查代码确认（比如 1 是成功还是失败）。
- 第三方面板（宝塔、1Panel 等）能用 Docker 起的就起一个，往它的数据库里灌演示数据；截完把会触发真实请求的定时任务关掉（例如自动续期会去请求正式 CA）。

## 浏览器报错页（中文 Chrome）

- macOS 上让 Chrome 显示中文界面：包一层脚本，在参数末尾加 `-AppleLanguages "(zh-CN)"`：

  ```sh
  #!/bin/sh
  exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "$@" -AppleLanguages "(zh-CN)"
  ```

- Playwright 默认启动参数会关掉一些安全特性（如 HTTPS 自动升级），要拍真实行为时，自己启动 Chrome（`--headless --remote-debugging-port=... --user-data-dir=<临时目录> --lang=zh-CN --no-proxy-server`），再 `chromium.connectOverCDP()` 连上去。2x 截图用 CDP 的 `Emulation.setDeviceMetricsOverride`。
- 证书错误页：本地起一个用自建 CA 签的 HTTPS 服务；HSTS 版报错页需要先在 `chrome://net-internals/#hsts` 加域名，再用 `--host-resolver-rules="MAP www.example.com 127.0.0.1:8443"` 指过去。本机有代理时必须加 `--no-proxy-server`，否则代理会绕过 resolver 规则。
- `chrome://interstitials/` 能直接打开各种拦截页，需先在 `chrome://chrome-urls` 点 "Enable internal debugging pages"。
- 截完在 DOM 里把主机名换成 `example.com`。
- 用完删除临时 user-data-dir，确认没有残留的 headless Chrome 进程。

## 终端输出（实验环境）

- 在 Docker 里真实跑一遍，把输出原样放进画面。写一个 `lab/run.sh` 能从零复现所有输出，归档时一起保存。
- 自建演示 CA 用 OpenSSL 3（Homebrew `openssl@3`）；macOS 自带的 LibreSSL 生成的 ECC 证书带显式曲线参数，curl 会拒绝。
- 验证配置和报错时可以绕过镜像自带的启动脚本直接跑程序（如 `docker run --rm --entrypoint nginx nginx:alpine -t`），每次实验一个配置文件；运行中改写 bind mount 的文件会读到半截内容。画面上展示给观众照着做的命令，要用他们实际会执行的写法，并且也要跑过。
- 本机走 TUN/fake-ip 代理时，任何 TCP 连接都会被"接通"，复现不了连接超时；在容器里 `--cap-add NET_ADMIN` + `iptables -A OUTPUT -p tcp --dport 443 -j DROP` 才能拿到真实的超时报错。
- 演示用的私钥、证书链是一次性的，不要用真实证书私钥。

## 拿不到真实素材时

- 第三方后台登录不了、本地没法搭：把日志/配置做成源码风格卡片，角标标"示例"；或者列出需要的截图清单请用户提供。
- 文档页面直接抓不到时，可以用 `curl https://r.jina.ai/<url>` 取正文。
