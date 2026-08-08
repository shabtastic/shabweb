#!/usr/bin/env python3
"""
gen_integration_options.py — builds integration-options.html

Draws 4 LAYOUT OPTIONS for how the converged research figure (v22, unchanged)
sits inside the homepage research section. This generator does NOT redesign the
figure: it lifts the v22 SVG verbatim into a <symbol> and <use>s it, so every
option shows the identical drawing at whatever scale that option needs.

COPY POLICY (hard): zero assistant-authored words appear in the output.
Every string in the generated page comes from exactly one of:
  - the v22 figure itself (Shabnam's verbatim labels, untouched inside the symbol)
  - index.html's #research section (the section label "Research", the eight
    .research-item h3 / p / .research-tag strings, including her typo
    "psycholgical" in item 02, which is preserved deliberately)
  - CLAUDE.md's cluster colour table
Option labels are bare letters (A, B1, B2, C, D). The section title is a
RESERVED EMPTY BLOCK — she is writing that copy separately, so no draft title
may appear anywhere.

FRAMING (revised 2026-08-07 per Shabnam, verbatim):
  "this is more how i approach the world and the areas are what emerge from it.
   there is some recursion (e.g., neuroscience projects that seem like they're
   only about physio)"
So: the figure is an APPROACH, and the eight areas EMERGE from it. They are not
slices, regions, or capability-subsets of it. The earlier "area = subset of the
paradigm" idea, and the older "area = position in the pipeline" idea, are BOTH
rejected and are not drawn here. Nothing in this file highlights a region of the
figure on behalf of an area.
"""

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "research-viz-lofi-v22.html"
OUT = HERE / "integration-options.html"


# ---------------------------------------------------------------- figure lift
def lift_figure():
    """Pull the v22 <svg> apart into (defs, body, aria-label). Verbatim."""
    src = SRC.read_text(encoding="utf-8")
    i = src.index("<svg ")
    j = src.index(">", i)
    head, inner = src[i:j + 1], src[j + 1:src.rindex("</svg>")]

    aria = re.search(r'aria-label="(.*?)"', head, re.S).group(1)

    # Hoist <defs> out of the symbol so the grid patterns resolve for every
    # <use> instance regardless of where the symbol lives in the document.
    d0 = inner.index("<defs>")
    d1 = inner.index("</defs>") + len("</defs>")
    return inner[d0:d1], inner[:d0] + inner[d1:], aria


DEFS, FIGBODY, FIG_ARIA = lift_figure()


def fig(cls="rv-fig", labelled=True):
    a = f' role="img" aria-label="{FIG_ARIA}"' if labelled else ' aria-hidden="true"'
    return (f'<svg class="{cls}" viewBox="0 0 1040 482"{a}>'
            f'<use href="#rvfig" width="1040" height="482"/></svg>')


# --------------------------------------------------------------- site content
# Verbatim from /Users/shabnam/projects/website/index.html .research-grid,
# in that file's display order. Colours are CLAUDE.md's cluster table; cluster 4
# uses the documented dark-amber display value #9a7c00 for legibility on paper.
AREAS = [
    ("01", "c0", "#7777FF",
     "Motivated Learning, Decision Making, &amp; Self Regulation",
     "How motivation, reward, and self-control shape learning and choice, with an emphasis on flexible, goal-directed decision making in real-world settings.",
     ["Motivation", "Self-regulation", "Decision science", "Neuroimaging"]),
    ("02", "c3", "#FF7792",
     "Intervention Science &amp; Applied Behavior Change",
     "Designing, testing, and personalizing behavior-change interventions ranging from improving understanding of health risks to just-in-time support for psycholgical flexibility and creativity.",
     ["Behavior change", "Intervention science", "Causality"]),
    ("03", "c1", "#C977FF",
     "Creativity &amp; Design",
     "Developing a mechanistic understanding of the <em>process</em> of creative work to promote not only innovation but also sustained creative wellbeing.",
     ["Creative cognition", "Design decision making", "Creativity support tools"]),
    ("04", "c2", "#FF77E4",
     "Psychology-Guided Generative AI",
     "Using psychological and neuroscientific theory to direct the underlying machinery of generative AI systems and better align their outputs with human thoughts and actions.",
     ["Human-AI alignment", "Active inference", "Bayesian surprise"]),
    ("05", "c4", "#9a7c00",
     "Preference Elicitation &amp; Prediction",
     "Novel elicitation methods and models for understanding individual preferences from psychology, physiology, and behavior that account for context and time.",
     ["Decision science", "Complexity", "Machine learning"]),
    ("06", "c7", "#AAFF77",
     "Agent State Inference",
     "Improved inference of humans' internal states and simulation of agent preferences to support human-AI teaming during complex tasks like driving.",
     ["Preference learning", "Agentic simulation", "Human-AI teaming"]),
    ("07", "c6", "#77FFE4",
     "Consumer Psychology &amp; Market Forecasting",
     "Leveraging psychographic and behavioral data, along with neural signals, to improve demand forecasting and product adoption, especially for innovative, new products.",
     ["Econometrics", "Demand forecasting", "Neuroforecasting"]),
    ("08", "c5", "#FFAE77",
     "Social, Cognitive, &amp; Affective Neuroscience",
     "Modeling complex interactions between cognition and affect to understand and predict individual behavior in social contexts.",
     ["Social cognition", "Affective processing", "Individual differences"]),
]


