import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/.superpowers/brainstorm/43386-1785285443/content/research-viz-lofi-v9.html"

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

# ---------- TRUE STATE: faint, calm, continuous, never banded or broken ----------
NUDGE_X = 600
def true_state(x):
    ts = 250 + 20*math.sin(2*math.pi*(x-70)/540.0) + 8*math.sin(2*math.pi*(x-70)/210.0 + 0.8)
    ts -= 24*smoothstep(NUDGE_X, 810, x)
    return ts

FAMCOL = {"body": "#FF7792", "behavior": "#FFAE77", "asking": "#7777FF"}
SLOT   = {"body": -9, "behavior": 0, "asking": 9}   # fixed comparative slots at every junction

# ---------- JUNCTIONS: which signal carries the information depends on the prediction ----------
# (x, dominant_family, prediction_tag, weights per family)  -- the dominant one ROTATES
JUNCTIONS = [
    (250, "behavior", "the next move",     {"body":0.34, "behavior":0.90, "asking":0.22}),
    (410, "body",     "a choice",          {"body":0.90, "behavior":0.30, "asking":0.24}),
    (560, "asking",   "how they'll feel",  {"body":0.26, "behavior":0.30, "asking":0.90}),
    (690, "behavior", "sticking with it",  {"body":0.40, "behavior":0.85, "asking":0.28}),
]
D_STEP = 5.0   # band tightening contributed by the decisive signal at each junction

GAPS = {"skin": [(330, 370)], "movement": [(110, 150)]}
HEROES = {"movement", "heart", "choices"}   # asking's hero is the big slate junction dot at J3
# name, color, y0(lane), draw_amp, x_start, x_merge
STRANDS = [
    ("heart",   "#FF7792",  86, 12, 70, 410),   # body hero -> J2 (a choice)
    ("movement","#FFAE77", 190,  8, 70, 250),   # behavior hero -> J1 (next move)
    ("choices", "#FFAE77", 208,  9, 70, 690),   # behavior hero -> J4 (sticking with it)
    ("behavior","#FFAE77", 172,  9, 70, 300),   # background richness
    ("eyes",    "#FF7792", 104,  6, 70, 330),   # background
    ("skin",    "#FF7792", 122,  8, 70, 490),   # background
    ("breath",  "#FF7792", 140,  7, 70, 620),   # background
]

MEAN = {}
for (nm, col, y0, damp, xs, xm) in STRANDS:
    samp = list(range(xm, 847, 2))
    MEAN[nm] = sum(shape(nm, x, xs) for x in samp) / len(samp)

E_MIN = 2.0
def err_env(x):
    h = E_MIN
    for (jx, fam, tag, w) in JUNCTIONS:
        h += D_STEP*(1 - smoothstep(jx-22, jx+22, x))
    h += 2.0*math.exp(-((x-350)/26.0)**2)   # skin sensor gap (soft)
    h += 2.0*math.exp(-((x-130)/24.0)**2)   # movement gap (soft)
    return h

def wander(x):
    return 0.62*math.sin(2*math.pi*(x-70)/150.0) + 0.4*math.sin(2*math.pi*(x-70)/83.0 + 1.2)

def texture(x):
    t = 0.0
    for (nm, col, y0, damp, xs, xm) in STRANDS:
        gt = smoothstep(xm-22, xm+22, x)
        if gt > 0:
            t += 0.8*(shape(nm, x, xs) - MEAN[nm])*gt
    return t*(1 - 0.6*smoothstep(NUDGE_X, 790, x))

def estimate(x):
    return true_state(x) + err_env(x)*wander(x) + texture(x)

ts_d = poly([(x, true_state(x)) for x in range(70, 851, 4)])

# ---------- strands ----------
strand_svg = ""
for (nm, col, y0, damp, xs, xm) in STRANDS:
    approach = xm - 55
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
    hero = nm in HEROES
    w, op = (1.5, 0.6) if hero else (1.0, 0.32)
    strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>\n' % (d, col, w, op)
    if not hero:
        strand_svg += '<circle cx="%d" cy="%.1f" r="1.5" fill="%s" opacity="0.4"/>\n' % (xm, estimate(xm), col)

# ---------- uncertainty band ----------
bx = list(range(110, 847, 3))
def band_path(scale):
    top = [(x, estimate(x) - err_env(x)*scale) for x in bx]
    bot = [(x, estimate(x) + err_env(x)*scale) for x in reversed(bx)]
    return poly(top + bot) + " Z"
