import { readFileSync, writeFileSync } from "node:fs"
const [dir, ...names] = process.argv.slice(2)
if (!dir || !names.length) {
  console.error("usage: node tools/icons.mjs node_modules/lucide-react/dist/esm/icons shield-check timer ...")
  process.exit(1)
}
const out = {}
for (const n of names) {
  const src = readFileSync(`${dir}/${n}.mjs`, "utf8")
  const m = src.match(/node: (\[[\s\S]*?\])(?:,\n  aliases: \[[^\]]*\])?\n\};/) ?? src.match(/const __iconNode = (\[[\s\S]*?\]);/)
  if (!m) {
    console.error(`skip ${n}: alias file or unknown format, use the canonical icon name`)
    continue
  }
  const nodes = Function(`return ${m[1]}`)()
  out[n] = nodes.map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).filter(([k]) => k !== "key").map(([k, v]) => `${k}="${v}"`).join(" ")}/>`).join("")
}
writeFileSync("comp/icons.js", `window.ICONS = ${JSON.stringify(out)};\n`)
console.log(Object.keys(out).length, "icons -> comp/icons.js")
