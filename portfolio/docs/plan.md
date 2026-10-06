# Design plan

**Concept — two rivers.** Born by the Mekong (Can Tho), studied by the Danube (Regensburg).
Research as a journey: the hero draws the real route Can Tho → Ho Chi Minh City → Regensburg,
and publications sit on a draggable rail like river stops.

## Palette (river water, not cream/terracotta)
| name | hex | use |
|---|---|---|
| Mist | #E9EEEA | page background (cool, grey-green) |
| Deep | #10261F | text, hero background |
| Silt | #C08A2E | Mekong — accent, route line, focus ring |
| Danube | #35566F | links, secondary surfaces |
| Reed | #7C927A | muted text on dark, rules |
| Foam | #F7F9F7 | cards |

## Type
- Newsreader (display, optical size, real italic, Vietnamese glyphs) for headings.
- Public Sans for body and UI. Scale 1.25 (minor third) from 17px.

## Layout
```
[ HERO deep green ]  name small top-left · nav right
  big serif headline (3 lines)            route SVG right / below on mobile
  one-line + [See my work]
[ ABOUT ] portrait frame | fact slides (Embla, dots)
[ AFFILIATIONS ] one line of typeset names, wraps
[ JOURNEYS ] h2 + prev/next · rail of 4 cards (3 papers + interests)
[ TEACHING ] text left | Flyers / PET / IELTS ladder right (parallax)
[ WHAT I DO ] 3 columns
[ FOOTER deep ] email large · Scholar · ORCID · (CV)
```
Left-aligned throughout. Quotes and FAQ hidden until real content exists.

## Motion
One hero sequence (lines rise, route reveals left-to-right via transform on a clip rect, CTA fades),
h2 line reveals, rail cards enter once, teaching ladder parallax. Reduced motion = final state.
