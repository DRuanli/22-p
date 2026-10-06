# Personal site — project brief for Claude Code

A personal introduction site for a young researcher and English teacher from Vietnam.
Layout rhythm and motion are modelled on https://tour-kyrgyzstan.com (a Framer travel site):
full-bleed video hero, big serif headlines, horizontal card carousels, quote carousel, FAQ
accordion, single contact CTA. We copy the *rhythm and motion grammar*, never its text,
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
1. Hero: full-bleed muted looping video or image sequence + headline with one
   italic serif word + one CTA ("See my work").
2. About: portrait + rotating short facts carousel (who I am, in 3–4 slides).
3. Affiliations strip: institution / journal names as typeset text (no third-party logos).
4. "Journeys" = publications & research lines as a horizontal draggable card rail.
5. Teaching: text + embedded video or photo collage.
6. What I do: three columns (Research · Teaching · Languages & travel).
7. Words from others: quote carousel — real quotes only, never invented.
8. FAQ accordion (collaboration, supervision, classes, contact).
9. Footer: email + one messaging link + CV download.

## Motion rules
- One orchestrated hero load sequence (SplitText lines rise + video scale-in). Everything
  else is scroll-linked and quiet; no fade-up on every block.
- Register plugins once in `src/scripts/motion.ts`; wrap all setup in `gsap.matchMedia()`
  with a `(prefers-reduced-motion: reduce)` branch that shows final states instantly.
- Animate only `transform` and `opacity`. No layout-thrashing properties.
- Lenis drives `ScrollTrigger.update`; use `gsap.ticker` for Lenis `raf`, `lagSmoothing(0)`.
- Call `ScrollTrigger.refresh()` after fonts and hero media load.

## Design notes
- The italic-accent-word headline IS a deliberate choice taken from the reference; keep it
  even though the frontend-design skill flags it as a generic tell. Use it in section
  headlines only, not in body copy.
- Avoid the generic AI looks listed in `.claude/skills/frontend-design/SKILL.md` everywhere else.
- Tokens live in `src/styles/tokens.css`; fonts self-hosted or from Google Fonts.

## Quality bar (check before saying "done")
- Lighthouse performance ≥ 90 mobile; hero video ≤ 4 MB, poster image, `preload="metadata"`.
- Works at 375, 768, 1280, 1440 px; no horizontal scroll; visible keyboard focus.
- Run the `visual-qa` agent and fix what it reports before opening a PR.

## Working style
- Plan first in `docs/plan.md`, build one section per commit, screenshot after each section.
- Never invent publications, quotes, numbers or affiliations: ask or leave `TODO:` markers.
