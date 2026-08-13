# Shabnam Hakimi — Website Context for Claude Code

## Project overview
Static HTML site, no framework, no build step. Four pages.
All CSS is inline in each file's `<style>` block.
All content is hardcoded HTML — edit in place.

## File structure
```
index.html              — Main page (hero, about, research, featured projects, CV, contact)
graph.html              — Scientific knowledge graph visualization
cv.html                 — Data-driven CV (selected publications from JSON, education, positions)
cv-viewer.html          — PDF viewer (fetches CV PDF from CV repo)
projects.html           — Scientific research projects (Ongoing | Past | Tools & Datasets)
extracurriculars.html   — Personal & side projects (creative, side projects, writing)
graph/graph.json        — Graph data: 339 nodes, 707 edges, 7 clusters, 48 papers in meta.papers
graph/tool/index.js     — CLI tool: node graph/tool/index.js add --doi <doi> to add papers to graph.json
graph/editor.html       — Graph editor (existing, untouched)
data/sync-bib.js        — Syncs CV bib files → publications.json + graph.json
data/publications.json  — Derived from CV bib files
```

## Design system
```css
--paper:    #f5f2ec    /* warm off-white, graph paper background */
--ink:      #111118    /* near-black body text */
--ink-blue: #1a2c6b    /* deep blue accent, pen/marker feel */
--ink-dim:  rgba(17,17,24,0.55)   /* darkened 2026-07-23 for legibility */
--ink-faint:rgba(17,17,24,0.15)
--blue-g:   rgba(80,140,200,0.20)   /* minor grid lines */
--blue-G:   rgba(80,140,200,0.42)   /* major grid lines */

/* Highlighter palette */
--h-yellow: #FFFF77   /* laser lemon */
--h-slate:  #7777FF   /* slate blue */
--h-helio:  #C977FF   /* heliotrope */
--h-violet: #FF77E4   /* violet web */
--h-red:    #FF7792   /* ultra red */
--h-cheese: #FFAE77   /* mac & cheese */
--h-mint:   #77FFE4   /* mint */
--h-lime:   #AAFF77   /* lime green */

/* Fonts */
--sans: 'DM Sans', sans-serif        /* headings, titles, hero name */
--mono: 'Space Mono', monospace      /* nav, labels, body, all UI text */
```

Graph paper background is CSS `background-image` with 4 gradients:
- Major grid: 80px × 80px at `--blue-G` opacity
- Minor grid: 16px × 16px at `--blue-g` opacity

## Navigation structure
```
SH    ABOUT    RESEARCH    EXTRACURRICULARS    CONTACT
                ↓ (hover only)
           Publications · CV
```
- Sub-links are `position: absolute`, out of flow — don't affect nav height
- Appear on hover over RESEARCH `li` via `max-height` + `opacity` transition
- Nav stays single-height at rest, equal spacing between all items
- graph.html uses a simple `#back` link, no full nav

Nav HTML pattern (index, cv, projects, extracurriculars):
```html
<nav>
  <a href="index.html" class="nav-logo">
    <span class="nav-logo-hl" id="nav-logo-hl"></span>
    <span class="nav-logo-text">SH</span>
  </a>
  <ul class="nav-links">
    <li><a href="...">About</a></li>
    <li><a href="...">Research</a>
      <div class="nav-sub-links">
        <a href="graph.html">Graph</a>
        <a href="projects.html">Projects</a>
        <a href="cv.html">CV</a>
      </div>
    </li>
    <li><a href="extracurriculars.html">Extracurriculars</a></li>
    <li><a href="...#contact">Contact</a></li>
  </ul>
</nav>
```
graph.html uses a mini-bar at top-left instead of full nav: `← Shabnam Hakimi   Research: Graph · Projects · CV`
Key CSS:
```css
.nav-links li { position: relative; }
.nav-sub-links {
  position: absolute; top: 100%; left: 0;
  max-height: 0; overflow: hidden; opacity: 0;
  transition: max-height 0.25s ease, opacity 0.2s ease, padding 0.25s ease;
}
.nav-links li:hover .nav-sub-links {
  max-height: 2rem; opacity: 1; padding-top: 0.3rem;
}
```

