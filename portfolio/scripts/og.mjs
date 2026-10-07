// Renders public/og.png (1200x630 link preview) in the site's style.
// Usage: node scripts/og.mjs   (uses CHROMIUM_PATH if set)
import { chromium } from "playwright";
import { readFileSync } from "node:fs";

// fonts are inlined: a page set with setContent() cannot load file:// URLs
const font = (p) => `data:font/woff2;base64,${readFileSync(`node_modules/@fontsource/${p}`).toString("base64")}`;
const html = `<!doctype html><html><head><style>
@font-face { font-family: Archivo; font-weight: 900; src: url(${font("archivo/files/archivo-latin-900-normal.woff2")}); }
@font-face { font-family: Plex; font-weight: 400; src: url(${font("ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2")}); }
html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; background: #1d1813; }
canvas { position: absolute; inset: 0; }
.shade { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(20,16,12,.92) 0%, rgba(20,16,12,.55) 55%, rgba(20,16,12,.2)); }
.box { position: absolute; inset: 64px; color: #fff; display: flex; flex-direction: column; justify-content: space-between; }
.name { font: 900 30px/1 Archivo; letter-spacing: -.01em; }
.name small { display: block; font-size: 13px; letter-spacing: .06em; margin-top: 4px; }
h1 { font: 900 74px/.95 Archivo; text-transform: uppercase; margin: 0; letter-spacing: -.01em; }
.tag { font: 400 17px/1 Plex; letter-spacing: .04em; text-transform: uppercase; display: flex; gap: 28px; align-items: center; }
.btn { background: #d2261a; padding: 14px 20px; }
.c { position: absolute; width: 22px; height: 22px; border: 0 solid #d2261a; }
</style></head><body><canvas id="c" width="1200" height="630"></canvas><div class="shade"></div>
<i class="c" style="left:40px;top:40px;border-top-width:2px;border-left-width:2px"></i>
<i class="c" style="right:40px;top:40px;border-top-width:2px;border-right-width:2px"></i>
<i class="c" style="left:40px;bottom:40px;border-bottom-width:2px;border-left-width:2px"></i>
<i class="c" style="right:40px;bottom:40px;border-bottom-width:2px;border-right-width:2px"></i>
<div class="box"><div class="name">NGUYEN LE<small>ACADEMIC JOURNEY</small></div>
<h1>Research<br>that holds up<br>in imperfect data</h1>
<div class="tag"><span class="btn">[ 3 × Q1 · FIRST AUTHOR ]</span><span>Data mining · Educational ML · Valedictorian 2026</span></div></div>
<script>
const x = document.getElementById("c").getContext("2d"), w = 1200, h = 630, cell = 10;
x.fillStyle = "#d8c7aa"; x.beginPath();
for (let y = 5; y < h; y += cell) for (let X = 5; X < w; X += cell) {
  const f = Math.sin(X*.0042+.3)*Math.cos(y*.006-.2) + .5*Math.sin((X+y)*.009+.5) + .25*Math.sin(X*.021-y*.013+.8);
  const c = ((f*2.2)%1+1)%1, band = 1-Math.abs(c-.5)*2, ny = y/h;
  const r = (Math.pow(band,3)*(.25+.75*ny)+.08*ny)*cell*.55;
  if (r > .35) { x.moveTo(X+r, y); x.arc(X, y, r, 0, Math.PI*2); }
}
x.fill();
</script></body></html>`;

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(html, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: "public/og.png" });
await browser.close();
console.log("wrote public/og.png");
