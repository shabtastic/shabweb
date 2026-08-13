import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/docs/superpowers/mockups/homepage-research-viz/research-viz-lofi-v16.html"

# ---------- v16 tuning: Shabnam's markup of v15a ----------
# Every string drawn in the figure is hers, verbatim. TICK_LBL is the one she
# flagged as placeholder wording, to be replaced later.
#
# 1. The inter-signal web is gone entirely — "get rid of all the callout lines"
#    — as is the dotted leader that ran from the estimate to the intervention
#    arrow. The pink arrow itself stays, and now lands on a marker.
# 2. The blue sampling ticks are untouched.
# 3. A solid pink dot sits on the estimate where the arrow tip arrives: the
#    intervention happens here, to the estimate, at a moment.
# 4. Her labels sit against their referents with no leader lines.
MARK_R      = 6.5          # radius of the pink intervention marker on the estimate
MARK_GAP    = 0.0          # arrow tip meets the marker's edge exactly
LBL_FS      = 7.5          # her curve labels — 7.5 not 8 so the true-state
                           # label clears the x=214 sampling tick horizontally
                           # (its x is pinned at the curve's start, x=70)
FAM_FS      = 9.0          # family labels in the left margin
FAM_X       = 6            # left margin — strands start at x=70
# Darkened family colours for text. Same values the series used in v11/v12/v14a,
# and the same move the site makes for laser lemon (#FFFF77 displays as #9a7c00).
# Contrast on #f5f2ec: 4.8:1 and 4.5:1.
FAM_INK     = {"body": "#b0475f", "behavior": "#a35e1c"}
# v16: the behaviour family's #FFAE77 was washing out — at 0.32 opacity it
# composites to ~1.17:1 against the paper, against the physiology family's
# ~1.30:1. A darker, more saturated draw colour at slightly higher opacity puts
# it at ~1.47:1: clearly legible, still plainly subordinate to the two curves.
DRAWCOL     = {"#FFAE77": "#D9822B"}
DRAWOP      = {"#FFAE77": 0.42}
STRAND_OP   = 0.32         # default non-hero strand opacity
TICK_LBL    = "individual experience"   # placeholder wording for the blue ticks
TICK_LBL_X  = 464          # right edge, 6px left of the x=470 tick
TICK_LBL_Y  = 209

def poly(pts):
    s = "M %.1f %.1f" % pts[0]
    for p in pts[1:]:
        s += " L %.1f %.1f" % p
    return s

def smoothstep(a, b, x):
    if x <= a: return 0.0
    if x >= b: return 1.0
    t = (x - a) / (b - a)
    return t * t * (3 - 2 * t)

def rnd(i):
    fr = math.sin(i * 12.9898) * 43758.5453
    return fr - math.floor(fr)

def gau(p, c, w):
    return math.exp(-((p - c) / w) ** 2)

def shape(name, x, xs):
    d = x - xs
    if name == "heart":
        per = 22.0; p = (d % per) / per
        return (-1.0*gau(p,0.20,0.05) + 0.35*gau(p,0.28,0.045) - 0.15*gau(p,0.12,0.04) - 0.22*gau(p,0.60,0.09))
    if name == "breath":
        return math.sin(2*math.pi*d/42.0)
    if name == "skin":
        v = 0.30*math.sin(2*math.pi*d/120.0)
        for c in (170, 300, 420):
            dt = x - c
            if dt >= 0:
                v += 0.9*math.exp(-dt/45.0)*(1 - math.exp(-dt/6.0))
        return v
    if name == "eyes":
        seg = int(math.floor(d/11.0))
        return rnd(seg)*1.8 - 0.9 + 0.12*math.sin(2*math.pi*d/4.0)
    if name == "behavior":
        env = (0.5 + 0.5*math.sin(2*math.pi*d/70.0)); env *= env
        return env*math.sin(2*math.pi*d/13.0 + 1.4*math.sin(2*math.pi*d/47.0))
    if name == "movement":
        v = 0.0
        for c in (170, 260, 330):
            v += math.exp(-((x-c)/20.0)**2)*math.sin(2*math.pi*(x-c)/11.0)
        return v
    if name == "choices":
        lvl = -0.4
        for (jx, jl) in [(70,-0.4),(230,0.5),(360,1.0),(520,-0.2),(640,0.6)]:
            if x >= jx: lvl = jl
        return lvl
    return 0.0

