import { chromium } from "playwright-core"
import { spawn } from "node:child_process"
import { readFileSync, readdirSync, mkdirSync, existsSync, rmSync } from "node:fs"
import { resolve, dirname, extname, join, basename } from "node:path"
import { createServer } from "node:http"

const args = Object.fromEntries(process.argv.slice(2).map((a) => a.replace(/^--/, "").split("=")))
const html = resolve(args.html ?? "comp/index.html")
const timeline = args.timeline ? JSON.parse(readFileSync(args.timeline, "utf8")) : null
const fps = Number(args.fps ?? 30)
const width = Number(args.width ?? 1920)
const height = Number(args.height ?? 1080)

const root = dirname(html)
const types = { ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2" }
const server = createServer((req, res) => {
  const file = join(root, decodeURIComponent(new URL(req.url, "http://x").pathname))
  if (!file.startsWith(root) || !existsSync(file)) { res.writeHead(404); res.end(); return }
  res.writeHead(200, { "content-type": types[extname(file)] ?? "application/octet-stream" })
  res.end(readFileSync(file))
})
await new Promise((r) => server.listen(0, "127.0.0.1", r))
const base = `http://127.0.0.1:${server.address().port}/`
const finish = async (browser) => { await browser.close(); server.closeAllConnections(); server.close(); process.exit(0) }

const browser = await chromium.launch({ channel: "chrome", args: ["--force-color-profile=srgb", "--font-render-hinting=none"] })
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 })
page.on("pageerror", (e) => { console.error("pageerror", e.message); process.exit(1) })
if (timeline) await page.addInitScript((tl) => { window.TIMELINE = tl }, timeline)
await page.goto(base + basename(html), { waitUntil: "load" })
await page.evaluate(async () => {
  await document.fonts.ready
  await Promise.all([...document.images].map((img) => (img.complete ? null : new Promise((r) => (img.onload = img.onerror = r)))))
})
await page.waitForTimeout(300)

if (args.stills) {
  const outDir = resolve(args.out ?? "build/stills")
  mkdirSync(outDir, { recursive: true })
  for (const f of readdirSync(outDir)) if (/^t[\d.]+\.png$/.test(f)) rmSync(join(outDir, f))
  for (const t of args.stills.split(",").map(Number)) {
    await page.evaluate((s) => window.__seek(s), t)
    await page.screenshot({ path: `${outDir}/t${t.toFixed(2).padStart(6, "0")}.png` })
  }
  await finish(browser)
}

if (args.png) {
  await page.evaluate((s) => window.__seek?.(s), Number(args.at ?? 0))
  mkdirSync(dirname(resolve(args.png)), { recursive: true })
  await page.screenshot({ path: resolve(args.png) })
  await finish(browser)
}

const duration = await page.evaluate(() => window.__duration)
const total = Math.round(duration * fps)
const start = Number(args.start ?? 0)
const end = Math.min(total, Number(args.end ?? total))
const out = resolve(args.out ?? "build/out.mp4")
mkdirSync(dirname(out), { recursive: true })
const ff = spawn("ffmpeg", [
  "-hide_banner", "-loglevel", "error", "-y",
  "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
  "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", String(fps),
  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
  out,
], { stdio: ["pipe", "inherit", "inherit"] })
const started = Date.now()
for (let i = start; i < end; i++) {
  await page.evaluate((s) => window.__seek(s), i / fps)
  const buf = await page.screenshot({ type: "png" })
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r))
  if ((i - start) % 300 === 0) process.stdout.write(`[${basename(out)}] frame ${i - start}/${end - start} ${((Date.now() - started) / 1000).toFixed(0)}s\n`)
}
ff.stdin.end()
await new Promise((r, j) => ff.on("close", (code) => (code === 0 ? r() : j(new Error(`ffmpeg ${code}`)))))
console.log(`done ${out} ${end - start} frames in ${((Date.now() - started) / 1000).toFixed(0)}s`)
await finish(browser)
