# Homepage Research Visual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace index.html's flat eight-box `.research-grid` with the approved approach figure plus a sparse eight-node area graph, keeping the grid as the small-screen fallback.

**Architecture:** Three SVGs are produced by Python generators and injected into `index.html` between HTML comment markers by a sync script, exactly mirroring how `data/inline-graph.js` keeps `graph.json` inlined. The generators become production code under `figures/`; `index.html` gains a marked block per SVG, ~90 lines of CSS, and one small vanilla-JS block for the area graph's click-to-open. No build step is added — the injected SVG is committed, so the site stays deployable as static files.

**Tech Stack:** Python 3 (generators, stdlib only), Node (existing sync tooling), plain HTML/CSS/JS, Playwright MCP for visual verification.

## Global Constraints

- **Every word in the figures is Shabnam's, verbatim.** Never add, reword, shorten, or paraphrase a label. If a label does not fit, drop it whole. Source of truth for area text is `index.html`'s `.research-grid`, scraped at generate time.
- **No title text anywhere in the figures.** The approach figure reserves 34px of headroom (`TOP_PAD`); the section title is written separately by Shabnam via `site-content.md`.
- Design principles in `docs/superpowers/specs/2026-08-06-homepage-research-visual-design.md` are binding: no dashed lines for uncertainty, no leader lines, no floating or unexplained glyphs, every label adjacent to its referent, the approach figure appears once and is never scoped or highlighted per area.
- Colors: physiology `#FF7792`, behavior `#D9822B`, family labels `#b0475f` / `#a35e1c`, experience ticks `#587722`, true state `rgba(17,17,24,0.30)`, estimate `#1a2c6b`, without-intervention `#5A6C9E`, intervention `#8E24AA`. Cluster colors darkened to ≥4.5:1 on `#f5f2ec`; cluster 4 renders `#9a7c00`.
- Site conventions: inline CSS in each page's `<style>`, no framework, no build step, DM Sans headings / Space Mono body, graph-paper background.
- **Breakpoint: 1000px.** At ≥1000px show the desktop approach figure + area graph. Below 1000px show the mobile approach figure + the existing `.research-grid`. Rationale: the area graph measured unreadable below ~900px and wants ≳1000px; the desktop figure is 1040 units wide.
- Generators are the source of truth. Never hand-edit injected SVG in `index.html`.

---

## File Structure

**Created:**
- `figures/approach.py` — desktop approach figure generator (from `gen_v22.py`). Emits an SVG fragment.
- `figures/approach_mobile.py` — mobile variant A (from `gen_v22_mobile.py`). Imports `approach.py` as a library.
- `figures/area_graph_data.py` — graph.json loading, cross-cluster pair weights, circle-order solver, contrast policy (from `gen_area_graph.py`).
- `figures/area_graph.py` — D-plain area graph generator (from `gen_area_graph_mytext.py`), scrapes `index.html` for area titles and hrefs.
- `figures/build.py` — renders all three SVGs and injects them into `index.html` between markers.
- `figures/README.md` — how to regenerate.

**Modified:**
- `index.html` — research section markup, CSS, one JS block.
- `CLAUDE.md` — document the figures pipeline.

**Not modified:** `graph/graph.json`, `data/inline-graph.js`, `projects.html`, `graph.html`, the mockups under `docs/superpowers/mockups/` (kept as the design record).

---

### Task 1: Move the generators into `figures/` and prove output is unchanged

**Files:**
- Create: `figures/approach.py`, `figures/approach_mobile.py`, `figures/area_graph_data.py`, `figures/area_graph.py`, `figures/README.md`
- Test: `figures/test_generators.py`

**Interfaces:**
- Produces: `figures/approach.py` exposing module-level `svg_fragment() -> str` returning the `<svg …>…</svg>` string (viewBox `0 0 1040 482`); `figures/approach_mobile.py` exposing `svg_fragment() -> str` (viewBox `0 0 336 329`); `figures/area_graph.py` exposing `svg_fragment() -> str` and `AREAS: list[tuple[str, str, str]]` of `(num, title, href)`.

