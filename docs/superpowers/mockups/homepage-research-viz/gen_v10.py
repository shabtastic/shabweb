import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/.superpowers/brainstorm/43386-1785285443/content/research-viz-lofi-v10.html"

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
def true_state(x):
    ts = 250 + 20*math.sin(2*math.pi*(x-70)/540.0) + 8*math.sin(2*math.pi*(x-70)/210.0 + 0.8)
    ts -= 24*smoothstep(NUDGE_X, 810, x)
    return ts

FAMCOL = {"body": "#FF7792", "behavior": "#FFAE77", "asking": "#7777FF"}
SLOT   = {"body": -9, "behavior": 0, "asking": 9}

# ---------- PARITY junctions: no proxy prioritized a priori (equal contributions) ----------
PJ_X   = [250, 560, 700]
D_PAR  = 3.2
# ---------- the ONE evidence-earned exception: gaze/eyes near a choice moment ----------
EYES_X = 460
D_EYE  = 6.5

GAPS = {"skin": [(330, 370)], "movement": [(110, 150)]}
# name, color, lane_y0, draw_amp, x_start, x_merge, hero
STRANDS = [
    ("heart",   "#FF7792",  86, 12, 70, 410, False),
    ("eyes",    "#FF7792", 104,  6, 70, EYES_X, True),   # gaze — evidence-earned heavyweight (inverted from v9)
    ("skin",    "#FF7792", 122,  8, 70, 490, False),
    ("breath",  "#FF7792", 140,  7, 70, 620, False),
    ("behavior","#FFAE77", 172,  9, 70, 300, False),
    ("movement","#FFAE77", 190,  8, 70, 250, False),
    ("choices", "#FFAE77", 208,  9, 70, 700, False),
]
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
    h += D_EYE*(1 - smoothstep(EYES_X-22, EYES_X+22, x))   # gaze tightens more — but only here
    h += 2.0*math.exp(-((x-350)/26.0)**2)   # skin sensor gap (soft)
    h += 2.0*math.exp(-((x-130)/24.0)**2)   # movement gap (soft)
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

ts_d = poly([(x, true_state(x)) for x in range(70, 851, 4)])

# ---------- inter-signal WEB: quiet relationships among the proxies themselves ----------
def arc(x1, y1, x2, y2, bow):
    mx, my = (x1+x2)/2.0, (y1+y2)/2.0
    dx, dy = x2-x1, y2-y1
    L = math.hypot(dx, dy) or 1.0
    cx, cy = mx - bow*dy/L, my + bow*dx/L
    return "M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x1, y1, cx, cy, x2, y2)

# solid = known coupling / strong evidence ; dotted = likely-but-uncharacterized (ML is learning it)
# (label, x1, lane1, x2, lane2, bow, grade)
WEB = [
    ("skin~heart",     150, "skin",  168, "heart",  8, "solid"),
    ("heart~breath",   198, "heart", 216, "breath",-10, "solid"),
    ("gaze~choices",   425, "eyes",  452, "choices",16, "solid"),   # the clearest known link
    ("eyes~behavior",  268, "eyes",  282, "behavior",10, "dotted"),
    ("breath~choices", 338, "breath",352, "choices",12, "dotted"),
    ("skin~breath",    468, "skin",  480, "breath",  7, "dotted"),
    ("asking~choices", 600, "choices",600, None,     0, "dotted"),  # to an asking droplet on the estimate
]
web_svg = ""
for (lab, x1, l1, x2, l2, bow, grade) in WEB:
    y1 = LANE[l1] + 2
    y2 = (estimate(x2) - 6) if l2 is None else (LANE[l2] + 2)   # asking link drops to a droplet
    if grade == "solid":
        conf = 0.55 if lab == "gaze~choices" else 0.42
        wdt  = 1.3 if lab == "gaze~choices" else 1.0
        web_svg += '<path d="%s" fill="none" stroke="#111118" stroke-width="%.1f" opacity="%.2f"/>\n' % (arc(x1,y1,x2,y2,bow), wdt, conf)
    else:
        web_svg += '<path d="%s" fill="none" stroke="#111118" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.3"/>' % arc(x1,y1,x2,y2,bow)
        mx, my = (x1+x2)/2.0, (y1+y2)/2.0
        web_svg += '<text x="%.0f" y="%.0f" class="rv10-svgtext" font-size="7" fill="rgba(17,17,24,0.45)" text-anchor="middle">?</text>\n' % (mx+3, my)

