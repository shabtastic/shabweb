#!/usr/bin/env python3
"""
area_graph_data.py — graph.json loading, cross-cluster pair weights, the
circular-ordering solver and the contrast/color policy behind the area-level
graph, plus the two brainstorming treatments (A, B) that were compared to
choose it. `area_graph.py` imports this module as `base` for the shared
graph data, solver and color policy; treatment A is what shipped (Shabnam's
choice), rendered there with her own text instead of graph.json's.

Originally gen_area_graph.py, showing the RELATIONSHIP between the eight
research areas on the homepage, instead of the flat 2-column .research-grid
(which reads as eight independent boxes).

Everything below is computed from graph/graph.json. Nothing is hand-transcribed:
node labels, cluster names, cross-cluster edge counts, bridge selection and every
coordinate are derived here and baked into static SVG. There is no force
simulation at load time and no animation loop — the layouts are solved once,
here, and written out as literal path/circle/text coordinates.

Treatments
  A  area-level graph          8 area nodes, edges = shared-concept count, thresholded
  B  bridge-concept graph      the 8 areas + the strongest bridging concepts, each
                               placed between the areas it actually connects

A third treatment — an emergent-neighbourhood concept cloud, ~70 nodes laid out so
the areas showed up as neighbourhoods — was built and cut on Shabnam's instruction:
"i don't wnt c -- i don't want to recapitulate the graph in full detail, but
static". The homepage must not look like a miniature of graph.html. The full
concept graph already exists at full detail one click away; this element has to
say something the flat grid cannot and then get out of the way. That rule is why
B is thresholded as hard as it is — see B_MIN_XDEG.

Composite (below the two): the approved approach figure lifted VERBATIM out of
research-viz-lofi-v22.html into a <symbol> and <use>d once, a reserved EMPTY title
block, and the recommended treatment beneath it.

Copy policy: zero assistant-authored prose. Every string in the output comes from
graph.json node labels (lowercased per the site convention), meta.clusters names,
or CLAUDE.md's cluster table. The title block is empty on purpose.
"""

import json, math, os, random, collections, html

HERE = os.path.dirname(os.path.abspath(__file__))
# figures/ sits at the repo root, so the repo containing THIS file is the one
# whose graph.json gets read by default -- important when this file is run
# from a worktree/checkout other than the primary one (see WEBSITE_GRAPH).
ROOT = os.path.dirname(HERE)
GRAPH_PATH = os.environ.get(
    "WEBSITE_GRAPH", os.path.join(ROOT, "graph", "graph.json")
)
V22_PATH = os.path.join(HERE, "research-viz-lofi-v22.html")
OUT_PATH = os.path.join(HERE, "area-graph-options.html")

# ---------------------------------------------------------------- site tokens
PAPER = "#f5f2ec"
INK = "#111118"
INK_BLUE = "#1a2c6b"
INK_DIM = "rgba(17,17,24,0.55)"
GRID_MIN = "rgba(80,140,200,0.20)"
GRID_MAJ = "rgba(80,140,200,0.42)"

# CLAUDE.md cluster colors, by cluster id.
CLUSTER_HL = {
    0: "#7777FF",  # slate blue
    1: "#C977FF",  # heliotrope
    2: "#FF77E4",  # violet web
    3: "#FF7792",  # ultra red
    4: "#FFFF77",  # laser lemon
    5: "#FFAE77",  # mac & cheese
    6: "#77FFE4",  # mint
    7: "#AAFF77",  # lime green
}
# CLAUDE.md: cluster 4's yellow is displayed as #9a7c00 for legibility on paper.
CLUSTER_DISPLAY_OVERRIDE = {4: "#9a7c00"}


# ------------------------------------------------------------ color utilities
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex(t):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in t)