- [ ] **Step 1: Copy the generators to their production home**

```bash
cd /Users/shabnam/projects/website
mkdir -p figures
M=.claude/worktrees/homepage-research-viz/docs/superpowers/mockups/homepage-research-viz
cp $M/gen_v22.py               figures/approach.py
cp $M/gen_v22_mobile.py        figures/approach_mobile.py
cp $M/gen_area_graph.py        figures/area_graph_data.py
cp $M/gen_area_graph_mytext.py figures/area_graph.py
```

- [ ] **Step 2: Write the failing test**

`figures/test_generators.py`:

```python
"""Plain-assert tests. Run: python3 figures/test_generators.py"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import approach, approach_mobile, area_graph

def test_approach_viewbox():
    s = approach.svg_fragment()
    assert s.startswith("<svg"), s[:40]
    assert 'viewBox="0 0 1040 482"' in s

def test_mobile_viewbox():
    s = approach_mobile.svg_fragment()
    assert 'viewBox="0 0 336 329"' in s

def test_area_graph_viewbox():
    s = area_graph.svg_fragment()
    assert s.startswith("<svg"), s[:40]

def test_no_generator_writes_html_on_import():
    # importing must not have written any mockup file into figures/
    stray = [f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
             if f.endswith(".html")]
    assert stray == [], stray

if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e))
    print(("%d failure(s)" % fails) if fails else "all passed")
    sys.exit(1 if fails else 0)
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `python3 figures/test_generators.py`
Expected: FAIL — the modules write mockup HTML on import and expose no `svg_fragment`.

- [ ] **Step 4: Refactor each generator to expose `svg_fragment()`**

In each of the four files: wrap the body that composes the SVG string in a function, remove the module-level `with open(OUT, "w")` write, and guard any remaining CLI behavior. Pattern to apply in `figures/approach.py`:

```python
def svg_fragment():
    """Return the approach figure as a standalone <svg> fragment."""
    return SVG            # the existing composed <svg …>…</svg> string

if __name__ == "__main__":
    print(svg_fragment())
```

In `figures/approach_mobile.py`, replace the `exec` of `gen_v22.py`'s source with a plain import, and keep only variant A:

```python
import approach as g       # was: exec(compile(_src[:_cut], SRC, "exec"), _ns)
```

In `figures/area_graph.py`, replace `import gen_area_graph as base` with `import area_graph_data as base`, drop every plate except D-plain, and drop the `lift_v22_symbol()` composite (the composite existed only for the mockup — in production the two SVGs are separate blocks in `index.html`).

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 figures/test_generators.py`
Expected: `all passed`

- [ ] **Step 6: Prove the drawing is byte-identical to the approved mockups**

```bash
cd /Users/shabnam/projects/website
M=.claude/worktrees/homepage-research-viz/docs/superpowers/mockups/homepage-research-viz
python3 - <<'EOF'
import re, sys, os
sys.path.insert(0, "figures")
import approach
new = approach.svg_fragment()
old = open(".claude/worktrees/homepage-research-viz/docs/superpowers/mockups/"
           "homepage-research-viz/research-viz-lofi-v22.html").read()
m = re.search(r'<svg viewBox="0 0 1040 482".*?</svg>', old, re.S)
a = re.sub(r'\s+', ' ', m.group(0)).strip()
b = re.sub(r'\s+', ' ', new).strip()
print("IDENTICAL" if a == b else "DIFFERS")
if a != b:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print("first diff at", i); print("old:", a[i-60:i+60]); print("new:", b[i-60:i+60]); break
EOF
```

Expected: `IDENTICAL`. If it differs, fix the refactor — the drawing must not change in this task.

- [ ] **Step 7: Write `figures/README.md`**

