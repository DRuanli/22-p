import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { ScrambleTextPlugin } from "gsap/ScrambleTextPlugin";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import Lenis from "lenis";
import EmblaCarousel from "embla-carousel";

gsap.registerPlugin(ScrollTrigger, SplitText, ScrambleTextPlugin, DrawSVGPlugin);
// Phones resize the viewport when the address bar shows/hides; don't recalculate every trigger then.
ScrollTrigger.config({ ignoreMobileResize: true });

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => root.querySelector<T>(s);
const $$ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => [...root.querySelectorAll<T>(s)];
const SCRAMBLE_CHARS = "0123456789<>/\\[]{}#$%&*+=-^!?_";

/* ---------- smooth scroll ---------- */

if ("scrollRestoration" in history) history.scrollRestoration = "manual";
const navType = (performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined)?.type;
const scrollKey = `scroll:${location.pathname}`;
window.addEventListener("pagehide", () => { try { sessionStorage.setItem(scrollKey, String(window.scrollY)); } catch {} });

const lenis = reduce || document.body.dataset.smooth === "off" ? null : new Lenis({ lerp: 0.1, anchors: { offset: -80 } });
if (lenis) {
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}

/* ---------- page transition: a black panel wipes across between pages ---------- */

const panel = $("[data-pt]");
const html = document.documentElement;
// GSAP owns the panel transform from here on (CSS only covers the first paint).
if (panel) gsap.set(panel, { x: 0, xPercent: html.classList.contains("pt-in") ? 0 : 100 });
function reveal() {
  try { sessionStorage.removeItem("pt"); } catch {}
  if (!panel || !html.classList.contains("pt-in")) return;
  html.classList.remove("pt-in");
  gsap.fromTo(panel, { xPercent: 0 }, { xPercent: -100, duration: 0.8, ease: "power3.inOut", delay: 0.1 });
}
reveal();
window.addEventListener("pageshow", (e) => {
  if (e.persisted && panel) gsap.set(panel, { xPercent: 100 });
});
if (panel && !reduce) {
  let leaving = false;
  window.addEventListener("pageshow", () => { leaving = false; });
  document.addEventListener("click", (e) => {
    const a = (e.target as Element).closest<HTMLAnchorElement>("a[data-transition]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || url.pathname === location.pathname) return;
    e.preventDefault();
    if (leaving) return;
    leaving = true;
    try { sessionStorage.setItem("pt", "1"); } catch {}
    gsap.fromTo(panel, { xPercent: 100 }, {
      xPercent: 0, duration: 0.7, ease: "power3.inOut",
      onComplete: () => { location.href = url.href; },
    });
  });
}

/* ---------- intro title card: typed line by line, then the page is revealed ---------- */

let introPending = html.classList.contains("intro-on");
const introDone: Promise<void> = new Promise((resolve) => {
  const el = $("[data-intro]");
  if (!el || !introPending) { el?.remove(); resolve(); return; }
  try { sessionStorage.setItem(`intro:${el.dataset.intro}`, "1"); } catch {}
  lenis?.stop();
  const lines = $$("[data-intro-line]", el);
  const finish = () => {
    introPending = false;
    html.classList.remove("intro-on");
    el.remove();
    lenis?.start();
    ScrollTrigger.refresh();
    resolve();
  };
  const tl = gsap.timeline({ onComplete: finish });
  lines.forEach((ln, i) => {
    const text = ln.dataset.introLine ?? "";
    const o = { n: 0 };
    tl.call(() => { lines.forEach((l) => l.classList.remove("is-typing")); ln.classList.add("is-typing"); ln.textContent = text.charAt(0); });
    tl.to(o, { n: text.length, duration: text.length * 0.032, ease: "none", onUpdate: () => { ln.textContent = text.slice(0, Math.max(1, Math.round(o.n))); } });
    tl.to({}, { duration: i === lines.length - 1 ? 0 : 0.22 });
  });
  tl.call(() => { lines.at(-1)?.classList.replace("is-typing", "is-last"); });
  tl.to({}, { duration: 0.75 });
  tl.to(el, { opacity: 0, duration: 0.7, ease: "power2.inOut" });
  // any click or key skips straight to the page
  const skip = () => { if (tl.progress() < 0.9) tl.progress(0.9); };
  el.addEventListener("click", skip);
  window.addEventListener("keydown", skip, { once: true });
});

/* ---------- nav + rulers: one batched update per frame, no layout reads while scrolling ---------- */

const nav = $("[data-nav]");
const rulers = $$("[data-rulers] .ruler").map((r) => ({ idx: $("[data-ruler-index]", r)!, ticks: $$("[data-tick]", r) }));
const tickState = rulers.map((r) => r.ticks.map(() => 1));
let rulerH = 0, maxScroll = 1, lastP = -1, ctaOn: boolean | null = null;
function measure() {
  rulerH = rulers[0]?.idx.parentElement?.clientHeight ?? 0;
  maxScroll = Math.max(1, document.documentElement.scrollHeight - innerHeight);
  lastP = -1;
}
function paintScroll(y: number) {
  const cta = y > innerHeight * 0.85;
  if (cta !== ctaOn) { ctaOn = cta; nav?.classList.toggle("is-cta", cta); }
  if (rulerH === 0) return; // rulers are hidden on small screens
  const p = Math.min(1, Math.max(0, y / maxScroll));
  if (Math.abs(p - lastP) < 0.0004) return;
  lastP = p;
  rulers.forEach((r, k) => {
    r.idx.style.transform = `translate3d(0, ${(p * rulerH).toFixed(1)}px, 0)`;
    const n = r.ticks.length - 1;
    r.ticks.forEach((t, i) => {
      const v = Math.round((1 + Math.max(0, 1 - (Math.abs(i / n - p) * n) / 2.5) * 0.85) * 100) / 100;
      if (v !== tickState[k][i]) { tickState[k][i] = v; t.style.transform = `scaleX(${v})`; }
    });
  });
}
measure();
window.addEventListener("resize", measure);
ScrollTrigger.addEventListener("refresh", measure);
if (lenis) lenis.on("scroll", (e: { scroll: number }) => paintScroll(e.scroll));
else {
  let queued = false;
  window.addEventListener("scroll", () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; paintScroll(window.scrollY); });
  }, { passive: true });
}
paintScroll(window.scrollY);