def rel_lum(rgb):
    def f(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def darken_to_contrast(hexcolor, target=4.5, bg=PAPER):
    """Scale a highlighter color toward black until it is readable on paper.

    This is the rule the site already applies by hand when it turns #FFFF77 into
    #9a7c00 — mechanized so all eight clusters get the same treatment.
    """
    bgc = hex_rgb(bg)
    base = hex_rgb(hexcolor)
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if contrast(tuple(c * mid for c in base), bgc) >= target:
            lo = mid
        else:
            hi = mid
    return rgb_hex(tuple(c * lo for c in base))


def rgba(hexcolor, a):
    r, g, b = hex_rgb(hexcolor)
    return "rgba(%d,%d,%d,%.3f)" % (r, g, b, a)


CLUSTER_INK = {}  # readable text/stroke color per cluster
for cid, hx in CLUSTER_HL.items():
    CLUSTER_INK[cid] = CLUSTER_DISPLAY_OVERRIDE.get(cid, darken_to_contrast(hx))
CLUSTER_FILL = dict(CLUSTER_HL)
CLUSTER_FILL[4] = "#9a7c00"  # the pale lemon is invisible as an area fill


def esc(s):
    return html.escape(s, quote=True)


# ------------------------------------------------------------------ load data
G = json.load(open(GRAPH_PATH))
NODES = {n["id"]: n for n in G["nodes"]}
EDGES = G["edges"]
CLUSTERS = {c["id"]: c["name"] for c in G["meta"]["clusters"]}
CIDS = sorted(CLUSTERS)

# cross-cluster degree per concept, and which foreign areas each one reaches
xdeg = collections.Counter()
foreign = collections.defaultdict(collections.Counter)
pair_w = collections.Counter()  # (cluster_a, cluster_b) -> shared-concept edges
for e in EDGES:
    a, b = NODES[e["a"]], NODES[e["b"]]
    if a["cluster"] != b["cluster"]:
        xdeg[a["id"]] += 1
        xdeg[b["id"]] += 1
        foreign[a["id"]][b["cluster"]] += 1
        foreign[b["id"]][a["cluster"]] += 1
        pair_w[tuple(sorted((a["cluster"], b["cluster"])))] += 1

CLUSTER_SIZE = collections.Counter(n["cluster"] for n in G["nodes"])


def label_lines(nid):
    """graph.json labels carry their own line breaks; site convention is lowercase."""
    return [ln.strip().lower() for ln in NODES[nid]["label"].split("\n") if ln.strip()]


def wrap(text, width):
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


# ------------------------------------------- shared: best circular area order
def best_circle_order(weights, ids):
    """Order the eight areas around a circle so heavily-shared pairs sit close.

    Exhaustive over all 7!=5040 rotations-fixed permutations; deterministic.
    Objective: minimise sum(w * angular separation).
    """
    n = len(ids)
    rest = ids[1:]
    best, best_cost = None, float("inf")
    import itertools

    for perm in itertools.permutations(rest):
        order = [ids[0]] + list(perm)
        pos = {c: i for i, c in enumerate(order)}
        cost = 0.0
        for (a, b), w in weights.items():
            d = abs(pos[a] - pos[b])
            d = min(d, n - d)
            cost += w * d
        if cost < best_cost - 1e-9:
            best_cost, best = cost, order
    return best


ORDER = best_circle_order(pair_w, CIDS)

# ------------------------------------------------------------------ SVG parts
def grid_defs(prefix):
    return (
        f'<pattern id="{prefix}min" width="16" height="16" patternUnits="userSpaceOnUse">'
        f'<path d="M16 0H0V16" fill="none" stroke="{GRID_MIN}" stroke-width="1"/></pattern>'
        f'<pattern id="{prefix}maj" width="80" height="80" patternUnits="userSpaceOnUse">'
        f'<path d="M80 0H0V80" fill="none" stroke="{GRID_MAJ}" stroke-width="1"/></pattern>'
    )


def grid_rects(prefix, w, h):
    return (
        f'<rect width="{w}" height="{h}" fill="{PAPER}"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{prefix}min)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{prefix}maj)"/>'
    )


def text_block(x, y, lines, size, color, anchor="middle", lh=None, weight="400",
               opacity=1.0, ls=0.0):
    lh = lh or size * 1.18
    out = []
    for i, ln in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{y + i*lh:.1f}" text-anchor="{anchor}" '
            f'font-family="\'Space Mono\', monospace" font-size="{size}" '
            f'font-weight="{weight}" letter-spacing="{ls}" fill="{color}" '
            f'opacity="{opacity:.2f}">{esc(ln)}</text>'
        )
    return "".join(out)