NUDGE_X = 600
NOW_X   = 850          # boundary between observed past and forecast future

# ---------- v14a: WARPED (log-like) TIME AXIS ----------
# One shared nonlinear time axis. x maps to "seconds before now" through a log,
# so recent time is stretched near 'now' and the deeper past is progressively
# compressed toward the left edge. The left edge of the observed span is one
# year ago; 'now' is x = NOW_X.
SPAN_SECONDS = 3.156e7        # one year across the observed span
X_LEFT       = 60             # left edge of the observed span
PXDEC        = (NOW_X - X_LEFT) / math.log10(1.0 + SPAN_SECONDS)   # px per decade
PXDEC_F      = 160.0 / math.log10(1.0 + SPAN_SECONDS)              # px per decade, forecast side

def tau_of_x(x):                      # seconds before 'now' at pixel x
    return 10.0 ** ((NOW_X - x) / PXDEC) - 1.0

def x_of_tau(t):                      # pixel for t seconds before 'now'
    return NOW_X - PXDEC * math.log10(1.0 + max(t, 0.0))

def x_of_tau_fwd(t):                  # pixel for t seconds after 'now'
    return NOW_X + PXDEC_F * math.log10(1.0 + max(t, 0.0))

def sec_per_px(x):                    # local compression: seconds covered by one px
    return math.log(10.0) / PXDEC * (1.0 + tau_of_x(x))

# Characteristic period of each signal, in real seconds. This is what decides
# where its fine structure is still resolvable on the warped axis.
PERIOD = {"heart": 1.0, "eyes": 0.35, "breath": 4.0, "skin": 90.0,
          "movement": 9.0, "behavior": 150.0, "choices": 9000.0}
# amplitude of the fast (oscillatory) part; 0 = the strand carries no fast part
FASTAMP = {"heart": 0.95, "eyes": 0.90, "breath": 1.00, "skin": 0.35,
           "movement": 1.00, "behavior": 1.00, "choices": 0.0}
PX_LO, PX_HI = 1.3, 4.5               # px per cycle: below LO invisible, above HI fully drawn

def px_per_cycle(nm, x):
    return PERIOD[nm] / sec_per_px(x)

def resolve(nm, x):                   # 0 = unresolvable smear, 1 = fully drawn
    if FASTAMP[nm] <= 0: return 1.0
    return smoothstep(PX_LO, PX_HI, px_per_cycle(nm, x))

# slow, event-scale structure keeps its pixel positions (it is resolvable
# everywhere it is drawn); only the fast carriers live in warped time.
SKIN_RESP    = (292.0, 478.0, 620.0)
MOVE_BURST   = (357.0, 543.0, 701.0)
CHOICE_STEPS = [(70, -0.4), (153, 0.2), (246, 0.6), (347, 1.0), (519, -0.2), (685, 0.6)]

ENV_SCALE = 0.55   # envelope band height, as a fraction of the fast amplitude
ENV_OP    = 0.11   # envelope band opacity
DRIFT     = {"heart": 0.30, "eyes": 0.26, "breath": 0.32, "skin": 0.34,
             "movement": 0.30, "behavior": 0.30, "choices": 0.0}
DRIFT_PH  = {"heart": 0.0, "eyes": 1.9, "breath": 3.4, "skin": 0.9,
             "movement": 2.6, "behavior": 4.4, "choices": 0.0}

def drift(nm, x):
    """Slow baseline trend — the one thing that stays legible at every scale, so
    the compressed past reads as summary rather than as a flat line."""
    d = DRIFT[nm]
    if d <= 0: return 0.0
    return d*(math.sin(2*math.pi*(x-70)/260.0 + DRIFT_PH[nm])
              + 0.45*math.sin(2*math.pi*(x-70)/97.0 + 2*DRIFT_PH[nm]))

def slow_w(nm, x):
    if nm == "skin":
        v = drift(nm, x)
        for c in SKIN_RESP:
            dt = x - c
            if dt >= 0: v += 0.9 * math.exp(-dt / 70.0) * (1 - math.exp(-dt / 12.0))
        return v
    if nm == "choices":
        lvl = -0.4
        for (jx, jl) in CHOICE_STEPS:
            if x >= jx: lvl = jl
        return lvl + drift(nm, x)
    return drift(nm, x)

