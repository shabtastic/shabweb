import math

# =============================================================================
# approach_mobile.py --- NARROW-SCREEN variant of the approved v22 figure.
#
# WHAT THIS IS
# ------------
# v22 (1040x482) is the converged desktop figure. Below ~900px the site falls
# back to the eight-item research grid and hides the area graph, but the
# approach figure itself is too important to lose ("that content feels too
# important to lose now"). This file draws a SPARSE version of it for a phone.
#
# TARGET WIDTH: a ~360-390px viewport. The figure is given a 336-unit-wide
# viewBox, which is what a 360px phone leaves after 12px of page padding on
# each side. At that width one viewBox unit renders as ~1 CSS px, so every
# font-size below is also its rendered pixel size --- no hidden shrinkage.
#
# HOW THE CURVES STAY COMPUTED
# ----------------------------
# approach.py is imported as a plain module (`import approach as g`) --- it
# writes nothing on import, so its namespace gives us the real model directly:
# true_state(), estimate(), err_env(), slow_w(), fast_env(), carrier(), the
# warp x_of_tau()/tau_of_x(), PERIOD/FASTAMP, MEAN, GAPS, APPR.
#
# The mobile axis is the SAME warped log-time axis over the SAME one-year span,
# just laid out over 218px of observed width instead of 790px. Because both
# axes are logs of the same span, mobile x maps to desktop x by an exact linear
# rescale (XSCALE below) that preserves tau at every pixel. So every y in these
# figures is g.<fn>(desktop x) put through one linear y map --- nothing is
# hand-faked, and nothing about the time semantics changes.
#
# The one thing that genuinely changes is RESOLUTION: px-per-cycle drops by
# XSCALE, so fine structure switches on much later (closer to 'now') and the
# faint envelope band covers more of each strand. That is honest --- at phone
# size you really cannot draw a heartbeat except right next to 'now'.
#
# The estimate curve is g.estimate() unchanged, i.e. still composed from all
# seven desktop strands even where only two or four are drawn. Re-deriving it
# from the surviving strands would produce a DIFFERENT curve from the approved
# one; the dropped signals still exist in the world, they are just not drawn.
#
# COPY POLICY (binding)
# ---------------------
# Zero new copy. Every string below is one of hers, already present in v22,
# character for character. Labels are DROPPED, never reworded or shortened.
# Three of her strings are RE-WRAPPED, never rewritten --- same words, same
# order, different line breaks, which v22 itself does freely (it renders
# "measurable"/"physiology" on two lines and her true-state label on two):
#   * "our best guess at the internal state (triangulated from many diverse
#     signals)" --- one line in v22, two here.
#   * "a higher likelihood of the desired outcome" --- one line in v22, two
#     here, so it fits right of 'now'.
#   * "measurable physiology" / "observable behavior" --- TWO lines in v22
#     (a 70px left margin forced it); one line each here, because on a phone
#     they sit above their lanes with the full width available.
# Nothing else moved, and nothing was shortened: where a string would not fit
# it was dropped whole.
#
# PRINCIPLES HELD AT THIS SIZE
# ----------------------------
# * true state continuous and unbroken; uncertainty lives in the sampling band
#   and in strand gaps, never in the state. No dashed line encodes uncertainty
#   (the forecast dashes are v22's own "not yet observed" dashes, unchanged).
# * no leader lines anywhere; no floating or unexplained glyphs --- where a
#   label had to go, the mark it explained went with it (see the ticks in B,
#   and the outcome markers).
# * every surviving label sits against its referent (adjacency compromises are
#   listed per variant below).
# * elicitation at all timescales: A's four ticks are spread across the warp
#   --- ~88 days, ~13 hours, ~56 seconds and ~2 seconds ago --- not bunched
#   at the fast end.
#
# -----------------------------------------------------------------------------
# VARIANT A --- moderate reduction.
#
# DROPPED (and the claim that goes with it):
#   * 3 of 7 signal strands (eyes, breath, behavior). Kept: heart + skin
#     (measurable physiology, 1s and 90s) and movement + choices (observable
#     behavior, 9s and 2.5h). CLAIM LOST: none outright --- both families
#     survive, and the kept four still span 1s..2.5h so the resolution
#     staircase still happens. WEAKENED: "many diverse signals" is now asserted
#     by her estimate label rather than shown seven times over.
#   * 2 of 5 timescale brackets (hours, weeks). Kept: seconds / days / years.
#     CLAIM LOST: that the nesting is a five-step staircase. SURVIVES: that the
#     timescales nest, on both sides of 'now', asymmetrically.
#   * 4 of 8 individual-experience ticks. CLAIM LOST: none --- the four kept are
#     spread across the warp, so "elicitation happens at all timescales" holds.
#   * her line "(internal state and/or behavior)". CLAIM LOST: that the outcome
#     being predicted may be an internal state OR a behaviour. It is 32
#     characters and cannot be broken without reading as two fragments.
#   * the second sampling-band tint (v22 draws an outer and an inner band; at
#     this scale the two are within a pixel of each other). CLAIM LOST: none.
#
# KEPT: grey true state; ink-blue estimate + uncertainty band; both signal
# families named; sensor gaps (skin, movement); rising ticks + "individual
# experience"; the swipe; 'now'; the forecast cone; BOTH futures (improved and
# "without intervention") with both outcome markers; her intervention sentence.
#
# ADJACENCY COMPROMISE: on a phone there is no left margin, so her two curve
# labels cannot sit beside their curves the way they do at 1040px --- they
# stack below the drawing, grey label above navy label, each still the only
# text of its colour and directly under the curve it names.
#
# Production note: the mockup compared this treatment (A, moderate reduction)
# against a more aggressive VARIANT B side by side; Shabnam chose A, so B's
# config and every code path that built it (build(B), the two-phone PAGE
# wrapper, the diagnostic prints comparing A and B) are dropped here. The
# history of what B traded away lives in the mockup's gen_v22_mobile.py, not
# in production.
# =============================================================================