# ---------- strands ----------
strand_svg = ""
for (nm, col, y0, damp, xs, xm, hero) in STRANDS:
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
    w, op = (1.5, 0.6) if hero else (1.0, 0.32)
    strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>\n' % (d, col, w, op)
    ex, ey = xm, estimate(xm)
    if hero:   # gaze confluence: the evidence-earned heavyweight
        strand_svg += '<circle cx="%d" cy="%.1f" r="5.5" fill="%s" opacity="0.85"/>' % (ex, ey, col)
        strand_svg += '<circle cx="%d" cy="%.1f" r="7.7" fill="none" stroke="%s" stroke-width="1" opacity="0.6"/>\n' % (ex, ey, col)
    else:
        strand_svg += '<circle cx="%d" cy="%.1f" r="1.5" fill="%s" opacity="0.4"/>\n' % (ex, ey, col)

# ---------- parity junction trios: equal contributions, no prioritization ----------
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

# ---------- nudge ----------
tsn = true_state(NUDGE_X)
nudge_svg = '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#FF7792" stroke-width="3" marker-end="url(#nud10)"/>' % (NUDGE_X, tsn+50, NUDGE_X, tsn+4)
link_svg = '<path d="M %.0f %.1f L %.0f %.1f" fill="none" stroke="#FF7792" stroke-width="1" stroke-dasharray="1 3" opacity="0.4"/>' % (
    576, estimate(576), NUDGE_X, tsn+50)

ts_lbl_y  = true_state(150) - 12
est_lbl_y = estimate(120) + err_env(120) - 4

HTML = '''<style>
  .rv10-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv10-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv10-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv10-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv10-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv10-wrap .option {{ margin-bottom:1.15rem; }}
  .rv10-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv10-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv10-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv10-wrap">
  <h2>v10 — triangulation and the signal web</h2>
  <p class="subtitle">We triangulate the hidden inner state from many proxies — no signal privileged in advance, only where the evidence has earned it (gaze, for instance, tracks choice through a well-understood mechanism). And the proxies aren&#39;t independent: they form a partly-known web of relationships, some measured, many still being learned by ML — and the web itself sharpens the inference. Click to select and note anything in the terminal.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">Triangulating a hidden state from a web of related proxies</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 500" role="img" aria-label="A faint true-state curve and a bold estimate triangulated from diverse proxies contributing roughly equally, except gaze which gets a large confluence near a choice moment; thin solid and dotted arcs connect the proxy strands into a partly-known web; a nudge acts on the true state over nested timescales">
            <defs>
              <pattern id="gA10" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA10maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="arE10" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#1a2c6b" stroke-width="1.4"/></marker>
              <marker id="nud10" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#FF7792" stroke-width="1.6"/></marker>
            </defs>
            <rect width="900" height="500" fill="#f5f2ec"/>
            <rect width="900" height="500" fill="url(#gA10)"/>
            <rect width="900" height="500" fill="url(#gA10maj)"/>

            <path d="{band_outer}" fill="rgba(26,44,107,0.07)" stroke="none"/>
            <path d="{band_inner}" fill="rgba(26,44,107,0.09)" stroke="none"/>

            <path d="{ts_d}" fill="none" stroke="rgba(17,17,24,0.30)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>

            <!-- inter-signal web (drawn among the strands, before/independent of the estimate) -->
            {web_svg}
            {strand_svg}
            {ask_svg}
            {est_svg}
            {junc_svg}
            {link_svg}
            {nudge_svg}

            <text x="70" y="52" class="rv10-svgtext" font-size="10.5" fill="#111118">many kinds of signal</text>
            <text x="150" y="{ts_lbl_y:.0f}" class="rv10-svgtext" font-size="10" fill="rgba(17,17,24,0.6)">the inner state we can&#39;t directly see</text>
            <text x="120" y="{est_lbl_y:.0f}" class="rv10-svgtext" font-size="10" fill="#1a2c6b">triangulated from many signals</text>
            <text x="452" y="150" class="rv10-svgtext" font-size="8" fill="#111118">gaze ↔ choice: strong evidence</text>
            <text x="300" y="156" class="rv10-svgtext" font-size="8" fill="rgba(17,17,24,0.5)">relationships we&#39;re still learning</text>
            <g class="rv10-svgtext" fill="#111118" text-anchor="middle">
              <text x="600" y="{nl1:.0f}" font-size="9.5">so we can nudge at the right moment</text>
              <text x="600" y="{nl2:.0f}" font-size="9.5" fill="rgba(17,17,24,0.75)">&#8594; toward creating, staying on track, and change</text>
            </g>

            <text x="70" y="70" class="rv10-svgtext" font-size="8" fill="#b0475f">heart · skin · breath · eyes</text>
            <text x="70" y="228" class="rv10-svgtext" font-size="8" fill="#a35e1c">behavior · movement · choices</text>

            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 398 v66 h780 v-66"/>
              <path d="M60 398 v54 h640 v-54"/>
              <path d="M60 398 v42 h480 v-42"/>
              <path d="M60 398 v28 h330 v-28"/>
              <path d="M60 398 v16 h190 v-16"/>
            </g>
            <g class="rv10-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="412">seconds</text><text x="384" y="424">minutes</text>
              <text x="534" y="438">hours</text><text x="694" y="450">days</text><text x="834" y="462">years</text>
            </g>
            <text x="60" y="484" class="rv10-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years; signals arrive at every span</text>
          </svg>
        </div>
      </div>
      <div class="rv10-cap">how it composes</div>
      <p class="rv10-mockup-title">Triangulation and the signal web</p>
      <p class="rv10-mockup-desc">The hidden inner state (faint grey) is triangulated into the bold blue estimate from many diverse proxies. By default no proxy is privileged — the family contributions at each junction are roughly equal — with one evidence-earned exception: gaze gets the large confluence near a choice, because that link is real and mechanistically understood. The proxies also relate to one another: thin solid arcs mark couplings we already know (gaze–choice the clearest, heart–breath, skin–heart), while fainter dotted arcs mark relationships biology says must exist but that we haven&#39;t characterized yet — the structure ML is learning. Those learned relationships tighten the estimate further, so we can nudge at the right moment, toward creating, staying on track, and change.</p>
    </div>
  </div>
</div>
'''