def fast_env(nm, x):                  # pixel-space envelope of the fast carrier
    if nm == "movement":
        e = 0.0
        for c in MOVE_BURST: e += math.exp(-((x - c) / 26.0) ** 2)
        return min(1.0, e)
    if nm == "behavior":
        e = 0.5 + 0.5 * math.sin(2 * math.pi * (x - 70) / 300.0)
        return e * e
    return 1.0

def carrier(nm, x):                   # the fast part, in warped time
    ph = tau_of_x(x) / PERIOD[nm]
    if nm == "heart":
        p = ph % 1.0
        return (-1.0*gau(p,0.20,0.05) + 0.35*gau(p,0.28,0.045)
                - 0.15*gau(p,0.12,0.04) - 0.22*gau(p,0.60,0.09))
    if nm == "breath":   return math.sin(2 * math.pi * ph)
    if nm == "eyes":     return rnd(int(math.floor(ph))) * 1.8 - 0.9
    if nm == "skin":     return 0.30 * math.sin(2 * math.pi * ph)
    if nm == "movement": return math.sin(2 * math.pi * ph)
    if nm == "behavior": return math.sin(2 * math.pi * ph)
    return 0.0

def walk_step(nm, x):                 # adaptive sampling: >=5 samples per drawn cycle
    if FASTAMP[nm] <= 0: return 3.0
    pc = px_per_cycle(nm, x)
    if pc < PX_LO: return 3.0
    return min(3.0, max(0.5, pc / 5.0))

def rendered(nm, x):
    """The strand as actually drawn at x. The estimate is built from this, not
    from the underlying signal, so the figure stays compositional: the estimate
    can only inherit texture the axis was able to resolve."""
    return slow_w(nm, x) + FASTAMP[nm]*fast_env(nm, x)*carrier(nm, x)*resolve(nm, x)

# ---------- v12 tuning: timescale brackets, nested and anchored on 'now' ----------
# Every bracket straddles the 'now' divider. Left arm = how far back the signals
# at that rate reach (into the observed span); right arm = how far ahead a
# prediction made at that rate can see (into the forecast zone). Arms are
# asymmetric (the observed side of the figure is far wider than the forecast
# side) but the nesting order holds independently on BOTH sides of 'now'.
TS_TOP     = 398   # y where every bracket's vertical arms start
TS_BASE    = 14    # depth of the innermost (seconds) bracket
TS_STEP    = 13    # extra depth per nesting level
TS_LABEL_DX = 4    # label offset to the right of its own bracket's left arm
TS_LABEL_DY = 4    # label baseline above its own bracket floor
ARM_L_MIN   = 26   # floor so the innermost bracket stays readable under the warp
ARM_R_MIN   = 16
# v14a: the arms are no longer hand-placed — each one lands where its unit
# actually falls on the warped axis, back and forward. Under log time the five
# come out roughly evenly stepped instead of telescoping.
TS_UNITS = [("seconds", 1.0), ("hours", 3600.0), ("days", 86400.0),
            ("weeks", 604800.0), ("years", 3.156e7)]
TIMESCALES = [(lab,
               int(round(min(x_of_tau(t),     NOW_X - ARM_L_MIN))),
               int(round(max(x_of_tau_fwd(t), NOW_X + ARM_R_MIN))))
              for (lab, t) in TS_UNITS]
def true_state(x):
    ts = 250 + 20*math.sin(2*math.pi*(x-70)/540.0) + 8*math.sin(2*math.pi*(x-70)/210.0 + 0.8)
    ts -= 24*smoothstep(NUDGE_X, 810, x)
    return ts

FAMCOL = {"body": "#FF7792", "behavior": "#FFAE77", "asking": "#7777FF"}
SLOT   = {"body": -9, "behavior": 0, "asking": 9}

PJ_X   = [250, 560, 700]
D_PAR  = 3.2
EYES_X = 460
D_EYE  = 6.5