## SH Logo
Cycles through highlighter colors slowly at rest, faster on hover.
```html
<a href="index.html" class="nav-logo">
  <span class="nav-logo-hl" id="nav-logo-hl"></span>
  <span class="nav-logo-text">SH</span>
</a>
```
JS at bottom of each page initializes the cycle. The `nav-logo-hl` span is
`position:absolute`, `top:28%`, `height:40%`, creating a mid-stroke highlight band.

## Cursor
Custom `+` crosshair in Space Mono Bold. Scales to 1.9× and turns ink-blue on hover
over `a` and `button` elements. `cursor: none` on `body`, `a`, `button`.

## Content locations in index.html
| Section | HTML selector |
|---|---|
| Hero tagline | `<p class="hero-tagline">` |
| About copy | `<div class="about-text">` |
| Research areas | `<div class="research-grid">` — 8 `.research-item` divs; below-1000px fallback + source text for the area graph, see "Research visual" below |
| Featured projects | `<div class="work-list">` — `.work-item` divs |
| CV entries | `<div class="cv-layout">` |
| Contact links | `<div class="contact-links">` |

## Research visual (index.html)
Two generated SVGs replace the old flat research grid at ≥1000px; below that,
a reduced mobile figure plus the original `.research-grid` show instead. The
breakpoint is a single `@media (min-width: 1000px)` block layered on
narrow-first defaults (mobile figure + grid shown, desktop figure + area
graph hidden) — one query, not two, so there's no fractional-viewport gap
either state could fall through.
- **Approach figure** — the state-estimation figure (how the research program
  approaches problems). Desktop version: `figures/approach.py`, viewBox
  1040×482. Narrow variant for <1000px: `figures/approach_mobile.py`
  (imports `approach.py`), viewBox 336×329, capped at `max-width: 420px`.
- **Area graph** — eight research-area nodes in a ring, edges weighted by
  shared concepts pulled from `graph/graph.json`. Titles only at rest;
  each node's description opens radially outward on click. Generated by
  `figures/area_graph.py` (rendering) + `figures/area_graph_data.py` (graph
  loading, cluster-pair weights, the circular layout solver), which scrape
  the area titles verbatim out of index.html's `.research-grid` `<h3>`s.
  Each node links to its `projects.html#section-…` anchor (e.g. Agent State
  Inference → `#section-agent-state`).

The `.research-grid` markup stays in the DOM permanently — it is both the
small-screen fallback AND the source of truth the area graph is generated
from, not just a legacy leftover. That makes `index.html`'s eight
`.research-item` titles and descriptions the de-facto canonical copy for the
eight research areas — `figures/area_graph.py` scrapes them from here, not
from `graph/graph.json`'s cluster names or from `projects.html`'s section
copy. The eight `<h3>` titles must also byte-match `graph.json`'s
`meta.clusters[].name` (the scraper asserts this at import time); if you
rename an area, edit index.html, `projects.html`, and `graph.json` together
so none of the three silently drifts from the others.

**Never hand-edit the SVG inside index.html.** Edit the generator, then:

    python3 figures/build.py

`build.py`'s `inject()` splices generated SVG between
`<!-- FIGURE:name -->` / `<!-- /FIGURE:name -->` markers; it refuses to
inject a payload that contains a literal copy of its own markers, and raises
on a missing marker rather than silently no-opping.

Tests (20 total, plain-assert, run directly — no test runner):
`python3 figures/test_generators.py` (9), `figures/test_build.py` (6),
`figures/test_sync.py` (5, fails if the injected SVG in index.html is stale
relative to the generators — rerun `python3 figures/build.py` if so).
`test_sync.py` also locks the eight area titles and descriptions verbatim
against index.html's `.research-grid`, and asserts the three `FIGURE:`
marker blocks stay before `.research-grid` (see the comment next to
`parse_research_grid()` in `area_graph.py` for why that ordering matters).
Design doc: `docs/superpowers/specs/2026-08-06-homepage-research-visual-design.md`.
Every word in both figures is Shabnam's, verbatim — never reword a label to
make it fit; drop it instead.