# ---- load the approved model -------------------------------------------
# Production: approach.py writes nothing on import (its file-write was
# removed when it gained svg_fragment()), so it can be imported directly
# instead of exec'd out of its source text.
import approach as g

# ---------------- the narrow canvas ----------------
VIEW_W    = 336        # = 360px phone - 12px page padding each side
X_LEFT_M  = 8          # left edge of the observed span (one year ago)
NOW_X_M   = 226        # the 'now' divider
FUT_X_M   = 320        # the outcome marker
TOP_PAD_M = 22         # headroom reserved for her title, as v22 reserves 34

XSCALE  = (g.NOW_X - g.X_LEFT) / float(NOW_X_M - X_LEFT_M)      # 790/218
PXDEC_M = (NOW_X_M - X_LEFT_M) / math.log10(1.0 + g.SPAN_SECONDS)
FORE_M  = FUT_X_M - NOW_X_M
PXDECF_M = FORE_M / math.log10(1.0 + g.SPAN_SECONDS)

def xd(x):                      # mobile pixel -> desktop pixel, tau preserved
    return g.NOW_X - (NOW_X_M - x) * XSCALE
def xm(x):                      # desktop pixel -> mobile pixel
    return NOW_X_M - (g.NOW_X - x) / XSCALE
def tau_m(x):
    return 10.0 ** ((NOW_X_M - x) / PXDEC_M) - 1.0
def secpp_m(x):                 # seconds covered by one MOBILE px
    return math.log(10.0) / PXDEC_M * (1.0 + tau_m(x))
def resolve_m(nm, x):           # the staircase, recomputed for this width
    if g.FASTAMP[nm] <= 0: return 1.0
    return g.smoothstep(g.PX_LO, g.PX_HI, g.PERIOD[nm] / secpp_m(x))
def walk_m(nm, x):
    if g.FASTAMP[nm] <= 0: return 1.2
    pc = g.PERIOD[nm] / secpp_m(x)
    if pc < g.PX_LO: return 1.2
    return min(1.2, max(0.22, pc / 5.0))

YS   = 0.55            # y compression: desktop px -> mobile px
YMID = 250.0           # true_state's own centre constant

GAPS_M = dict((nm, [(xm(a), xm(b)) for (a, b) in gg]) for nm, gg in g.GAPS.items())
# The fold into the estimate must NOT be scaled by XSCALE. The bend's vertical
# drop scales with YS (0.55) while its horizontal run would scale with XSCALE
# (1/3.62), which turns v22's staggered fan into a near-vertical wall --- the
# first render did exactly that. Scaling the run by YS-ish instead keeps the
# slope of each bend close to v22's, so the merges still read as a fan.
APPR_M = dict((nm, v * 0.75) for nm, v in g.APPR.items())
XS_M   = xm(70.0)      # every strand still starts where it starts in v22