GAPS = {"skin": [(330, 370)], "movement": [(110, 150)]}
# v14a: every strand still spans the full observed width, but the fold into the
# estimate is re-ordered by timescale — the slowest signal folds in first, the
# fastest last — so each strand stays on its own lane long enough for its fine
# structure to become resolvable near 'now' before it merges.
# v15: with the margin labels gone the lanes reclaim that room — 21px apart
# instead of 18, which gives the resolved detail near 'now' space to be read.
# The gap between the two families is unchanged.
STRANDS = [
    ("heart",   "#FF7792",  78, 12, 70, 820, False),
    ("eyes",    "#FF7792",  99,  6, 70, 842, True),
    ("skin",    "#FF7792", 120,  8, 70, 768, False),
    ("breath",  "#FF7792", 141,  7, 70, 796, False),
    ("behavior","#FFAE77", 173,  9, 70, 690, False),
    ("movement","#FFAE77", 194,  8, 70, 730, False),
    ("choices", "#FFAE77", 215,  9, 70, 640, False),
]
# length of the bend into the estimate — long enough that the merges read as a
# staggered fan rather than a wall; detail keeps being drawn through the bend,
# just at half amplitude
APPR = {"heart": 62, "eyes": 52, "skin": 75, "breath": 70,
        "behavior": 85, "movement": 80, "choices": 90}
LANE = {nm: y0 for (nm, col, y0, damp, xs, xm, hero) in STRANDS}

MEAN = {}
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
    samp = list(range(xm, 847, 2)) or [xm]
    MEAN[nm] = sum(rendered(nm, x) for x in samp) / len(samp)

E_MIN = 2.0
def err_env(x):
    h = E_MIN
    for jx in PJ_X:
        h += D_PAR*(1 - smoothstep(jx-22, jx+22, x))
    h += D_EYE*(1 - smoothstep(EYES_X-22, EYES_X+22, x))
    h += 2.0*math.exp(-((x-350)/26.0)**2)
    h += 2.0*math.exp(-((x-130)/24.0)**2)
    return h

def wander(x):
    return 0.62*math.sin(2*math.pi*(x-70)/150.0) + 0.4*math.sin(2*math.pi*(x-70)/83.0 + 1.2)

def texture(x):
    t = 0.0
    for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
        gt = smoothstep(xm-22, xm+22, x)
        if gt > 0:
            t += 0.8*(rendered(nm, x) - MEAN[nm])*gt
    return t*(1 - 0.6*smoothstep(NUDGE_X, 790, x))

def estimate(x):
    return true_state(x) + err_env(x)*wander(x) + texture(x)

# true state fades as it approaches 'now' (we never see it in the future)
ts_d = poly([(x, true_state(x)) for x in range(70, 843, 4)])

# ---------- inter-signal web ----------
# v16: removed outright. Every arc between strands — solid, dotted, and the
# heavy gaze-choice one — is gone at her instruction, along with the arc helper
# that drew them. The couplings are still implied by the strands folding into
# one estimate; nothing is drawn to assert them.

# ---------- strands, drawn on the warped axis ----------
# Two layers per strand: the line itself, whose fast structure is only drawn
# where the axis still resolves it, and a faint envelope band standing in for
# the fast structure that exists but is compressed past the point of drawing it.
strand_svg = ""
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
    dcol = DRAWCOL.get(col, col)          # v16: darkened draw colour for the
    dop  = DRAWOP.get(col, STRAND_OP)     # washed-out behaviour family
    approach = xm - APPR[nm]
    gaps = GAPS.get(nm, [])
    segs = []; envs = []
    cur = []; env_t = []; env_b = []
    x = float(xs)
    while x <= xm:
        if any(a <= x <= b for (a, b) in gaps):
            if len(cur) > 1: segs.append(cur); envs.append((env_t, env_b))
            cur = []; env_t = []; env_b = []
            x += 3.0; continue
        if x < approach:
            base = y0; taper = 1.0
        else:
            t = (x - approach)/float(xm - approach)
            base = y0 + (estimate(xm) - y0)*smoothstep(0, 1, t)
            taper = 1.0 - 0.5*t
        r  = resolve(nm, x)
        sl = slow_w(nm, x)
        fe = FASTAMP[nm]*fast_env(nm, x)
        cur.append((x, base + damp*(sl + fe*carrier(nm, x)*r)*taper))
        if fe > 0.01 and r < 0.98:
            h = damp*fe*(1.0 - r)*taper*ENV_SCALE
            mid = base + damp*sl*taper
            env_t.append((x, mid - h)); env_b.append((x, mid + h))
        x += walk_step(nm, x)
    cur.append((xm, estimate(xm))); segs.append(cur); envs.append((env_t, env_b))
    for (et, eb) in envs:
        if len(et) > 2:
            strand_svg += '<path d="%s" fill="%s" stroke="none" opacity="%.2f"/>\n' % (
                poly(et + list(reversed(eb))) + " Z", dcol, ENV_OP)
    d = " ".join(poly(s) for s in segs if len(s) > 1)
    w, op = (1.5, dop*1.9) if hero else (1.0, dop)
    strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>\n' % (d, dcol, w, op)
    ex, ey = xm, estimate(xm)
    if hero:
        strand_svg += '<circle cx="%d" cy="%.1f" r="5.5" fill="%s" opacity="0.85"/>' % (ex, ey, dcol)
        strand_svg += '<circle cx="%d" cy="%.1f" r="7.7" fill="none" stroke="%s" stroke-width="1" opacity="0.6"/>\n' % (ex, ey, dcol)
    else:
        strand_svg += '<circle cx="%d" cy="%.1f" r="1.5" fill="%s" opacity="0.4"/>\n' % (ex, ey, dcol)