// nav text turns white while a dark section sits under it
// (ScrollTrigger skips callbacks during a refresh, e.g. after reload/back, so also sync on refresh)
// (declared first: a trigger that is already active calls onToggle while it is being created)
const darkSTs: ScrollTrigger[] = [];
function syncDark() { nav?.classList.toggle("is-dark", darkSTs.some((t) => t.isActive)); }
$$("[data-dark]").forEach((sec) => darkSTs.push(ScrollTrigger.create({
  trigger: sec, start: "top top+=40", end: "bottom top+=40",
  onToggle: () => syncDark(),
})));
ScrollTrigger.addEventListener("refresh", syncDark);
syncDark();

/* ---------- scramble text ---------- */

function scramble(el: HTMLElement, text: string, duration = 1.1, lock = true) {
  if (reduce) { el.textContent = text; return; }
  gsap.killTweensOf(el);
  // scrambled characters replace spaces too, so lock the box: no reflow of the page below
  if (lock && !el.classList.contains("is-scrambling")) el.style.height = `${el.offsetHeight}px`;
  el.classList.add("is-scrambling");
  gsap.to(el, {
    duration,
    scrambleText: { text, chars: SCRAMBLE_CHARS, speed: 0.6, revealDelay: duration * 0.35 },
    ease: "none",
    onComplete: () => { el.classList.remove("is-scrambling"); if (lock) el.style.height = ""; },
  });
}
function scrambleOnView(el: HTMLElement) {
  const text = el.textContent?.replace(/\s+/g, " ").trim() ?? "";
  // keep layout stable: lock height while scrambling
  ScrollTrigger.create({
    trigger: el, start: "top bottom", once: true,
    onEnter: () => scramble(el, text, 0.9),
  });
}
if (!reduce) {
  $$("[data-scramble]").forEach(scrambleOnView);
  $$("[data-scramble-in]").forEach((el) => {
    const text = el.textContent?.replace(/\s+/g, " ").trim() ?? "";
    introDone.then(() => gsap.delayedCall(0.6, () => scramble(el, text, 1.4)));
  });
}

/* ---------- hero: halftone landscape ----------
   Two frames of the contour field are drawn once; the animation only drifts and cross-fades
   them (transform + opacity), so the browser never repaints the hero while it moves. */

function drawHalftone(canvas: HTMLCanvasElement, time: number) {
  const dpr = Math.min(window.devicePixelRatio || 1, 1.25); // dots stay crisp; ~40% of the pixels of 2x
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d")!;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = "#1d1813";
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#d8c7aa";
  ctx.beginPath();
  const cell = 10, s = time;
  for (let y = cell / 2; y < h; y += cell) {
    const ny = y / h;
    for (let x = cell / 2; x < w; x += cell) {
      const f =
        Math.sin(x * 0.0042 + s * 0.15) * Math.cos(y * 0.006 - s * 0.1) +
        0.5 * Math.sin((x + y) * 0.009 + s * 0.25) +
        0.25 * Math.sin(x * 0.021 - y * 0.013 + s * 0.4);
      const c = (f * 2.2) % 1;
      const band = 1 - Math.abs((c < 0 ? c + 1 : c) - 0.5) * 2; // contour ridges
      const r = (Math.pow(band, 3) * (0.25 + 0.75 * ny) + 0.08 * ny) * cell * 0.55;
      if (r > 0.35) { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2); }
    }
  }
  ctx.fill();
}