DAMP_S = 0.38          # strand amplitude scale
ENV_OP_M    = 0.17     # v22's 0.11 vanishes at this size; the envelope band is
ENV_SCALE_M = 0.70     # the whole mechanism for 'there is structure here we
                       # cannot resolve', so it has to survive the shrink
INT_COL, TICK_COL, GHOST_COL = g.INT_COL, g.TICK_COL, g.GHOST_COL
DCOL   = {"#FF7792": "#FF7792", "#FFAE77": "#D9822B"}
DOP    = {"#FF7792": 0.32,      "#FFAE77": 0.42}
STRAND_COL = {"heart": "#FF7792", "eyes": "#FF7792", "skin": "#FF7792",
              "breath": "#FF7792", "behavior": "#FFAE77",
              "movement": "#FFAE77", "choices": "#FFAE77"}
MONO = 0.6             # Space Mono advance width, in em

def tw(s, fs):         # rendered width of a mono string
    return len(s.replace("&#39;", "'")) * MONO * fs

def poly(pts):
    s = "M %.2f %.2f" % pts[0]
    for p in pts[1:]:
        s += " L %.2f %.2f" % p
    return s

# ---------------- variant configuration ----------------
A = dict(
    key="A",
    # 18px lanes, not 14: at 0.55x vertical scale the envelope bands of two
    # neighbours merge into one smear and the two signals stop reading as two.
    strands=[("heart", 46), ("skin", 64), ("movement", 94), ("choices", 112)],
    fams=[("body", "measurable physiology", 34),
          ("behavior", "observable behavior", 80)],
    # 4 of v22's 8, spread across the warp so principle 5 holds: reading left
    # to right these are ~88 days, ~13 hours, ~56 seconds and ~2 seconds ago.
    ticks=[26, 90, 175, 212],
    units=["seconds", "days", "years"],
    ghost=True, y0=172, ts_step=9, int_dy=40,
)

# taller than a straight 0.55x scaling of v22 (which would give 8.8/11):
# the y axis is compressed here, so the droplets need extra rise to clear
# the sampling band and open a pocket for her label above them.
TICK_STEM_M, TICK_DROP_M, TICK_R = 16.0, 20.0, 1.2
F_W_M, F_PAD_TOP_M, F_CORE_IN_M = 7.0, 5.0, 3.0
TS_BASE_M, ARM_R_MIN_M = 8, 10
# v23: the innermost bracket's left arm is derived from its own label, not
# fixed at 20. "seconds" needs ~34 units at FS_UNIT plus the 3-unit label
# offset, so a 20-unit arm both overflowed the bracket and pushed the word
# across the 'now' divider that bracket straddles -- the same defect the
# desktop figure had. Kept as a formula so it survives a type-size change.
ARM_L_MIN_M = max(20, int(len("seconds") * 8.0 * 0.6) + 3 + 4)
FS_FAM, FS_TICK, FS_LBL, FS_UNIT, FS_NOW = 8.5, 8.0, 8.0, 8.0, 8.0
FS_SENT, FS_INT, FS_FC = 8.5, 10.0, 8.0
# nothing anywhere in either figure is rendered below 8.0px.


