import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/docs/superpowers/mockups/homepage-research-viz/research-viz-lofi-v14b.html"

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

# v14b: the event-scale structure inside each strand is re-placed to sit inside
# that strand's new, telescoped span (see STRANDS below). Nothing about the
# morphologies themselves changed — only where along x their events fall.
SKIN_RESP    = (662, 712, 758)
MOVE_BURST   = (520, 600, 690)
CHOICE_STEPS = [(288, -0.4), (400, 0.5), (520, 1.0), (620, -0.2), (700, 0.6)]

def shape(name, x, xs):
    d = x - xs
    if name == "heart":
        per = 22.0; p = (d % per) / per
        return (-1.0*gau(p,0.20,0.05) + 0.35*gau(p,0.28,0.045) - 0.15*gau(p,0.12,0.04) - 0.22*gau(p,0.60,0.09))
    if name == "breath":
        return math.sin(2*math.pi*d/42.0)
    if name == "skin":
        v = 0.30*math.sin(2*math.pi*d/120.0)
        for c in SKIN_RESP:
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
        for c in MOVE_BURST:
            v += math.exp(-((x-c)/20.0)**2)*math.sin(2*math.pi*(x-c)/11.0)
        return v
    if name == "choices":
        lvl = -0.4
        for (jx, jl) in CHOICE_STEPS:
            if x >= jx: lvl = jl
        return lvl
    return 0.0

NUDGE_X = 600
NOW_X   = 850          # boundary between observed past and forecast future

# ---------- v12 tuning: timescale brackets, nested and anchored on 'now' ----------
# Every bracket straddles the 'now' divider. Left arm = how far back the signals
# at that rate reach (into the observed span); right arm = how far ahead a
# prediction made at that rate can see (into the forecast zone). Arms are
# asymmetric (the observed side of the figure is far wider than the forecast
# side) but the nesting order holds independently on BOTH sides of 'now'.
TS_TOP     = 398   # y where every bracket's vertical arms start
TS_BASE    = 14    # depth of the innermost (seconds) bracket
TS_STEP    = 13    # extra depth per nesting level
TS_LABEL_DX = 7    # label offset to the right of the 'now' divider
TS_LABEL_DY = 4    # label baseline above its own bracket floor
# (label, left arm end x, right arm end x) — innermost first
TIMESCALES = [
    ("seconds", 792,  905),
    ("hours",   648,  936),
    ("days",    486,  962),
    ("weeks",   288,  986),
    ("years",    60, 1012),   # right arm reaches the outcome-of-interest marker
]
def true_state(x):
    ts = 250 + 20*math.sin(2*math.pi*(x-70)/540.0) + 8*math.sin(2*math.pi*(x-70)/210.0 + 0.8)
    ts -= 24*smoothstep(NUDGE_X, 810, x)
    return ts

FAMCOL = {"body": "#FF7792", "behavior": "#FFAE77", "asking": "#7777FF"}
SLOT   = {"body": -9, "behavior": 0, "asking": 9}

# v14b: parity junctions can only sit where all three evidence families are
# actually on the page. With telescoped extents the body family starts at skin
# (648) and the behaviour family runs out at movement (780), so the three-way
# overlap is the window 648-780 — the trios move there. Parity itself is intact:
# still three equal dots, no proxy privileged.
PJ_X   = [668, 714, 762]
D_PAR  = 3.2
EYES_X = 840          # gaze junction, now at the gaze strand's own merge point
D_EYE  = 6.5

# v14b: TELESCOPED STRAND EXTENTS. Linear time is kept. Each strand's horizontal
# reach is its natural timescale: gaze/heart/breath hug 'now', skin runs back
# hours, movement and behaviour days-to-weeks, choices weeks. Right edges stay
# a staggered fan folding into the estimate, now ordered by timescale.
GAPS = {"skin": [(676, 692)], "movement": [(540, 562)]}
STRANDS = [
    ("heart",   "#FF7792",  86, 12, 770, 830, False),
    ("eyes",    "#FF7792", 104,  6, 792, EYES_X, True),
    ("skin",    "#FF7792", 122,  8, 648, 800, False),
    ("breath",  "#FF7792", 140,  7, 740, 816, False),
    ("behavior","#FFAE77", 172,  9, 380, 762, False),
    ("movement","#FFAE77", 190,  8, 486, 780, False),
    ("choices", "#FFAE77", 208,  9, 288, 744, False),
]
# bend length into the estimate, scaled to each strand's (now very different) span
APPR = {"heart": 36, "eyes": 30, "skin": 60, "breath": 45,
        "behavior": 85, "movement": 70, "choices": 90}