## Node schema (graph/graph.json)
Each node: `{id, label, weight, cluster, level, nodes_contributed?}`.
- `level` (added 2026-05-09): one of `theory | construct | method | mechanism | domain`. graph.html only renders `construct + theory` by default (see `VISIBLE_LEVELS` in graph.html). Reclassify all with `node graph/tool/classify-levels.js --all` (uses claude-opus-4-7).
- After any change to `graph.json`, run `node data/inline-graph.js` to sync the inlined data blocks in `index.html` and `graph.html`, **and** `python3 figures/build.py` to regenerate the area graph on index.html (see "Research visual" above) — it also derives from `graph.json` (cluster pair weights, node sizing, ring order), so a `graph/tool/index.js add` or lift/merge run that skips this step ships a stale area graph. `figures/test_sync.py` catches the staleness but only if someone remembers to run it.
- Labels render lowercase site-wide (applied at render time and requested in the extraction prompt).

## Cluster color tokens (used on cv.html, projects.html)
`class="c0"` through `c6` on a parent element sets `--cc` to the cluster's highlighter color. Children that style themselves with `var(--cc)` (e.g., `.pub-cluster`, `.project-cluster`) pick it up.
Cluster color for yellow (c4) uses `#9a7c00` (dark amber) for legibility on light bg.

## Research clusters (graph.html + cv.html + projects.html)
Renamed 2026-07-22 to match the site's research themes; see
`docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md` for the
full paper-to-cluster mapping and the rationale behind each boundary.
| # | Name | Color |
|---|---|---|
| 0 | Motivated Learning, Decision Making, & Self Regulation | `#7777FF` slate blue |
| 1 | Creativity & Design | `#C977FF` heliotrope |
| 2 | Psychology-Guided Generative AI | `#FF77E4` violet web |
| 3 | Intervention Science & Applied Behavior Change | `#FF7792` ultra red |
| 4 | Preference Elicitation & Prediction | `#FFFF77` laser lemon (display as `#9a7c00`) |
| 5 | Social, Cognitive, & Affective Neuroscience | `#FFAE77` mac & cheese |
| 6 | Consumer Psychology & Market Forecasting | `#77FFE4` mint |
| 7 | Agent State Inference | `#AAFF77` lime green |

## Extracurriculars page structure
Three sections: Creative, Side projects, Writing. Static anchor index at top (no filtering JS).
Each `.project-item` has `data-type` of `creative`, `side-project`, or `writing` and a colored `.project-type` label.

## Projects page structure (scientific research)
Three sections: Ongoing, Past, Tools & Datasets. Static anchor index at top.
Each `.project-item` has a `c0`–`c6` cluster class (parent-level), and renders a `.project-cluster` pill in cluster color plus free-form `.project-tag` chips. `.project-status` shows status sub-label (Active / Completed / Released, etc.).

## Eulerian doodles (cv.html + projects.html + extracurriculars.html)
5 animated Eulerian graph doodles per page, rendered on a fixed canvas behind all content.
Each doodle cycles through 12 graphs in order, one highlighter color at a time.
Key constants at the top of the doodle JS block:
```js
const DOODLES_ENABLED = true;  // toggle off with false
const COUNT = 5;               // number of doodles
const SIZE  = 160;             // px — 2× major grid cell (80px)
const OP    = 0.15;            // opacity
```
Positions use golden ratio horizontal spacing across the page height.

## Content card
cv.html, projects.html, and extracurriculars.html have a semi-transparent content card
(`rgba(245,242,236,0.80)`) wrapping all content. index.html is full-bleed (intentional).
graph.html has its own full-screen canvas UI.

