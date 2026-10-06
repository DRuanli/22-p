import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import Lenis from "lenis";
import EmblaCarousel from "embla-carousel";

gsap.registerPlugin(ScrollTrigger, SplitText);

const reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const $ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => root.querySelector<T>(s);
const $$ = <T extends Element = HTMLElement>(s: string, root: ParentNode = document) => [...root.querySelectorAll<T>(s)];

/* ---------- smooth scroll ---------- */

const lenis = reduceQuery.matches ? null : new Lenis({ lerp: 0.1, anchors: { offset: -72 } });
if (lenis) {
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}

/* ---------- nav: solid after hero, hides on scroll down, progress bar ---------- */

const nav = $("[data-nav]");
const progress = $("[data-progress]");
const toggle = $<HTMLButtonElement>("[data-nav-toggle]");
const menu = $("[data-nav-menu]");
if (nav) {
  let lastY = window.scrollY;
  const onScroll = () => {
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - innerHeight;
    nav.classList.toggle("is-solid", y > innerHeight * 0.6);
    const menuOpen = toggle?.getAttribute("aria-expanded") === "true";
    nav.classList.toggle("is-hidden", !menuOpen && y > lastY && y > innerHeight);
    lastY = y;
    if (progress) progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  // keyboard users always see the nav
  nav.addEventListener("focusin", () => nav.classList.remove("is-hidden"));
}
if (toggle && menu) {
  const setOpen = (open: boolean) => {
    toggle.setAttribute("aria-expanded", String(open));
    menu.hidden = !open;
    nav?.classList.toggle("is-solid", open || window.scrollY > innerHeight * 0.6);
  };
  toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
  $$("a", menu).forEach((a) => a.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (e) => e.key === "Escape" && setOpen(false));
}

/* ---------- about: fact carousel ---------- */

const factsRoot = $("[data-facts]");
if (factsRoot) {
  const embla = EmblaCarousel($(".facts__viewport", factsRoot)!, { loop: true, duration: 30 });
  const dots = $$<HTMLButtonElement>("[data-dot]", factsRoot);
  const sync = () => dots.forEach((d, j) => d.setAttribute("aria-current", String(embla.selectedScrollSnap() === j)));
  dots.forEach((d, j) => d.addEventListener("click", () => embla.scrollTo(j)));
  embla.on("select", sync);
  sync();
  let timer: number | undefined;
  let touched = false;
  const stop = () => window.clearInterval(timer);
  const start = () => {
    stop();
    if (!reduceQuery.matches && !touched) timer = window.setInterval(() => embla.scrollNext(), 6000);
  };
  factsRoot.addEventListener("mouseenter", stop);
  factsRoot.addEventListener("mouseleave", start);
  factsRoot.addEventListener("focusin", stop);
  embla.on("pointerDown", () => { touched = true; stop(); });
  start();
}

/* ---------- expeditions: card rail + route dialogs ---------- */

const railRoot = $("[data-rail]");
if (railRoot) {
  const embla = EmblaCarousel(railRoot, { dragFree: true, containScroll: "trimSnaps", align: "start" });
  const prev = $<HTMLButtonElement>("[data-rail-prev]")!;
  const next = $<HTMLButtonElement>("[data-rail-next]")!;
  prev.addEventListener("click", () => embla.scrollPrev());
  next.addEventListener("click", () => embla.scrollNext());
  const sync = () => { prev.disabled = !embla.canScrollPrev(); next.disabled = !embla.canScrollNext(); };
  embla.on("select", sync).on("reInit", sync).on("scroll", sync);
  sync();
}

$$<HTMLButtonElement>("[data-open]").forEach((btn) => {
  const dlg = $<HTMLDialogElement>(`#route-${btn.dataset.open}`);
  if (!dlg) return;
  btn.addEventListener("click", () => {
    dlg.showModal();
    lenis?.stop();
    if (!reduceQuery.matches) {
      gsap.fromTo(dlg, { opacity: 0, y: 40, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" });
      gsap.from($$(".route__steps li", dlg), { opacity: 0, x: 24, duration: 0.5, stagger: 0.07, delay: 0.2, ease: "power2.out" });
    }
  });
  dlg.addEventListener("close", () => { lenis?.start(); btn.focus(); });
  $("[data-close]", dlg)?.addEventListener("click", () => dlg.close());
  // click on the backdrop closes
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
});

/* ---------- profile tabs ---------- */

const tabsRoot = $("[data-tabs]");
if (tabsRoot) {
  const tabs = $$<HTMLButtonElement>('[role="tab"]', tabsRoot);
  const ink = $("[data-tabs-ink]", tabsRoot)!;
  const moveInk = (t: HTMLElement) => {
    ink.style.transform = `translateX(${t.offsetLeft}px) scaleX(${t.offsetWidth / 100})`;
  };
  const select = (t: HTMLButtonElement, focus = false) => {
    tabs.forEach((x) => {
      const on = x === t;
      x.setAttribute("aria-selected", String(on));
      x.tabIndex = on ? 0 : -1;
      const panel = $(`#${x.getAttribute("aria-controls")}`)!;
      panel.hidden = !on;
      if (on && !reduceQuery.matches) gsap.from(panel.children, { opacity: 0, y: 14, duration: 0.45, stagger: 0.05, ease: "power2.out" });
    });
    moveInk(t);
    if (focus) t.focus();
    ScrollTrigger.refresh();
  };
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => select(t));
    t.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) select(tabs[(i + d + tabs.length) % tabs.length], true);
    });
  });
  const current = () => tabs.find((t) => t.getAttribute("aria-selected") === "true")!;
  moveInk(current());
  window.addEventListener("resize", () => moveInk(current()));
  document.fonts.ready.then(() => moveInk(current()));
}

