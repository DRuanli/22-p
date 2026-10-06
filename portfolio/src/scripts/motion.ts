import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import Lenis from "lenis";
import EmblaCarousel from "embla-carousel";

gsap.registerPlugin(ScrollTrigger, SplitText);

/* ---------- carousels (work with or without motion) ---------- */

const reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

const factsRoot = document.querySelector<HTMLElement>("[data-facts]");
if (factsRoot) {
  const viewport = factsRoot.querySelector<HTMLElement>(".facts__viewport")!;
  const dots = [...factsRoot.querySelectorAll<HTMLButtonElement>("[data-dot]")];
  const embla = EmblaCarousel(viewport, { loop: true, duration: 30 });
  const sync = () => {
    const i = embla.selectedScrollSnap();
    dots.forEach((d, j) => d.setAttribute("aria-current", String(i === j)));
  };
  dots.forEach((d, j) => d.addEventListener("click", () => embla.scrollTo(j)));
  embla.on("select", sync);
  sync();

  // Gentle autoplay; stops for reduced motion, hover, focus, or once the visitor interacts.
  let timer: number | undefined;
  const stop = () => window.clearInterval(timer);
  const start = () => {
    stop();
    if (!reduceQuery.matches) timer = window.setInterval(() => embla.scrollNext(), 6000);
  };
  factsRoot.addEventListener("mouseenter", stop);
  factsRoot.addEventListener("mouseleave", start);
  factsRoot.addEventListener("focusin", stop);
  embla.on("pointerDown", () => { stop(); factsRoot.removeEventListener("mouseleave", start); });
  start();
}

const railRoot = document.querySelector<HTMLElement>("[data-rail]");
if (railRoot) {
  const embla = EmblaCarousel(railRoot, { dragFree: true, containScroll: "trimSnaps", align: "start" });
  const prev = document.querySelector<HTMLButtonElement>("[data-rail-prev]")!;
  const next = document.querySelector<HTMLButtonElement>("[data-rail-next]")!;
  prev.addEventListener("click", () => embla.scrollPrev());
  next.addEventListener("click", () => embla.scrollNext());
  const sync = () => {
    prev.disabled = !embla.canScrollPrev();
    next.disabled = !embla.canScrollNext();
  };
  embla.on("select", sync).on("reInit", sync).on("scroll", sync);
  sync();
}

/* ---------- motion ---------- */

const lenis = new Lenis({ lerp: 0.1, anchors: true });
lenis.on("scroll", ScrollTrigger.update);
gsap.ticker.add((t) => lenis.raf(t * 1000));
gsap.ticker.lagSmoothing(0);

const mm = gsap.matchMedia();

mm.add(
  { motion: "(prefers-reduced-motion: no-preference)", reduce: "(prefers-reduced-motion: reduce)" },
  (ctx) => {
    const { reduce } = ctx.conditions as { reduce: boolean };
    if (reduce) {
      // CSS defaults are the final states; just drop smooth scrolling.
      lenis.destroy();
      return;
    }

    /* 1. hero load sequence — the one orchestrated moment */
    const title = document.querySelector<HTMLElement>("[data-hero-title]");
    const fades = gsap.utils.toArray<HTMLElement>("[data-hero-fade]");
    const mask = document.querySelector<SVGRectElement>("[data-route-mask]");
    const stops = gsap.utils.toArray<SVGGElement>("[data-stop]");
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    if (mask) tl.from(mask, { scaleX: 0, svgOrigin: "0 0", duration: 1.6, ease: "power2.inOut" }, 0);
    if (stops.length) tl.from(stops, { opacity: 0, duration: 0.4, stagger: 0.45 }, 0.2);
    if (title) {
      SplitText.create(title, {
        type: "lines",
        mask: "lines",
        autoSplit: true,
        onSplit: (self) =>
          tl.from(self.lines, { yPercent: 110, duration: 1, stagger: 0.08 }, 0.1),
      });
    }
    if (fades.length) tl.from(fades, { opacity: 0, y: 16, duration: 0.6, stagger: 0.1 }, 0.9);

    /* 2. section headline reveal */
    gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((h) => {
      SplitText.create(h, {
        type: "lines",
        mask: "lines",
        autoSplit: true,
        onSplit: (self) =>
          gsap.from(self.lines, {
            yPercent: 110,
            duration: 0.9,
            stagger: 0.08,
            ease: "power3.out",
            scrollTrigger: { trigger: h, start: "top 85%", once: true },
          }),
      });
    });

    /* 3. parallax inside framed media */
    gsap.utils.toArray<HTMLElement>("[data-parallax]").forEach((frame) => {
      const inner = frame.querySelector("[data-parallax-inner]");
      if (!inner) return;
      gsap.fromTo(
        inner,
        { yPercent: -6 },
        { yPercent: 6, ease: "none", scrollTrigger: { trigger: frame, start: "top bottom", end: "bottom top", scrub: true } },
      );
    });

    /* 4. rail cards enter once */
    const cards = gsap.utils.toArray<HTMLElement>("[data-card]");
    if (cards.length) {
      gsap.from(cards, {
        x: 60,
        opacity: 0,
        duration: 0.9,
        stagger: 0.06,
        ease: "power3.out",
        scrollTrigger: { trigger: "[data-rail]", start: "top 80%", once: true },
      });
    }
  },
);

document.fonts.ready.then(() => ScrollTrigger.refresh());
