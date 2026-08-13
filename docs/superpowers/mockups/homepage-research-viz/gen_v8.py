import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/.superpowers/brainstorm/89599-1785131035/content/research-viz-lofi-v8.html"

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

def g(p, c, w):  # gaussian bump
    return math.exp(-((p - c) / w) ** 2)

# ---- distinct morphology per strand; returns ~unit-scale value around 0 ----
def shape(name, x, xs):
    d = x - xs
    if name == "heart":          # fast quasi-ECG: flat then sharp spike + small T
        per = 22.0; p = (d % per) / per
        return (-1.0*g(p,0.20,0.05) + 0.35*g(p,0.28,0.045) - 0.15*g(p,0.12,0.04) - 0.22*g(p,0.60,0.09))
    if name == "breath":         # regular rounded medium wave
        return math.sin(2*math.pi*d/42.0)
    if name == "skin":           # slow drift + occasional SCR rises
        v = 0.30*math.sin(2*math.pi*d/120.0)
        for c in (150, 290, 400):
            dt = x - c
            if dt >= 0:
                v += 0.9*math.exp(-dt/45.0)*(1 - math.exp(-dt/6.0))
        return v
    if name == "eyes":           # darty saccade-like steps + micro jitter
        seg = int(math.floor(d/11.0))
        lvl = rnd(seg)*1.8 - 0.9
        return lvl + 0.12*math.sin(2*math.pi*d/4.0)
    if name == "behavior":       # irregular bursty activity
        env = (0.5 + 0.5*math.sin(2*math.pi*d/70.0)); env *= env
        return env*math.sin(2*math.pi*d/13.0 + 1.4*math.sin(2*math.pi*d/47.0))
    if name == "movement":       # intermittent bursts separated by quiet
        v = 0.0
        for c in (150, 240, 315):
            v += math.exp(-((x-c)/20.0)**2)*math.sin(2*math.pi*(x-c)/11.0)
        return v
    if name == "choices":        # step function: discrete levels, sparse jumps
        lvl = -0.4
        for (jx, jl) in [(70,-0.4),(200,0.5),(340,1.0),(500,-0.2),(620,0.6)]:
            if x >= jx: lvl = jl
        return lvl
    return 0.0

def baseline(x):
    return 255 + 52*(x-110)/710.0

# sparse discontinuities: a couple of strands drop out for a stretch (sensor off /
# quiet between sessions) while the RIVER keeps flowing smooth through the gap.
GAPS = {
    "skin":     [(300, 360)],   # wearable off for a stretch
    "movement": [(182, 236)],   # quiet between sessions
}

# name, color, y0, draw_amp, x_start, x_merge, river_amp, primary
STRANDS = [
    ("heart",   "#FF7792",  88, 12, 70, 200, 3.0, True),
    ("eyes",    "#FF7792", 106,  6, 70, 430, 2.4, False),
    ("skin",    "#FF7792", 126,  8, 70, 500, 3.0, False),
    ("breath",  "#FF7792", 144,  7, 70, 600, 3.4, False),
    ("behavior","#FFAE77", 178,  9, 70, 270, 4.0, True),
    ("movement","#FFAE77", 197,  8, 70, 360, 3.2, False),
    ("choices", "#FFAE77", 216,  9, 70, 690, 4.2, False),
]

# de-mean each strand's river contribution over its merged span so baseline stays put
MEAN = {}
for (nm, col, y0, damp, xs, xm, camp, prim) in STRANDS:
    xs_samp = range(xm, 821, 2)
    MEAN[nm] = sum(shape(nm, x, xs) for x in xs_samp) / len(list(xs_samp))

def river_y(x):
    y = baseline(x)
    for (nm, col, y0, damp, xs, xm, camp, prim) in STRANDS:
        gate = smoothstep(xm-22, xm+22, x)
        if gate > 0:
            y += camp*(shape(nm, x, xs) - MEAN[nm])*gate
    return y

# ---- strand paths: own morphology, then descend + blend onto river at junction ----
strand_svg = ""
for (nm, col, y0, damp, xs, xm, camp, prim) in STRANDS:
    approach = xm - 55
    gaps = GAPS.get(nm, [])
    segs = []   # broken sub-paths so a gap is a clean break
    cur = []
    x = xs
    while x <= xm:
        if any(a <= x <= b for (a, b) in gaps):
            if cur: segs.append(cur); cur = []
            x += 3; continue
        if x < approach:
            base = y0; taper = 1.0
        else:
            t = (x - approach)/float(xm - approach)
            base = y0 + (river_y(xm) - y0)*smoothstep(0, 1, t)
            taper = 1.0 - 0.5*t
        cur.append((x, base + damp*shape(nm, x, xs)*taper))
        x += 3
    cur.append((xm, river_y(xm)))
    segs.append(cur)
    d = " ".join(poly(s) for s in segs if len(s) > 1)
    if prim:
        strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="1.5" opacity="0.6"/>\n' % (d, col)
    else:
        strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="1" opacity="0.3"/>\n' % (d, col)
    ry = river_y(xm)
    strand_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"/>\n' % (xm, ry, 2.4 if prim else 1.6, col, 0.65 if prim else 0.4)