/* ---------- FAQ accordion (native details, animated height) ---------- */

$$<HTMLDetailsElement>("[data-acc]").forEach((d) => {
  const summary = $("summary", d)!;
  const body = $("[data-acc-body]", d)!;
  summary.addEventListener("click", (e) => {
    if (reduceQuery.matches) return;
    e.preventDefault();
    if (d.open) {
      gsap.to(body, { height: 0, duration: 0.4, ease: "power2.inOut", onComplete: () => { d.open = false; gsap.set(body, { clearProps: "height" }); ScrollTrigger.refresh(); } });
    } else {
      d.open = true;
      gsap.fromTo(body, { height: 0 }, { height: "auto", duration: 0.5, ease: "power3.out", onComplete: () => ScrollTrigger.refresh() });
    }
  });
});

/* ---------- scroll + load motion ---------- */

const mm = gsap.matchMedia();

mm.add(
  {
    motion: "(prefers-reduced-motion: no-preference)",
    desktop: "(prefers-reduced-motion: no-preference) and (min-width: 861px)",
    mobile: "(prefers-reduced-motion: no-preference) and (max-width: 860px)",
  },
  (ctx) => {
    const { motion, desktop, mobile } = ctx.conditions as Record<string, boolean>;
    if (!motion) return; // reduced motion: CSS defaults are the final states

    /* 1. hero load sequence: landscape settles, title lines rise */
    const land = $("[data-hero-land]");
    const title = $("[data-hero-title]");
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    if (land) tl.from(land, { scale: 1.15, opacity: 0, duration: 1.6 }, 0);
    if (title) {
      SplitText.create(title, {
        type: "lines", mask: "lines", autoSplit: true,
        onSplit: (self) => tl.from(self.lines, { yPercent: 110, duration: 1.1, stagger: 0.09 }, 0.25),
      });
    }
    tl.from($$("[data-hero-fade]"), { opacity: 0, y: 18, duration: 0.7, stagger: 0.1 }, 0.9);

    // contour layers drift at different depths, and the hero copy lifts away
    $$("[data-layer]").forEach((layer, i) => {
      gsap.to(layer, { yPercent: -(i + 1) * 7, ease: "none", scrollTrigger: { trigger: "[data-hero]", start: "top top", end: "bottom top", scrub: true } });
      gsap.fromTo(layer, { xPercent: -1.5 * (i + 1) }, { xPercent: 1.5 * (i + 1), duration: 14 + i * 4, ease: "sine.inOut", repeat: -1, yoyo: true });
    });
    gsap.to("[data-hero-content]", { yPercent: -18, opacity: 0.2, ease: "none", scrollTrigger: { trigger: "[data-hero]", start: "top top", end: "bottom top", scrub: true } });

    /* 2. section headlines */
    $$("[data-reveal]").forEach((h) => {
      SplitText.create(h, {
        type: "lines", mask: "lines", autoSplit: true,
        onSplit: (self) => gsap.from(self.lines, {
          yPercent: 110, duration: 0.9, stagger: 0.08, ease: "power3.out",
          scrollTrigger: { trigger: h, start: "top 85%", once: true },
        }),
      });
    });

    /* 3. counters */
    $$("[data-count]").forEach((el) => {
      const end = Number(el.dataset.count);
      const dec = Number(el.dataset.decimals);
      const o = { v: 0 };
      el.textContent = (0).toFixed(dec);
      gsap.to(o, {
        v: end, duration: 1.8, ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 90%", once: true },
        onUpdate: () => { el.textContent = o.v.toFixed(dec); },
      });
    });

    /* 4. parallax inside framed media */
    $$("[data-parallax]").forEach((frame) => {
      const inner = $("[data-parallax-inner]", frame);
      if (inner) gsap.fromTo(inner, { yPercent: -6 }, { yPercent: 6, ease: "none", scrollTrigger: { trigger: frame, start: "top bottom", end: "bottom top", scrub: true } });
    });

    /* 6. expedition cards enter once */
    gsap.from($$("[data-card]"), {
      x: 60, opacity: 0, duration: 0.9, stagger: 0.08, ease: "power3.out",
      scrollTrigger: { trigger: "[data-rail]", start: "top 80%", once: true },
    });

    /* 5. the journey: pinned horizontal travel on desktop, drawn line on mobile */
    const journey = $("[data-journey]");
    const track = $("[data-journey-track]");
    const line = $("[data-journey-line]");
    const stationsEls = $$("[data-station]");
    if (journey && track && line && desktop) {
      journey.classList.add("is-pinned");
      const distance = () => track.scrollWidth - innerWidth;
      const travel = gsap.to(track, {
        x: () => -distance(), ease: "none",
        scrollTrigger: {
          trigger: "[data-journey-pin]", start: "top top", end: () => `+=${distance()}`,
          pin: true, scrub: 0.6, invalidateOnRefresh: true, anticipatePin: 1,
        },
      });
      gsap.fromTo(line, { scaleX: 0 }, {
        scaleX: 1, ease: "none",
        scrollTrigger: { trigger: "[data-journey-pin]", start: "top top", end: () => `+=${distance()}`, scrub: 0.6, invalidateOnRefresh: true },
      });
      stationsEls.forEach((s) => {
        gsap.from(s.children, {
          opacity: 0, y: 30, duration: 0.6, stagger: 0.05, ease: "power2.out",
          scrollTrigger: { trigger: s, containerAnimation: travel, start: "left 85%", toggleActions: "play none none reverse" },
        });
      });
      return () => journey.classList.remove("is-pinned");
    }
    if (journey && line && mobile) {
      gsap.fromTo(line, { scaleX: 1, scaleY: 0 }, { scaleY: 1, ease: "none", scrollTrigger: { trigger: track, start: "top 70%", end: "bottom 70%", scrub: true } });
    }
  },
);

document.fonts.ready.then(() => ScrollTrigger.refresh());
window.addEventListener("load", () => ScrollTrigger.refresh());