const heroA = $<HTMLCanvasElement>("[data-halftone]");
if (heroA) {
  const heroB = heroA.cloneNode() as HTMLCanvasElement;
  heroB.style.opacity = "0";
  heroA.after(heroB);
  const paint = () => {
    drawHalftone(heroA, 2);
    const idle = (window as any).requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 200));
    idle(() => drawHalftone(heroB, 3.4));
  };
  paint();
  let rt: number | undefined;
  let rw = innerWidth;
  window.addEventListener("resize", () => {
    if (innerWidth === rw) return; // ignore mobile address-bar height changes
    rw = innerWidth; clearTimeout(rt); rt = window.setTimeout(paint, 250);
  });
  if (!reduce) {
    const loops = [
      gsap.to(heroB, { opacity: 1, duration: 7, ease: "sine.inOut", repeat: -1, yoyo: true, delay: 1 }),
      gsap.fromTo(heroA, { xPercent: -1.5, yPercent: 1 }, { xPercent: 1.5, yPercent: -1, duration: 16, ease: "sine.inOut", repeat: -1, yoyo: true }),
      gsap.fromTo(heroB, { xPercent: 1.5, yPercent: -1 }, { xPercent: -1.5, yPercent: 1, duration: 19, ease: "sine.inOut", repeat: -1, yoyo: true }),
    ];
    // nothing to animate once the hero has scrolled away
    ScrollTrigger.create({
      trigger: heroA.closest("[data-hero]") ?? heroA, start: "top bottom", end: "bottom top",
      onToggle: (self) => loops.forEach((t) => (self.isActive ? t.resume() : t.pause())),
    });
  }
}

/* ---------- founder: halftone portrait (photo if provided, monogram otherwise) ---------- */

const portrait = $<HTMLCanvasElement>("[data-portrait]");
if (portrait) {
  const N = 56, size = 480, cell = size / N;
  const sample = document.createElement("canvas");
  sample.width = sample.height = N;
  const sctx = sample.getContext("2d", { willReadFrequently: true })!;
  const out = portrait.getContext("2d")!;
  portrait.width = portrait.height = size;
  let lum: number[] = [];

  const paint = (k: number) => {
    out.clearRect(0, 0, size, size);
    out.fillStyle = "#121212";
    out.beginPath();
    for (let i = 0; i < N * N; i++) {
      const x = (i % N) * cell + cell / 2, y = Math.floor(i / N) * cell + cell / 2;
      const r = (1 - lum[i]) * cell * 0.62 * k;
      if (r > 0.3) { out.moveTo(x + r, y); out.arc(x, y, r, 0, Math.PI * 2); }
    }
    out.fill();
  };
  const readLum = () => {
    const d = sctx.getImageData(0, 0, N, N).data;
    lum = Array.from({ length: N * N }, (_, i) => (0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]) / 255);
  };
  const start = () => {
    readLum();
    paint(1);
    if (reduce) return;
    gsap.from(portrait, { opacity: 0, scale: 0.9, duration: 1.2, ease: "power3.out", scrollTrigger: { trigger: portrait, start: "top 85%", once: true } });
  };
  const src = portrait.dataset.src;
  if (src) {
    const img = new Image();
    img.onload = () => {
      const s = Math.min(img.width, img.height);
      sctx.fillStyle = "#fff"; sctx.fillRect(0, 0, N, N);
      sctx.drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, N, N);
      start();
    };
    img.src = src;
  } else {
    document.fonts.ready.then(() => {
      sctx.fillStyle = "#fff"; sctx.fillRect(0, 0, N, N);
      const g = sctx.createRadialGradient(N / 2, N / 2, 4, N / 2, N / 2, N * 0.7);
      g.addColorStop(0, "#fff"); g.addColorStop(1, "#bbb");
      sctx.fillStyle = g; sctx.fillRect(0, 0, N, N);
      sctx.fillStyle = "#000";
      sctx.font = `900 ${N * 0.5}px Archivo, Arial, sans-serif`;
      sctx.textAlign = "center"; sctx.textBaseline = "middle";
      sctx.fillText("NL", N / 2, N / 2 + 2);
      start();
    });
  }
}

/* ---------- routes: pinned list, centre frame, scrambled description ---------- */

