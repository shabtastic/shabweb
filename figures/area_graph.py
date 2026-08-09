#!/usr/bin/env python3
"""
area_graph.py — treatment A (the area-level graph) carrying HER text.

Shabnam chose treatment A out of area_graph_data.py: eight area nodes, edges
weighted by how many concept-to-concept edges cross each pair of areas. What she
rejected was the *vocabulary*: the labels there came from graph.json (pipeline
cluster names and extracted concepts). Treatment B of that file (bridge concepts)
is dead and is not rebuilt here.

This file keeps A's graph exactly — same pair weights from graph.json, same
circular-ordering solver, same MIN_PAIR threshold with the same connectivity
assert, same darken_to_contrast() color policy, imported from area_graph_data.py
rather than reimplemented — and swaps every string for text scraped straight out
of index.html's .research-grid.

Plates A (title + tag chips), B (all descriptions open at once) and C (title
only) did their job and are gone: she chose D, click-to-open, and settled two of
its three questions on 2026-08-08 —

  * the marker that says a node opens leaves the node disc and sits beside the
    area TITLE (the in-node chevron is rejected);
  * the description opens RADIATING OUTWARD from the centre of the graphic, so
    opening never pushes content inward across the graph.

The mockup rendered D two ways to settle the last open question, tags: D-tags
(title + her .research-tag chips at rest) and D-plain (title only at rest),
each shown both closed and with one area's description open. She chose
D-plain — title only — and that is the only frame this file ships:
production renders the resting (closed) frame; the description-open behavior
is CSS/JS click-to-open on top of it (see figures/README.md and the
implementation plan), not a separately generated frame.

Layout is solved here in Python and baked as literal SVG coordinates: no
simulation, no animation, nothing computed at load. Label placement is a box
solver (solve_labels): each label block gets an axis-aligned box, seeded
radially outward from its node, then relaxed against the eight node discs,
against every other box, and against the canvas edges, with a weak spring
back to its radial seed so a label never drifts away from the node it names.
It ends with an assert that no two boxes overlap and no box sits on a node.
The footprint reserved is every area's open card, not just the one that
happens to be open, so clicking any of the eight reflows nothing.

Copy policy: zero assistant-authored prose. Every word rendered comes from
index.html — the eight <h3> titles, the eight <p> descriptions, the
.research-tag chips — verbatim; the file is re-scraped on every run, so her
edits to index.html carry straight through. The only added glyph is the
disclosure chevron.
"""

import os, re, math, html, collections

import area_graph_data as base  # graph data, color policy, circle solver

# figures/ sits at the repo root, so the repo containing THIS file is the one
# whose index.html gets scraped by default -- otherwise figures/build.py
# would inject an SVG generated from one repo's index.html into another
# repo's index.html (e.g. main checkout vs. a worktree on a feature branch),
# and the figure could silently disagree with the page it lands in. See
# WEBSITE_INDEX to override.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.environ.get(
    "WEBSITE_INDEX", os.path.join(ROOT, "index.html")
)

PAPER, INK, INK_BLUE = base.PAPER, base.INK, base.INK_BLUE
GRID_MIN, GRID_MAJ = base.GRID_MIN, base.GRID_MAJ
CLUSTER_INK, CLUSTER_FILL = base.CLUSTER_INK, base.CLUSTER_FILL
CLUSTERS, CIDS, ORDER = base.CLUSTERS, base.CIDS, base.ORDER
pair_w, CLUSTER_SIZE = base.pair_w, base.CLUSTER_SIZE
esc, rgba = base.esc, base.rgba