def tags(ts):
    return "".join(f'<span class="research-tag">{t}</span>' for t in ts)


# The reserved title block. Deliberately empty — her copy, not ours.
TITLE_SLOT = ('<!-- reserved: the section title Shabnam is writing. Kept empty '
              'on purpose; the figure already reserves 34px of headroom for it. -->\n'
              '<div class="title-slot" aria-hidden="true"></div>')

SECTION_LABEL = '<p class="section-label s-red"><span class="hl">Research</span></p>'


# ------------------------------------------------------------------ option A
def option_a():
    items = "".join(
        f'''<div class="research-item">
          <span class="research-num">{num}</span>
          <div class="research-content">
            <h3>{title}</h3>
            <p>{body}</p>
            {tags(ts)}
          </div>
        </div>''' for num, _, _, title, body, ts in AREAS)
    return f'''
    <!-- A — figure runs once as the section opener; the existing eight-area
         grid follows below completely unchanged. Neutral on the relationship
         between figure and areas: it asserts nothing, so it cannot assert
         anything wrong. This is the cheap baseline. -->
    {SECTION_LABEL}
    {TITLE_SLOT}
    <div class="fig-block">{fig()}</div>
    <div class="research-grid">{items}</div>'''


# ------------------------------------------------------------------ option B
def _b_row(num, cc, title, body, ts, open_):
    inner = (f'<p>{body}</p>{tags(ts)}' if open_ else "")
    return f'''<li class="darea{' is-open' if open_ else ''}" style="--cc:{cc}">
        <div class="darea-head">
          <span class="research-num">{num}</span>
          <h3>{title}</h3>
          <span class="darea-mark">{'&#8722;' if open_ else '+'}</span>
        </div>
        <div class="darea-body">{inner}</div>
      </li>'''


def option_b(open_index=None):
    rows = "".join(_b_row(n, cc, t, b, ts, open_index == k)
                   for k, (n, _, cc, t, b, ts) in enumerate(AREAS))
    return f'''
    <!-- B — emergence. The figure is the approach; the eight areas hang off a
         single spine that descends out of the bottom of the figure, so they
         read as things that CAME FROM it. Selecting an area opens that area's
         own copy and does NOTHING to the figure — the figure never dims and no
         region of it is ever highlighted, because an area is not a part of the
         approach, it is a product of it. The +/- marks are the affordance
         (same pattern as projects.html's .section-divider buttons).
         B1 = resting.  B2 = one area open. -->
    {SECTION_LABEL}
    {TITLE_SLOT}
    <div class="fig-block">{fig()}</div>
    <div class="derive">
      <svg class="derive-stem" viewBox="0 0 1040 60" preserveAspectRatio="none" aria-hidden="true">
        <path d="M 520 0 C 520 26 300 18 26 38 L 26 60" fill="none"
              stroke="rgba(26,44,107,0.35)" stroke-width="1"/>
      </svg>
      <ol class="derive-list">{rows}</ol>
    </div>'''


# ------------------------------------------------------------------ option C
def option_c(open_index=7):
    cells = []
    for k, (num, _, cc, title, body, ts) in enumerate(AREAS):
        if k == open_index:
            cells.append(f'''<div class="research-item is-open" style="--cc:{cc}">
            <span class="research-num">{num}</span>
            <div class="research-content">
              <h3>{title}</h3>
              <p>{body}</p>
              {tags(ts)}
              <div class="recurse">{fig("rv-fig rv-fig-sm", labelled=False)}</div>
            </div>
            <span class="darea-mark">&#8722;</span>
          </div>''')
        else:
            cells.append(f'''<div class="research-item" style="--cc:{cc}">
            <span class="research-num">{num}</span>
            <div class="research-content"><h3>{title}</h3></div>
            <span class="darea-mark">+</span>
          </div>''')
    return f'''
    <!-- C — recursion by drill-down. Same figure as opener; the areas collapse
         to titles. Opening one does not reveal a different diagram or a
         highlighted slice — it reveals THE SAME FIGURE AGAIN, scoped to that
         area. Her example drove the choice of which card to show open here:
         neuroscience projects that look like they are only about physiology are
         themselves full instances of the approach at a smaller scale.
         Precedent for the drill-down gesture already exists on the site:
         graph.html's cluster -> papers overlay. -->
    {SECTION_LABEL}
    {TITLE_SLOT}
    <div class="fig-block">{fig()}</div>
    <div class="research-grid research-grid-c">{"".join(cells)}</div>'''