# ---- river: shared shape, width-stepped, dashed->solid ----
riverpts = [(x, river_y(x)) for x in range(110, 821, 3)]
bounds = [110, 200, 300, 430, 600, 821]
widths = [1.6, 2.6, 3.4, 4.4, 5.2]
river_svg = ""
for i in range(len(widths)):
    lo, hi = bounds[i], bounds[i+1]
    seg = [p for p in riverpts if lo <= p[0] <= hi]
    if i == 0:
        river_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="1.6" stroke-dasharray="5 5" opacity="0.7"/>\n' % poly(seg)
    else:
        end = ' marker-end="url(#arA8)"' if i == len(widths)-1 else ''
        river_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"%s/>\n' % (poly(seg), widths[i], end)

# ---- asking: varied droplets along the whole length ----
drops = [(150,2.0),(212,1.5),(278,2.7),(342,1.7),(408,2.2),(470,1.4),
         (538,2.9),(602,1.8),(668,2.4),(732,1.6),(792,2.6)]
ask_svg = ""
for (dx, r) in drops:
    dy = river_y(dx)
    ask_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.3" opacity="0.7"/>' % (dx, dy-24, dx, dy-8)
    ask_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="#7777FF" opacity="0.8"/>\n' % (dx, dy-6, r)

HTML = '''<style>
  .rv8-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv8-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv8-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv8-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv8-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv8-wrap .option {{ margin-bottom:1.15rem; }}
  .rv8-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv8-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv8-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv8-wrap">
  <h2>v8 — diverse signals, named</h2>
  <p class="subtitle">Each strand now has its own kind of shape — a heartbeat spikes, breath rolls, eyes dart, choices step — so the families read as genuinely different measurements. Names sit quietly in the left margin where each family begins. Click to select and note anything in the terminal.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">Confluence — diverse signal families, named at the margin</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 470" role="img" aria-label="Families of distinct signal shapes — spiky heartbeat, drifting skin, rolling breath, darting eyes, bursty behavior, intermittent movement, stepping choices — each join a central river at staggered points, which thickens and grows richer downstream over nested timescales">
            <defs>
              <pattern id="gA8" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA8maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="arA8" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#1a2c6b" stroke-width="1.4"/></marker>
            </defs>
            <rect width="900" height="470" fill="#f5f2ec"/>
            <rect width="900" height="470" fill="url(#gA8)"/>
            <rect width="900" height="470" fill="url(#gA8maj)"/>

            <!-- signal families (distinct morphologies), each descending to its junction -->
            {strand_svg}
            <!-- asking: varied droplets all along the length -->
            {ask_svg}
            <!-- river: dashed/thin upstream -> thick/solid downstream, inheriting each strand's character -->
            {river_svg}

            <!-- plain-language anchors (each at its referent) -->
            <text x="70" y="52" class="rv8-svgtext" font-size="10.5" fill="#111118">many kinds of signal</text>
            <text x="110" y="248" class="rv8-svgtext" font-size="10.5" fill="#1a2c6b">the inner states we can&#39;t directly see &#8594;</text>
            <text x="520" y="334" class="rv8-svgtext" font-size="9" fill="rgba(17,17,24,0.7)">supporting creativity · self-control · lasting change</text>

            <!-- margin strand-name notes, at each family's left origin (no leaders needed) -->
            <text x="70" y="70" class="rv8-svgtext" font-size="8" fill="#b0475f">heart · skin · breath · eyes</text>
            <text x="70" y="166" class="rv8-svgtext" font-size="8" fill="#a35e1c">behavior · movement · choices</text>
            <text x="250" y="236" class="rv8-svgtext" font-size="8" fill="#5656cf">asking</text>

            <!-- nested containment timescales -->
            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 372 v70 h780 v-70"/>
              <path d="M60 372 v56 h640 v-56"/>
              <path d="M60 372 v42 h480 v-42"/>
              <path d="M60 372 v28 h330 v-28"/>
              <path d="M60 372 v16 h190 v-16"/>
            </g>
            <g class="rv8-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="386">seconds</text><text x="384" y="398">minutes</text>
              <text x="534" y="412">hours</text><text x="694" y="426">days</text><text x="834" y="440">years</text>
            </g>
            <text x="60" y="460" class="rv8-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years; strands join at every span</text>
          </svg>
        </div>
      </div>
      <div class="rv8-cap">how it composes</div>
      <p class="rv8-mockup-title">Diverse signals, named</p>
      <p class="rv8-mockup-desc">Every strand carries a distinct morphology — heart as a spiky heartbeat, skin as slow drift with rises, breath as a rounded wave, eyes as darting saccades; behavior as irregular bursts, movement as intermittent flurries, choices as a discrete step function — so the signal families read as genuinely different kinds of measurement. Each joins the river at its own moment along the timeline, and the river folds that strand&#39;s actual character into its shape as it thickens downstream. Names live quietly in the left margin, right where each family enters.</p>
    </div>
  </div>
</div>
'''.format(strand_svg=strand_svg, ask_svg=ask_svg, river_svg=river_svg)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes;", len(STRANDS), "strands")
