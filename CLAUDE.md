# Shabnam Hakimi — Website Context for Claude Code

## Project overview
Static HTML site, no framework, no build step. Four pages.
All CSS is inline in each file's `<style>` block.
All content is hardcoded HTML — edit in place.

## File structure
```
index.html        — Main page (hero, about, research, featured projects, CV, contact)
graph.html        — Scientific knowledge graph visualization
publications.html — Full publications list
projects.html     — Personal & side projects (extracurriculars)
graph.json        — Graph data: 42 nodes, 100 edges, 7 clusters, 1 paper in meta.papers
index.js          — CLI tool: node index.js add --doi <doi> to add papers to graph.json
editor.html       — Graph editor (existing, untouched)
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

Nav HTML pattern (index, publications, projects):
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
        <a href="publications.html">Publications</a>
        <a href="...#cv">CV</a>
      </div>
    </li>
    <li><a href="projects.html">Extracurriculars</a></li>
    <li><a href="...#contact">Contact</a></li>
  </ul>
</nav>
```
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

## Publications page structure
Year-grouped entries. Each entry:
```html
<div class="pub-entry reveal c1" data-clusters="1 2">
  <div class="pub-main">
    <div class="pub-title"><a href="DOI_URL">Title</a></div>
    <div class="pub-authors">Author, A., <strong>Hakimi, S.</strong>, ...</div>
    <div class="pub-venue"><em>Journal/Venue</em>, Year</div>
  </div>
  <div class="pub-aside">
    <span class="pub-year">2024</span>
    <span class="pub-cluster">Cluster name</span>
    <a href="DOI_URL" class="pub-link">DOI →</a>
  </div>
</div>
```
`data-clusters` is space-separated cluster numbers (0–6).
`class="c0"` through `c6` sets the cluster color via `--cc` CSS variable.
Cluster color for yellow (c4) uses `#9a7c00` (dark amber) for legibility on light bg.

## Research clusters (graph.html + publications.html)
| # | Name | Color |
|---|---|---|
| 0 | Self-regulation | `#7777FF` slate blue |
| 1 | Predictive brain | `#C977FF` heliotrope |
| 2 | Generative AI | `#FF77E4` violet web |
| 3 | Interventions | `#FF7792` ultra red |
| 4 | Neuroeconomics | `#FFFF77` laser lemon (display as `#9a7c00`) |
| 5 | Social neuroscience | `#FFAE77` mac & cheese |
| 6 | Consumer & preference | `#77FFE4` mint |

## Projects page structure
Three sections: Creative, Side projects, Writing.
Static anchor index at top (no filtering JS).
Each item:
```html
<div class="project-item reveal" data-type="creative">
  <div class="project-meta">
    <span class="project-year">2024</span>
    <span class="project-type" style="color:var(--h-violet)">Creative</span>
  </div>
  <div class="project-body">
    <div class="project-title">Title</div>
    <p class="project-desc">Description.</p>
    <div class="project-tags"><span class="project-tag">tag</span></div>
    <a href="url" class="project-link">View →</a>
  </div>
</div>
```
`data-type`: `creative`, `side-project`, or `writing`

## Eulerian doodles (publications.html + projects.html)
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
publications.html and projects.html have a semi-transparent content card
(`rgba(245,242,236,0.80)`) wrapping all content. index.html is full-bleed (intentional).
graph.html has its own full-screen canvas UI.

## Known TODOs (priority order)
1. **Populate publications.html** from bib files in CV repo
   - Parse all `.bib` entries: title, authors, year, venue, DOI/URL
   - Use `selected` tag to identify featured papers
   - Update featured projects on index.html `#work` section with selected papers
   - Assign `data-clusters` to each paper (can be approximate)
   - Fill in DOI links (currently `href="#"` on several entries)

2. **Fill in projects.html** — all 3 items are placeholder templates

3. **Review/edit about copy** — written from public sources, needs your voice. Placeholder '[hobby / interest]' sentence has been removed.

4. **`cv.html`** — standalone CV page doesn't exist yet. Nav sub-link currently points to `index.html#cv` (a section). Build a full page from the LaTeX CV source. Should include: full employment history, education, publications list (or link to publications.html), awards, talks.

5. **CV PDF link** — `href="#"` in contact section, needs real file

6. **Mobile CSS pass** — untested at ≤768px; graph.html sidebar especially
   needs rethinking (sidebar is 320px fixed, will overflow on mobile)

7. **Inline graph sync** — `graph.json` has papers in `meta.papers` but
   `index.html` and `graph.html` inline the graph data. After `node index.js add --doi`,
   need a step to re-inline the updated graph.json into both HTML files.
   Look at how graph data is loaded: `<script type="application/json" id="graph-data">`

8. **Nav active state** — currently no scroll-spy; active link doesn't update on scroll

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