# ---------- parity junction trios ----------
# v15a: no dot trios. PJ_X is still what err_env tightens on, so parity reads
# through the band and through the strands folding in identically.
junc_svg = ""

# ---------- asking droplets ----------
drops = [(150,1.6),(214,1.5),(300,1.6),(346,1.7),(470,1.5),(640,1.7),(732,1.6),(792,1.7)]
ask_svg = ""
for (dx, r) in drops:
    dy = estimate(dx)
    ask_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.2" opacity="0.55"/>' % (dx, dy-20, dx, dy-8)
    ask_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="#7777FF" opacity="0.7"/>\n' % (dx, dy-6, r)
# v16: one label for the ticks, sitting against the x=470 one — the only pocket
# in the middle band with real clearance (~8px to the nearest strand) — with no
# leader line. Placeholder wording, hers to replace.
ask_svg += '<text x="%d" y="%d" class="rv16-svgtext" font-size="%.1f" fill="#7777FF" text-anchor="end">%s</text>\n' % (
    TICK_LBL_X, TICK_LBL_Y, LBL_FS - 1.0, TICK_LBL)

# ---------- estimate line ----------
est_pts = [(x, estimate(x)) for x in range(110, 847, 3)]
bounds = [110, 210, 320, 450, 600, 847]
widths = [1.8, 2.6, 3.4, 4.4, 4.8]
est_svg = ""
for i in range(len(widths)):
    lo, hi = bounds[i], bounds[i+1]
    seg = [p for p in est_pts if lo <= p[0] <= hi]
    est_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"/>\n' % (poly(seg), widths[i])

bx = list(range(110, 847, 3))
def band_path(scale):
    top = [(x, estimate(x) - err_env(x)*scale) for x in bx]
    bot = [(x, estimate(x) + err_env(x)*scale) for x in reversed(bx)]
    return poly(top + bot) + " Z"
band_outer = band_path(1.0)
band_inner = band_path(0.55)

# ---------- intervention arrow + marker ----------
# v13: markedly smaller than v12's chunky open chevron, with a clean filled
# triangular head.
# v16: it no longer points at the true state — it points at a solid pink dot ON
# the estimate, which is the thing we actually act through. The tip meets the
# marker's edge. The dotted leader that used to run from the estimate back to
# the arrow tail is gone with the rest of the callout line-work.
ARR_LEN   = 30     # shaft length in px (v12: 46)
ARR_W     = 1.4    # shaft stroke width (v12: 3)
mark_y   = estimate(NUDGE_X)
arr_tip  = mark_y + MARK_R + MARK_GAP
arr_tail = arr_tip + ARR_LEN
nudge_svg = '<circle cx="%d" cy="%.1f" r="%.1f" fill="#FF7792"/>' % (NUDGE_X, mark_y, MARK_R)
nudge_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#FF7792" stroke-width="%.1f" marker-end="url(#nud13)"/>' % (
    NUDGE_X, arr_tail, NUDGE_X, arr_tip, ARR_W)
link_svg = ''