const routesRoot = $("[data-routes]");
if (routesRoot) {
  const items = $$("[data-route-item]", routesRoot);
  const links = $$<HTMLAnchorElement>("[data-route-link]", routesRoot);
  const text = $("[data-route-text]", routesRoot);
  const cta = $<HTMLAnchorElement>("[data-route-cta]", routesRoot);
  const teasers = items.map((it) => $(".routes__mobile .justify", it)?.textContent?.trim() ?? "");
  const live = $("[data-route-live]", routesRoot);
  const pin = $("[data-routes-pin]", routesRoot);
  const frame = $(".routes__frame", routesRoot);
  let active = -1;
  const setActive = (i: number) => {
    if (i === active) return;
    active = i;
    items.forEach((it, j) => it.classList.toggle("is-active", j === i));
    links.forEach((a, j) => a.classList.toggle("is-active", j === i));
    if (cta && links[i]) cta.href = links[i].href;
    if (live) live.textContent = teasers[i];
    if (frame && !reduce && active >= 0) gsap.fromTo(frame, { scale: 1.035, opacity: 0.4 }, { scale: 1, opacity: 1, duration: 0.6, ease: "power3.out", overwrite: true });
    if (!text || !teasers[i]) return;
    if (pin && pin.offsetParent === null) text.textContent = teasers[i]; // pinned layer hidden (mobile)
    else scramble(text, teasers[i], 0.9, false);
  };
  const bars = $$("[data-route-bar]", routesRoot);
  const sts: ScrollTrigger[] = [];
  items.forEach((it, i) => {
    const bar = bars[i];
    const setBar = bar ? gsap.quickSetter(bar, "scaleX") : null;
    sts.push(ScrollTrigger.create({
      trigger: it, start: "top center", end: "bottom+=36 center",
      onToggle: (self) => self.isActive && setActive(i),
      onUpdate: (self) => setBar?.(self.progress), // red bar under the active name fills as its plate passes
      onRefresh: (self) => setBar?.(self.progress),
    }));
  });
  // after a refresh (reload, back, resize) pick whichever plate is under the frame now
  const syncRoute = () => {
    const i = sts.findIndex((t) => t.isActive);
    if (i >= 0) setActive(i);
    else if (sts.length && window.scrollY > sts[sts.length - 1].end) setActive(sts.length - 1);
    else setActive(0);
  };
  ScrollTrigger.addEventListener("refresh", syncRoute);
  syncRoute();
}

/* ---------- itinerary rows: the row in the middle of the screen is active ---------- */

$$("[data-itin]").forEach((list) => {
  const rows = $$("[data-itin-row]", list);
  // Whichever row is nearest the line at 55% of the viewport is active, so the first and
  // last rows also get their turn. Row centres are measured on refresh, not while scrolling.
  let centres: number[] = [];
  let current = -1;
  const measureRows = () => { centres = rows.map((r) => { const b = r.getBoundingClientRect(); return b.top + window.scrollY + b.height / 2; }); };
  const update = () => {
    const line = window.scrollY + innerHeight * 0.55;
    let best = 0;
    centres.forEach((c, i) => { if (Math.abs(c - line) < Math.abs(centres[best] - line)) best = i; });
    if (best === current) return;
    current = best;
    rows.forEach((r, i) => r.classList.toggle("is-active", i === best));
  };
  ScrollTrigger.create({ trigger: list, start: "top bottom", end: "bottom top", onUpdate: update, onRefresh: () => { measureRows(); current = -1; update(); } });
});

/* ---------- carousels ---------- */

const exploreRoot = $("[data-explore]");
if (exploreRoot) {
  const embla = EmblaCarousel(exploreRoot, { align: "start", containScroll: "trimSnaps", dragFree: true });
  const prev = $<HTMLButtonElement>("[data-explore-prev]");
  const next = $<HTMLButtonElement>("[data-explore-next]");
  prev?.addEventListener("click", () => embla.scrollPrev());
  next?.addEventListener("click", () => embla.scrollNext());
  const sync = () => {
    if (prev) prev.disabled = !embla.canScrollPrev();
    if (next) next.disabled = !embla.canScrollNext();
  };
  embla.on("select", sync).on("reInit", sync).on("scroll", sync);
  sync();
}

/* ---------- mobile menu ---------- */

const menuBtn = $<HTMLButtonElement>("[data-menu-btn]");
const menu = $("[data-menu]");
if (menuBtn && menu && nav) {
  const setMenu = (open: boolean) => {
    menuBtn.setAttribute("aria-expanded", String(open));
    menuBtn.textContent = open ? "Close" : "Menu";
    menu.hidden = !open;
    nav.classList.toggle("is-menu", open);
    if (open) {
      lenis?.stop();
      if (!reduce) gsap.fromTo(menu.querySelectorAll("nav a, .nav__menu-mail"), { yPercent: 60, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.6, stagger: 0.05, ease: "power3.out" });
    } else lenis?.start();
  };
  menuBtn.addEventListener("click", () => setMenu(menuBtn.getAttribute("aria-expanded") !== "true"));
  $$("[data-menu-link]", menu).forEach((a) => a.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) { setMenu(false); menuBtn.focus(); } });
}

/* ---------- publications: expandable entries, copy citation, pointer preview ---------- */