# ------------------------------------------------------------------ option D
def option_d():
    cells = "".join(f'''<div class="research-item tile" style="--cc:{cc}">
        <div class="tile-fig">{fig("rv-fig rv-fig-tile", labelled=False)}
          <span class="tile-wash"></span></div>
        <div class="tile-head">
          <span class="research-num">{num}</span>
          <div class="research-content">
            <h3>{title}</h3>
            <p>{body}</p>
            {tags(ts)}
          </div>
        </div>
      </div>''' for num, _, cc, title, body, ts in AREAS)
    return f'''
    <!-- D — self-similar tiling, two scales. The approach runs once at full
         size, then again eight times at small size, once per area. Each tile
         carries the WHOLE figure, not a crop, not a subset, not a highlighted
         region: every area is the same approach instantiated, which is what
         "the areas are what emerge from it" and "there is some recursion" both
         say. The cluster colour appears only as a wash over the tile and as the
         tile's rule, so no area ever owns a mark inside the drawing. -->
    {SECTION_LABEL}
    {TITLE_SLOT}
    <div class="fig-block">{fig()}</div>
    <div class="research-grid research-grid-d">{cells}</div>'''


# ------------------------------------------------------------------- assembly
OPTIONS = [
    ("A", option_a()),
    ("B1", option_b(None)),
    ("B2", option_b(3)),
    ("C", option_c(7)),
    ("D", option_d()),
]

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --paper:#f5f2ec; --paper-2:#edeae1; --ink:#111118; --ink-blue:#1a2c6b;
  --ink-dim:rgba(17,17,24,0.55); --ink-faint:rgba(17,17,24,0.15);
  --blue-g:rgba(80,140,200,0.20); --blue-G:rgba(80,140,200,0.42);
  --mono:'Space Mono', ui-monospace, monospace;
  --sans:'DM Sans', system-ui, sans-serif;
}
html { scroll-behavior:smooth; }
body {
  background: var(--paper); color: var(--ink);
  font-family: var(--mono); font-size:12px; line-height:1.7;
  background-image:
    linear-gradient(var(--blue-G) 1px, transparent 1px),
    linear-gradient(90deg, var(--blue-G) 1px, transparent 1px),
    linear-gradient(var(--blue-g) 1px, transparent 1px),
    linear-gradient(90deg, var(--blue-g) 1px, transparent 1px);
  background-size: 80px 80px, 80px 80px, 16px 16px, 16px 16px;
}
.rv22-svgtext { font-family:'Space Mono', ui-monospace, monospace; }

/* option shell — the letter is the only chrome */
.opt { padding: 5rem 2.5rem 6rem; border-top: 1px solid var(--blue-G); }
.opt:first-of-type { border-top: none; }
.opt-inner { max-width: 1040px; margin: 0 auto; position: relative; }
.opt-letter {
  font-family: var(--sans); font-weight:300; font-size:2.6rem; line-height:1;
  color: var(--ink-blue); opacity:0.5; margin-bottom:1.6rem;
}

/* index.html section-label, verbatim */
.section-label {
  font-size:0.7rem; letter-spacing:0.3em; text-transform:uppercase;
  color: var(--ink-blue); margin-bottom:0.6rem;
  display:flex; align-items:center; gap:1rem;
}
.section-label::before { content:''; display:block; width:28px; height:1px; background:currentColor; }
.section-label > .hl {
  display:inline-block; padding:0 6px; margin-left:-6px;
  background-image: linear-gradient(transparent 30%,
    rgb(var(--hl-rgb,26 44 107) / var(--hl-a,0)) 30%,
    rgb(var(--hl-rgb,26 44 107) / var(--hl-a,0)) 85%, transparent 85%);
}
.section-label.s-red { --hl-rgb:255 119 146; --hl-a:0.55; }

/* the empty, reserved title block */
.title-slot {
  height: 4.2rem; margin: 1.4rem 0 1.8rem;
  border: 1px dashed rgba(26,44,107,0.28); background: rgba(26,44,107,0.02);
}