# ================================================================ TREATMENT A
# Eight area nodes on an optimised circle. Edge = number of concept-to-concept
# edges that cross that pair of areas. Weak pairs are dropped so the picture
# stays sparse: 25 of the 28 possible pairs are non-empty, which as a complete
# graph is a hairball; MIN_PAIR keeps only the load-bearing ones. It is set at
# the value that still leaves every one of the eight areas attached — an isolated
# area node would be the flat-grid problem wearing a new costume.
A_W, A_H = 1040, 610
A_MIN_PAIR = 6


def a_radius(cid):
    return 13 + 20 * math.sqrt(CLUSTER_SIZE[cid] / max(CLUSTER_SIZE.values()))


def treatment_a():
    cx, cy, R = 520, 315, 176
    pos = {}
    for i, cid in enumerate(ORDER):
        ang = -math.pi / 2 + 2 * math.pi * i / len(ORDER)
        pos[cid] = (cx + R * math.cos(ang), cy + R * math.sin(ang), ang)

    kept = {p: w for p, w in pair_w.items() if w >= A_MIN_PAIR}
    assert set(c for p in kept for c in p) == set(CIDS), "an area fell off the graph"
    wmax = max(kept.values())

    s = [f"<defs>{grid_defs('ga')}</defs>", grid_rects("ga", A_W, A_H)]

    # edges, weakest first so the strongest read on top; trimmed to the node rims
    for (a, b), w in sorted(kept.items(), key=lambda kv: kv[1]):
        x1, y1, _ = pos[a]
        x2, y2, _ = pos[b]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        qx, qy = mx + (cx - mx) * 0.16, my + (cy - my) * 0.16
        d1 = math.hypot(qx - x1, qy - y1) or 1
        d2 = math.hypot(qx - x2, qy - y2) or 1
        x1, y1 = x1 + (qx - x1) / d1 * a_radius(a), y1 + (qy - y1) / d1 * a_radius(a)
        x2, y2 = x2 + (qx - x2) / d2 * a_radius(b), y2 + (qy - y2) / d2 * a_radius(b)
        t = w / wmax
        sw = 1.1 + 7.4 * t
        op = 0.16 + 0.46 * t
        s.append(
            f'<path d="M{x1:.1f} {y1:.1f} Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{INK_BLUE}" stroke-opacity="{op:.2f}" '
            f'stroke-width="{sw:.2f}" stroke-linecap="round"/>'
        )

    for cid in ORDER:
        x, y, ang = pos[cid]
        r = a_radius(cid)
        s.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{rgba(CLUSTER_FILL[cid], 0.62)}" stroke="{CLUSTER_INK[cid]}" '
            f'stroke-width="1.8"/>'
        )
        # label outward
        ux, uy = math.cos(ang), math.sin(ang)
        lx, ly = x + ux * (r + 16), y + uy * (r + 16)
        if ux > 0.35:
            anchor = "start"
        elif ux < -0.35:
            anchor = "end"
        else:
            anchor = "middle"
        lines = wrap(CLUSTERS[cid], 22)
        ly += 11 if uy > 0.35 else (-11 * len(lines) if uy < -0.35 else -5 * (len(lines) - 1))
        s.append(text_block(lx, ly, lines, 12.5, CLUSTER_INK[cid], anchor=anchor, lh=15))
    return f'<svg viewBox="0 0 {A_W} {A_H}" width="100%">' + "".join(s) + "</svg>"