band_outer = band_path(1.0)
band_inner = band_path(0.55)

# ---------- estimate line ----------
est_pts = [(x, estimate(x)) for x in range(110, 847, 3)]
bounds = [110, 210, 320, 450, 600, 847]
widths = [1.8, 2.6, 3.4, 4.4, 4.8]
est_svg = ""
for i in range(len(widths)):
    lo, hi = bounds[i], bounds[i+1]
    seg = [p for p in est_pts if lo <= p[0] <= hi]
    end = ' marker-end="url(#arE9)"' if i == len(widths)-1 else ''
    est_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"%s/>\n' % (poly(seg), widths[i], end)

# ---------- junction contribution trios: same three slots each time, the big one MOVES ----------
junc_svg = ""
for (jx, fam, tag, w) in JUNCTIONS:
    ey = estimate(jx)
    for f in ("body", "behavior", "asking"):
        sx = jx + SLOT[f]
        r = 1.3 + 3.7*w[f]
        dom = (f == fam)
        junc_svg += '<circle cx="%d" cy="%.1f" r="%.2f" fill="%s" opacity="%.2f"/>' % (sx, ey, r, FAMCOL[f], 0.85 if dom else 0.5)
        if dom:
            junc_svg += '<circle cx="%d" cy="%.1f" r="%.2f" fill="none" stroke="%s" stroke-width="1" opacity="0.6"/>' % (sx, ey, r+2.2, FAMCOL[f])
    junc_svg += "\n"

# small plain tags at the two most contrasting junctions
tag_svg = ""
tag_svg += '<text x="410" y="%.0f" class="rv9-svgtext" font-size="8" fill="#111118" text-anchor="middle">for a choice, the body leads</text>' % (estimate(410)+32)
tag_svg += '<text x="560" y="%.0f" class="rv9-svgtext" font-size="8" fill="#111118" text-anchor="middle">for a feeling, what they say leads</text>' % (estimate(560)-22)

# ---------- asking droplets (small everywhere; the J3 heavyweight is the big slate junction dot) ----------
drops = [(150,1.6),(214,1.5),(300,1.6),(346,1.7),(470,1.5),(640,1.7),(732,1.6),(792,1.7)]
ask_svg = ""
for (dx, r) in drops:
    dy = estimate(dx)
    ask_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.2" opacity="0.6"/>' % (dx, dy-20, dx, dy-8)
    ask_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="#7777FF" opacity="0.75"/>\n' % (dx, dy-6, r)

# ---------- nudge on the true state ----------
tsn = true_state(NUDGE_X)
nudge_svg = '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#FF7792" stroke-width="3" marker-end="url(#nud9)"/>' % (NUDGE_X, tsn+50, NUDGE_X, tsn+4)
link_svg = '<path d="M %.0f %.1f L %.0f %.1f" fill="none" stroke="#FF7792" stroke-width="1" stroke-dasharray="1 3" opacity="0.4"/>' % (
    576, estimate(576), NUDGE_X, tsn+50)

ts_lbl_y  = true_state(150) - 12
est_lbl_y = estimate(120) + err_env(120) - 4
anchor_y  = 366

