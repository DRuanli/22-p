# Personal site — project brief for Claude Code

An academic profile site for a young researcher from Vietnam (data mining, educational ML).
Layout rhythm and motion are modelled on https://tour-kyrgyzstan.com (a Framer travel site), as
shown in the owner's screen recordings: white paper, heavy uppercase grotesk headlines starting on
column 5, uppercase justified monospace text, red bracket buttons `[ … ]`, red crop marks around
media, fixed edge rulers with a red scroll index, red scramble-text reveals, a pinned route list
with plates scrolling under a fixed centre frame, itinerary rows with a red note box, PREV/NEXT
line sliders, a ruled FAQ grid, per-route detail pages, and a black panel wipe between pages. We copy the *rhythm and motion grammar*, never its text,
photos, video, logo or brand. All content comes from `docs/content.md`.

## Stack (do not change without asking)
- Astro 5 (static output) + TypeScript, plain CSS with custom properties (no Tailwind).
- GSAP 3 (`gsap` npm package, all plugins are free: ScrollTrigger, SplitText) for motion.
- Lenis (`lenis` npm package) for smooth scroll, synced to ScrollTrigger.
- Embla Carousel (`embla-carousel`) for draggable carousels.
- Deploy: GitHub Pages via GitHub Actions (`../.github/workflows/deploy-portfolio.yml`, repo root), no server code.

## Commands
- `npm run dev` — dev server on http://localhost:4321
- `npm run build && npm run preview` — production check
- `npm run shots` — Playwright screenshots into `qa/` (see visual-qa agent)

## Sections (map of reference → this site)
Home (`src/pages/index.astro`):
1. Hero: full-bleed cover photo (Ken Burns drift, parallax), uppercase headline, scrambled intro, red CTA.
2. Founder: ruled 3-column grid — halftone portrait (public/portrait.jpg or monogram), text, facts.
3. Routes: pinned list (name + length) · fixed crop frame with [ DISCOVER ] · scrambled teaser;
   film plates scroll under the frame. Each route has a detail page.
4. Feature: 675-student cohort plate, wide crop frame, [ READ IN ESWA ].
5. The route so far: itinerary rows (when · where · title) with a red note box.
6. Academic profile: stat row + ruled grid (Education, Honours, Skills).
7. Publications (after Feature): stat row + expandable entries (citation, copy, route link), a
   plate preview follows the pointer on desktop.
8. FAQ: ruled 4-column grid.
9. Footer: big email in a crop frame, Scholar, ORCID, CV when public/cv.pdf exists.
Route pages (`src/pages/routes/[id].astro`): plate hero, stat row, "What the paper found"
(PaperDepth: summary, count-up figures, BarChart, contributions, data), N-month overview itinerary,
CTA, "Continue exploring" cards. TUFCI adds PaperFigures (open-access figures); Regensburg adds
Exchange (numbers, notebook, a DrawSVG map of every trip).
Gallery (`src/pages/gallery.astro`): dark intro card, then GalleryPlane — an endless draggable
plane of photos, paper figures and plates with a lens bend, a lightbox, and a List view.
Home and Gallery open with an Intro typewriter card once per session (skipped for reduced motion
and after a page wipe).

## Motion rules
- Smoothness first: never redraw canvases or SVG filters per frame; animate pre-rendered
  layers with transform/opacity. Scroll work is batched into Lenis' scroll event with cached
  measurements (refresh on ScrollTrigger refresh/resize). No mix-blend-mode on fixed elements.
- One orchestrated hero load sequence (SplitText lines rise + video scale-in). Everything
  else is scroll-linked and quiet; no fade-up on every block.
- Register plugins once in `src/scripts/motion.ts`; wrap all setup in `gsap.matchMedia()`
  with a `(prefers-reduced-motion: reduce)` branch that shows final states instantly.
- Animate only `transform` and `opacity`. No layout-thrashing properties.
- Lenis drives `ScrollTrigger.update`; use `gsap.ticker` for Lenis `raf`, `lagSmoothing(0)`.
- Call `ScrollTrigger.refresh()` after fonts and hero media load.

## Design notes
- The owner asked for the reference's design language specifically; follow it over the
  frontend-design skill's generic advice (uppercase mono labels, brackets etc. are intended here).
- Visuals are generated "film plates" (`Plate.astro`); a real photo at public/media/<id>.jpg
  replaces a plate automatically. Never use the reference site's photos, text or logo.
- Tokens live in `src/styles/tokens.css`; fonts self-hosted or from Google Fonts.

## Quality bar (check before saying "done")
- Lighthouse performance ≥ 90 mobile; hero video ≤ 4 MB, poster image, `preload="metadata"`.
- Works at 375, 768, 1280, 1440 px; no horizontal scroll; visible keyboard focus.
- Run the `visual-qa` agent and fix what it reports before opening a PR.

## Working style
- Plan first in `docs/plan.md`, build one section per commit, screenshot after each section.
- Never invent publications, quotes, numbers or affiliations: ask or leave `TODO:` markers.