# ------------------------------------------------- her text, out of index.html
def clean(s):
    """Drop inline markup (<em> in item 03), unescape, collapse whitespace.

    Words are never altered — this only removes tags the SVG cannot render.
    """
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_research_grid():
    src = open(INDEX_PATH).read()
    i = src.index('<div class="research-grid">')
    sec = src[i : src.index("</section>", i)]
    out = {}
    for chunk in sec.split('<span class="research-num">')[1:]:
        title = clean(re.search(r"<h3>(.*?)</h3>", chunk, re.S).group(1))
        desc = clean(re.search(r"<p>(.*?)</p>", chunk, re.S).group(1))
        tags = [
            clean(t)
            for t in re.findall(
                r'<span class="research-tag">(.*?)</span>', chunk, re.S
            )
        ]
        cid = [c for c, n in CLUSTERS.items() if n == title]
        assert len(cid) == 1, f"no unique cluster for {title!r}"
        out[cid[0]] = {"title": title, "desc": desc, "tags": tags}
    assert set(out) == set(CIDS), "index.html and graph.json disagree on the areas"
    return out


AREAS = parse_research_grid()

# ------------------------------------------------------------------ type metrics
# Space Mono is monospaced at 600/1000 em; letter-spacing adds a flat per-glyph
# amount. Everything below is measured with these two numbers, so the boxes the
# solver moves around are the boxes the browser draws.
ADV = 0.60


def text_w(s, size, ls=0.0):
    return len(s) * (size * ADV + ls)


def wrap(text, width):
    return base.wrap(text, width)


# ------------------------------------------------------------------ graph geometry
# Identical to treatment A in area_graph_data.py's mockup-era circle solver.
W = 1040
CX = 520
R = 176
MIN_PAIR = base.A_MIN_PAIR
KEPT = {p: w for p, w in pair_w.items() if w >= MIN_PAIR}
assert set(c for p in KEPT for c in p) == set(CIDS), "an area fell off the graph"
WMAX = max(KEPT.values())


def a_radius(cid):
    return 13 + 20 * math.sqrt(CLUSTER_SIZE[cid] / max(CLUSTER_SIZE.values()))


def positions(cy):
    pos = {}
    for i, cid in enumerate(ORDER):
        ang = -math.pi / 2 + 2 * math.pi * i / len(ORDER)
        pos[cid] = (CX + R * math.cos(ang), cy + R * math.sin(ang), ang)
    return pos


def edges_svg(pos, cy):
    s = []
    for (a, b), w in sorted(KEPT.items(), key=lambda kv: kv[1]):
        x1, y1, _ = pos[a]
        x2, y2, _ = pos[b]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        qx, qy = mx + (CX - mx) * 0.16, my + (cy - my) * 0.16
        d1 = math.hypot(qx - x1, qy - y1) or 1
        d2 = math.hypot(qx - x2, qy - y2) or 1
        x1, y1 = x1 + (qx - x1) / d1 * a_radius(a), y1 + (qy - y1) / d1 * a_radius(a)
        x2, y2 = x2 + (qx - x2) / d2 * a_radius(b), y2 + (qy - y2) / d2 * a_radius(b)
        t = w / WMAX
        s.append(
            f'<path d="M{x1:.1f} {y1:.1f} Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{INK_BLUE}" stroke-opacity="{0.16 + 0.46 * t:.2f}" '
            f'stroke-width="{1.1 + 7.4 * t:.2f}" stroke-linecap="round"/>'
        )
    return "".join(s)


# ------------------------------------------------------------------ label blocks
# A block is a list of rows; a row is ("t", string) title line or ("c", [chips]).
TITLE_SIZE, TITLE_LH, TITLE_WRAP = 12.5, 15.0, 22
DESC_SIZE, DESC_LH, DESC_WRAP = 10.5, 13.4, 31
CHIP_SIZE, CHIP_LS, CHIP_LH = 8.0, 1.05, 15.0
CHIP_PADX, CHIP_GAP = 5.0, 4.0
PAD_X, PAD_Y = 6.0, 5.0
CHIP_MAXW = 208.0


def chip_w(t):
    return text_w(t, CHIP_SIZE, CHIP_LS) + 2 * CHIP_PADX


