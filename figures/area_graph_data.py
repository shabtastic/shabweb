#!/usr/bin/env python3
"""
area_graph_data.py — graph.json loading, cross-cluster pair weights, the
circular-ordering solver and the contrast/color policy behind the area-level
graph. `area_graph.py` imports this module as `base` for the shared graph
data, solver and color policy, and renders it as treatment A (Shabnam's
choice out of the brainstorming: see area_graph.py's own docstring) with her
own text from index.html instead of graph.json's node/cluster labels.

Everything below is computed from graph/graph.json. Nothing is hand-transcribed:
cluster names, cross-cluster edge counts, and every coordinate the circular
solver produces are derived here. There is no force simulation at load time
and no animation loop — the ordering is solved once, at import, and consumed
as a plain list of cluster ids.

Copy policy: zero assistant-authored prose. The only strings this module
itself renders are `esc()`-escaped pass-throughs of whatever the caller
gives it; the area titles/descriptions actually shown on the homepage are
scraped from index.html by area_graph.py, not sourced here.
"""

import json, os, collections, html

HERE = os.path.dirname(os.path.abspath(__file__))
# figures/ sits at the repo root, so the repo containing THIS file is the one
# whose graph.json gets read by default -- important when this file is run
# from a worktree/checkout other than the primary one (see WEBSITE_GRAPH).
ROOT = os.path.dirname(HERE)
GRAPH_PATH = os.environ.get(
    "WEBSITE_GRAPH", os.path.join(ROOT, "graph", "graph.json")
)

# ---------------------------------------------------------------- site tokens
PAPER = "#f5f2ec"
INK = "#111118"
INK_BLUE = "#1a2c6b"
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
with open(GRAPH_PATH, encoding="utf-8") as f:
    G = json.load(f)
NODES = {n["id"]: n for n in G["nodes"]}
EDGES = G["edges"]
CLUSTERS = {c["id"]: c["name"] for c in G["meta"]["clusters"]}
CIDS = sorted(CLUSTERS)

# shared-concept edges per pair of areas: (cluster_a, cluster_b) -> count
pair_w = collections.Counter()
for e in EDGES:
    a, b = NODES[e["a"]], NODES[e["b"]]
    if a["cluster"] != b["cluster"]:
        pair_w[tuple(sorted((a["cluster"], b["cluster"])))] += 1

CLUSTER_SIZE = collections.Counter(n["cluster"] for n in G["nodes"])


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


# Eight area nodes on an optimised circle. Edge = number of concept-to-concept
# edges that cross that pair of areas. Weak pairs are dropped so the picture
# stays sparse: 25 of the 28 possible pairs are non-empty, which as a complete
# graph is a hairball; MIN_PAIR keeps only the load-bearing ones. It is set at
# the value that still leaves every one of the eight areas attached — an isolated
# area node would be the flat-grid problem wearing a new costume. area_graph.py
# reads this threshold (as base.A_MIN_PAIR) to keep its own edge set consistent
# with the mockup's treatment A, which is what this constant originally sized.
A_MIN_PAIR = 6

