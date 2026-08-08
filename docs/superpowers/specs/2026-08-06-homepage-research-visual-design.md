# Homepage research visual — design

**Status:** figure design converged (mockup v22). Site integration NOT yet decided — see Open questions.
**Date:** 2026-08-06
**Mockups:** `docs/superpowers/mockups/homepage-research-viz/` (v1–v21 + `gen_v*.py` generators)
**Supersedes:** the mockup README's "design as converged (v11)" section, which described the pre-warp figure.

## Problem

`index.html` presents the research program as a flat `.research-grid` — eight
`.research-item` boxes in a 2-column grid. Eight boxes read as eight parallel
interests. The program is not eight interests; it is one program with eight
positions in it: detecting unobservable psychological states over time, at
nested timescales, in context — via new elicitation, multi-signal
triangulation, and computational models — in order to intervene well.

The visual's job is to make that single argument legible at a glance, in
layperson language, without turning the homepage into a lecture.

## The figure

A hand-sketched, graph-paper state-estimation figure on one shared time axis.
Read left to right; "now" divides measured past from predicted future.

**Time axis (warped).** One shared nonlinear axis spanning one year:
`x = now − 105.3·log₁₀(1 + seconds ago)`. Recent time is stretched, deep past
compressed. This is what lets a heartbeat and a year-long trend coexist on one
axis honestly.

**Signal strands.** Seven strands in two named families — *measurable
physiology* (heart, skin, breath, eyes) and *observable behavior* (behavior,
movement, choices) — each with a real period in seconds (gaze 0.35s, heart 1s,
breath 4s, movement 9s, skin 90s, behavior 150s, choices 2.5h). Fine structure
is drawn only where one cycle exceeds ~1.3px; left of that point the strand
carries a faint envelope band instead. Detail therefore switches on in a
staircase mirroring the timescale brackets. Strands include sensor gaps —
discontinuities in *sampling*, never in the state.

**Individual experience.** Eight olive ticks rising from the grey true-state
curve, droplet at the top — moments when the state is measured by asking the
person. They occur at every timescale, not just the fast end. Rooted exactly on
the grey curve (verified 0.0px), drawn *before* the estimate so the navy stroke
overdraws each crossing cleanly.

**Two curves.** A faint grey continuous **true state** — never broken, never
uncertain, because uncertainty lives in sampling and not in the state — and a
bold ink-blue **estimate** carrying a sampling-uncertainty band that tightens as
evidence arrives and converges toward the true state. The estimate's shape is
computed from the strands, not hand-faked.

**Nested timescale brackets.** Five brackets — seconds, hours, days, weeks,
years — each straddling the "now" divider, nesting strictly on both sides. The
left arm is how far back that rate reaches; the right arm is how far ahead it
lets us see. Arms are asymmetric (the observed span is wider than the forecast)
but nesting order holds independently on each side. Arm positions are computed
from the warp, not hand-placed.

**Now and the forecast.** A thin solid divider at "now". Past it, the estimate
projects a widening cone to an outcome marker, with two ghost futures: the
drift (*without intervention*, in a lighter tint of the estimate blue so label
and path read as one secondary element) and the improved path.

**Intervention.** A purple **highlighter swipe** across the moment — a soft
vertical band (13px wide, rounded ends, 0.30 opacity) spanning the two curves
and their band, with a hairline core at 0.85. Plus her sentence in the same
purple, and the forecast-zone block.

The swipe was chosen over four glyph alternatives (filled triangle, purple
tick, diamond, open caret) and over a no-glyph treatment that recolored a
stretch of the estimate. Its case: the site's entire design system is built on
highlighter colors — the SH logo is a highlight band — so a swipe is native
vocabulary that needs no explaining. It is an *area*, so it cannot be confused
with the olive tick marks; it is vertical like the "now" divider, so it reads as
a moment in time; and areas survive scaling down, which thin glyphs do not.
Alternatives are preserved in `gen_marker_options.py` / `research-viz-marker-options.html`.

## What the figure is, and how the eight areas relate to it

Settled 2026-08-07 after three wrong hypotheses. Her framing, verbatim:

> "this is more how i approach the world and the areas are what emerge from it.
> there is some recursion (e.g., neuroscience projects that seem like they're
> only about physio)"

> "every project at least epistemologically runs the entire thing even if it's
> not using every capability or addressing every issue at mechnistic depth"

**The figure is an approach — an epistemology — not a map of the program.** The
eight research areas are what *emerged* from working that way. They are products
of it, not components, regions, positions, or capability-subsets of it.

**Every project runs the whole thing epistemologically.** Projects differ in
which capabilities they actually use and how deep they go mechanistically, but
none of them is a slice of the approach. A project that looks narrow — her
example: neuroscience work that appears to be only about physiology — still runs
the entire loop. The narrowness is an appearance, not a fact.

**Three rejected hypotheses, so they stay rejected:**

1. *Areas map to positions in the pipeline* (signals / state / inference /
   intervention / outcomes). Rejected outright. Some areas resisted placement
   because outputs cannot be located inside the process that produced them.
2. *Each area uses a subset of the paradigm's capabilities, and the page shows
   which.* Too weak and slightly wrong — it still treats areas as slices.