def build_block(cid, kind, opened=False):
    rows = [("t", ln) for ln in wrap(AREAS[cid]["title"], TITLE_WRAP)]
    if kind == "click":
        kind = "desc" if opened else "name"
    if kind == "tags":
        line, wsum = [], 0.0
        for t in AREAS[cid]["tags"]:
            cw = chip_w(t)
            if line and wsum + CHIP_GAP + cw > CHIP_MAXW:
                rows.append(("c", line))
                line, wsum = [t], cw
            else:
                wsum += (CHIP_GAP if line else 0) + cw
                line.append(t)
        if line:
            rows.append(("c", line))
    elif kind == "desc":
        rows += [("d", ln) for ln in wrap(AREAS[cid]["desc"], DESC_WRAP)]
    return rows


def block_size(rows):
    w = h = 0.0
    for i, (k, v) in enumerate(rows):
        if k == "t":
            w = max(w, text_w(v, TITLE_SIZE))
            h += TITLE_LH
        elif k == "d":
            w = max(w, text_w(v, DESC_SIZE))
            h += DESC_LH + (3.0 if i and rows[i - 1][0] == "t" else 0.0)
        else:
            w = max(w, sum(chip_w(t) for t in v) + CHIP_GAP * (len(v) - 1))
            h += CHIP_LH + (3.0 if i and rows[i - 1][0] != "c" else 0.0)
    return w + 2 * PAD_X, h + 2 * PAD_Y


# ------------------------------------------------------------- placement solver
GAP_NODE = 12.0  # clearance between a label box and any node disc
GAP_BOX = 12.0  # clearance between two label boxes
EDGE = 14.0  # clearance from the canvas edge


def solve_labels(sizes, cy, H, iters=1400, tag="plate", seeds=None):
    """Seed each label radially outward from its node, then relax to no overlap.

    `sizes` is the *occupancy* per area — for plate D that is the open card's
    footprint, reserved even in the resting frame, which is what keeps the two
    frames from moving relative to each other.

    `seeds` overrides the default radial seed. Plate D passes its own, because
    there the occupancy box is the union of a head block and a card offset
    radially away from it, and what wants to sit a fixed distance off the disc
    is the *head*, not the union.

    Constraints, applied every sweep:
      * box vs node disc  — AABB push-out against every one of the eight discs
      * box vs box        — push apart along the shallower penetration axis
      * box vs canvas     — clamp inside
      * spring to seed    — weak pull back so a label stays beside its own node
    """
    kind = tag
    pos = positions(cy)
    boxes = {}
    if seeds is None:
        seeds = {}
        for cid in ORDER:
            x, y, ang = pos[cid]
            bw, bh = sizes[cid]
            ux, uy = math.cos(ang), math.sin(ang)
            reach = a_radius(cid) + GAP_NODE + abs(ux) * bw / 2 + abs(uy) * bh / 2
            seeds[cid] = (x + ux * reach, y + uy * reach)
    for cid in ORDER:
        bw, bh = sizes[cid]
        boxes[cid] = [seeds[cid][0], seeds[cid][1], bw, bh]

    for it in range(iters):
        k = 1.0 - it / iters  # anneal the spring away so constraints win at the end
        for cid in ORDER:
            b = boxes[cid]
            for oid in ORDER:  # keep off the node discs
                ox, oy, _ = pos[oid]
                r = a_radius(oid) + GAP_NODE
                dx, dy = b[0] - ox, b[1] - oy
                px = b[2] / 2 + r - abs(dx)
                py = b[3] / 2 + r - abs(dy)
                if px > 0 and py > 0:
                    if px < py:
                        b[0] += px * (1 if dx >= 0 else -1)
                    else:
                        b[1] += py * (1 if dy >= 0 else -1)
        for i, a in enumerate(ORDER):  # keep off each other
            for c in ORDER[i + 1 :]:
                ba, bc = boxes[a], boxes[c]
                dx, dy = bc[0] - ba[0], bc[1] - ba[1]
                px = (ba[2] + bc[2]) / 2 + GAP_BOX - abs(dx)
                py = (ba[3] + bc[3]) / 2 + GAP_BOX - abs(dy)
                if px > 0 and py > 0:
                    if px / (ba[2] + bc[2]) < py / (ba[3] + bc[3]):
                        sh = px / 2 * (1 if dx >= 0 else -1)
                        ba[0] -= sh
                        bc[0] += sh
                    else:
                        sh = py / 2 * (1 if dy >= 0 else -1)
                        ba[1] -= sh
                        bc[1] += sh
        for cid in ORDER:  # spring home, then clamp to the canvas
            b = boxes[cid]
            b[0] += (seeds[cid][0] - b[0]) * 0.05 * k
            b[1] += (seeds[cid][1] - b[1]) * 0.05 * k
            b[0] = min(max(b[0], EDGE + b[2] / 2), W - EDGE - b[2] / 2)
            b[1] = min(max(b[1], EDGE + b[3] / 2), H - EDGE - b[3] / 2)

    # verification, not decoration: if this trips, the plate needs a taller canvas
    for i, a in enumerate(ORDER):
        ba = boxes[a]
        for oid in ORDER:
            ox, oy, _ = pos[oid]
            r = a_radius(oid)
            assert not (
                abs(ba[0] - ox) < ba[2] / 2 + r and abs(ba[1] - oy) < ba[3] / 2 + r
            ), f"{kind}: label {a} sits on node {oid}"
        for c in ORDER[i + 1 :]:
            bc = boxes[c]
            assert not (
                abs(bc[0] - ba[0]) < (ba[2] + bc[2]) / 2 - 0.5
                and abs(bc[1] - ba[1]) < (ba[3] + bc[3]) / 2 - 0.5
            ), f"{kind}: labels {a} and {c} overlap"
    return pos, boxes