# ================================================================ TREATMENT B
# The eight areas plus the concepts that actually do the connecting. A concept
# qualifies as a bridge by cross-cluster degree — how many of its edges land in
# a different area. B_MIN_XDEG curates that list down to the strongest.
#
# The threshold is the whole design. At >=5 this is 19 concepts and starts to
# look like graph.html shrunk down, which is the one thing it must not be. At >=7
# it is 8 concepts — roughly one per area — every one of the eight areas is still
# touched, and each label is a claim a reader can actually hold. Raise the number
# if it ever feels dense again; do not lower it.
B_W, B_H = 1040, 720
B_MIN_XDEG = 7


def treatment_b():
    cx, cy, R = 520, 360, 252
    apos = {}
    for i, cid in enumerate(ORDER):
        ang = -math.pi / 2 + 2 * math.pi * i / len(ORDER)
        apos[cid] = (cx + R * math.cos(ang), cy + R * math.sin(ang), ang)

    bridges = [nid for nid, c in xdeg.items() if c >= B_MIN_XDEG]
    bridges.sort(key=lambda n: (-xdeg[n], n))
    touched = set()
    for nid in bridges:
        touched.add(NODES[nid]["cluster"])
        touched.update(foreign[nid])
    assert touched == set(CIDS), f"areas with no bridge: {set(CIDS) - touched}"

    # weighted centroid: own cluster pulls with OWN_W of the total foreign mass
    OWN_W = 0.85
    bp = {}
    for nid in bridges:
        own = NODES[nid]["cluster"]
        tot = sum(foreign[nid].values())
        ws = dict(foreign[nid])
        ws[own] = ws.get(own, 0) + OWN_W * tot
        sw = sum(ws.values())
        x = sum(apos[c][0] * w for c, w in ws.items()) / sw
        y = sum(apos[c][1] * w for c, w in ws.items()) / sw
        bp[nid] = [x, y]

    # label boxes, then relax overlaps (baked here, not at load)
    boxes = {}
    for nid in bridges:
        lines = label_lines(nid)
        w = max(len(l) for l in lines) * 6.95 + 16
        h = 14.5 * len(lines) + 18
        boxes[nid] = (w, h)

    rnd = random.Random(11)
    for nid in bridges:  # break exact ties deterministically
        bp[nid][0] += rnd.uniform(-2, 2)
        bp[nid][1] += rnd.uniform(-2, 2)
    def b_radius(cid):
        return 11 + 15 * math.sqrt(CLUSTER_SIZE[cid] / max(CLUSTER_SIZE.values()))

    for _ in range(600):
        for nid in bridges:  # never let a concept box sit on an area disc
            for cidt in CIDS:
                ax, ay, _ = apos[cidt]
                bw, bh = boxes[nid]
                clear = b_radius(cidt) + max(bw, bh) * 0.45 + 10
                dx, dy = bp[nid][0] - ax, bp[nid][1] - ay
                d = math.hypot(dx, dy) or 1
                if d < clear:
                    bp[nid][0] = ax + dx / d * clear
                    bp[nid][1] = ay + dy / d * clear
        for i, a in enumerate(bridges):
            for b in bridges[i + 1 :]:
                wa, ha = boxes[a]
                wb, hb = boxes[b]
                dx = bp[b][0] - bp[a][0]
                dy = bp[b][1] - bp[a][1]
                ox = (wa + wb) / 2 + 8 - abs(dx)
                oy = (ha + hb) / 2 + 6 - abs(dy)
                if ox > 0 and oy > 0:
                    if ox / (wa + wb) < oy / (ha + hb):
                        sh = ox / 2 * (1 if dx >= 0 else -1)
                        bp[a][0] -= sh
                        bp[b][0] += sh
                    else:
                        sh = oy / 2 * (1 if dy >= 0 else -1)
                        bp[a][1] -= sh
                        bp[b][1] += sh
        for nid in bridges:  # keep inside the ring of areas
            dx, dy = bp[nid][0] - cx, bp[nid][1] - cy
            d = math.hypot(dx, dy) or 1
            if d > R - 46:
                bp[nid][0] = cx + dx / d * (R - 46)
                bp[nid][1] = cy + dy / d * (R - 46)

    s = [f"<defs>{grid_defs('gb')}</defs>", grid_rects("gb", B_W, B_H)]

    # bridge -> area edges, tinted by the area they reach
    for nid in bridges:
        own = NODES[nid]["cluster"]
        links = dict(foreign[nid])
        links[own] = max(links.get(own, 0), 2)
        for cidt, w in sorted(links.items(), key=lambda kv: kv[1]):
            x2, y2, _ = apos[cidt]
            x1, y1 = bp[nid]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            qx, qy = mx + (cx - mx) * 0.10, my + (cy - my) * 0.10
            sw = 0.8 + 0.62 * w
            op = 0.28 + 0.055 * w
            s.append(
                f'<path d="M{x1:.1f} {y1:.1f} Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="{CLUSTER_INK[cidt]}" stroke-opacity="{min(op,0.72):.2f}" '
                f'stroke-width="{sw:.2f}" stroke-linecap="round"/>'
            )

    smax = max(CLUSTER_SIZE.values())
    for cid in ORDER:
        x, y, ang = apos[cid]
        r = 11 + 15 * math.sqrt(CLUSTER_SIZE[cid] / smax)
        s.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{rgba(CLUSTER_FILL[cid], 0.55)}" stroke="{CLUSTER_INK[cid]}" '
            f'stroke-width="1.8"/>'
        )
        ux, uy = math.cos(ang), math.sin(ang)
        lx, ly = x + ux * (r + 14), y + uy * (r + 14)
        anchor = "start" if ux > 0.35 else ("end" if ux < -0.35 else "middle")
        lines = wrap(CLUSTERS[cid], 20)
        ly += 11 if uy > 0.35 else (-11 * len(lines) if uy < -0.35 else -5 * (len(lines) - 1))
        # area names sit a step above the concept labels in the hierarchy
        s.append(text_block(lx, ly, lines, 12.5, CLUSTER_INK[cid], anchor=anchor, lh=14.5))

    for nid in bridges:
        x, y = bp[nid]
        lines = label_lines(nid)
        bw, bh = boxes[nid]
        s.append(
            f'<rect x="{x-bw/2:.1f}" y="{y-bh/2:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
            f'rx="3" fill="{PAPER}" fill-opacity="0.93" stroke="{rgba(INK,0.16)}" stroke-width="0.8"/>'
        )
        ty = y - (len(lines) - 1) * 7.25 + 4.1
        s.append(text_block(x, ty, lines, 11.5, INK_BLUE, lh=14.5))
    return f'<svg viewBox="0 0 {B_W} {B_H}" width="100%">' + "".join(s) + "</svg>"