## Known TODOs (priority order)
1. **Fill in extracurriculars.html** — still a placeholder template. projects.html was rebuilt with real content 2026-07-24. Blocked on Shabnam filling 4 content blanks in site-content.md.
2. **Homepage research visual (index.html)** — implemented (generators, tests, CSS, injection into index.html) but NOT yet merged to main and NOT live; lives on branch/worktree `worktree-homepage-research-viz`. Open decisions before merge:
   - **Static vs animated** — shipping static. index.html's hero already runs a canvas animation; a second animated element is a separate call, deferred.
   - **The section title** — Shabnam is writing it via site-content.md; the approach figure already reserves 34px of headroom for it, and index.html carries a comment, not a placeholder heading, in the meantime. One line of connective copy between the two figures is expected alongside it, also hers.
   - **Accessibility** — each area-graph node currently produces two tab stops because a real `<a>` is nested inside a `role="button"` group (an ARIA anti-pattern). Known, deferred for Shabnam's call at merge time, not yet fixed.
3. ~~**Review/edit about copy on index.html**~~ — done. Shabnam rewrote the About section copy (2026-07-26) in her own voice.
4. ~~**CV PDF link**~~ — done. Contact section links to cv-viewer.html.
5. ~~**Mobile CSS pass**~~ — done. Nav overflow fixed on all pages; cursor reset on mobile; graph.html stacks canvas/sidebar.
6. ~~**Inline graph sync**~~ — done. `node data/inline-graph.js` re-inlines `graph/graph.json` into both `index.html` and `graph.html`. Run after `node graph/tool/index.js add` or `node data/sync-bib.js`. The `clusterData` block in graph.html is still hard-coded with friendly cluster names (separate from `graphData.meta.clusters`); leave for now unless cluster names change.
7. ~~**Nav active state**~~ — done. Passive scroll listener replaces broken IntersectionObserver.
8. ~~**Concept extraction**~~ — done. 48/49 papers have graph nodes; Bachman2020journal intentionally excluded (scicomm keyword, no research concepts). `rebuild-from-corpus.js` filters `EXCLUDED_KEYWORDS = ['scicomm', 'commentary', 'unlisted']`.

## Related repos (corpus lives elsewhere)
The personal-research corpus pipeline (matches CV publications to local PDFs/DOCs across `~/Downloads/{fromSugarSync,Projects,Project Archive,fromInternet}`) lives in a separate private repo: `~/projects/research-corpus`. It reads `data/publications.json` from here via `$WEBSITE_DATA_DIR` (defaults to `~/projects/website/data`) and writes its own `corpus-catalog.json`. v1 (2026-05-16) ships matching + acquisition labeling; v2+ (policy classification, PDF hosting on cv.html, concept re-extraction into graph.json) is parked. See `docs/spec.md` and `docs/plan.md` in that repo.

## CV source
Shabnam has a private local LaTeX CV repo with `.bib` files.
Some bib entries are tagged `selected` — use these for featured publications.

## Real contact info
- Email: shabnam@tri.global
- Google Scholar: https://scholar.google.com/citations?user=KVRrn40AAAAJ
- GitHub: shabtastic
- LinkedIn: https://www.linkedin.com/in/shabnam-hakimi-8a85166

## Graph animation notes (index.html)
- Marching-squares contour lines driven by spreading activation
- Collins & Loftus (1975) spreading activation model
- 7 base Gaussian hills + node activation peaks
- Contour lines in single ink-blue color (opacity + weight only encode intensity)
- Animation canvas: `id="field-canvas"`, `mix-blend-mode` not set (paper bg shows through)

## Graph page notes (graph.html)
- Force-directed layout, 400 iterations, cluster gravity
- Topographic contour overlay beneath nodes (same marching squares algorithm)
- Cluster overlay: "projects →" button in sidebar opens a full-screen overlay
  showing papers from `graph.json` meta.papers for that cluster
- Spreading activation: DECAY=0.22, SPREAD=0.22, interaction cooldown=5s
- Edge weights encoded as line thickness (w^1.5 × 2.0px) + opacity (w^1.8 × 0.22)
- Edge pulses: small dots traveling along active edges (spawn rate 0.18)