```markdown
# figures/

Generators for the homepage research visual. **These are the source of truth —
never hand-edit the injected SVG in index.html.**

- `approach.py`         desktop approach figure (1040x482)
- `approach_mobile.py`  narrow-screen variant (336x329), imports approach.py
- `area_graph_data.py`  graph.json loading, cluster pair weights, layout solver
- `area_graph.py`       eight-area graph; scrapes index.html for area titles
- `build.py`            regenerates all three and injects them into index.html

Regenerate after changing any generator, or after `graph/graph.json` or the
research-area text in index.html changes:

    python3 figures/build.py

Tests: `python3 figures/test_generators.py`

Design doc: docs/superpowers/specs/2026-08-06-homepage-research-visual-design.md
Mockup history: docs/superpowers/mockups/homepage-research-viz/
```

- [ ] **Step 8: Commit**

```bash
cd /Users/shabnam/projects/website
git add figures/
git commit -m "figures: move research-visual generators into production home

Each generator now exposes svg_fragment() and writes nothing on import.
Verified the desktop figure is byte-identical to the approved v22 mockup."
```

---

### Task 2: Area graph emits links to projects.html

**Files:**
- Modify: `figures/area_graph.py`
- Test: `figures/test_generators.py`

**Interfaces:**
- Consumes: `area_graph.svg_fragment()` from Task 1.
- Produces: for each of the eight areas the SVG emits, in this exact order and as **immediate siblings**, a group `<g role="button" aria-expanded="false">` (disc, title wrapped in `<a href="projects.html#section-…">`, and the expand marker) followed by `<g class="ag-card">` holding that area's description. Tasks 5 and 6 depend on both the class name `ag-card` and on it being the group's next sibling — the CSS selector is `[aria-expanded="true"] + .ag-card`. Titles carry `class="ag-title"`.

- [ ] **Step 1: Read the real projects.html section ids**

Run: `grep -o 'id="section-[a-z]*"' projects.html`
Expected, in order: `section-motivation`, `section-intervention`, `section-creativity`, `section-genai`, `section-preference`, `section-agentstate`, `section-consumer`, `section-social` (confirm the exact eight before hardcoding — do not guess).

- [ ] **Step 2: Write the failing test**

Append to `figures/test_generators.py`:

```python
def test_every_node_links_to_projects():
    s = area_graph.svg_fragment()
    hrefs = re.findall(r'href="(projects\.html#section-[a-z]+)"', s)
    assert len(hrefs) == 8, hrefs
    assert len(set(hrefs)) == 8, "duplicate hrefs: %r" % hrefs

def test_nodes_are_expandable_buttons():
    s = area_graph.svg_fragment()
    assert s.count('aria-expanded="false"') == 8, s.count('aria-expanded="false"')
    assert s.count('role="button"') == 8

def test_each_button_is_followed_by_its_card():
    # Tasks 5 and 6 depend on this adjacency: the CSS selector that reveals a
    # description is [aria-expanded="true"] + .ag-card, so the card must be the
    # button group's IMMEDIATE next sibling.
    s = area_graph.svg_fragment()
    assert s.count('class="ag-card"') == 8, s.count('class="ag-card"')
    pairs = re.findall(r'</g>\s*<g class="ag-card"', s)
    assert len(pairs) == 8, "cards are not immediate siblings of their buttons: %d" % len(pairs)
```

- [ ] **Step 3: Run to verify it fails**

Run: `python3 figures/test_generators.py`
Expected: FAIL on `test_every_node_links_to_projects` — no hrefs emitted yet.

- [ ] **Step 4: Add the mapping, emit the links, and fix the card adjacency**

Emit each area as a button group immediately followed by its card, so the CSS sibling selector in Task 5 works:

```python
node_svg += (
    '<g role="button" aria-expanded="false" aria-controls="ag-card-%d">%s</g>'
    '<g class="ag-card" id="ag-card-%d">%s</g>'
) % (cid, head_svg, cid, card_svg)
```