.fig-block { border:1px solid var(--blue-G); background: var(--paper); }
.rv-fig { display:block; width:100%; height:auto; }

/* index.html research grid, verbatim */
.research-grid { display:grid; grid-template-columns:repeat(2,1fr); }
.research-item { padding:2rem; border:1px solid var(--blue-G); display:flex; gap:1.2rem; }
.research-num { font-size:0.68rem; letter-spacing:0.2em; color:var(--ink-dim); padding-top:0.25em; white-space:nowrap; }
.research-content h3 { font-family:var(--sans); font-size:1.05rem; font-weight:400; color:var(--ink); margin-bottom:0.5rem; }
.research-content p { font-size:0.7rem; color:var(--ink-dim); line-height:1.85; }
.research-content p em { font-style:italic; color:var(--ink); }
.research-tag {
  display:inline-block; font-size:0.68rem; letter-spacing:0.15em; text-transform:uppercase;
  color:var(--ink-blue); border:1px solid rgba(26,44,107,0.2);
  padding:0.15rem 0.45rem; margin-top:0.7rem; margin-right:0.3rem;
}

/* B — derivation spine */
.derive { position:relative; }
.derive-stem { display:block; width:100%; height:60px; }
.derive-list { list-style:none; margin-left:26px; border-left:1px solid rgba(26,44,107,0.35); }
.darea { position:relative; padding:0 0 0 30px; }
.darea::before {
  content:''; position:absolute; left:0; top:1.55rem;
  width:22px; height:2px; background:var(--cc);
}
.darea-head {
  display:flex; align-items:baseline; gap:1.2rem;
  padding:1.05rem 0; border-bottom:1px solid var(--blue-G);
}
.darea-head h3 { flex:1; font-family:var(--sans); font-size:1.05rem; font-weight:400; color:var(--ink); }
.darea-mark { font-size:0.9rem; color:var(--ink-blue); opacity:0.6; padding-left:1rem; }
.darea-body:not(:empty) {
  padding:1.1rem 0 1.6rem; border-bottom:1px solid var(--blue-G);
  border-left:2px solid var(--cc); margin-left:-30px; padding-left:30px;
}
.darea-body p { font-size:0.7rem; color:var(--ink-dim); line-height:1.85; max-width:62ch; }
.darea-body p em { font-style:italic; color:var(--ink); }
.darea.is-open .darea-head { border-bottom-color:transparent; }

/* C — collapsed cards + one recursive expansion */
.research-grid-c .research-item { align-items:flex-start; }
.research-grid-c .research-item .darea-mark { padding-left:0; }
.research-grid-c .research-item .research-content { flex:1; }
.research-grid-c .research-item h3 { margin-bottom:0; }
.research-grid-c .is-open {
  grid-column:1 / -1; border-left:3px solid var(--cc); background:rgba(255,255,255,0.35);
}
.research-grid-c .is-open h3 { margin-bottom:0.5rem; }
.recurse { margin-top:1.5rem; border:1px solid var(--blue-G); max-width:760px; }
.rv-fig-sm { display:block; width:100%; height:auto; }

/* D — same figure, eight more times, one per area */
.research-grid-d .tile { flex-direction:column; gap:0; padding:0; border-left:3px solid var(--cc); }
.tile-fig { position:relative; border-bottom:1px solid var(--blue-G); }
.rv-fig-tile { display:block; width:100%; height:auto; opacity:0.5; }
.tile-wash { position:absolute; inset:0; background:var(--cc); opacity:0.10; pointer-events:none; }
.tile-head { display:flex; gap:1.2rem; padding:1.6rem 2rem 2rem; }

@media (max-width:900px) {
  .opt { padding:3.5rem 1.25rem 4rem; }
  .research-grid { grid-template-columns:1fr; }
  .research-grid-d .tile-head { padding:1.2rem 1.25rem 1.6rem; }
}
"""


def build():
    blocks = "".join(
        f'<section class="opt"><div class="opt-inner">'
        f'<div class="opt-letter">{letter}</div>{body}</div></section>\n'
        for letter, body in OPTIONS)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>integration-options</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300;1,400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

<!-- The v22 figure, lifted verbatim and defined once. Every instance below is a
     <use> of this one symbol, so no option shows a redrawn or edited figure. -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
{DEFS}
<symbol id="rvfig" viewBox="0 0 1040 482">{FIGBODY}</symbol>
</svg>

{blocks}
</body>
</html>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}  ({len(doc):,} bytes)")


if __name__ == "__main__":
    build()