const pubs = $("[data-pubs]");
if (pubs) {
  const items = $$("[data-pub]", pubs);
  items.forEach((item) => {
    const btn = $<HTMLButtonElement>("[data-pub-toggle]", item)!;
    const panel = $("[data-pub-panel]", item)!;
    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") !== "true";
      if (open) pubs.dispatchEvent(new CustomEvent("pub:open"));
      btn.setAttribute("aria-expanded", String(open));
      item.classList.toggle("is-open", open);
      if (reduce) { panel.hidden = !open; ScrollTrigger.refresh(); return; }
      gsap.killTweensOf(panel);
      if (open) {
        panel.hidden = false;
        gsap.fromTo(panel, { height: 0 }, { height: "auto", duration: 0.6, ease: "power3.out", onComplete: () => ScrollTrigger.refresh() });
        const kids = panel.querySelectorAll("dl > div, .pubs__cite > *");
        gsap.killTweensOf(kids);
        gsap.fromTo(kids, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.45, stagger: 0.04, delay: 0.1, ease: "power2.out" });
      } else {
        gsap.set(panel.querySelectorAll("dl > div, .pubs__cite > *"), { opacity: 1, y: 0 });
        gsap.to(panel, { height: 0, duration: 0.45, ease: "power2.inOut", onComplete: () => { panel.hidden = true; gsap.set(panel, { clearProps: "height" }); ScrollTrigger.refresh(); } });
      }
    });

    const copy = $<HTMLButtonElement>("[data-copy]", item);
    const cite = $("[data-citation]", item);
    copy?.addEventListener("click", async () => {
      const label = "Copy citation";
      try {
        await navigator.clipboard.writeText(cite?.textContent?.trim() ?? "");
        scramble(copy, "Copied", 0.5);
      } catch {
        // clipboard blocked: select the citation so it can be copied by hand
        const range = document.createRange();
        if (cite) { range.selectNodeContents(cite); getSelection()?.removeAllRanges(); getSelection()?.addRange(range); }
        scramble(copy, "Selected, press Ctrl+C", 0.5);
      }
      setTimeout(() => scramble(copy, label, 0.5), 2200);
    });
  });

  // a film plate follows the pointer over the list (fine pointers only)
  const preview = $("[data-pub-preview]", pubs);
  if (preview && !reduce && window.matchMedia("(hover: hover) and (min-width: 861px)").matches) {
    const xTo = gsap.quickTo(preview, "x", { duration: 0.55, ease: "power3.out" });
    const yTo = gsap.quickTo(preview, "y", { duration: 0.55, ease: "power3.out" });
    const plates = $$("[data-preview]", preview);
    let shown = false;
    const show = (on: boolean) => {
      if (on === shown) return;
      shown = on;
      gsap.to(preview, { opacity: on ? 1 : 0, scale: on ? 1 : 0.92, duration: 0.35, ease: "power2.out" });
    };
    gsap.set(preview, { scale: 0.92, xPercent: 12, yPercent: -50 });
    items.forEach((item) => {
      const row = $("[data-pub-toggle]", item)!;
      row.addEventListener("pointerenter", () => {
        if (item.classList.contains("is-open")) return;
        plates.forEach((pl) => pl.classList.toggle("is-on", pl.dataset.preview === item.dataset.plate));
        show(true);
      });
      row.addEventListener("pointerleave", () => show(false));
    });
    pubs.addEventListener("pointermove", (e) => { xTo(e.clientX); yTo(e.clientY); });
    pubs.addEventListener("pub:open", () => show(false));
  }
}

/* ---------- numbers that count up, charts that grow ---------- */

// Counts every number inside a string ("3.2×", "−60%", "24,601–29,496") up from zero,
// keeping its decimals, thousands separators and the surrounding symbols.
function countUp(el: HTMLElement) {
  const text = el.textContent ?? "";
  const parts = text.split(/(\d[\d,]*(?:\.\d+)?)/);
  const nums = parts.map((p, i) => (i % 2 ? { n: parseFloat(p.replace(/,/g, "")), dec: (p.split(".")[1] ?? "").length, comma: p.includes(",") } : null));
  const render = (k: number) => parts.map((p, i) => {
    const m = nums[i];
    if (!m) return p;
    const v = (m.n * k).toFixed(m.dec);
    return m.comma ? Number(v).toLocaleString("en-US", { minimumFractionDigits: m.dec }) : v;
  }).join("");
  el.style.minWidth = `${el.offsetWidth}px`; // no width jitter while digits change
  const o = { k: 0 };
  el.textContent = render(0);
  gsap.to(o, { k: 1, duration: 1.6, ease: "power3.out", onUpdate: () => { el.textContent = render(o.k); }, onComplete: () => { el.textContent = text; } });
}
$$("[data-count-text]").forEach((el) => {
  if (reduce) return;
  ScrollTrigger.create({ trigger: el, start: "top 88%", once: true, onEnter: () => countUp(el) });
});