Then, next to the existing area table:

```python
# cluster id -> projects.html section anchor (verified against projects.html)
SECTION_ANCHOR = {
    0: "section-motivation", 3: "section-intervention", 1: "section-creativity",
    2: "section-genai",      4: "section-preference",   7: "section-agentstate",
    6: "section-consumer",   5: "section-social",
}
```

Wrap each node's disc+title in an anchor, and keep the expand affordance on the group:

```python
node_svg += (
    '<a href="projects.html#%s">'
    '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>'
    '<text x="%.1f" y="%.1f" class="ag-title">%s</text>'
    '</a>' % (SECTION_ANCHOR[cid], cx, cy, r, col, tx, ty, title)
)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3 figures/test_generators.py`
Expected: `all passed`

- [ ] **Step 6: Commit**

```bash
git add figures/
git commit -m "figures: link each area node to its projects.html section"
```

---

### Task 3: Build script injects the SVGs into index.html

**Files:**
- Create: `figures/build.py`
- Modify: `index.html` (add the three marker blocks — markup comes in Task 4; here just the markers so injection has a target)
- Test: `figures/test_build.py`

**Interfaces:**
- Consumes: `svg_fragment()` from all three generators.
- Produces: `figures/build.py` with `inject(html: str, marker: str, svg: str) -> str` and a `main()`. Markers are HTML comments: `<!-- FIGURE:approach -->` … `<!-- /FIGURE:approach -->`, likewise `FIGURE:approach-mobile` and `FIGURE:area-graph`.

- [ ] **Step 1: Write the failing test**

`figures/test_build.py`:

```python
"""Run: python3 figures/test_build.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

def test_inject_replaces_between_markers():
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    out = build.inject(src, "x", "NEW")
    assert out == "a<!-- FIGURE:x -->NEW<!-- /FIGURE:x -->b", out

def test_inject_is_idempotent():
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    once = build.inject(src, "x", "NEW")
    assert build.inject(once, "x", "NEW") == once

def test_inject_raises_on_missing_marker():
    try:
        build.inject("no markers here", "x", "NEW")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a missing marker")

if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e))
    print(("%d failure(s)" % fails) if fails else "all passed")
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 figures/test_build.py`
Expected: FAIL — `build` does not exist.

- [ ] **Step 3: Write `figures/build.py`**

```python
#!/usr/bin/env python3
"""Regenerate the research-visual SVGs and inject them into index.html.

Mirrors data/inline-graph.js: find a marked block, replace its body.
Run after changing any generator, graph/graph.json, or the research-area
text in index.html:

    python3 figures/build.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
sys.path.insert(0, HERE)


def inject(html, marker, svg):
    """Replace the body between <!-- FIGURE:marker --> and its closer."""
    open_tag = "<!-- FIGURE:%s -->" % marker
    close_tag = "<!-- /FIGURE:%s -->" % marker
    start = html.find(open_tag)
    if start == -1:
        raise ValueError("missing marker %r in target" % open_tag)
    end = html.find(close_tag, start)
    if end == -1:
        raise ValueError("missing closing marker %r" % close_tag)
    return html[:start + len(open_tag)] + svg + html[end:]


def main():
    import approach, approach_mobile, area_graph
    html = open(INDEX, encoding="utf-8").read()
    for marker, svg in (
        ("approach",        approach.svg_fragment()),
        ("approach-mobile", approach_mobile.svg_fragment()),
        ("area-graph",      area_graph.svg_fragment()),
    ):
        html = inject(html, marker, svg)
        print("injected FIGURE:%s (%d bytes)" % (marker, len(svg)))
    open(INDEX, "w", encoding="utf-8").write(html)
    print("wrote", INDEX)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 figures/test_build.py`
Expected: `all passed`

- [ ] **Step 5: Commit**

