import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { ScrambleTextPlugin } from "gsap/ScrambleTextPlugin";
import Lenis from "lenis";
import EmblaCarousel from "embla-carousel";

gsap.registerPlugin(ScrollTrigger, SplitText, ScrambleTextPlugin);

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => root.querySelector<T>(s);
const $$ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => [...root.querySelectorAll<T>(s)];
const SCRAMBLE_CHARS = "0123456789<>/\\[]{}#$%&*+=-^!?_";

/* ---------- smooth scroll ---------- */

const lenis = reduce ? null : new Lenis({ lerp: 0.1, anchors: { offset: -80 } });
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
  document.addEventListener("click", (e) => {
    const a = (e.target as Element).closest<HTMLAnchorElement>("a[data-transition]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || url.pathname === location.pathname) return;
    e.preventDefault();
    try { sessionStorage.setItem("pt", "1"); } catch {}
    gsap.fromTo(panel, { xPercent: 100 }, {
      xPercent: 0, duration: 0.7, ease: "power3.inOut",
      onComplete: () => { location.href = url.href; },
    });
  });
}

/* ---------- nav: CTA replaces the links once past the hero; rulers track progress ---------- */

const nav = $("[data-nav]");
const rulerIdx = $$("[data-ruler-index]");
const rulerTicks = $$("[data-rulers] .ruler").map((r) => $$("[data-tick]", r));
function onScroll() {
  const y = window.scrollY;
  nav?.classList.toggle("is-cta", y > innerHeight * 0.85);
  const max = document.documentElement.scrollHeight - innerHeight;
  const p = max > 0 ? Math.min(1, Math.max(0, y / max)) : 0;
  rulerIdx.forEach((el) => {
    const h = (el.parentElement as HTMLElement).clientHeight;
    el.style.transform = `translateY(${p * h}px)`;
  });
  rulerTicks.forEach((ticks) => {
    const n = ticks.length - 1;
    ticks.forEach((t, i) => {
      const d = Math.abs(i / n - p) * n;
      t.style.transform = `scaleX(${1 + Math.max(0, 1 - d / 2.5) * 0.85})`;
    });
  });
}
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

/* ---------- scramble text ---------- */

function scramble(el: HTMLElement, text: string, duration = 1.1) {
  if (reduce) { el.textContent = text; return; }
  gsap.killTweensOf(el);
  el.classList.add("is-scrambling");
  gsap.to(el, {
    duration,
    scrambleText: { text, chars: SCRAMBLE_CHARS, speed: 0.6, revealDelay: duration * 0.35 },
    ease: "none",
    onComplete: () => el.classList.remove("is-scrambling"),
  });
}
function scrambleOnView(el: HTMLElement) {
  const text = el.textContent?.replace(/\s+/g, " ").trim() ?? "";
  // keep layout stable: lock height while scrambling
  ScrollTrigger.create({
    trigger: el, start: "top 88%", once: true,
    onEnter: () => {
      el.style.minHeight = `${el.offsetHeight}px`;
      scramble(el, text, 1.2);
    },
  });
}
if (!reduce) {
  $$("[data-scramble]").forEach(scrambleOnView);
  $$("[data-scramble-in]").forEach((el) => {
    const text = el.textContent?.replace(/\s+/g, " ").trim() ?? "";
    el.style.minHeight = `${el.offsetHeight}px`;
    gsap.delayedCall(0.6, () => scramble(el, text, 1.6));
  });
}

/* ---------- hero: animated halftone landscape ---------- */