# ------------------------------------------------- radial-outward card geometry
# Her decision, 2026-08-08: the click marker leaves the node disc and sits beside
# the area TITLE, and the description opens *radiating outward* from the centre
# of the graphic — each area's card expands away from the layout centre along
# that node's own radial direction, so opening never pushes content inward
# across the graph.
#
# Geometry. Each area owns two blocks:
#
#   head — the title (plus, in the tags variant, her .research-tag chips) and
#          the marker. This is what is visible at rest.
#   card — the description. Hidden at rest, shown when that area is open.
#
# The card's centre is placed at the head's centre plus u * L, where u is the
# unit outward radial and L is the SMALLEST slide along u that clears the head
# box. Two axis-aligned boxes are clear as soon as *either* axis separates, so
#
#   L = min( ((hw+dw)/2 + CARD_GAP)/|ux| ,  ((hh+dh)/2 + CARD_GAP)/|uy| )
#
# with a zero component reading as infinity. Taking the min rather than summing
# the projected half-extents matters on the four diagonals: summing pushes the
# card ~1.5x further out than it needs to go and strands it in the corner.
#
# For the node at the top of the ring the card lands directly above its title;
# for the node on the right it lands directly to the right; for the four
# diagonals it lands on the diagonal. One formula, no per-node special cases in
# the direction itself.
#
# What the solver moves around is the *union* of head and card — reserved for
# all eight areas at once, not just the one that happens to be open in a frame.
# That is what makes zero-reflow true for a click on any area rather than only
# for the pre-chosen one. Because cards grow outward, the reserved space all
# lands in the outer margin and the heads still hug the ring.
#
# Two places where "outward" fights the canvas:
#
#   vertical  — the top and bottom areas need the tallest reach. Rather than
#               clamp them (which would drag their titles back onto the ring),
#               the canvas height is *derived* from the solved reach: see
#               auto_height(). The clamp in solve_labels never fires.
#   horizontal — the two areas at due-left and due-right grow into a margin of
#               fixed width, and a full-measure title beside a full-measure
#               paragraph does not fit in 1040px. fit_card() handles those two
#               by narrowing the title (wrap_tight, breaking at hyphens her text
#               already contains) and then searching down the description
#               measure until the union box fits. No text is altered.