```bash
git add figures/
git commit -m "figures: add build.py, marker-based SVG injection into index.html"
```

---

### Task 4: Research section markup

**Files:**
- Modify: `index.html:469-539` (the `#research` section)

**Interfaces:**
- Consumes: the three markers from Task 3.
- Produces: `.research-figure`, `.research-figure-mobile`, `.research-areas` wrappers; the existing `.research-grid` retained unchanged as the small-screen fallback.

- [ ] **Step 1: Read the current section**

Run: `sed -n '469,540p' index.html`
Confirm the section opens `<section id="research">`, contains `<p class="section-label …>` and the eight `.research-item` divs, and note the exact closing structure before editing.

- [ ] **Step 2: Insert the figure blocks above the existing grid**

Immediately after the section's `section-label` paragraph and before `<div class="research-grid">`, insert:

```html
  <!-- The section title is written by Shabnam via site-content.md; the
       approach figure reserves 34px of headroom for it. Do not add a
       placeholder heading here. -->

  <div class="research-figure"><!-- FIGURE:approach --><!-- /FIGURE:approach --></div>
  <div class="research-areas"><!-- FIGURE:area-graph --><!-- /FIGURE:area-graph --></div>
  <div class="research-figure-mobile"><!-- FIGURE:approach-mobile --><!-- /FIGURE:approach-mobile --></div>
```

Leave `<div class="research-grid">` and all eight `.research-item` divs exactly as they are — they are the small-screen fallback and the source of truth the area graph scrapes.

- [ ] **Step 3: Run the build to populate the markers**

Run: `python3 figures/build.py`
Expected: three `injected FIGURE:…` lines and `wrote …/index.html`.

- [ ] **Step 4: Verify all three SVGs landed and the grid survived**

```bash
python3 - <<'EOF'
src = open("index.html", encoding="utf-8").read()
for m in ("approach", "approach-mobile", "area-graph"):
    o, c = "<!-- FIGURE:%s -->" % m, "<!-- /FIGURE:%s -->" % m
    body = src[src.index(o)+len(o):src.index(c)]
    print(m, len(body), "bytes", "OK" if body.lstrip().startswith("<svg") else "EMPTY/BAD")
print("research-item count:", src.count('class="research-item'))
EOF
```

Expected: three non-empty blocks each starting with `<svg`, and `research-item count: 8`.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "research: add figure and area-graph blocks to the research section

The eight-item grid stays in place as the small-screen fallback and as
the text the area graph is generated from."
```

---

### Task 5: Responsive CSS

**Files:**
- Modify: `index.html` (the `<style>` block, next to the existing `.research-grid` rules around line 245)

- [ ] **Step 1: Add the layout and breakpoint rules**

Insert after the existing `.research-tag` rule:

```css
/* --- research visual (see figures/README.md) ------------------------- */
.research-figure, .research-figure-mobile, .research-areas { margin: 0 auto; }
.research-figure   { max-width: 1040px; }
.research-areas    { max-width: 1040px; margin-top: 1.5rem; }
.research-figure svg, .research-areas svg, .research-figure-mobile svg {
  display: block; width: 100%; height: auto;
}
/* the mobile figure is drawn for 336px; never let it stretch past that much */
.research-figure-mobile { max-width: 420px; }

/* Desktop: figures only. Below 1000px: mobile figure + the original grid. */
.research-figure-mobile { display: none; }
@media (max-width: 999px) {
  .research-figure, .research-areas { display: none; }
  .research-figure-mobile { display: block; }
}
@media (min-width: 1000px) {
  .research-grid { display: none; }
}