3. *Recursion is fractal: each area contains a smaller copy of the figure, and
   drilling into one reveals it scoped.* Rejected. If the figure is how she
   approaches the world it does not vary by area — that invariance is exactly
   what makes it connective — so eight scoped instances would claim eight
   approaches and reintroduce partitioning.

**Design consequence:** the figure appears **once**, precisely because it does
not subdivide. Nothing on the page may highlight, scope, crop, or instantiate it
on behalf of an area. The areas sit below it as the eight names that emerged.

## Copy policy

All figure text is Shabnam's, verbatim, and is not to be reworded, "improved",
or extended without her. Assistant-drafted copy was rejected wholesale during
iteration; every surviving string came from her markup passes:

- `measurable physiology` · `observable behavior` — family names
- `a person's true internal state` / `(that we can't directly see)`
- `our best guess at the internal state (triangulated from many diverse signals)`
- `individual experience`
- `intervention` / `a higher likelihood of the desired outcome` / `(internal state and/or behavior)`
- `the right intervention for the right person,` / `in the right context, at the right time`
- `without intervention` · `now` · the five unit names

**Title: deliberately absent.** The figure ships with no title of ours. The
title goes through the normal site copy route — written by Shabnam in
`site-content.md` alongside the rest of the section copy. The canvas reserves
34px of headroom (`TOP_PAD`) so a title drops in with zero relayout.

## Color

| element | value | note |
|---|---|---|
| physiology strands | `#FF7792` | site ultra red |
| behavior strands | `#D9822B` | darkened from `#FFAE77`, which washed out on paper |
| family labels | `#b0475f` / `#a35e1c` | dark versions of their own family color |
| individual-experience ticks | `#587722` | site lime darkened; 4.61:1; 52° off behavior amber |
| true state | `rgba(17,17,24,0.30)` | grey, 2px |
| estimate | `#1a2c6b` | site ink-blue, 11.63:1 |
| without-intervention fork | `#5A6C9E` | same hue family, 4.61:1, plainly secondary |
| intervention (marker + sentence) | `#8E24AA` | site heliotrope darkened, 6.3:1 |

Two color rules were learned the hard way and should hold: **darken site
highlighter colors for anything that must be read** (the site already does this
turning `#FFFF77` into `#9a7c00`), and **separate by hue, not just lightness** —
goldenrod failed as a tick color because at label size it collapsed into the
behavior amber despite different lightness.

## Principles (do not regress)

1. **Layperson language everywhere.** The eight cluster names are the only
   taxonomy text the figure may carry.
2. **Uncertainty lives in sampling, never in the state.** The true-state curve
   is continuous and unbroken. **No dashed lines for uncertainty** — dashes read
   as discontinuity. Use the band.
3. **No unexplained glyphs, no leader lines, no floating marks.** Every label
   sits adjacent to its referent. A legend miniature added in v17 to link words
   to marks became a floating fake tick and was deleted in v20 — the fix for
   "the label doesn't look connected" is to move the label next to a *real*
   instance, never to draw a decorative copy of one.
4. **Signal utility is prediction-target-dependent.** No fixed ranking, no
   privileged proxy. An earlier explicit parity device (colored dot trios) was
   removed as unreadable; parity now holds structurally — every strand folds
   into the estimate on identical terms.
5. **Elicitation happens at all timescales**, not only the fast end.
6. **Compositionality.** Curves are computed by the generators from the signals;
   the estimate's shape genuinely derives from the strands.
7. **Annotation is expensive.** The figure was stripped from 23 text elements to
   ~20 deliberately, and got better each time. Adding anything back should have
   to justify itself.

## Removed, and why (so it stays removed)

- **Inter-signal web arcs** (solid known couplings + dotted learned ones) —
  removed at her instruction ("get rid of all the callout lines"). Cost: the
  figure no longer states that the couplings between signals are themselves a
  research object.
- **The gaze↔choice hero junction** (heavier arc, emphasized end circle) — the
  arc went with the web; the circle became an unexplained glyph and was removed.
  Gaze now folds in like every other strand.
- **Parity dot trios**, **the legend miniature**, **the "?" glyphs**, **the
  arrow device**, **the bracket caption**, **all assistant-written titles and
  prose chrome** — all removed; see the generator headers for per-item rationale.

## Open questions

These are unresolved and block a complete implementation plan.

1. **Site integration.** Does the figure replace `.research-grid` or frame it?
   Static SVG or animated canvas? What happens at ≤768px, where the warped axis
   and 20 labels cannot survive as-is? Are the areas interactive (linking to
   projects/graph)?
3. **Context** is not represented geometrically; it currently lives only in her
   sentence ("in the right context"). Judged acceptable for now — everything the
   figure draws unfolds over time, and context is the dimension that doesn't.

## Implementation notes

The mockups are generated, not hand-drawn: `gen_v12.py` … `gen_v21.py`, each
extending its predecessor, tuning constants at the top of each file, generator
headers carrying the rationale for every change. `gen_v22.py` is current and is
the reference implementation of everything specified above. Output is a
self-contained HTML fragment (inline `<style>` + one `<svg>`), 1040×482,
which matches how the site works — inline CSS, no build step.

Porting to `index.html` should keep the generator as the source of truth for the
static geometry rather than hand-transcribing 20 labels and seven computed
strands into markup.