# ---------- FORECAST: prediction of the outcome, and how the nudge moves it ----------
E_END_X = 846
ey = estimate(E_END_X)
FUT_X = 1010
good_y = ey - 40      # better outcome (nudge worked): trajectory improves
less_y = ey + 18      # lesser outcome (no nudge): drifts worse
# forecast cone (belongs to the estimate; widens into the future)
cone = "M 852 %.1f L %d %.1f L %d %.1f L 852 %.1f Z" % (ey-3.5, FUT_X, good_y-26, FUT_X, good_y+26, ey+3.5)
# actual forecast, post-nudge, bending to the better outcome
better = "M %d %.1f Q %d %.1f %d %.1f" % (E_END_X, ey, 930, ey-34, FUT_X, good_y)
# ghost forecast, without the nudge, drifting to a lesser outcome
ghost  = "M %d %.1f Q %d %.1f %d %.1f" % (E_END_X, ey, 930, ey+16, FUT_X, less_y)
forecast_svg  = '<path d="%s" fill="rgba(26,44,107,0.07)" stroke="none"/>\n' % cone
forecast_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="1.6" stroke-dasharray="4 4" opacity="0.7"/>\n' % better
forecast_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="1.2" stroke-dasharray="2 4" opacity="0.32"/>\n' % ghost
# outcome markers
forecast_svg += '<circle cx="%d" cy="%.1f" r="9" fill="none" stroke="#FFFF77" stroke-width="4" opacity="0.9"/>' % (FUT_X, good_y)
forecast_svg += '<circle cx="%d" cy="%.1f" r="3.4" fill="#1a2c6b"/>\n' % (FUT_X, good_y)
forecast_svg += '<circle cx="%d" cy="%.1f" r="3.4" fill="none" stroke="rgba(17,17,24,0.4)" stroke-width="1.4"/>\n' % (FUT_X, less_y)
# fork labels. v13: Shabnam's wording, two stacked lines over the rising
# with-intervention path, ending at the outcome marker. Sized/positioned to sit
# entirely inside the forecast zone (right of 'now', clear of the cone's top edge).
# v16: three stacked lines, and line 1 now dominates — she asked for
# "intervention" bold and noticeably larger than what follows it. Lines 2-3 stay
# at 7.0 so the longest of them still ends inside the 1040-wide canvas.
FLBL_X   = 854     # just right of the 'now' divider
FLBL_FS  = 7.0     # sized so the longer line ends at ~1026, inside the canvas
FLBL_FS1 = 11.5    # line 1 — bold, and 1.6x lines 2-3
forecast_svg += '<text x="%d" y="%.0f" class="rv16-svgtext" font-size="%.1f" font-weight="700" fill="#111118">intervention &#8594;</text>' % (FLBL_X, good_y-58, FLBL_FS1)
forecast_svg += '<text x="%d" y="%.0f" class="rv16-svgtext" font-size="%.1f" fill="rgba(17,17,24,0.7)">a higher likelihood of the desired outcome</text>' % (FLBL_X, good_y-43, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv16-svgtext" font-size="%.1f" fill="rgba(17,17,24,0.7)">(internal state and/or behavior)</text>\n' % (FLBL_X, good_y-33, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv16-svgtext" font-size="7.5" fill="rgba(17,17,24,0.4)">without intervention</text>\n' % (905, less_y+14)

# 'now' divider between observed past and forecast future
now_svg  = '<line x1="%d" y1="44" x2="%d" y2="470" stroke="rgba(17,17,24,0.35)" stroke-width="1" stroke-dasharray="3 4"/>' % (NOW_X, NOW_X)
now_svg += '<text x="%d" y="40" class="rv16-svgtext" font-size="9" fill="rgba(17,17,24,0.6)" text-anchor="middle">now</text>' % NOW_X

# ---------- nested timescale brackets, anchored on 'now' ----------
bracket_svg = ""
tslabel_svg = ""
prev_l, prev_r = NOW_X, NOW_X
for i, (lab, xl, xr) in enumerate(TIMESCALES):
    assert xl < prev_l and xr > prev_r, "nesting violated at %s" % lab
    prev_l, prev_r = xl, xr
    fy = TS_TOP + TS_BASE + i*TS_STEP          # this bracket's floor
    bracket_svg += '<path d="M %d %d V %d H %d V %d"/>\n' % (xl, TS_TOP, fy, xr, TS_TOP)
    # v14a: the label rides its own bracket's back edge — under the warp that
    # edge is where the unit actually falls, so the brackets double as the axis.
    tslabel_svg += '<text x="%d" y="%d" font-size="9">%s</text>\n' % (
        xl + TS_LABEL_DX, fy - TS_LABEL_DY, lab)

# faint axis above the brackets, ticked where each unit lands on the warped axis
AXIS_Y = TS_TOP - 8
bracket_svg += '<path d="M %d %d H %d" stroke="rgba(17,17,24,0.22)" stroke-width="0.9"/>\n' % (
    X_LEFT, AXIS_Y, NOW_X)
for (lab, xl, xr) in TIMESCALES:
    bracket_svg += '<path d="M %d %d V %d" stroke="rgba(17,17,24,0.22)" stroke-width="0.9"/>\n' % (
        xl, AXIS_Y - 3, AXIS_Y + 3)

# ---------- v16: her labels ----------
# All four groups sit against their referent with no leader line. Placement is
# the only thing I chose; every word is hers.
#
# The family names go in the true left margin (x=6..60, the strands start at
# x=70), wrapped to two lines because one line of either at 9px is ~113px and
# the margin is 70px wide. Each pair is centred on its own block of lanes.
FAM_LBL = [
    ("body",     ["measurable", "physiology"], 105),   # lanes 78-141
    ("behavior", ["observable", "behavior"],   190),   # lanes 173-215
]
mylbl_svg = ""
for (fam, lines, y) in FAM_LBL:
    for i, ln in enumerate(lines):
        mylbl_svg += '<text x="%d" y="%d" class="rv16-svgtext" font-size="%.1f" fill="%s">%s</text>\n' % (
            FAM_X, y + i*12, FAM_FS, FAM_INK[fam], ln)

# The true state, named where its curve starts (x=70, y~256) — above it, in the
# clear band between the choices strand and the curve itself.
TS_LBL_X, TS_LBL_Y = 70, 234
for i, ln in enumerate(["a person&#39;s true internal state",
                        "(that we can&#39;t directly see)"]):
    mylbl_svg += '<text x="%d" y="%d" class="rv16-svgtext" font-size="%.1f" fill="rgba(17,17,24,0.6)">%s</text>\n' % (
        TS_LBL_X, TS_LBL_Y + i*12, LBL_FS, ln)

# The estimate, named below and left of where its line starts (x=110). y=310
# clears the widest part of the sampling band (its underside is at ~290 there).
EST_LBL_X, EST_LBL_Y = 70, 310
mylbl_svg += '<text x="%d" y="%d" class="rv16-svgtext" font-size="%.1f" fill="#1a2c6b">our best guess at the internal state (triangulated from many diverse signals)</text>\n' % (
    EST_LBL_X, EST_LBL_Y, LBL_FS)

HTML = '''<style>
  .rv16-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv16-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv16-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv16-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv16-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv16-wrap .option {{ margin-bottom:1.15rem; }}
  .rv16-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv16-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv16-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv16-wrap">
  <h2>v16 — your markup of v15a</h2>
  <p class="subtitle">Your pass, applied. The whole inter-signal web is gone, including the heavy gaze-choice arc and the dotted leader to the intervention arrow; the blue sampling ticks are untouched. The arrow now lands on a solid pink dot sitting on the estimate. Your labels are in verbatim, each against its referent with no leader line, and the forecast block leads with a bold, larger &#8220;intervention &#8594;&#8221;. Every word in the figure is yours; the tick label is the one you flagged as a placeholder to reword. The behaviour strands were also darkened &#8212; they were reading as near-invisible yellow.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">Signals &#8594; triangulated state &#8594; predicted outcome &#8594; better outcome</div>
        <div class="mockup-body">
          <svg viewBox="0 0 1040 500" role="img" aria-label="A faint true-state curve and a bold triangulated estimate fed by many signal strands; at 'now' the estimate projects a dotted forecast cone into the future toward an outcome marker, with a ghost path to a lesser outcome without the nudge and the actual path to the better outcome after nudging; five nested timescale brackets — seconds, hours, days, weeks, years — each straddle the 'now' divider, reaching back into the observed signals and forward into the forecast">
            <defs>
              <pattern id="gA11" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA11maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="nud13" markerWidth="6" markerHeight="6" refX="4.6" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 Z" fill="#FF7792" stroke="none"/></marker>
            </defs>
            <rect width="1040" height="500" fill="#f5f2ec"/>
            <rect width="1040" height="500" fill="url(#gA11)"/>
            <rect width="1040" height="500" fill="url(#gA11maj)"/>

            <path d="{band_outer}" fill="rgba(26,44,107,0.07)" stroke="none"/>
            <path d="{band_inner}" fill="rgba(26,44,107,0.09)" stroke="none"/>

            <path d="{ts_d}" fill="none" stroke="rgba(17,17,24,0.30)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>

            {strand_svg}
            {ask_svg}
            {est_svg}
            {junc_svg}
            {link_svg}
            {nudge_svg}

            <!-- forecast into the future zone, and the outcome -->
            {forecast_svg}
            {now_svg}

            <g class="rv16-svgtext" fill="#111118" text-anchor="middle">
              <text x="600" y="{nl1:.0f}" font-size="9.5">the right intervention for the right person,</text>
              <text x="600" y="{nl2:.0f}" font-size="9.5">in the right context, at the right time</text>
            </g>

            <!-- her labels, each against its referent, no leader lines -->
            {mylbl_svg}

            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              {bracket_svg}
            </g>
            <g class="rv16-svgtext" fill="#1a2c6b" text-anchor="start">
              {tslabel_svg}
            </g>
            <text x="60" y="484" class="rv16-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">the state and its signals evolve together at every timescale — how far back we&#39;ve measured, how far ahead we can see &#183; the state keeps changing even as we measure it</text>
          </svg>
        </div>
      </div>
      <div class="rv16-cap">what changed from v15a</div>
      <p class="rv16-mockup-title">Your markup, applied</p>
      <p class="rv16-mockup-desc">Gone: every arc between strands (solid and dotted, gaze-choice included) and the dotted leader from the estimate to the arrow — no callout line-work remains. Kept exactly: the blue sampling ticks, the warp, the strands, both curves, the band, the cone and its two ghost paths, the &#8216;now&#8217; divider, the brackets and their captions, and your intervention sentence. New: a solid pink dot on the estimate where the arrow tip arrives, your four label groups, and a third forecast line under a bold, larger first line. The behaviour strands are drawn in a darker orange (#D9822B at 0.42) so they hold the same visual weight as the physiology strands instead of fading into the paper; your family names use the darkened text colours the series already used for them (4.8:1 and 4.5:1 on the paper).</p>

    </div>
  </div>
</div>
'''.format(band_outer=band_outer, band_inner=band_inner, ts_d=ts_d,
           strand_svg=strand_svg, ask_svg=ask_svg, est_svg=est_svg,
           junc_svg=junc_svg, link_svg=link_svg, nudge_svg=nudge_svg,
           forecast_svg=forecast_svg, now_svg=now_svg, mylbl_svg=mylbl_svg,
           bracket_svg=bracket_svg, tslabel_svg=tslabel_svg,
           nl1=arr_tail+14, nl2=arr_tail+27)

with open(OUT, "w") as f:
    # v16: write pure ASCII — the em-dashes and arrows go out as numeric
    # entities, so the fragment renders the same in any shell, with or without a
    # charset declaration. No wording changes; only the encoding.
    f.write(HTML.encode("ascii", "xmlcharrefreplace").decode("ascii"))
print("wrote", OUT, len(HTML), "bytes")
print("intervention marker (%d, %.1f) r=%.1f  arrow tip %.1f  tail %.1f" % (
    NUDGE_X, mark_y, MARK_R, arr_tip, arr_tail))
print("estimate end(846)=%.1f  good_y=%.1f  less_y=%.1f  NOW_X=%d FUT_X=%d" % (ey, good_y, less_y, NOW_X, FUT_X))
for i, (lab, xl, xr) in enumerate(TIMESCALES):
    fy = TS_TOP + TS_BASE + i*TS_STEP
    print("  %-8s left arm %4d px  right arm %3d px  floor y=%d" % (lab, NOW_X-xl, xr-NOW_X, fy))