/* area-graph node styling; the SVG carries no presentation of its own */
.research-areas a { text-decoration: none; }
.research-areas .ag-title { font-family: var(--mono); fill: var(--ink); }
.research-areas [role="button"] { cursor: none; }
.research-areas .ag-card { display: none; }
.research-areas [aria-expanded="true"] + .ag-card { display: block; }
```

- [ ] **Step 2: Verify at desktop width in the browser**

Use Playwright: navigate to the local file, set viewport 1280×900, screenshot the research section.
Expected: approach figure visible, area graph below it, no eight-box grid, no mobile figure.

- [ ] **Step 3: Verify at phone width**

Set viewport 375×800, screenshot the same section.
Expected: mobile figure visible at ≤420px wide, the eight-item grid below it, no desktop figure, no area graph, and **no horizontal page scroll**.

- [ ] **Step 4: Verify the crossover**

Set viewport 999×800 then 1000×800.
Expected: exactly one figure treatment visible at each; nothing doubled, nothing blank.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "research: responsive rules for the research visual

>=1000px shows the approach figure and area graph; below that the mobile
figure and the original eight-item grid."
```

---

### Task 6: Area graph click-to-open

**Files:**
- Modify: `index.html` (new `<script>` block at the bottom, beside the existing page scripts)

**Interfaces:**
- Consumes: the area-graph SVG's `[role="button"][aria-expanded]` groups and their sibling `.ag-card` elements from Task 2.

- [ ] **Step 1: Add the toggle script**

Append inside the existing bottom `<script>` block:

```javascript
/* Research area graph: click a node to reveal its description.
   Cards are pre-positioned by figures/area_graph.py and their footprints
   are already reserved, so opening one never reflows the layout. */
(function () {
  var nodes = document.querySelectorAll('.research-areas [role="button"]');
  if (!nodes.length) return;
  function closeAll(except) {
    nodes.forEach(function (n) {
      if (n !== except) n.setAttribute('aria-expanded', 'false');
    });
  }
  nodes.forEach(function (node) {
    function toggle(e) {
      e.preventDefault();
      var open = node.getAttribute('aria-expanded') === 'true';
      closeAll(node);
      node.setAttribute('aria-expanded', open ? 'false' : 'true');
    }
    node.addEventListener('click', toggle);
    node.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') toggle(e);
    });
    node.setAttribute('tabindex', '0');
  });
})();
```

- [ ] **Step 2: Verify opening works and nothing moves**

With Playwright at 1280×900: record each node's bounding box, click one node, re-record all boxes.
Expected: the clicked node's card becomes visible; every node's bounding box is unchanged (zero reflow); clicking a second node closes the first.

- [ ] **Step 3: Verify the link still works**

Click an area *title* (the anchor) rather than the expand affordance.
Expected: navigates to `projects.html#section-…` and that section is present on the page.

If the anchor and the toggle conflict (the toggle's `preventDefault` swallowing navigation), scope the toggle listener to the affordance marker only, not the whole group, and re-run both checks.

- [ ] **Step 4: Verify keyboard access**

Tab to a node, press Enter.
Expected: the card opens and `aria-expanded` flips to `true`.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "research: click-to-open descriptions on the area graph"
```

---

### Task 7: Guard against drift between index.html and the generated SVG

**Files:**
- Create: `figures/test_sync.py`

**Interfaces:**
- Consumes: `svg_fragment()` from all three generators; the injected blocks in `index.html`.

- [ ] **Step 1: Write the failing test**

`figures/test_sync.py`:

```python
"""Fails if index.html's injected SVG is stale, or if any figure text is
not verbatim from the research grid. Run: python3 figures/test_sync.py"""
import os, re, sys, html as _html
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import approach, approach_mobile, area_graph

SRC = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

def block(marker):
    o, c = "<!-- FIGURE:%s -->" % marker, "<!-- /FIGURE:%s -->" % marker
    return SRC[SRC.index(o) + len(o):SRC.index(c)]

def test_injected_matches_generators():
    for marker, mod in (("approach", approach),
                        ("approach-mobile", approach_mobile),
                        ("area-graph", area_graph)):
        assert block(marker) == mod.svg_fragment(), (
            "%s is stale in index.html — run python3 figures/build.py" % marker)

def test_area_titles_are_verbatim():
    grid = SRC[SRC.index('<div class="research-grid">'):]
    grid = grid[:grid.index("</section>")]
    titles = [_html.unescape(t) for t in re.findall(r"<h3>(.*?)</h3>", grid, re.S)]
    assert len(titles) == 8, len(titles)
    drawn = block("area-graph")
    for t in titles:
        flat = re.sub(r"\s+", " ", t).strip()
        assert _html.escape(flat, quote=False) in drawn or flat in drawn, flat

def test_no_placeholder_title_in_figures():
    for marker in ("approach", "approach-mobile", "area-graph"):
        b = block(marker).lower()
        for bad in ("lorem", "tbd", "placeholder", "untitled"):
            assert bad not in b, (marker, bad)

if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e))
    print(("%d failure(s)" % fails) if fails else "all passed")
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it — it should pass against the current tree**