$$("[data-chart]").forEach((chart) => {
  const bars = $$("[data-bar]", chart);
  if (!reduce) {
    gsap.set(bars, { scaleX: 0 });
    ScrollTrigger.create({
      trigger: chart, start: "top 85%", once: true,
      onEnter: () => gsap.to(bars, { scaleX: 1, duration: 1.1, stagger: 0.12, ease: "power3.out" }),
    });
  }
  // per-bar tooltip on hover and keyboard focus
  const tip = $("[data-chart-tip]", chart);
  if (!tip) return;
  $$("[data-tip]", chart).forEach((row) => {
    const show = (on: boolean) => {
      if (on) {
        tip.textContent = row.dataset.tip ?? "";
        const r = row.getBoundingClientRect(), c = chart.getBoundingClientRect();
        tip.style.left = `${Math.max(0, r.left - c.left)}px`;
        tip.style.top = `${r.bottom - c.top + 8}px`;
      }
      tip.classList.toggle("is-on", on);
    };
    row.addEventListener("pointerenter", () => show(true));
    row.addEventListener("pointerleave", () => show(false));
    row.addEventListener("focus", () => show(true));
    row.addEventListener("blur", () => show(false));
  });
});

/* ---------- the prediction horizon sweeps across the cohort, then rests on the boundary ---------- */

const horizon = $("[data-horizon]");
if (horizon && !reduce) {
  const frame = horizon.parentElement!;
  gsap.fromTo(horizon,
    { x: () => -frame.clientWidth * 0.62 },
    { x: 0, ease: "none", scrollTrigger: { trigger: frame, start: "top 85%", end: "center 45%", scrub: true, invalidateOnRefresh: true } });
}

/* ---------- cover photo: a slow Ken Burns drift, paused once the hero is gone ---------- */

const coverPhoto = $<HTMLImageElement>("[data-hero-photo]");
if (coverPhoto) {
  const refresh = () => ScrollTrigger.refresh();
  if (coverPhoto.complete) refresh(); else coverPhoto.addEventListener("load", refresh, { once: true });
  if (!reduce) {
    const drift = gsap.fromTo(coverPhoto, { scale: 1.1, xPercent: -1.5 }, { scale: 1.02, xPercent: 1.5, duration: 26, ease: "sine.inOut", repeat: -1, yoyo: true });
    ScrollTrigger.create({
      trigger: coverPhoto.closest("[data-hero]") ?? coverPhoto, start: "top bottom", end: "bottom top",
      onToggle: (self) => (self.isActive ? drift.resume() : drift.pause()),
    });
  }
}

/* ---------- exchange map: trips draw themselves as the map scrolls in ---------- */

const xmap = $("[data-xmap]");
if (xmap && !reduce) {
  const river = $$("[data-xmap-river]", xmap);
  const trips = $$("[data-xmap-trip]", xmap);
  const stops = $$("[data-xmap-stop]", xmap);
  const tl = gsap.timeline({ scrollTrigger: { trigger: xmap, start: "top 80%", end: "bottom 70%", scrub: 0.6 } });
  tl.from(river, { drawSVG: "0%", duration: 1, ease: "none" }, 0)
    .from(stops, { opacity: 0, scale: 0.4, transformOrigin: "50% 50%", stagger: 0.06, duration: 0.3 }, 0.1)
    .from(trips, { drawSVG: "0%", duration: 1.4, stagger: 0.25, ease: "none" }, 0.3);
  const pulse = $("[data-xmap-pulse]", xmap);
  if (pulse) gsap.fromTo(pulse, { scale: 0.6, opacity: 0.9, svgOrigin: `${pulse.dataset.cx} ${pulse.dataset.cy}` }, { scale: 1.8, opacity: 0, duration: 1.8, ease: "power1.out", repeat: -1, svgOrigin: `${pulse.dataset.cx} ${pulse.dataset.cy}` });
}

/* ---------- gallery: an endless plane of frames, bent like a lens near the edges ---------- */