CARD_GAP = 11.0
MARK_BOX, MARK_GAP, MARK_SIZE = 12.0, 5.0, 11.0
MARK_SHUT, MARK_OPEN = "▾", "▴"  # projects.html's .section-arrow
TITLE_WRAP_TIGHT = 12
CHIP_MAXW_TIGHT = 118.0
FLAT = 0.10  # |uy| below this counts as a due-left / due-right node


def wrap_tight(text, width):
    """Greedy wrap that may also break after a hyphen her text already has."""
    lines, cur = [], ""
    for word in text.split():
        for j, piece in enumerate(re.split(r"(?<=-)", word)):
            if not piece:
                continue
            sep = "" if j else (" " if cur else "")
            if cur and len(cur) + len(sep) + len(piece) > width:
                lines.append(cur)
                cur = piece
            else:
                cur += sep + piece
    if cur:
        lines.append(cur)
    return lines


def mark_row(rows):
    """The marker rides the LAST title line — a two-line title reads as one
    phrase, and hanging the glyph off line 1 puts it inside the phrase."""
    return max(i for i, (k, _) in enumerate(rows) if k == "t")


def rows_size(rows, mark=False):
    """block_size(), plus room for the marker beside the marker row."""
    mrow = mark_row(rows) if mark else -1
    w = h = 0.0
    for i, (k, v) in enumerate(rows):
        if k == "t":
            rw = text_w(v, TITLE_SIZE)
            if i == mrow:
                rw += MARK_GAP + MARK_BOX
            w = max(w, rw)
            h += TITLE_LH
        elif k == "d":
            w = max(w, text_w(v, DESC_SIZE))
            h += DESC_LH + (3.0 if i and rows[i - 1][0] == "t" else 0.0)
        else:
            w = max(w, sum(chip_w(t) for t in v) + CHIP_GAP * (len(v) - 1))
            h += CHIP_LH + (3.0 if i and rows[i - 1][0] != "c" else 0.0)
    return w + 2 * PAD_X, h + 2 * PAD_Y


def head_rows(cid, with_tags, tight=False):
    title = AREAS[cid]["title"]
    lines = wrap_tight(title, TITLE_WRAP_TIGHT) if tight else wrap(title, TITLE_WRAP)
    rows = [("t", ln) for ln in lines]
    if with_tags:
        cap = CHIP_MAXW_TIGHT if tight else CHIP_MAXW
        line, wsum = [], 0.0
        for t in AREAS[cid]["tags"]:
            cw = chip_w(t)
            if line and wsum + CHIP_GAP + cw > cap:
                rows.append(("c", line))
                line, wsum = [t], cw
            else:
                wsum += (CHIP_GAP if line else 0) + cw
                line.append(t)
        if line:
            rows.append(("c", line))
    return rows


def unit(cid):
    i = ORDER.index(cid)
    ang = -math.pi / 2 + 2 * math.pi * i / len(ORDER)
    return math.cos(ang), math.sin(ang)


def side_of(ux):
    return "start" if ux > 0.15 else ("end" if ux < -0.15 else "middle")