Run: `python3 figures/test_sync.py`
Expected: `all passed`.

- [ ] **Step 3: Prove the staleness check actually catches staleness**

```bash
python3 - <<'EOF'
src = open("index.html", encoding="utf-8").read()
o = "<!-- FIGURE:approach -->"
open("index.html", "w", encoding="utf-8").write(src.replace(o, o + "<!--x-->", 1))
EOF
python3 figures/test_sync.py; echo "exit=$?"
python3 figures/build.py
python3 figures/test_sync.py; echo "exit=$?"
```

Expected: first run FAILs with the "stale" message and `exit=1`; after `build.py`, `all passed` and `exit=0`.

- [ ] **Step 4: Commit**

```bash
git add figures/
git commit -m "figures: test that index.html's injected SVG is not stale"
```

---

### Task 8: Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add a section to CLAUDE.md**

Insert after the "Content locations in index.html" table:

```markdown
## Research visual (index.html)
Two generated SVGs replace the old flat research grid at ≥1000px:
- **Approach figure** — the state-estimation figure (how the research program
  approaches problems). Generated by `figures/approach.py`.
- **Area graph** — eight research areas, edges weighted by shared concepts from
  `graph/graph.json`, titles only at rest, descriptions opening radially
  outward on click, each node linking to its projects.html section.
  Generated by `figures/area_graph.py`, which scrapes the area titles out of
  index.html's `.research-grid`.

Below 1000px both are hidden; a reduced approach figure
(`figures/approach_mobile.py`) plus the original eight-item `.research-grid`
are shown instead. The grid stays in the markup — it is both the small-screen
fallback and the text the area graph is generated from.

**Never hand-edit the SVG inside index.html.** Edit the generator, then:

    python3 figures/build.py

Tests: `python3 figures/test_generators.py`, `figures/test_build.py`,
`figures/test_sync.py`. Design doc:
`docs/superpowers/specs/2026-08-06-homepage-research-visual-design.md`.
Every word in both figures is Shabnam's, verbatim — never reword a label to
make it fit; drop it instead.
```

- [ ] **Step 2: Update the Known TODOs list**

In CLAUDE.md's "Known TODOs", strike the homepage-research-visual item if present and note the remaining open decisions: static vs animated, and the section title (Shabnam is writing it via `site-content.md`).

- [ ] **Step 3: Run every test once more**

```bash
python3 figures/test_generators.py && python3 figures/test_build.py && python3 figures/test_sync.py
```

Expected: `all passed` three times.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document the research visual pipeline in CLAUDE.md"
```

---

## Deferred (not in this plan)

- **Static vs animated.** Shipping static. index.html's hero already runs a canvas animation; a second animated element is a separate decision.
- **The section title.** Shabnam writes it via `site-content.md`; the markup carries a comment, not a placeholder heading.
- **Connective copy between the two figures.** One line, hers, added when she writes the title.
- **Tablet polish between 420px and 1000px**, where the mobile figure sits centered with whitespace either side. Acceptable for launch.