const hero = $<HTMLCanvasElement>("[data-halftone]");
if (hero) {
  const ctx = hero.getContext("2d")!;
  let w = 0, h = 0, visible = true, last = 0;
  const cell = 10;
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    w = hero.clientWidth; h = hero.clientHeight;
    hero.width = w * dpr; hero.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  const draw = (t: number) => {
    ctx.fillStyle = "#1d1813";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#d8c7aa";
    ctx.beginPath();
    const s = t * 0.001;
    for (let y = cell / 2; y < h; y += cell) {
      const ny = y / h;
      for (let x = cell / 2; x < w; x += cell) {
        const f =
          Math.sin(x * 0.0042 + s * 0.15) * Math.cos(y * 0.006 - s * 0.1) +
          0.5 * Math.sin((x + y) * 0.009 + s * 0.25) +
          0.25 * Math.sin(x * 0.021 - y * 0.013 + s * 0.4);
        const c = (f * 2.2) % 1;
        const band = 1 - Math.abs((c < 0 ? c + 1 : c) - 0.5) * 2; // contour ridges
        const v = Math.pow(band, 3) * (0.25 + 0.75 * ny) + 0.08 * ny;
        const r = v * cell * 0.55;
        if (r > 0.35) { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2); }
      }
    }
    ctx.fill();
  };
  const loop = (t: number) => {
    if (visible && t - last > 33) { draw(t); last = t; }
    requestAnimationFrame(loop);
  };
  resize();
  window.addEventListener("resize", () => { resize(); draw(performance.now()); });
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(hero);
  if (reduce) draw(12000);
  else requestAnimationFrame(loop);
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
    if (reduce) { paint(1); return; }
    const o = { k: 0 };
    paint(0);
    gsap.to(o, { k: 1, duration: 1.6, ease: "power2.out", onUpdate: () => paint(o.k), scrollTrigger: { trigger: portrait, start: "top 85%", once: true } });
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
  let active = -1;
  const setActive = (i: number) => {
    if (i === active) return;
    active = i;
    items.forEach((it, j) => it.classList.toggle("is-active", j === i));
    links.forEach((a, j) => a.classList.toggle("is-active", j === i));
    if (cta && links[i]) cta.href = links[i].href;
    if (text && teasers[i]) scramble(text, teasers[i], 0.9);
  };
  items.forEach((it, i) => {
    ScrollTrigger.create({
      trigger: it, start: "top center", end: "bottom+=36 center",
      onToggle: (self) => self.isActive && setActive(i),
    });
  });
  setActive(0);
  // clicking a list item on the home page: travel to its plate first, then the link works as usual
}

/* ---------- itinerary rows: the row in the middle of the screen is active ---------- */

$$("[data-itin]").forEach((list) => {
  const rows = $$("[data-itin-row]", list);
  rows.forEach((row) => {
    ScrollTrigger.create({
      trigger: row, start: "top 55%", end: "bottom 55%",
      onToggle: (self) => {
        if (!self.isActive) return;
        rows.forEach((r) => r.classList.toggle("is-active", r === row));
      },
    });
  });
});

/* ---------- carousels ---------- */

const papersRoot = $("[data-papers]");
if (papersRoot) {
  const embla = EmblaCarousel(papersRoot, { loop: true, align: "center", duration: 32 });
  const slides = embla.slideNodes();
  const sync = () => slides.forEach((s, i) => s.classList.toggle("is-snapped", i === embla.selectedScrollSnap()));
  embla.on("select", sync).on("reInit", sync);
  sync();
  $("[data-papers-prev]")?.addEventListener("click", () => embla.scrollPrev());
  $("[data-papers-next]")?.addEventListener("click", () => embla.scrollNext());
}

const exploreRoot = $("[data-explore]");
if (exploreRoot) {
  const embla = EmblaCarousel(exploreRoot, { align: "start", containScroll: "trimSnaps", dragFree: true });
  $("[data-explore-prev]")?.addEventListener("click", () => embla.scrollPrev());
  $("[data-explore-next]")?.addEventListener("click", () => embla.scrollNext());
}

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
  const tl = gsap.timeline({ delay, defaults: { ease: "power3.out" } });
  const media = $("[data-hero-media]");
  if (media) tl.from(media, { scale: 1.12, duration: 1.8 }, 0);
  const title = $("[data-hero-title]");
  if (title) {
    SplitText.create(title, {
      type: "lines", mask: "lines", autoSplit: true,
      onSplit: (self) => tl.from(self.lines, { yPercent: 105, duration: 1, stagger: 0.08 }, 0.2),
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
window.addEventListener("load", () => ScrollTrigger.refresh());