const gal = $("[data-gallery]");
if (gal) {
  const plane = $("[data-gal-plane]", gal)!;
  const tiles = $$("[data-gal-tile]", plane);
  const COLS = Number(gal.dataset.cols), ROWS = Number(gal.dataset.rows);
  let cell = 280, W = 0, H = 0, vw = innerWidth, vh = innerHeight;
  const layout = () => {
    vw = innerWidth; vh = innerHeight;
    cell = Math.round(Math.min(340, Math.max(190, vw / 4.6)));
    W = COLS * cell; H = ROWS * cell;
    tiles.forEach((t) => { t.style.width = `${Math.round(cell * Number(t.dataset.w))}px`; });
    sizes = tiles.map((t) => [t.offsetWidth, t.offsetHeight]);
  };
  let sizes: number[][] = [];
  layout();
  window.addEventListener("resize", layout);

  // pan state: target (tx, ty) eased into current (x, y); a slow drift when idle
  let x = -W / 2 + vw / 2, y = -H / 2 + vh / 2, tx = x, ty = y, lastInput = 0;
  const wrap = (v: number, m: number) => ((v % m) + m) % m;
  const render = () => {
    const now = performance.now();
    if (!reduce && now - lastInput > 2500) { tx -= 0.25; ty -= 0.12; }
    x += (tx - x) * 0.09; y += (ty - y) * 0.09;
    const cx = vw / 2, cy = vh / 2, rx = vw * 0.75, ry = vh * 0.75;
    tiles.forEach((t, i) => {
      const c = Number(t.dataset.c), r = Number(t.dataset.r);
      const [tw, th] = sizes[i];
      const px = wrap(c * cell + x + Number(t.dataset.jx) * cell * 0.35, W) - cell;
      const py = wrap(r * cell + y + Number(t.dataset.jy) * cell * 0.3, H) - cell;
      const mx = px + tw / 2, my = py + th / 2;
      const dx = (mx - cx) / rx, dy = (my - cy) / ry;
      const d = Math.min(1.4, Math.hypot(dx, dy));
      const s = reduce ? 1 : 1 - 0.42 * d * d;
      const rotY = reduce ? 0 : dx * -18, rotX = reduce ? 0 : dy * 14;
      // pull frames slightly toward the centre so the plane reads as a curved surface
      const pull = reduce ? 0 : 0.12 * d;
      t.style.transform = `translate3d(${(px - (mx - cx) * pull).toFixed(1)}px, ${(py - (my - cy) * pull).toFixed(1)}px, 0) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale(${s.toFixed(3)})`;
    });
  };
  gsap.ticker.add(render);

  // drag (mouse, pen, touch) with a little inertia
  let dragging = false, moved = 0, sx = 0, sy = 0, vx = 0, vy = 0, lx = 0, ly = 0;
  gal.addEventListener("pointerdown", (e) => {
    if ((e.target as Element).closest(".gal__hud, .gal__list, dialog")) return;
    dragging = true; moved = 0; sx = lx = e.clientX; sy = ly = e.clientY; vx = vy = 0;
    gal.setPointerCapture(e.pointerId); gal.classList.add("is-dragging"); lastInput = performance.now();
  });
  gal.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const ddx = e.clientX - lx, ddy = e.clientY - ly;
    lx = e.clientX; ly = e.clientY; vx = ddx; vy = ddy;
    tx += ddx * 1.4; ty += ddy * 1.4; moved += Math.abs(ddx) + Math.abs(ddy);
    lastInput = performance.now();
  });
  const end = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false; gal.classList.remove("is-dragging");
    tx += vx * 12; ty += vy * 12; // fling
    if (moved < 6) {
      const tile = (document.elementsFromPoint(e.clientX, e.clientY).find((el) => (el as HTMLElement).dataset?.galTile !== undefined) as HTMLElement | undefined);
      if (tile) openItem(Number(tile.dataset.item));
    }
  };
  gal.addEventListener("pointerup", end);
  gal.addEventListener("pointercancel", end);
  gal.addEventListener("wheel", (e) => { e.preventDefault(); tx -= e.deltaX * 1.1; ty -= e.deltaY * 1.1; lastInput = performance.now(); }, { passive: false });
  window.addEventListener("keydown", (e) => {
    const k = { ArrowLeft: [1, 0], ArrowRight: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key];
    if (!k || box.open || !listEl.hidden) return;
    tx += k[0] * cell; ty += k[1] * cell; lastInput = performance.now(); e.preventDefault();
  });

  // lightbox
  const box = $<HTMLDialogElement>("[data-gal-box]", gal)!;
  const stage = $("[data-gal-stage]", box)!;
  const sources = $<HTMLTemplateElement>("[data-gal-sources]", gal)!;
  let opener: HTMLElement | null = null;
  function openItem(i: number) {
    const src = sources.content.querySelector<HTMLElement>(`[data-src-item="${i}"]`);
    if (!src) return;
    opener = document.activeElement as HTMLElement;
    stage.replaceChildren(...[...src.childNodes].map((n) => n.cloneNode(true)));
    $("[data-gal-cap]", box)!.textContent = src.dataset.caption ?? "";
    $("[data-gal-place]", box)!.textContent = src.dataset.place ? `· ${src.dataset.place}` : "";
    box.showModal();
    if (!reduce) gsap.fromTo(box, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.45, ease: "power3.out" });
  }
  $("[data-gal-close]", box)?.addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => { if (e.target === box) box.close(); });
  box.addEventListener("close", () => opener?.focus());

  // accessible list view
  const listBtn = $<HTMLButtonElement>("[data-gal-list-btn]", gal)!;
  const listEl = $("[data-gal-list]", gal)!;
  listBtn.addEventListener("click", () => {
    const open = listEl.hidden;
    listEl.hidden = !open;
    listBtn.setAttribute("aria-expanded", String(open));
    listBtn.textContent = open ? "Plane view" : "List view";
  });
  $$<HTMLButtonElement>("[data-gal-open]", listEl).forEach((b) => b.addEventListener("click", () => openItem(Number(b.dataset.galOpen))));

  // first reveal once the intro card has gone
  if (!reduce) introDone.then(() => gsap.from(tiles, { opacity: 0, duration: 1.2, stagger: { each: 0.015, from: "center" }, ease: "power2.out" }));
}

