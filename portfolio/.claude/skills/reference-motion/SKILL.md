---
name: reference-motion
description: Recipes for this site's motion system (hero load sequence, split-line headline reveals, video scale-on-scroll, draggable card rail, quote carousel, accordion) built with GSAP + ScrollTrigger + SplitText + Lenis + Embla in Astro. Use whenever adding or changing any section, animation, scroll effect or carousel on this site.
---

# Reference motion system

The reference (tour-kyrgyzstan.com, built in Framer) uses a small, repeated motion
vocabulary. Reuse these recipes instead of inventing new effects per section.

## 0. Bootstrap (src/scripts/motion.ts) — run once

```ts
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger, SplitText);

export const lenis = new Lenis({ lerp: 0.1 });
lenis.on("scroll", ScrollTrigger.update);
gsap.ticker.add((t) => lenis.raf(t * 1000));
gsap.ticker.lagSmoothing(0);

export const mm = gsap.matchMedia();
document.fonts.ready.then(() => ScrollTrigger.refresh());
```

Every recipe below runs inside:
```ts
mm.add({ motion: "(prefers-reduced-motion: no-preference)",
         reduce: "(prefers-reduced-motion: reduce)" }, (ctx) => {
  const { reduce } = ctx.conditions!;
  if (reduce) { lenis.stop(); return; } // final states are the CSS defaults
  /* recipe code */
});
```
CSS default state = final visible state. JS sets the "from" state, so no-JS and
reduced-motion users always see content.

## 1. Hero load sequence (only orchestrated moment on the page)
- Split headline into lines with a mask:
  `SplitText.create(el, { type: "lines", mask: "lines", autoSplit: true, onSplit: (s) => tl.from(s.lines, …) })`
  — create the tween inside `onSplit` and return it so re-splits on resize/font load stay in sync.
  Do not use `text-wrap: balance` on split headlines.
- Timeline: video wrapper `scale 1.15 → 1`, `opacity 0 → 1` (1.4s, `power3.out`);
  lines `yPercent 110 → 0`, stagger 0.08, starting at `-=1.0`; CTA fades last.
- Total ≤ 1.8 s. No preloader screen unless the hero video blocks first paint.

## 2. Section headline reveal (all section h2)
Same masked line rise, triggered `start: "top 80%"`, `once: true`. The italic accent word
gets a 0.1 s extra delay — that is the only flourish.

## 3. Media scale-on-scroll (teaching video, about portrait)
`scrub: true`, `start: "top bottom"`, `end: "bottom top"`; inner image `yPercent -8 → 8`
inside an `overflow:hidden` frame (parallax). Never animate the pinned/trigger element itself.

## 4. Card rail ("Journeys" = publications)
Embla with `dragFree: true`, `containScroll: "trimSnaps"`; prev/next buttons with
`aria-label`; cards enter with `x: 60, opacity: 0`, stagger 0.06 when the rail hits
`top 75%`. Card hover: image `scale 1.04` over 0.6 s via CSS transition, not GSAP.

## 5. Quote carousel
Embla `loop: true`, autoplay paused on hover/focus and when reduced motion is on.
Crossfade text, keep height stable (`min-height` from the tallest quote).

## 6. FAQ accordion
Native `<details>`/`<summary>`; animate height with GSAP from 0 to `"auto"` on toggle.
Keyboard accessible by default — do not replace with divs.

## Performance checklist
- `will-change` only during the tween (GSAP sets/clears it).
- `ScrollTrigger.batch` for repeated items; kill triggers on Astro view transitions
  (`document.addEventListener("astro:before-swap", () => mm.revert())`).
- Hero video: H.264 MP4 + WebM, ≤ 4 MB, muted, playsinline, poster JPEG/AVIF.

## Verify
After any change run `npm run shots` and look at `qa/*.png`; also scroll-record with
Playwright video for motion review when a timeline changes.