# ================================================================= COMPOSITE
def lift_v22_symbol():
    """Lift the approved approach figure out of research-viz-lofi-v22.html verbatim.

    Nothing inside is redrawn or altered — the <svg> element's children are moved
    into a <symbol> untouched, so a single <use> renders exactly the approved
    figure, once. Its own <style> block is carried across too.
    """
    src = open(V22_PATH).read()
    st0 = src.index("<style>")
    st1 = src.index("</style>") + len("</style>")
    style = src[st0:st1]
    i = src.index("<svg ")
    body_start = src.index(">", i) + 1
    body_end = src.rindex("</svg>")
    inner = src[body_start:body_end]
    sym = (
        '<symbol id="approach-figure" viewBox="0 0 1040 482">' + inner + "</symbol>"
    )
    return style, sym


def composite():
    """Approach figure once + a reserved EMPTY title block + the recommendation.

    Per the design spec the figure appears exactly once and is never scoped,
    cropped or highlighted on behalf of an area, so it is <use>d whole. The title
    block is deliberately empty: the section title is Shabnam's to write.
    """
    return f"""
  <div class="composite">
    <div class="title-reserve"></div>
    <svg viewBox="0 0 1040 482" width="100%" style="display:block">
      <use href="#approach-figure" x="0" y="0" width="1040" height="482"/>
    </svg>
    <div class="composite-gap"></div>
    {treatment_b()}
  </div>
"""