HTML = '''<style>
  .rv9-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv9-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv9-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv9-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv9-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv9-wrap .option {{ margin-bottom:1.15rem; }}
  .rv9-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv9-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv9-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv9-wrap">
  <h2>v9 — continuous state, uncertainty band</h2>
  <p class="subtitle">The faint grey line is the true inner state — calm, continuous, never directly visible. The bold blue line is our approximation, built from many diverse signals. Which signal carries the decisive information isn&#39;t fixed — it depends on what we&#39;re predicting: the body may tell us most about a choice, while what someone says tells us most about how they&#39;ll feel. Watch which family leads at each junction. Click to select and note anything in the terminal.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">A hidden state — and which signal matters shifts with the question</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 500" role="img" aria-label="A faint true-state curve and a bold estimate built from diverse signals; at each junction three family contribution dots appear in fixed slots and the largest one rotates — behavior leads for the next move, body leads for a choice, self-report leads for a feeling — tightening the uncertainty band; a nudge acts on the true state over nested timescales">
            <defs>
              <pattern id="gA9" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA9maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="arE9" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#1a2c6b" stroke-width="1.4"/></marker>
              <marker id="nud9" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#FF7792" stroke-width="1.6"/></marker>
            </defs>
            <rect width="900" height="500" fill="#f5f2ec"/>
            <rect width="900" height="500" fill="url(#gA9)"/>
            <rect width="900" height="500" fill="url(#gA9maj)"/>

            <path d="{band_outer}" fill="rgba(26,44,107,0.07)" stroke="none"/>
            <path d="{band_inner}" fill="rgba(26,44,107,0.09)" stroke="none"/>

            <path d="{ts_d}" fill="none" stroke="rgba(17,17,24,0.30)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>

            {strand_svg}
            {ask_svg}
            {est_svg}
            <!-- junction contribution trios: fixed slots, dominant family rotates -->
            {junc_svg}
            {tag_svg}
            {link_svg}
            {nudge_svg}

            <text x="70" y="52" class="rv9-svgtext" font-size="10.5" fill="#111118">many kinds of signal</text>
            <text x="150" y="{ts_lbl_y:.0f}" class="rv9-svgtext" font-size="10" fill="rgba(17,17,24,0.6)">the inner state we can&#39;t directly see</text>
            <text x="120" y="{est_lbl_y:.0f}" class="rv9-svgtext" font-size="10" fill="#1a2c6b">approximated from many signals</text>
            <text x="485" y="{anchor_y:.0f}" class="rv9-svgtext" font-size="9" fill="#111118" text-anchor="middle">which signal matters most depends on what we&#39;re predicting</text>
            <g class="rv9-svgtext" fill="#111118" text-anchor="middle">
              <text x="600" y="{nl1:.0f}" font-size="9.5">so we can nudge at the right moment</text>
              <text x="600" y="{nl2:.0f}" font-size="9.5" fill="rgba(17,17,24,0.75)">&#8594; toward creating, staying on track, and change</text>
            </g>

            <text x="70" y="70" class="rv9-svgtext" font-size="8" fill="#b0475f">heart · skin · breath · eyes</text>
            <text x="70" y="162" class="rv9-svgtext" font-size="8" fill="#a35e1c">behavior · movement · choices</text>

            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 398 v66 h780 v-66"/>
              <path d="M60 398 v54 h640 v-54"/>
              <path d="M60 398 v42 h480 v-42"/>
              <path d="M60 398 v28 h330 v-28"/>
              <path d="M60 398 v16 h190 v-16"/>
            </g>
            <g class="rv9-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="412">seconds</text><text x="384" y="424">minutes</text>
              <text x="534" y="438">hours</text><text x="694" y="450">days</text><text x="834" y="462">years</text>
            </g>
            <text x="60" y="484" class="rv9-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years; signals arrive at every span</text>
          </svg>
        </div>
      </div>
      <div class="rv9-cap">how it composes</div>
      <p class="rv9-mockup-title">Continuous state, context-dependent signals</p>
      <p class="rv9-mockup-desc">The inner state is one calm continuous grey line — always there, never directly visible. We approximate it with the bold blue line, built from many diverse signals. Crucially, no signal is best in general: at each junction the three families each contribute (fixed body / behavior / asking slots), but the heavyweight — the big dot that tightens the band most — rotates with the question. Behavior carries the most unique information for what they&#39;ll do next; the body carries it for a choice; what someone says carries it for how they&#39;ll feel. Every signal is still used, and the nudge acts on the state itself, toward creating, staying on track, and change.</p>
    </div>
  </div>
</div>
'''.format(band_outer=band_outer, band_inner=band_inner, ts_d=ts_d,
           strand_svg=strand_svg, ask_svg=ask_svg, est_svg=est_svg, junc_svg=junc_svg, tag_svg=tag_svg,
           link_svg=link_svg, nudge_svg=nudge_svg,
           ts_lbl_y=ts_lbl_y, est_lbl_y=est_lbl_y, anchor_y=anchor_y, nl1=tsn+62, nl2=tsn+75)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes")
for (jx, fam, tag, w) in JUNCTIONS:
    doms = max(w, key=w.get)
    ok = "OK" if doms == fam else "MISMATCH"
    print("x=%d predict '%s' dominant=%s %s  radii body/beh/ask=%.1f/%.1f/%.1f" % (
        jx, tag, doms, ok, 1.3+3.7*w['body'], 1.3+3.7*w['behavior'], 1.3+3.7*w['asking']))
print("err_env up(120)=%.1f afterJ1(280)=%.1f afterJ2(440)=%.1f afterJ3(590)=%.1f afterJ4(720)=%.1f" % (
    err_env(120), err_env(280), err_env(440), err_env(590), err_env(720)))