def card_geom(cid, with_tags, dwrap, tight):
    """Head box, card box offset radially outward, and their union AABB."""
    hrows = head_rows(cid, with_tags, tight)
    hw, hh = rows_size(hrows, mark=True)
    drows = [("d", ln) for ln in wrap(AREAS[cid]["desc"], dwrap)]
    dw, dh = rows_size(drows)
    ux, uy = unit(cid)
    inf = float("inf")
    tx = ((hw + dw) / 2 + CARD_GAP) / abs(ux) if abs(ux) > 1e-9 else inf
    ty = ((hh + dh) / 2 + CARD_GAP) / abs(uy) if abs(uy) > 1e-9 else inf
    L = min(tx, ty)
    ox, oy = ux * L, uy * L
    xmin, xmax = min(-hw / 2, ox - dw / 2), max(hw / 2, ox + dw / 2)
    ymin, ymax = min(-hh / 2, oy - dh / 2), max(hh / 2, oy + dh / 2)
    mx, my = (xmin + xmax) / 2, (ymin + ymax) / 2  # union centre, rel. head centre
    return {
        "cid": cid,
        "hrows": hrows,
        "drows": drows,
        "hw": hw, "hh": hh, "dw": dw, "dh": dh,
        "aw": xmax - xmin, "ah": ymax - ymin,
        "head_off": (-mx, -my),      # head centre, relative to union centre
        "card_off": (ox - mx, oy - my),
        "u": (ux, uy),
        "side": side_of(ux),
        "dwrap": dwrap,
        "tight": tight,
    }


def head_seed(g, pos):
    """Union-box centre such that the HEAD clears its disc by GAP_NODE."""
    cid = g["cid"]
    x, y, _ = pos[cid]
    ux, uy = g["u"]
    reach = (
        a_radius(cid) + GAP_NODE + (abs(ux) * g["hw"] + abs(uy) * g["hh"]) / 2
    )
    hx, hy = x + ux * reach, y + uy * reach
    return hx - g["head_off"][0], hy - g["head_off"][1]


def fit_card(cid, with_tags, cy):
    """Widest description measure whose union box still fits the canvas width."""
    ux, uy = unit(cid)
    tight = abs(uy) < FLAT
    pos = positions(cy)
    tries = [DESC_WRAP] if not tight else list(range(DESC_WRAP, 15, -1))
    for dw in tries:
        g = card_geom(cid, with_tags, dw, tight)
        sx, _ = head_seed(g, pos)
        if sx - g["aw"] / 2 >= EDGE and sx + g["aw"] / 2 <= W - EDGE:
            return g
    return card_geom(cid, with_tags, tries[-1], tight)


def auto_canvas(geoms, cy0):
    """Canvas derived from the reach the cards actually need, up and down
    separately — the ring is not vertically centred, it sits wherever the two
    reaches put it, so neither the top nor the bottom area is clamped."""
    pos = positions(cy0)
    up = down = 0.0
    for cid in ORDER:
        g = geoms[cid]
        _, sy = head_seed(g, pos)
        up = max(up, cy0 - (sy - g["ah"] / 2))
        down = max(down, (sy + g["ah"] / 2) - cy0)
    cy = up + EDGE + 1
    return cy, cy + down + EDGE + 1