/* ---------- nav: which section am I in ---------- */

const navNum = $("[data-nav-num]");
const navName = $("[data-nav-name]");
if (navNum && navName) {
  const sections = $$("[data-section]");
  let current = -1;
  const show = (i: number) => {
    if (i < 0 || i === current) return;
    current = i;
    navNum.textContent = String(i + 1).padStart(2, "0");
    scramble(navName, sections[i].dataset.section ?? "", 0.5, false);
  };
  const secSTs: ScrollTrigger[] = [];
  sections.forEach((sec, i) => secSTs.push(ScrollTrigger.create({
    trigger: sec, start: "top 50%", end: "bottom 50%",
    onToggle: (self) => self.isActive && show(i),
  })));
  ScrollTrigger.addEventListener("refresh", () => show(secSTs.findIndex((t) => t.isActive)));
}

/* ---------- small touches: hover scramble on bracket links, back to top ---------- */

if (!reduce && window.matchMedia("(hover: hover)").matches) {
  $$("a.bracket, .routes__list a > span:first-child").forEach((el) => {
    if (el.children.length) return; // only plain-text labels
    const label = el.textContent ?? "";
    let busy = false;
    el.addEventListener("pointerenter", () => {
      if (busy) return;
      busy = true;
      gsap.to(el, { duration: 0.45, scrambleText: { text: label, chars: SCRAMBLE_CHARS, speed: 1 }, ease: "none", onComplete: () => { busy = false; } });
    });
  });
}
$$("[data-to-top]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  if (lenis) lenis.scrollTo(0, { duration: 1.6 });
  else window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  $("#main")?.focus({ preventScroll: true });
}));

/* ---------- FAQ cells ---------- */

$$<HTMLButtonElement>("[data-faq]").forEach((btn) => {
  const answer = $(`#${btn.getAttribute("aria-controls")}`)!;
  btn.addEventListener("click", () => {
    const open = btn.getAttribute("aria-expanded") !== "true";
    btn.setAttribute("aria-expanded", String(open));
    answer.hidden = !open;
    if (open && !reduce) {
      const p = $("p", answer)!;
      scramble(p, p.textContent?.trim() ?? "", 0.7);
    }
    ScrollTrigger.refresh();
  });
});

/* ---------- load + scroll motion (skipped entirely for reduced motion) ---------- */

const mm = gsap.matchMedia();
mm.add("(prefers-reduced-motion: no-preference)", () => {
  const delay = html.classList.contains("pt-in") ? 0.5 : 0;
  const tl = gsap.timeline({ delay, paused: introPending, defaults: { ease: "power3.out" } });
  if (introPending) introDone.then(() => tl.play());
  const media = $("[data-hero-media]");
  if (media) tl.from(media, { scale: 1.12, duration: 1.8 }, 0);
  const title = $("[data-hero-title]");
  if (title) {
    SplitText.create(title, {
      type: "lines", mask: "lines", autoSplit: true,
      onSplit: (self) => {
        const t = gsap.from(self.lines, { yPercent: 105, duration: 1, stagger: 0.08, ease: "power3.out", delay: delay + 0.2, paused: introPending });
        if (introPending) introDone.then(() => t.play());
        return t;
      },
    });
  }
  const fades = $$("[data-hero-fade]");
  if (fades.length) tl.from(fades, { opacity: 0, y: 14, duration: 0.6 }, 0.9);

  // hero media drifts slower than the page
  if (media) gsap.to(media, { yPercent: 18, ease: "none", scrollTrigger: { trigger: media.parentElement, start: "top top", end: "bottom top", scrub: true } });

  $$("[data-reveal]").forEach((h) => {
    SplitText.create(h, {
      type: "lines", mask: "lines", autoSplit: true,
      onSplit: (self) => gsap.from(self.lines, {
        yPercent: 105, duration: 0.9, stagger: 0.08, ease: "power3.out",
        scrollTrigger: { trigger: h, start: "top 85%", once: true },
      }),
    });
  });

  $$("[data-parallax]").forEach((frame) => {
    const inner = $("[data-parallax-inner]", frame);
    if (inner) gsap.fromTo(inner, { yPercent: -6 }, { yPercent: 6, ease: "none", scrollTrigger: { trigger: frame, start: "top bottom", end: "bottom top", scrub: true } });
  });
});

document.fonts.ready.then(() => ScrollTrigger.refresh());
window.addEventListener("load", () => {
  ScrollTrigger.refresh();
  // reload / back: return to where the reader was, once layout has settled
  let saved = 0;
  try { saved = Number(sessionStorage.getItem(scrollKey) ?? 0); } catch {}
  if ((navType === "reload" || navType === "back_forward") && saved > 0 && !location.hash) {
    if (lenis) lenis.scrollTo(saved, { immediate: true, force: true });
    else window.scrollTo(0, saved);
    ScrollTrigger.update();
  }
});
