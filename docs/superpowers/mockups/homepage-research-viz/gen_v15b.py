import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/docs/superpowers/mockups/homepage-research-viz/research-viz-lofi-v15b.html"

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
def arc(x1, y1, x2, y2, bow):
    mx, my = (x1+x2)/2.0, (y1+y2)/2.0
    dx, dy = x2-x1, y2-y1
    L = math.hypot(dx, dy) or 1.0
    cx, cy = mx - bow*dy/L, my + bow*dx/L
    return "M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x1, y1, cx, cy, x2, y2)

WEB = [
    ("skin~heart",     150, "skin",  168, "heart",  8, "solid"),
    ("heart~breath",   198, "heart", 216, "breath",-10, "solid"),
    ("gaze~choices",   425, "eyes",  452, "choices",16, "solid"),
    ("eyes~behavior",  268, "eyes",  282, "behavior",10, "dotted"),
    ("breath~choices", 338, "breath",352, "choices",12, "dotted"),
    ("skin~breath",    468, "skin",  480, "breath",  7, "dotted"),
    ("asking~choices", 600, "choices",600, None,     0, "dotted"),
]
web_svg = ""
for (lab, x1, l1, x2, l2, bow, grade) in WEB:
    y1 = LANE[l1] + 2
    y2 = (estimate(x2) - 6) if l2 is None else (LANE[l2] + 2)
    if grade == "solid":
        conf = 0.55 if lab == "gaze~choices" else 0.42
        wdt  = 1.3 if lab == "gaze~choices" else 1.0
        web_svg += '<path d="%s" fill="none" stroke="#111118" stroke-width="%.1f" opacity="%.2f"/>\n' % (arc(x1,y1,x2,y2,bow), wdt, conf)
    else:
        # v15: the arc alone carries "expected but not yet characterised" —
        # the "?" glyph is gone, the dotted stroke stays.
        web_svg += '<path d="%s" fill="none" stroke="#111118" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.3"/>\n' % arc(x1,y1,x2,y2,bow)

# ---------- strands, drawn on the warped axis ----------
# Two layers per strand: the line itself, whose fast structure is only drawn
# where the axis still resolves it, and a faint envelope band standing in for
# the fast structure that exists but is compressed past the point of drawing it.
strand_svg = ""
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
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
                poly(et + list(reversed(eb))) + " Z", col, ENV_OP)
    d = " ".join(poly(s) for s in segs if len(s) > 1)
    w, op = (1.5, 0.6) if hero else (1.0, 0.32)
    strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>\n' % (d, col, w, op)
    ex, ey = xm, estimate(xm)
    if hero:
        strand_svg += '<circle cx="%d" cy="%.1f" r="5.5" fill="%s" opacity="0.85"/>' % (ex, ey, col)
        strand_svg += '<circle cx="%d" cy="%.1f" r="7.7" fill="none" stroke="%s" stroke-width="1" opacity="0.6"/>\n' % (ex, ey, col)
    else:
        strand_svg += '<circle cx="%d" cy="%.1f" r="1.5" fill="%s" opacity="0.4"/>\n' % (ex, ey, col)

# ---------- parity junction trios ----------
junc_svg = ""
for jx in PJ_X:
    ey = estimate(jx)
    for f in ("body", "behavior", "asking"):
        sx = jx + SLOT[f]
        junc_svg += '<circle cx="%d" cy="%.1f" r="3.1" fill="%s" opacity="0.55"/>' % (sx, ey, FAMCOL[f])
    junc_svg += "\n"

# ---------- asking droplets ----------
drops = [(150,1.6),(214,1.5),(300,1.6),(346,1.7),(470,1.5),(640,1.7),(732,1.6),(792,1.7)]
ask_svg = ""
for (dx, r) in drops:
    dy = estimate(dx)
    ask_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.2" opacity="0.55"/>' % (dx, dy-20, dx, dy-8)
    ask_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="#7777FF" opacity="0.7"/>\n' % (dx, dy-6, r)

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

# ---------- intervention arrow (on the true state, informed by the estimate) ----------
# v13: markedly smaller than v12's chunky open chevron, with a clean filled
# triangular head. Same colour, same referent point (the true state at NUDGE_X).
ARR_LEN   = 30     # shaft length in px (v12: 46)
ARR_W     = 1.4    # shaft stroke width (v12: 3)
tsn = true_state(NUDGE_X)
arr_tail = tsn + 4 + ARR_LEN
nudge_svg = '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#FF7792" stroke-width="%.1f" marker-end="url(#nud13)"/>' % (
    NUDGE_X, arr_tail, NUDGE_X, tsn+4, ARR_W)