LANE = {nm: y0 for (nm, col, y0, damp, xs, xm, hero) in STRANDS}

MEAN = {}
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
    samp = list(range(xm, 847, 2))
    MEAN[nm] = sum(shape(nm, x, xs) for x in samp) / len(samp)

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
            t += 0.8*(shape(nm, x, xs) - MEAN[nm])*gt
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

# v14b: every arc re-anchored so both endpoints land inside their strand's new
# span. The gaze-choice hero arc is now a long diagonal — those two strands no
# longer sit side by side, which is exactly the point the telescoping makes.
WEB = [
    ("skin~heart",     730, "skin",  782, "heart",  8, "solid"),
    ("heart~breath",   786, "heart", 764, "breath",-10, "solid"),
    ("gaze~choices",   800, "eyes",  700, "choices",10, "solid"),
    ("eyes~behavior",  812, "eyes",  742, "behavior", 6, "dotted"),
    ("breath~choices", 752, "breath",668, "choices",12, "dotted"),
    ("skin~breath",    680, "skin",  748, "breath",  7, "dotted"),
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
        web_svg += '<path d="%s" fill="none" stroke="#111118" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.3"/>' % arc(x1,y1,x2,y2,bow)
        mx, my = (x1+x2)/2.0, (y1+y2)/2.0
        web_svg += '<text x="%.0f" y="%.0f" class="rv14b-svgtext" font-size="7" fill="rgba(17,17,24,0.45)" text-anchor="middle">?</text>\n' % (mx+3, my)

# ---------- strands ----------
strand_svg = ""
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
    approach = xm - APPR[nm]
    gaps = GAPS.get(nm, [])
    segs = []; cur = []; x = xs
    while x <= xm:
        if any(a <= x <= b for (a, b) in gaps):
            if cur: segs.append(cur); cur = []
            x += 3; continue
        if x < approach:
            base = y0; taper = 1.0
        else:
            t = (x - approach)/float(xm - approach)
            base = y0 + (estimate(xm) - y0)*smoothstep(0, 1, t)
            taper = 1.0 - 0.5*t
        cur.append((x, base + damp*shape(nm, x, xs)*taper))
        x += 3
    cur.append((xm, estimate(xm))); segs.append(cur)
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
forecast_svg += '<text x="%d" y="%.0f" class="rv14b-svgtext" font-size="%.1f" fill="#111118">intervention &#8594;</text>' % (FLBL_X, good_y-50, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv14b-svgtext" font-size="%.1f" fill="rgba(17,17,24,0.7)">a higher likelihood of the desired outcome</text>\n' % (FLBL_X, good_y-39, FLBL_FS)
forecast_svg += '<text x="%d" y="%.0f" class="rv14b-svgtext" font-size="7.5" fill="rgba(17,17,24,0.4)">without it</text>\n' % (905, less_y+14)

# 'now' divider between observed past and forecast future
now_svg  = '<line x1="%d" y1="44" x2="%d" y2="470" stroke="rgba(17,17,24,0.35)" stroke-width="1" stroke-dasharray="3 4"/>' % (NOW_X, NOW_X)
now_svg += '<text x="%d" y="40" class="rv14b-svgtext" font-size="9" fill="rgba(17,17,24,0.6)" text-anchor="middle">now</text>' % NOW_X

# ---------- nested timescale brackets, anchored on 'now' ----------
bracket_svg = ""
tslabel_svg = ""
prev_l, prev_r = NOW_X, NOW_X
for i, (lab, xl, xr) in enumerate(TIMESCALES):
    assert xl < prev_l and xr > prev_r, "nesting violated at %s" % lab
    prev_l, prev_r = xl, xr
    fy = TS_TOP + TS_BASE + i*TS_STEP          # this bracket's floor
    bracket_svg += '<path d="M %d %d V %d H %d V %d"/>\n' % (xl, TS_TOP, fy, xr, TS_TOP)
    tslabel_svg += '<text x="%d" y="%d" font-size="9.5">%s</text>\n' % (
        NOW_X + TS_LABEL_DX, fy - TS_LABEL_DY, lab)

ts_lbl_y  = true_state(150) - 12
est_lbl_y = estimate(120) + err_env(120) - 4

HTML = '''<style>
  .rv14b-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv14b-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv14b-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv14b-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv14b-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv14b-wrap .option {{ margin-bottom:1.15rem; }}
  .rv14b-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv14b-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv14b-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv14b-wrap">
  <h2>v14b — telescoped strand extents</h2>
  <p class="subtitle">Fix B for the strands-vs-brackets mismatch. Time stays linear and the brackets are exactly v13&#39;s; what changes is how far each strand reaches. A strand is only drawn over the span its signal actually covers, so the strand lengths echo the bracket nesting: gaze, heartbeats and breath hug &#39;now&#39;, skin runs back hours, movement and behaviour days to weeks, choices weeks. The asking droplets stay spread across every timescale. All wording is unchanged from v13. Click to select and note anything in the terminal.</p>

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

            <text x="648" y="52" class="rv14b-svgtext" font-size="10.5" fill="#111118">many kinds of signal</text>
            <text x="150" y="{ts_lbl_y:.0f}" class="rv14b-svgtext" font-size="10" fill="rgba(17,17,24,0.6)">the inner state we can&#39;t directly see</text>
            <text x="120" y="{est_lbl_y:.0f}" class="rv14b-svgtext" font-size="10" fill="#1a2c6b">triangulated from many signals</text>
            <text x="600" y="158" class="rv14b-svgtext" font-size="8" fill="#111118">gaze ↔ choice: strong evidence</text>
            <text x="556" y="140" class="rv14b-svgtext" font-size="8" fill="rgba(17,17,24,0.5)">relationships we&#39;re still learning</text>
            <g class="rv14b-svgtext" fill="#111118" text-anchor="middle">
              <text x="600" y="{nl1:.0f}" font-size="9.5">the right intervention for the right person,</text>
              <text x="600" y="{nl2:.0f}" font-size="9.5">in the right context, at the right time</text>
            </g>

            <text x="648" y="70" class="rv14b-svgtext" font-size="8" fill="#b0475f">heart · skin · breath · eyes</text>
            <text x="288" y="228" class="rv14b-svgtext" font-size="8" fill="#a35e1c">behavior · movement · choices</text>

            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              {bracket_svg}
            </g>
            <g class="rv14b-svgtext" fill="#1a2c6b" text-anchor="start">
              {tslabel_svg}
            </g>
            <text x="60" y="484" class="rv14b-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">the state and its signals evolve together at every timescale — how far back we&#39;ve measured, how far ahead we can see &#183; the state keeps changing even as we measure it</text>
          </svg>
        </div>
      </div>
      <div class="rv14b-cap">what changed from v13</div>
      <p class="rv14b-mockup-title">Fix B — each strand only as long as its signal</p>
      <p class="rv14b-mockup-desc">Linear time, v13&#39;s brackets untouched, and every strand cut back to the span it genuinely covers. Three things fall out of that and are worth looking at before choosing between A and B. The left third of the figure empties: at weeks-and-longer the only evidence is choices and the asking droplets, which is honest but costs the dense signal field. The three evidence families only coexist between skin&#39;s start and movement&#39;s end, so the parity junctions have to live in that window — still three equal dots, no proxy privileged, but bunched. And the gaze-choice arc becomes a long diagonal instead of a short hop, because the two strands no longer sit side by side. The estimate stays smooth until the signals arrive and its band stays wide out west, both of which are computed, not drawn in.</p>

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