# ==================================================================== assemble
def main():
    style_v22, symbol_v22 = lift_v22_symbol()
    parts = [
        "<!doctype html>",
        "<!-- area-graph-options — generated by gen_area_graph.py, do not hand-edit -->",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>area-graph-options</title>",
        # Same font route index.html uses. Everything else in this file is inline;
        # the stacks below fall back cleanly if the fonts do not load.
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700'
        '&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">',
        style_v22,
        f"""<style>
  :root {{
    --paper:{PAPER}; --ink:{INK}; --ink-blue:{INK_BLUE}; --ink-dim:{INK_DIM};
    --ink-faint:rgba(17,17,24,0.15);
    --sans:'DM Sans', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    --mono:'Space Mono', ui-monospace, Menlo, monospace;
  }}
  body {{
    margin:0; background:{PAPER}; color:var(--ink); font-family:var(--mono);
    background-image:
      linear-gradient(to right, {GRID_MAJ} 1px, transparent 1px),
      linear-gradient(to bottom, {GRID_MAJ} 1px, transparent 1px),
      linear-gradient(to right, {GRID_MIN} 1px, transparent 1px),
      linear-gradient(to bottom, {GRID_MIN} 1px, transparent 1px);
    background-size: 80px 80px, 80px 80px, 16px 16px, 16px 16px;
  }}
  .page {{ max-width:1120px; margin:0 auto; padding:56px 40px 96px; }}
  .plate {{ margin:0 0 88px; }}
  .plate-letter {{
    font-family:var(--sans); font-size:1.5rem; font-weight:700;
    color:var(--ink-blue); margin:0 0 14px; letter-spacing:0.04em;
  }}
  .frame {{ border:1px solid var(--ink-faint); background:{PAPER}; }}
  .frame svg {{ display:block; width:100%; height:auto; }}
  hr.sep {{ border:0; border-top:2px solid rgba(26,44,107,0.28); margin:0 0 64px; }}
  .composite {{ border:1px solid var(--ink-faint); background:{PAPER}; padding:0 0 28px; }}
  .title-reserve {{
    height:96px; margin:28px 40px 8px;
    border:1px dashed rgba(26,44,107,0.30); border-radius:2px; background:transparent;
  }}
  .composite-gap {{ height:36px; }}
  .composite svg {{ display:block; width:100%; height:auto; }}
</style>""",
        "</head><body>",
        '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
        + symbol_v22
        + "</defs></svg>",
        '<div class="page">',
        '<div class="plate"><div class="plate-letter">A</div>'
        f'<div class="frame">{treatment_a()}</div></div>',
        '<div class="plate"><div class="plate-letter">B</div>'
        f'<div class="frame">{treatment_b()}</div></div>',
        '<hr class="sep"/>',
        composite(),
        "</div>",
        "</body></html>",
    ]
    open(OUT_PATH, "w").write("\n".join(parts) + "\n")
    print("wrote", OUT_PATH)
    print("circle order:", ORDER)
    print("A pairs kept:", sum(1 for w in pair_w.values() if w >= A_MIN_PAIR), "of", len(pair_w))
    print("B bridges:", sum(1 for c in xdeg.values() if c >= B_MIN_XDEG))


if __name__ == "__main__":
    main()