def build(V):
    y0    = V["y0"]
    diag  = {}
    def Y(yd): return y0 + (yd - YMID) * YS
    def est_y(x): return Y(g.estimate(xd(x)))

    # ---------- strands ----------
    strand_svg = ""
    strand_bot = -1e9
    strand_pts = []            # every drawn strand sample, for collision tests
    for (nm, lane) in V["strands"]:
        col   = STRAND_COL[nm]
        dcol  = DCOL[col]; dop = DOP[col]
        dampm = dict(g.STRANDS and [(s[0], s[3]) for s in g.STRANDS])[nm] * DAMP_S
        xmg   = xm(dict([(s[0], s[5]) for s in g.STRANDS])[nm])
        appr  = xmg - APPR_M[nm]
        gaps  = GAPS_M.get(nm, [])
        segs, envs = [], []
        cur, et, eb = [], [], []
        x = float(XS_M)
        while x <= xmg:
            if any(a <= x <= b for (a, b) in gaps):
                if len(cur) > 1: segs.append(cur); envs.append((et, eb))
                cur, et, eb = [], [], []
                x += 1.2; continue
            if x < appr:
                base, taper = float(lane), 1.0
            else:
                t = (x - appr) / float(xmg - appr)
                base = lane + (est_y(xmg) - lane) * g.smoothstep(0, 1, t)
                taper = 1.0 - 0.5 * t
            D  = xd(x)
            r  = resolve_m(nm, x)
            sl = g.slow_w(nm, D)
            fe = g.FASTAMP[nm] * g.fast_env(nm, D)
            yy = base + dampm * (sl + fe * g.carrier(nm, D) * r) * taper
            cur.append((x, yy)); strand_bot = max(strand_bot, yy)
            strand_pts.append((x, yy))
            if fe > 0.01 and r < 0.98:
                h   = dampm * fe * (1.0 - r) * taper * ENV_SCALE_M
                mid = base + dampm * sl * taper
                et.append((x, mid - h)); eb.append((x, mid + h))
                strand_bot = max(strand_bot, mid + h)
                strand_pts.append((x, mid + h))
            x += walk_m(nm, x)
        cur.append((xmg, est_y(xmg))); segs.append(cur); envs.append((et, eb))
        for (a, b) in envs:
            if len(a) > 2:
                strand_svg += '<path d="%s" fill="%s" stroke="none" opacity="%.2f"/>\n' % (
                    poly(a + list(reversed(b))) + " Z", dcol, ENV_OP_M)
        d = " ".join(poly(s) for s in segs if len(s) > 1)
        strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="1.0" opacity="%.2f"/>\n' % (
            d, dcol, min(0.55, dop * 1.35))
        strand_svg += '<circle cx="%.1f" cy="%.1f" r="1.1" fill="%s" opacity="0.4"/>\n' % (
            xmg, est_y(xmg), dcol)
    diag["strand_bottom"] = strand_bot

    # ---------- family labels ----------
    fam_svg = ""
    for (fam, text, ly) in V["fams"]:
        fam_svg += '<text x="%d" y="%d" class="rvm-t" font-size="%.1f" fill="%s">%s</text>\n' % (
            X_LEFT_M, ly, FS_FAM, g.FAM_INK[fam], text)

    # ---------- true state ----------
    tsd = poly([(x, Y(g.true_state(xd(x)))) for x in
                [X_LEFT_M + i * 0.8 for i in range(int((225.5 - X_LEFT_M) / 0.8) + 1)]])

    # ---------- individual-experience ticks ----------
    ask_svg = ""
    if V["ticks"]:
        drops = []
        for tx in V["ticks"]:
            ry = Y(g.true_state(xd(tx)))
            ask_svg += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" opacity="0.55"/>' % (
                tx, ry, tx, ry - TICK_STEM_M, TICK_COL)
            ask_svg += '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.7"/>\n' % (
                tx, ry - TICK_DROP_M, TICK_R, TICK_COL)
            drops.append((tx, ry - TICK_DROP_M))
        # her label goes in the open band between the strand block and the
        # droplet row, 5px directly above one of the real droplets --- so that
        # droplet is the nearest mark on the page to the words. No leader, no
        # drawn miniature (v20 deleted that and it stays deleted).
        #
        # Which droplet is chosen is not a free hand: the placement is searched.
        # Every (droplet x alignment x rise) is scored on its worst clearance to
        # (a) the drawn strands above, (b) the top of the sampling band below,
        # (c) every OTHER droplet, and (d) the intervention swipe. The winner is
        # the one that sits CLOSEST above its droplet while clearing everything
        # by CLEAR px --- so the anchor droplet is always the nearest mark to
        # the words, which is the whole point of the placement. This is what
        # keeps the label out of the fan where the strands dive into the
        # estimate; the first render put it straight through them.
        CLEAR = 4.0
        w  = tw(g.TICK_LBL, FS_TICK)
        NXs = xm(float(g.NUDGE_X))
        def bandtop(x): return est_y(x) - g.err_env(xd(x)) * YS
        best = None
        for rise in [5.0 + i for i in range(16)]:
            for (ax, ay) in drops:
                for lx in (ax - w / 2.0, ax + 4.0, ax - 4.0 - w,
                           float(X_LEFT_M), VIEW_W - 4.0 - w):
                    if lx < X_LEFT_M or lx + w > VIEW_W - 4: continue
                    ly   = ay - rise
                    box  = (lx - 2, lx + w + 2, ly - FS_TICK - 1, ly + 2)
                    above = [p[1] for p in strand_pts if box[0] <= p[0] <= box[1]]
                    c = [box[2] - max(above)] if above else [99.0]
                    c.append(min(bandtop(box[0] + i * (box[1] - box[0]) / 24.0)
                                 for i in range(25)) - box[3])
                    for (ox, oy) in drops:
                        if ox == ax: continue
                        if box[0] <= ox <= box[1]:
                            c.append(abs(oy - ly) - 6.0)
                            c.append(rise - 1.0)   # anchor must stay the nearest
                    if box[0] <= NXs <= box[1]:
                        c.append(-99.0)            # never sit across the swipe
                    s = min(c)
                    if s >= CLEAR and (best is None or s > best[0]):
                        best = (s, lx, ly, ax, ay, rise)
            if best: break                          # smallest rise that works
        assert best, "no clear pocket for the tick label"
        _, lx, ly, ax, ay, rise = best
        ask_svg += '<text x="%.1f" y="%.1f" class="rvm-t" font-size="%.1f" fill="%s">%s</text>\n' % (
            lx, ly, FS_TICK, TICK_COL, g.TICK_LBL)
        diag["tick_label"] = (lx, ly, w, best[0], ax, rise)

    # ---------- estimate + sampling band ----------
    bxs = [X_LEFT_M + i * 0.8 for i in range(int((225.2 - X_LEFT_M) / 0.8) + 1)]
    top = [(x, est_y(x) - g.err_env(xd(x)) * YS) for x in bxs]
    bot = [(x, est_y(x) + g.err_env(xd(x)) * YS) for x in reversed(bxs)]
    band = poly(top + bot) + " Z"
    band_bottom = max(p[1] for p in bot)
    band_top    = min(p[1] for p in top)
    diag["band"] = (band_top, band_bottom)

    E_START = xm(110.0)
    epts = [(x, est_y(x)) for x in bxs if x >= E_START]
    ebounds = [xm(b) for b in (110, 210, 320, 450, 600, 847)]
    ewid    = [1.2, 1.5, 1.8, 2.2, 2.6]
    est_svg = ""
    for i in range(len(ewid)):
        seg = [p for p in epts if ebounds[i] <= p[0] <= ebounds[i + 1]]
        if len(seg) > 1:
            est_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"/>\n' % (
                poly(seg), ewid[i])

    # ---------- text rows below the drawing ----------
    # Order: her intervention sentence first, so it stays the nearest text to
    # the swipe's foot (the swipe is then extended down to lean into it, as it
    # does in v22); then the grey curve label, then the navy one.
    row = math.ceil(band_bottom) + 12
    SENT_Y1, SENT_Y2 = row, row + 12
    TS_LBL_Y = SENT_Y2 + 18
    ES_LBL_Y = TS_LBL_Y + 12 + 12
    lbl_svg = ""
    lbl_svg += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="rgba(17,17,24,0.6)">a person&#39;s true internal state</text>\n' % (
        X_LEFT_M, TS_LBL_Y, FS_LBL)
    lbl_svg += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="rgba(17,17,24,0.6)">(that we can&#39;t directly see)</text>\n' % (
        X_LEFT_M, TS_LBL_Y + 12, FS_LBL)
    lbl_svg += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="#1a2c6b">our best guess at the internal state</text>\n' % (
        X_LEFT_M, ES_LBL_Y, FS_LBL)
    lbl_svg += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="#1a2c6b">(triangulated from many diverse signals)</text>\n' % (
        X_LEFT_M, ES_LBL_Y + 12, FS_LBL)

    # ---------- the intervention swipe ----------
    NX  = xm(float(g.NUDGE_X))
    mky = est_y(NX); gry = Y(g.true_state(xd(NX)))
    ee  = g.err_env(xd(NX)) * YS
    F_TOP = min(mky - ee, gry) - F_PAD_TOP_M
    F_BOT = SENT_Y1 - FS_SENT * 0.78 - 3.0        # leans into her sentence
    nudge_svg = '<rect x="%.2f" y="%.2f" width="%.1f" height="%.2f" rx="%.1f" fill="%s" opacity="%.2f"/>' % (
        NX - F_W_M / 2, F_TOP, F_W_M, F_BOT - F_TOP, F_W_M / 2, INT_COL, g.F_OP)
    nudge_svg += '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.1" opacity="%.2f"/>' % (
        NX, F_TOP + F_CORE_IN_M, NX, F_BOT - F_CORE_IN_M, INT_COL, g.F_CORE_OP)
    diag["swipe"] = (NX, F_TOP, F_BOT)

    sent_svg = ('<g class="rvm-t" fill="%s" text-anchor="middle" font-weight="700">'
                '<text x="%.1f" y="%.0f" font-size="%.1f">the right intervention for the right person,</text>'
                '<text x="%.1f" y="%.0f" font-size="%.1f">in the right context, at the right time</text></g>\n') % (
        INT_COL, VIEW_W / 2.0, SENT_Y1, FS_SENT, VIEW_W / 2.0, SENT_Y2, FS_SENT)

    # ---------- forecast ----------
    E_END = 224.5
    ey    = est_y(E_END)
    good_y = ey - 22.0
    less_y = ey + 10.0
    cone = "M %.1f %.1f L %d %.1f L %d %.1f L %.1f %.1f Z" % (
        NOW_X_M + 2, ey - 2.0, FUT_X_M, good_y - 15, FUT_X_M, good_y + 15, NOW_X_M + 2, ey + 2.0)
    better = "M %.1f %.1f Q %.1f %.1f %d %.1f" % (E_END, ey, 275.0, ey - 19.0, FUT_X_M, good_y)
    fc  = '<path d="%s" fill="rgba(26,44,107,0.07)" stroke="none"/>\n' % cone
    fc += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="1.3" stroke-dasharray="3 3" opacity="0.7"/>\n' % better
    if V["ghost"]:
        ghost = "M %.1f %.1f Q %.1f %.1f %d %.1f" % (E_END, ey, 275.0, ey + 9.0, FUT_X_M, less_y)
        fc += '<path d="%s" fill="none" stroke="%s" stroke-width="1" stroke-dasharray="1.5 3" opacity="%.2f"/>\n' % (
            ghost, GHOST_COL, g.GHOST_OP)
    fc += '<circle cx="%d" cy="%.1f" r="5.5" fill="none" stroke="#FFFF77" stroke-width="2.6" opacity="0.9"/>' % (FUT_X_M, good_y)
    fc += '<circle cx="%d" cy="%.1f" r="2.2" fill="#1a2c6b"/>\n' % (FUT_X_M, good_y)
    FLX = NOW_X_M + 2
    fc += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" font-weight="700" fill="#111118">intervention</text>\n' % (
        FLX, good_y - V["int_dy"], FS_INT)
    if V["ghost"]:
        # her one line, broken (not reworded) so it fits right of 'now'
        fc += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="rgba(17,17,24,0.7)">a higher likelihood of</text>\n' % (
            FLX, good_y - 28, FS_FC)
        fc += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="rgba(17,17,24,0.7)">the desired outcome</text>\n' % (
            FLX, good_y - 19, FS_FC)
        fc += '<circle cx="%d" cy="%.1f" r="2.2" fill="none" stroke="rgba(17,17,24,0.4)" stroke-width="1.1"/>\n' % (FUT_X_M, less_y)
        fc += '<text x="%d" y="%.0f" class="rvm-t" font-size="%.1f" fill="%s" text-anchor="end">without intervention</text>\n' % (
            VIEW_W - 6, less_y + 12, FS_FC, GHOST_COL)
    diag["forecast"] = (ey, good_y, less_y)

    # ---------- nested timescale brackets ----------
    UNIT_T = dict(g.TS_UNITS)
    # the bracket block starts one clear row under the last text row, so the
    # arms never crowd her estimate label's descenders
    ts_top = int(ES_LBL_Y + 12 + 14); step = V["ts_step"]
    br_svg = ""; un_svg = ""
    prev_l, prev_r = NOW_X_M, NOW_X_M
    floors = []
    for i, lab in enumerate(V["units"]):
        t  = UNIT_T[lab]
        xl = min(NOW_X_M - PXDEC_M * math.log10(1.0 + t), NOW_X_M - ARM_L_MIN_M)
        xr = max(NOW_X_M + PXDECF_M * math.log10(1.0 + t), NOW_X_M + ARM_R_MIN_M)
        xl = max(xl, X_LEFT_M); xr = min(xr, FUT_X_M)
        assert xl < prev_l and xr > prev_r, "nesting violated at %s" % lab
        prev_l, prev_r = xl, xr
        fy = ts_top + TS_BASE_M + i * step
        floors.append(fy)
        br_svg += '<path d="M %.1f %d V %d H %.1f V %d"/>\n' % (xl, ts_top, fy, xr, ts_top)
        un_svg += '<text x="%.1f" y="%d" font-size="%.1f">%s</text>\n' % (
            xl + 3, fy - 3, FS_UNIT, lab)
    BR_FLOOR = floors[-1]
    H = BR_FLOOR + 12

    now_svg  = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="rgba(17,17,24,0.35)" stroke-width="1"/>' % (
        NOW_X_M, TOP_PAD_M + 14, NOW_X_M, BR_FLOOR + 8)
    now_svg += '<text x="%d" y="%d" class="rvm-t" font-size="%.1f" fill="rgba(17,17,24,0.6)" text-anchor="middle">now</text>' % (
        NOW_X_M, TOP_PAD_M + 10, FS_NOW)

    aria = ("A faint grey true-state curve and a bold ink-blue estimate with a "
            "sampling-uncertainty band, fed by signal strands that fold into it; "
            "a purple highlighter swipe marks an intervention, and past the 'now' "
            "divider the estimate projects a forecast cone toward an outcome; "
            "nested timescale brackets straddle 'now'.")

    svg = '''<svg viewBox="0 0 {w} {h}" role="img" aria-label="{aria}">
  <!-- no paper fill, no grid: see approach.py. The mismatch is worse here —
       this figure is 336 units drawn into a box up to 420px wide, so its own
       ruling would render ~1.25x the page's. -->

  <!-- the top {tp}px are empty on purpose: the room her title drops into -->

  <path d="{band}" fill="rgba(26,44,107,0.09)" stroke="none"/>
  <path d="{tsd}" fill="none" stroke="rgba(17,17,24,0.30)" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/>

  {strands}
  {fams}
  {ask}
  {est}
  {nudge}
  {fc}
  {now}
  {sent}
  {lbl}

  <g fill="none" stroke="#1a2c6b" stroke-width="1.1">
    {br}
  </g>
  <g class="rvm-t" fill="#1a2c6b" text-anchor="start">
    {un}
  </g>
</svg>'''.format(w=VIEW_W, h=H, k=V["key"], tp=TOP_PAD_M, aria=aria,
                 band=band, tsd=tsd, strands=strand_svg, fams=fam_svg,
                 ask=ask_svg, est=est_svg, nudge=nudge_svg, fc=fc,
                 now=now_svg, sent=sent_svg, lbl=lbl_svg, br=br_svg, un=un_svg)
    diag["H"] = H
    diag["rows"] = (SENT_Y1, SENT_Y2, TS_LBL_Y, ES_LBL_Y)
    return svg, H, diag


# Shabnam chose variant A (moderate reduction) over B (aggressive reduction)
# out of the mockup's side-by-side comparison; only A ships. build()'s `svg`
# is already the standalone <svg viewBox="0 0 336 {H}" ...>...</svg> element
# --- no page wrapper, no <style> block --- so it needs no further trimming
# to become the production fragment.
_svgA, _HA, _diagA = build(A)

# Applied here, not at a file-write step, so svg_fragment() returns the same
# bytes regardless of how it is consumed. (This file's strings are already
# pure ASCII, so the transform is a no-op; kept for parity with approach.py
# in case that ever changes.)
SVG = _svgA.encode("ascii", "xmlcharrefreplace").decode("ascii")


def svg_fragment():
    """Return the mobile approach figure (variant A) as a standalone <svg> fragment."""
    return SVG


if __name__ == "__main__":
    print(svg_fragment())
