// Full-page screenshots at 4 widths + a reduced-motion pass.
// Usage: node scripts/shots.mjs [url]   (default http://localhost:4321)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const url = process.argv[2] ?? "http://localhost:4321";
const widths = [375, 768, 1280, 1440];
mkdirSync("qa", { recursive: true });

const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}
);
for (const reduced of [false, true]) {
  for (const w of widths) {
    if (reduced && w !== 375 && w !== 1440) continue;
    const ctx = await browser.newContext({
      viewport: { width: w, height: 900 },
      reducedMotion: reduced ? "reduce" : "no-preference",
    });
    const page = await ctx.newPage();
    page.on("console", (m) => m.type() === "error" && console.log(`[console ${w}]`, m.text()));
    page.on("pageerror", (e) => console.log(`[pageerror ${w}]`, e.message));
    await page.goto(url, { waitUntil: "networkidle" });
    // scroll through so ScrollTrigger reveals fire before the full-page capture
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 120));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(800);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (overflow) console.log(`[overflow] horizontal scroll at ${w}px`);
    const name = `qa/${w}${reduced ? "-reduced" : ""}.png`;
    await page.screenshot({ path: name, fullPage: true });
    console.log("saved", name);
    await ctx.close();
  }
}
await browser.close();
