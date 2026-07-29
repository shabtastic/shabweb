import math

OUT = "/Users/shabnam/projects/website/.claude/worktrees/homepage-research-viz/.superpowers/brainstorm/89599-1785131035/content/research-viz-lofi-v6.html"

def poly(points):
    s = "M %.1f %.1f" % points[0]
    for p in points[1:]:
        s += " L %.1f %.1f" % p
    return s

# ---------------- OPTION A : CONFLUENCE ----------------
def riverbase(x):
    return 250 + 50*(x-110)/710.0

# Seg A upstream: thin dashed smooth (baseline only)
segA = [(x, riverbase(x)) for x in range(110, 251, 10)]
# Seg B: baseline + medium wave (inherited from behavior tributary), phase from x=250
def med(x):
    return 9*math.sin(2*math.pi*(x-250)/60.0)
segB = [(x, riverbase(x)+med(x)) for x in range(250, 471, 6)]
# Seg C: baseline + medium + fast jitter (inherited from body tributary), phase from x=470
def fast(x):
    return 4*math.sin(2*math.pi*(x-470)/22.0)
segC = [(x, riverbase(x)+med(x)+fast(x)) for x in range(470, 821, 5)]

# behavior tributary: medium orange wave then descend to merge at (250,~260)
beh = [(x, 150+8*math.sin(2*math.pi*(x-70)/60.0)) for x in range(70, 211, 6)]
beh += [(224,168),(238,210),(250, riverbase(250))]
# body tributary: fast red wiggle then descend to merge at (470,~275)
bod = [(x, 90+6*math.sin(2*math.pi*(x-70)/22.0)) for x in range(70, 431, 5)]
bod += [(444,120),(456,200),(470, riverbase(470))]

segA_d = poly(segA)
segB_d = poly(segB)
segC_d = poly(segC)
beh_d  = poly(beh)
bod_d  = poly(bod)

# asking droplets along the whole river
drops = [180,300,430,560,680,770]
drop_svg = ""
for dx in drops:
    dy = riverbase(dx)
    drop_svg += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#7777FF" stroke-width="1.4" opacity="0.75"/>'
                 % (dx, dy-26, dx, dy-8))
    drop_svg += '<circle cx="%d" cy="%.1f" r="2.4" fill="#7777FF" opacity="0.85"/>' % (dx, dy-6)

# ---------------- OPTION B : SUPERPOSITION ----------------
CX0, CX1 = 110, 810
# composite = trend (arch) + medium wave + fast jitter, around y=140
def trend(x):
    return -34*math.sin(math.pi*(x-110)/700.0)
def medB(x):
    return 16*math.sin(2*math.pi*(x-110)/120.0)
def fastB(x):
    return 6*math.sin(2*math.pi*(x-110)/30.0)
comp = [(x, 140+trend(x)+medB(x)+fastB(x)) for x in range(CX0, CX1+1, 6)]
comp_d = poly(comp)

# components (decomposition), each on its own faint baseline, same x-range so they align
cfast = [(x, 250+7*math.sin(2*math.pi*(x-110)/30.0)) for x in range(CX0, CX1+1, 6)]
cmed  = [(x, 292+14*math.sin(2*math.pi*(x-110)/120.0)) for x in range(CX0, CX1+1, 6)]
cslow = [(x, 332-20*math.sin(math.pi*(x-110)/700.0)) for x in range(CX0, CX1+1, 6)]
cfast_d = poly(cfast); cmed_d = poly(cmed); cslow_d = poly(cslow)