link_svg = '<path d="M %.0f %.1f L %.0f %.1f" fill="none" stroke="#FF7792" stroke-width="1" stroke-dasharray="1 3" opacity="0.4"/>' % (
    576, estimate(576), NUDGE_X, arr_tail)

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
FLBL_X  = 854     # just right of the 'now' divider
FLBL_FS = 7.0     # sized so the longer line ends at ~1031, inside the 1040 canvas
forecast_svg += '<text x="%d" y="%.0f" class="rv15b-svgtext" font-size="%.1f" fill="#111118">intervention &#8594;</text>' % (FLBL_X, good_y-50, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv15b-svgtext" font-size="%.1f" fill="rgba(17,17,24,0.7)">a higher likelihood of the desired outcome</text>\n' % (FLBL_X, good_y-39, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv15b-svgtext" font-size="7.5" fill="rgba(17,17,24,0.4)">without it</text>\n' % (905, less_y+14)

# 'now' divider between observed past and forecast future
now_svg  = '<line x1="%d" y1="44" x2="%d" y2="470" stroke="rgba(17,17,24,0.35)" stroke-width="1" stroke-dasharray="3 4"/>' % (NOW_X, NOW_X)
now_svg += '<text x="%d" y="40" class="rv15b-svgtext" font-size="9" fill="rgba(17,17,24,0.6)" text-anchor="middle">now</text>' % NOW_X

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

ts_lbl_y  = true_state(150) - 12
est_lbl_y = estimate(120) + err_env(120) - 4

HTML = '''<style>
  .rv15b-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv15b-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv15b-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv15b-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv15b-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv15b-wrap .option {{ margin-bottom:1.15rem; }}
  .rv15b-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv15b-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv15b-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv15b-wrap">
  <h2>v15b — minimal</h2>
  <p class="subtitle">The other end of the range. Same strip-back as v15a &#8212; no family margins, no question marks, no gaze-choice or web labels &#8212; but the two labels naming the curves stay, and so do the parity dot trios, so you can judge the bare version knowing what those dots were saying.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">Signals &#8594; triangulated state &#8594; predicted outcome &#8594; better outcome</div>
        <div class="mockup-body">
          <svg viewBox="0 0 1040 500" role="img" aria-label="A faint true-state curve and a bold triangulated estimate over a web of proxies; at 'now' the estimate projects a dotted forecast cone into the future toward an outcome marker, with a ghost path to a lesser outcome without the nudge and the actual path to the better outcome after nudging; five nested timescale brackets — seconds, hours, days, weeks, years — each straddle the 'now' divider, reaching back into the observed signals and forward into the forecast">
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

            {web_svg}
            {strand_svg}
            {ask_svg}
            {est_svg}
            {junc_svg}
            {link_svg}
            {nudge_svg}

            <!-- forecast into the future zone, and the outcome -->
            {forecast_svg}
            {now_svg}

            <text x="150" y="{ts_lbl_y:.0f}" class="rv15b-svgtext" font-size="10" fill="rgba(17,17,24,0.6)">the inner state we can&#39;t directly see</text>
            <text x="120" y="{est_lbl_y:.0f}" class="rv15b-svgtext" font-size="10" fill="#1a2c6b">triangulated from many signals</text>
            <g class="rv15b-svgtext" fill="#111118" text-anchor="middle">
              <text x="600" y="{nl1:.0f}" font-size="9.5">the right intervention for the right person,</text>
              <text x="600" y="{nl2:.0f}" font-size="9.5">in the right context, at the right time</text>
            </g>


            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              {bracket_svg}
            </g>
            <g class="rv15b-svgtext" fill="#1a2c6b" text-anchor="start">
              {tslabel_svg}
            </g>
            <text x="60" y="484" class="rv15b-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">the state and its signals evolve together at every timescale — how far back we&#39;ve measured, how far ahead we can see &#183; the state keeps changing even as we measure it</text>
          </svg>
        </div>
      </div>
      <div class="rv15b-cap">what changed from v14a</div>
      <p class="rv15b-mockup-title">Minimal &#8212; the two curves still named</p>
      <p class="rv15b-mockup-desc">Five of the seven annotations are gone along with the &#8220;?&#8221; glyphs. What stays is the pair that carries the central idea &#8212; the grey curve named as the state we cannot see, the blue one named as the estimate triangulated from many signals &#8212; plus the three parity dot trios on the estimate. Everything else matches v15a exactly, including the 3px wider lane spacing, so the two can be read against each other.</p>

    </div>
  </div>
</div>
'''.format(band_outer=band_outer, band_inner=band_inner, ts_d=ts_d,
           web_svg=web_svg, strand_svg=strand_svg, ask_svg=ask_svg, est_svg=est_svg,
           junc_svg=junc_svg, link_svg=link_svg, nudge_svg=nudge_svg,
           forecast_svg=forecast_svg, now_svg=now_svg,
           bracket_svg=bracket_svg, tslabel_svg=tslabel_svg,
           ts_lbl_y=ts_lbl_y, est_lbl_y=est_lbl_y, nl1=arr_tail+14, nl2=arr_tail+27)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes")
print("estimate end(846)=%.1f  good_y=%.1f  less_y=%.1f  NOW_X=%d FUT_X=%d" % (ey, good_y, less_y, NOW_X, FUT_X))
for i, (lab, xl, xr) in enumerate(TIMESCALES):
    fy = TS_TOP + TS_BASE + i*TS_STEP
    print("  %-8s left arm %4d px  right arm %3d px  floor y=%d" % (lab, NOW_X-xl, xr-NOW_X, fy))
