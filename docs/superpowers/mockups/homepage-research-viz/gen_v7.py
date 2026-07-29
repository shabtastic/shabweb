import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/.superpowers/brainstorm/89599-1785131035/content/research-viz-lofi-v7.html"

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

def baseline(x):
    return 250 + 55 * (x - 110) / 710.0

# ---- signal families: (name, color, y0, draw_wl, draw_amp, x_start, x_merge, c_amp, c_wl, primary) ----
# merge points deliberately staggered across the timescale brackets below
STRANDS = [
    # BODY family (red, fast) — heart / skin / breath / eyes + primary
    ("heart",   "#FF7792",  85, 16, 5, 70, 200, 2.6, 16, False),
    ("body",    "#FF7792", 100, 22, 7, 70, 300, 3.2, 22, True),
    ("skin",    "#FF7792", 112, 30, 5, 70, 430, 2.4, 30, False),
    ("eyes",    "#FF7792",  95, 18, 4, 70, 520, 2.2, 18, False),
    ("breath",  "#FF7792", 122, 46, 6, 70, 600, 3.0, 46, False),
    # BEHAVIOR family (orange, medium) — movement / choices + primary
    ("behavior","#FFAE77", 168, 60, 9, 70, 260, 6.0, 60, True),
    ("movement","#FFAE77", 155, 50, 7, 70, 360, 5.0, 50, False),
    ("choices", "#FFAE77", 185, 72, 8, 70, 680, 5.5, 72, False),
]

def river_y(x):
    y = baseline(x)
    for (nm, col, y0, dwl, damp, xs, xm, camp, cwl, prim) in STRANDS:
        g = smoothstep(xm - 20, xm + 20, x)
        if g > 0:
            y += camp * math.sin(2 * math.pi * (x - xs) / cwl) * g
    return y

# ---- build strand paths: horizontal wiggle, then descend + blend onto the river at its junction ----
strand_svg = ""
for (nm, col, y0, dwl, damp, xs, xm, camp, cwl, prim) in STRANDS:
    approach = xm - 55
    pts = []
    x = xs
    while x <= xm:
        if x < approach:
            base = y0; taper = 1.0
        else:
            t = (x - approach) / float(xm - approach)
            base = y0 + (river_y(xm) - y0) * smoothstep(0, 1, t)
            taper = 1.0 - 0.45 * t
        pts.append((x, base + damp * math.sin(2 * math.pi * (x - xs) / dwl) * taper))
        x += 5
    pts.append((xm, river_y(xm)))
    if prim:
        strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="1.7" opacity="0.72"/>\n' % (poly(pts), col)
    else:
        strand_svg += '<path d="%s" fill="none" stroke="%s" stroke-width="1" opacity="0.32"/>\n' % (poly(pts), col)
    # tiny confluence dot at each junction
    ry = river_y(xm)
    strand_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"/>\n' % (
        xm, ry, 2.4 if prim else 1.6, col, 0.7 if prim else 0.4)

# ---- river drawn as width-stepped segments (shared shape, thickening downstream) ----
riverpts = [(x, river_y(x)) for x in range(110, 821, 4)]
bounds = [110, 200, 300, 430, 600, 821]
widths = [1.6, 2.6, 3.4, 4.4, 5.2]
river_svg = ""
for i in range(len(widths)):
    lo, hi = bounds[i], bounds[i + 1]
    seg = [p for p in riverpts if lo <= p[0] <= hi]
    if i == 0:
        river_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="1.6" stroke-dasharray="5 5" opacity="0.7"/>\n' % poly(seg)
    else:
        end = ' marker-end="url(#arA7)"' if i == len(widths) - 1 else ''
        river_svg += '<path d="%s" fill="none" stroke="#1a2c6b" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"%s/>\n' % (poly(seg), widths[i], end)

# ---- asking: many varied droplets joining along the whole length ----
drops = [(150,2.0),(212,1.5),(278,2.7),(342,1.7),(408,2.2),(470,1.4),
         (538,2.9),(602,1.8),(668,2.4),(732,1.6),(792,2.6)]
ask_svg = ""
for (dx, r) in drops:
    dy = river_y(dx)
    ask_svg += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.3" opacity="0.7"/>' % (dx, dy-24, dx, dy-8)
    ask_svg += '<circle cx="%d" cy="%.1f" r="%.1f" fill="#7777FF" opacity="0.8"/>\n' % (dx, dy-6, r)

HTML = '''<style>
  .rv7-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b; font-family:'Space Mono', monospace; }}
  .rv7-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv7-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700; font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv7-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv7-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv7-wrap .option {{ margin-bottom:1.15rem; }}
  .rv7-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv7-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv7-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv7-wrap">
  <h2>v7 — confluence with signal families</h2>
  <p class="subtitle">Each signal is now a family of strands — several fainter siblings alongside a primary — and each strand joins the river at its own point along the timeline, so the confluences themselves show signals arriving at every timescale. Click to select and add notes in the terminal.</p>

  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">Confluence — families of signals, staggered junctions</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 460" role="img" aria-label="Families of faint signal strands each join a central river at staggered points across the timeline; the river thickens and grows richer downstream, over nested timescales">
            <defs>
              <pattern id="gA7" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA7maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="arA7" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#1a2c6b" stroke-width="1.4"/></marker>
            </defs>
            <rect width="900" height="460" fill="#f5f2ec"/>
            <rect width="900" height="460" fill="url(#gA7)"/>
            <rect width="900" height="460" fill="url(#gA7maj)"/>

            <!-- signal families (faint siblings + primary), each descending to its junction -->
            {strand_svg}
            <!-- asking: sparse varied droplets all along the length -->
            {ask_svg}
            <!-- the river: dashed/thin upstream -> thick/solid downstream, richer as strands fold in -->
            {river_svg}

            <!-- minimal labels -->
            <text x="70" y="60" class="rv7-svgtext" font-size="10.5" fill="#111118">what we can measure</text>
            <text x="140" y="214" class="rv7-svgtext" font-size="9" fill="#7777FF">what we ask, at every scale</text>
            <text x="560" y="250" class="rv7-svgtext" font-size="11" fill="#1a2c6b">the inner states we can&#39;t directly see &#8594;</text>

            <!-- nested containment timescales -->
            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 360 v72 h780 v-72"/>
              <path d="M60 360 v58 h640 v-58"/>
              <path d="M60 360 v44 h480 v-44"/>
              <path d="M60 360 v30 h330 v-30"/>
              <path d="M60 360 v18 h190 v-18"/>
            </g>
            <g class="rv7-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="375">seconds</text><text x="384" y="387">minutes</text>
              <text x="534" y="401">hours</text><text x="694" y="415">days</text><text x="834" y="429">years</text>
            </g>
            <text x="60" y="450" class="rv7-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years; strands join at every span</text>
          </svg>
        </div>
      </div>
      <div class="rv7-cap">how it composes</div>
      <p class="rv7-mockup-title">Confluence with signal families</p>
      <p class="rv7-mockup-desc">Each signal type is a family: a primary trace plus several fainter siblings — body as heart, skin, eyes, breath; behavior as movement and choices — and every strand joins the river at its own point along the timeline. Fast strands merge early, slow ones far downstream, so the junctions themselves spread across seconds-to-years. The river folds each strand&#39;s rhythm into its shape as it goes, thin and dashed upstream, thick and composite downstream. Siblings stay low-opacity so the primary structure still reads at a glance.</p>
    </div>
  </div>
</div>
'''.format(strand_svg=strand_svg, ask_svg=ask_svg, river_svg=river_svg)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes;", len(STRANDS), "strands")
