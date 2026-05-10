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
graph/graph.json        — Graph data: 42 nodes, 100 edges, 7 clusters, papers in meta.papers
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
--ink-dim:  rgba(17,17,24,0.45)
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
| Research areas | `<div class="research-grid">` — 4 `.research-item` divs |
| Featured projects | `<div class="work-list">` — `.work-item` divs |
| CV entries | `<div class="cv-layout">` |
| Contact links | `<div class="contact-links">` |

## Node schema (graph/graph.json)
Each node: `{id, label, weight, cluster, level, nodes_contributed?}`.
- `level` (added 2026-05-09): one of `theory | construct | method | mechanism | domain`. graph.html only renders `construct + theory` by default (see `VISIBLE_LEVELS` in graph.html). Reclassify all with `node graph/tool/classify-levels.js --all` (uses claude-opus-4-7).
- After any change to `graph.json`, run `node data/inline-graph.js` to sync the inlined data blocks in `index.html` and `graph.html`.
- Labels render lowercase site-wide (applied at render time and requested in the extraction prompt).

## Cluster color tokens (used on cv.html, projects.html)
`class="c0"` through `c6` on a parent element sets `--cc` to the cluster's highlighter color. Children that style themselves with `var(--cc)` (e.g., `.pub-cluster`, `.project-cluster`) pick it up.
Cluster color for yellow (c4) uses `#9a7c00` (dark amber) for legibility on light bg.

## Research clusters (graph.html + cv.html + projects.html)
| # | Name | Color |
|---|---|---|
| 0 | Self-regulation | `#7777FF` slate blue |
| 1 | Predictive brain | `#C977FF` heliotrope |
| 2 | Generative AI | `#FF77E4` violet web |
| 3 | Interventions | `#FF7792` ultra red |
| 4 | Neuroeconomics | `#FFFF77` laser lemon (display as `#9a7c00`) |
| 5 | Social neuroscience | `#FFAE77` mac & cheese |
| 6 | Consumer & preference | `#77FFE4` mint |

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
1. **Fill in projects.html and extracurriculars.html** — both are placeholder templates
2. **Review/edit about copy on index.html** — written from public sources, needs Shabnam's voice
3. **CV PDF link** — `href="#"` in contact section, needs real file (or point to cv-viewer.html)
4. **Mobile CSS pass** — untested at ≤768px; graph.html sidebar (320px fixed) overflows on mobile
5. ~~**Inline graph sync**~~ — done. `node data/inline-graph.js` re-inlines `graph/graph.json` into both `index.html` and `graph.html`. Run after `node graph/tool/index.js add` or `node data/sync-bib.js`. The `clusterData` block in graph.html is still hard-coded with friendly cluster names (separate from `graphData.meta.clusters`); leave for now unless cluster names change.
6. **Nav active state** — no scroll-spy on index.html; active link doesn't update on scroll
7. **Concept extraction** — 19 of 45 publications still have no graph nodes (per memory)

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