# estimate line (kept identical to v9)
est_pts = [(x, estimate(x)) for x in range(110, 847, 3)]
bounds = [110, 210, 320, 450, 600, 847]
widths = [1.8, 2.6, 3.4, 4.4, 4.8]
est_svg = ""
for i in range(len(widths)):
    lo, hi = bounds[i], bounds[i+1]
    seg = [p for p in est_pts if lo <= p[0] <= hi]
    end = ' marker-end="url(#arE10)"' if i == len(widths)-1 else ''
    est_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"%s/>\n' % (poly(seg), widths[i], end)

bx = list(range(110, 847, 3))
def band_path(scale):
    top = [(x, estimate(x) - err_env(x)*scale) for x in bx]
    bot = [(x, estimate(x) + err_env(x)*scale) for x in reversed(bx)]
    return poly(top + bot) + " Z"

HTML = HTML.format(band_outer=band_path(1.0), band_inner=band_path(0.55), ts_d=ts_d,
                   web_svg=web_svg, strand_svg=strand_svg, ask_svg=ask_svg, est_svg=est_svg,
                   junc_svg=junc_svg, link_svg=link_svg, nudge_svg=nudge_svg,
                   ts_lbl_y=ts_lbl_y, est_lbl_y=est_lbl_y, nl1=tsn+62, nl2=tsn+75)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes")
print("err_env up(120)=%.1f  afterJ1(280)=%.1f  after gaze(490)=%.1f  afterJ2(590)=%.1f  afterJ3(730)=%.1f" % (
    err_env(120), err_env(280), err_env(490), err_env(590), err_env(730)))
print("gaze band drop:", round(err_env(438)-err_env(482),1), " parity-junction drop:", round(err_env(228)-err_env(272),1))
for (lab, x1, l1, x2, l2, bow, grade) in WEB:
    print("  web %-16s x=%d grade=%s" % (lab, x1, grade))