HTML = '''<style>
  .rv6-wrap {{ --paper:#f5f2ec; --ink:#111118; --blue:#1a2c6b;
    font-family:'Space Mono', monospace; }}
  .rv6-wrap h2 {{ font-family:'DM Sans', sans-serif; }}
  .rv6-mockup-title {{ font-family:'DM Sans', sans-serif; font-weight:700;
    font-size:1.02rem; margin:0 0 .15rem; color:var(--blue); }}
  .rv6-mockup-desc {{ font-size:.82rem; line-height:1.45; margin:0; opacity:.82; max-width:66ch; }}
  .rv6-wrap .mockup-body {{ background:#f5f2ec; padding:0; }}
  .rv6-wrap .option {{ margin-bottom:1.15rem; }}
  .rv6-wrap svg {{ display:block; width:100%; height:auto; }}
  .rv6-cap {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; margin:.55rem 0 .05rem; }}
  .rv6-svgtext {{ font-family:'Space Mono', monospace; }}
</style>

<div class="rv6-wrap">
  <h2>v6 — compositionality: two treatments</h2>
  <p class="subtitle">The state curve should not be a separate object the signals merely point at — its very shape should be built from theirs. Two ways to do that. Click the one that feels right and tell me in the terminal.</p>

  <!-- ================= OPTION A : CONFLUENCE ================= -->
  <div class="option" data-choice="A" onclick="toggleSelect(this)">
    <span class="letter">A</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">A · Confluence — tributaries become the river</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 440" role="img" aria-label="Signal traces flow in as tributaries and merge into a single river; past each junction the river carries the joining rhythm, thin and dashed upstream, thick and composite downstream, over nested timescales">
            <defs>
              <pattern id="gA6" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gA6maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
              <marker id="arA6" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#1a2c6b" stroke-width="1.4"/></marker>
            </defs>
            <rect width="900" height="440" fill="#f5f2ec"/>
            <rect width="900" height="440" fill="url(#gA6)"/>
            <rect width="900" height="440" fill="url(#gA6maj)"/>

            <!-- tributaries -->
            <path d="{bod_d}" fill="none" stroke="#FF7792" stroke-width="1.5" opacity="0.7"/>
            <path d="{beh_d}" fill="none" stroke="#FFAE77" stroke-width="1.9" opacity="0.75"/>

            <!-- asking droplets joining all along -->
            {drop_svg}

            <!-- the river: upstream thin+dashed, thickening + inheriting rhythm downstream -->
            <path d="{segA_d}" fill="none" stroke="#1a2c6b" stroke-width="1.6" stroke-dasharray="5 5" opacity="0.7"/>
            <path d="{segB_d}" fill="none" stroke="#1a2c6b" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
            <path d="{segC_d}" fill="none" stroke="#1a2c6b" stroke-width="4.6" stroke-linejoin="round" stroke-linecap="round" marker-end="url(#arA6)"/>

            <!-- minimal labels -->
            <text x="70" y="70" class="rv6-svgtext" font-size="10.5" fill="#111118">what we can measure</text>
            <text x="150" y="182" class="rv6-svgtext" font-size="9" fill="#7777FF">what we ask, at every scale</text>
            <text x="560" y="250" class="rv6-svgtext" font-size="11" fill="#1a2c6b">the inner states we can&#39;t directly see →</text>

            <!-- nested containment timescales -->
            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 350 v72 h780 v-72"/>
              <path d="M60 350 v58 h640 v-58"/>
              <path d="M60 350 v44 h480 v-44"/>
              <path d="M60 350 v30 h330 v-30"/>
              <path d="M60 350 v18 h190 v-18"/>
            </g>
            <g class="rv6-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="366">seconds</text><text x="384" y="378">minutes</text>
              <text x="534" y="392">hours</text><text x="694" y="406">days</text><text x="834" y="420">years</text>
            </g>
            <text x="60" y="436" class="rv6-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years</text>
          </svg>
        </div>
      </div>
      <div class="rv6-cap">how it composes</div>
      <p class="rv6-mockup-title">Confluence</p>
      <p class="rv6-mockup-desc">The signals are tributaries that flow in and physically become the state line. Past each junction the river inherits that tributary&#39;s rhythm — the medium wave folded in where behavior joins, fine texture where the body signal joins — while asking drips in at every point along the length. Upstream it&#39;s thin, dashed, uncertain; downstream it&#39;s thick, composite, confident.</p>
    </div>
  </div>

  <!-- ================= OPTION B : SUPERPOSITION ================= -->
  <div class="option" data-choice="B" onclick="toggleSelect(this)">
    <span class="letter">B</span>
    <div class="content">
      <div class="mockup">
        <div class="mockup-header">B · Superposition — the curve is the sum of its rhythms</div>
        <div class="mockup-body">
          <svg viewBox="0 0 900 480" role="img" aria-label="One bold state curve shown as the sum of a slow trend, a medium wave, and a fast jitter, with the three components stacked below as an aligned decomposition, over nested timescales">
            <defs>
              <pattern id="gB6" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
              <pattern id="gB6maj" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="rgba(80,140,200,0.42)" stroke-width="1"/></pattern>
            </defs>
            <rect width="900" height="480" fill="#f5f2ec"/>
            <rect width="900" height="480" fill="url(#gB6)"/>
            <rect width="900" height="480" fill="url(#gB6maj)"/>

            <!-- faint vertical alignment guides -->
            <g stroke="rgba(26,44,107,0.28)" stroke-width="1" stroke-dasharray="2 5">
              <line x1="290" y1="96" x2="290" y2="352"/>
              <line x1="560" y1="96" x2="560" y2="352"/>
            </g>

            <!-- composite (the sum) -->
            <path d="{comp_d}" fill="none" stroke="#1a2c6b" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
            <text x="470" y="96" class="rv6-svgtext" font-size="11" fill="#1a2c6b">the inner states we can&#39;t directly see</text>

            <!-- equals / plus math down the left margin -->
            <g class="rv6-svgtext" fill="#1a2c6b" text-anchor="middle">
              <text x="88" y="208" font-size="18">=</text>
              <text x="88" y="275" font-size="18">+</text>
              <text x="88" y="315" font-size="18">+</text>
            </g>

            <!-- component decomposition (what we can measure) -->
            <path d="{cfast_d}" fill="none" stroke="#FF7792" stroke-width="1.6" opacity="0.85"/>
            <path d="{cmed_d}"  fill="none" stroke="#FFAE77" stroke-width="1.9" opacity="0.85"/>
            <path d="{cslow_d}" fill="none" stroke="#7777FF" stroke-width="2"   opacity="0.85"/>
            <g class="rv6-svgtext" font-size="9" fill="rgba(17,17,24,0.7)">
              <text x="118" y="238">fast — moment to moment</text>
              <text x="118" y="278">medium — day to day</text>
              <text x="118" y="318">slow — the long arc</text>
            </g>
            <text x="118" y="215" class="rv6-svgtext" font-size="10.5" fill="#111118">what we can measure</text>

            <!-- nested containment timescales -->
            <g fill="none" stroke="#1a2c6b" stroke-width="1.3">
              <path d="M60 364 v72 h780 v-72"/>
              <path d="M60 364 v58 h640 v-58"/>
              <path d="M60 364 v44 h480 v-44"/>
              <path d="M60 364 v30 h330 v-30"/>
              <path d="M60 364 v18 h190 v-18"/>
            </g>
            <g class="rv6-svgtext" font-size="10" fill="#1a2c6b" text-anchor="end">
              <text x="244" y="380">seconds</text><text x="384" y="392">minutes</text>
              <text x="534" y="406">hours</text><text x="694" y="420">days</text><text x="834" y="434">years</text>
            </g>
            <text x="60" y="456" class="rv6-svgtext" font-size="8.5" fill="rgba(17,17,24,0.55)">nested timescales — seconds within minutes within hours within days within years</text>
          </svg>
        </div>
      </div>
      <div class="rv6-cap">how it composes</div>
      <p class="rv6-mockup-title">Superposition</p>
      <p class="rv6-mockup-desc">One bold state curve drawn honestly as the sum of three nested rhythms — a slow long arc, a medium day-to-day wave, and fast moment-to-moment jitter. Below, the same three components are stacked as a decomposition with +/=, vertically aligned so you can see each rhythm living inside the composite. Nested timescales become intrinsic to the curve itself.</p>
    </div>
  </div>
</div>
'''.format(bod_d=bod_d, beh_d=beh_d, drop_svg=drop_svg,
           segA_d=segA_d, segB_d=segB_d, segC_d=segC_d,
           comp_d=comp_d, cfast_d=cfast_d, cmed_d=cmed_d, cslow_d=cslow_d)

with open(OUT, "w") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "bytes")