# ------------------------------------------------------------------- rendering
def render_rows(rows, bx, by, bw, bh, side, ink, mark=None):
    """Draw one block. `mark` renders the disclosure glyph on the title line."""
    x0, x1 = bx - bw / 2 + PAD_X, bx + bw / 2 - PAD_X
    ax = {"start": x0, "end": x1, "middle": bx}[side]
    y = by - bh / 2 + PAD_Y
    mrow = mark_row(rows) if mark else -1
    out = []
    for i, (k, v) in enumerate(rows):
        if k == "t":
            y += TITLE_LH
            tx, mx = ax, None
            if i == mrow:
                tw = text_w(v, TITLE_SIZE)
                if side == "start":
                    mx = ax + tw + MARK_GAP
                elif side == "end":
                    mx = ax - tw - MARK_GAP - MARK_BOX
                else:
                    tx = bx - (MARK_GAP + MARK_BOX) / 2
                    mx = tx + tw / 2 + MARK_GAP
            out.append(
                f'<text x="{tx:.1f}" y="{y - 3.6:.1f}" text-anchor="{side}" '
                f"font-family=\"'Space Mono', monospace\" font-size=\"{TITLE_SIZE}\" "
                f'font-weight="700" fill="{ink}">{esc(v)}</text>'
            )
            if mx is not None:
                out.append(
                    f'<text x="{mx + MARK_BOX / 2:.1f}" y="{y - 4.0:.1f}" '
                    f'text-anchor="middle" font-family="\'Space Mono\', monospace" '
                    f'font-size="{MARK_SIZE}" fill="{ink}" fill-opacity="0.9">'
                    f"{mark}</text>"
                )
        elif k == "d":
            y += DESC_LH + (3.0 if i and rows[i - 1][0] == "t" else 0.0)
            out.append(
                f'<text x="{ax:.1f}" y="{y - 3.4:.1f}" text-anchor="{side}" '
                f"font-family=\"'Space Mono', monospace\" font-size=\"{DESC_SIZE}\" "
                f'fill="{INK}" fill-opacity="0.80">{esc(v)}</text>'
            )
        else:
            y += CHIP_LH + (3.0 if i and rows[i - 1][0] != "c" else 0.0)
            tot = sum(chip_w(t) for t in v) + CHIP_GAP * (len(v) - 1)
            cx0 = {"start": x0, "end": x1 - tot, "middle": bx - tot / 2}[side]
            for t in v:
                cw = chip_w(t)
                out.append(
                    f'<rect x="{cx0:.1f}" y="{y - CHIP_LH + 1.5:.1f}" width="{cw:.1f}" '
                    f'height="{CHIP_LH - 3:.1f}" rx="1.5" fill="none" '
                    f'stroke="{rgba(INK_BLUE, 0.28)}" stroke-width="0.9"/>'
                    f'<text x="{cx0 + CHIP_PADX:.1f}" y="{y - 4.4:.1f}" '
                    f"font-family=\"'Space Mono', monospace\" font-size=\"{CHIP_SIZE}\" "
                    f'letter-spacing="{CHIP_LS}" style="text-transform:uppercase" '
                    f'fill="{INK_BLUE}">{esc(t)}</text>'
                )
                cx0 += cw + CHIP_GAP
    return "".join(out)


def box_exit(cx, cy_, w, h, ux, uy):
    """Where the ray from a box centre along (ux,uy) leaves that box."""
    ts = []
    if abs(ux) > 1e-9:
        ts.append((w / 2) / abs(ux))
    if abs(uy) > 1e-9:
        ts.append((h / 2) / abs(uy))
    t = min(ts)
    return cx + ux * t, cy_ + uy * t


def card_svg(g, hx, hy, cx, cy_, ink):
    """The description card: paper panel, spine on its inward edge, and a
    connector drawn along the radial itself — on the four diagonals the card
    lands up-and-over from its title, and the connector is what says that the
    displacement is the outward direction rather than a stray box."""
    dw, dh = g["dw"], g["dh"]
    ux, uy = g["u"]
    ax, ay = box_exit(hx, hy, g["hw"], g["hh"], ux, uy)
    bx, by = box_exit(cx, cy_, dw, dh, -ux, -uy)
    lead = (
        f'<path d="M{ax:.1f} {ay:.1f}L{bx:.1f} {by:.1f}" stroke="{ink}" '
        f'stroke-opacity="0.42" stroke-width="1" fill="none"/>'
    )
    x, y = cx - dw / 2, cy_ - dh / 2
    if abs(uy) >= abs(ux):  # grew vertically -> spine on the edge facing the ring
        sx, sy, sw, sh = x, (y + dh - 2.5) if uy < 0 else y, dw, 2.5
    else:
        sx, sy, sw, sh = (x + dw - 2.5) if ux < 0 else x, y, 2.5, dh
    return (
        lead
        + f'<rect x="{x:.1f}" y="{y:.1f}" width="{dw:.1f}" height="{dh:.1f}" rx="3" '
        f'fill="{PAPER}" fill-opacity="0.96" stroke="{rgba(INK, 0.18)}" '
        f'stroke-width="0.9"/>'
        f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" '
        f'fill="{ink}"/>'
    )


# ------------------------------------------------------------------- plate D
def solve_variant(with_tags, tag):
    """Solve ONE layout per variant; both frames of that variant reuse it."""
    cy0 = 500.0
    geoms = {cid: fit_card(cid, with_tags, cy0) for cid in ORDER}
    cy, H = auto_canvas(geoms, cy0)
    pos = positions(cy)
    sizes = {cid: (geoms[cid]["aw"], geoms[cid]["ah"]) for cid in ORDER}
    seeds = {cid: head_seed(geoms[cid], pos) for cid in ORDER}
    pos, boxes = solve_labels(sizes, cy, H, tag=tag, seeds=seeds)
    drift = 0.0
    for cid in ORDER:
        bx, by, bw, bh = boxes[cid]
        assert (
            bx - bw / 2 >= EDGE - 0.5
            and bx + bw / 2 <= W - EDGE + 0.5
            and by - bh / 2 >= EDGE - 0.5
            and by + bh / 2 <= H - EDGE + 0.5
        ), f"{tag}: reserved card footprint for {cid} runs off the canvas"
        drift = max(drift, math.hypot(bx - seeds[cid][0], by - seeds[cid][1]))
    heads = {
        cid: (
            boxes[cid][0] + geoms[cid]["head_off"][0],
            boxes[cid][1] + geoms[cid]["head_off"][1],
        )
        for cid in ORDER
    }
    cards = {
        cid: (
            boxes[cid][0] + geoms[cid]["card_off"][0],
            boxes[cid][1] + geoms[cid]["card_off"][1],
        )
        for cid in ORDER
    }
    return {
        "geoms": geoms, "H": H, "cy": cy, "pos": pos, "drift": drift,
        "boxes": boxes, "heads": heads, "cards": cards, "tag": tag,
    }


def d_frame(v, prefix, opened=frozenset()):
    """One frame of a variant. Only `opened` changes; every coordinate is fixed."""
    H, cy, pos = v["H"], v["cy"], v["pos"]
    s = [f"<defs>{base.grid_defs(prefix)}</defs>", base.grid_rects(prefix, W, H)]
    s.append(edges_svg(pos, cy))
    for cid in ORDER:
        g = v["geoms"][cid]
        ink = CLUSTER_INK[cid]
        x, y, _ = pos[cid]
        r = a_radius(cid)
        is_open = cid in opened
        hx, hy = v["heads"][cid]
        s.append(
            f'<g role="button" tabindex="0" aria-expanded="{"true" if is_open else "false"}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{rgba(CLUSTER_FILL[cid], 0.62)}" stroke="{ink}" stroke-width="1.8"/>'
        )
        if is_open:
            ccx, ccy = v["cards"][cid]
            s.append(card_svg(g, hx, hy, ccx, ccy, ink))
            s.append(
                render_rows(
                    g["drows"], ccx, ccy, g["dw"], g["dh"], g["side"], ink
                )
            )
        s.append(
            render_rows(
                g["hrows"], hx, hy, g["hw"], g["hh"], g["side"], ink,
                mark=MARK_OPEN if is_open else MARK_SHUT,
            )
        )
        s.append("</g>")
    return f'<svg viewBox="0 0 {W} {H:.0f}" width="100%">' + "".join(s) + "</svg>"


# ---------------------------------------------------------------- production
# Only D-plain ships, at rest: title only (no .research-tag chips), no card
# open. D-tags, both "/open" frames, and the composite (which lifted the
# approach figure into a <symbol> so the mockup could compare it side by
# side with each plate on one page) existed only for that comparison — in
# production the approach figure and the area graph are two separate blocks
# in index.html (see figures/README.md), so none of that ships here.
_variant_d_plain = solve_variant(False, "D-plain")
SVG = d_frame(_variant_d_plain, "dp1", opened=frozenset())


def svg_fragment():
    """Return the area graph (treatment D-plain, at rest) as a standalone <svg> fragment."""
    return SVG


if __name__ == "__main__":
    print(svg_fragment())
