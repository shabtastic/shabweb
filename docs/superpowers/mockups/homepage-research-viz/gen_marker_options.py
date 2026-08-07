"""Six treatments for the intervention marker, drawn on v21's real geometry.

Nothing here is redrawn by hand. gen_v21.py is executed in a private namespace
(with its file write suppressed) and every curve, strand, tick, band and label in
the crops below is the same string v21 emits. Only the marker differs.

No copy is added anywhere. The crops carry bare letters and nothing else.
"""
import builtins, contextlib, io, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "gen_v21.py")
OUT  = os.path.join(HERE, "research-viz-marker-options.html")

# ---------- load v21's geometry without letting it write its own file ----------
_real_open = builtins.open
class _Sink:
    def write(self, *a): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
def _open(path, mode="r", *a, **k):
    if "w" in str(mode) or "a" in str(mode): return _Sink()
    return _real_open(path, mode, *a, **k)

V = {"__name__": "v21", "__file__": SRC}
with _real_open(SRC) as f:
    src = f.read()
builtins.open = _open
try:
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, SRC, "exec"), V)
finally:
    builtins.open = _real_open

poly       = V["poly"]
estimate   = V["estimate"]
true_state = V["true_state"]
err_env    = V["err_env"]
NUDGE_X    = V["NUDGE_X"]
INT_COL    = V["INT_COL"]
TICK_COL   = V["TICK_COL"]
GREY_W     = V["GREY_W"]
TOP_PAD    = V["TOP_PAD"]
bounds     = V["bounds"]
widths     = V["widths"]

gy = true_state(NUDGE_X)          # 241.2 — the grey curve at the marker
ey = estimate(NUDGE_X)            # 239.5 — the estimate at the marker
abut = gy + GREY_W / 2.0          # the grey stroke's lower edge

# ---------------------------------------------------------------- treatments --
# A — v21 as it stands: filled equilateral, apex up, abutting the grey from below.
A_R = V["TRI_R"]
A_hw, A_h = A_R * math.sqrt(3) / 2.0, A_R * 1.5
tri_A = poly([(NUDGE_X, abut), (NUDGE_X + A_hw, abut + A_h), (NUDGE_X - A_hw, abut + A_h)]) + " Z"
T_A = '<path d="%s" fill="%s" stroke="none"/>' % (tri_A, INT_COL)

# B — the olive ticks' own grammar, purple and hanging down off the grey curve.
#     Same stroke-then-droplet form, same lengths; heavier and opaque so it reads
#     as a deliberate act rather than another observation.
B_STEM, B_DROP, B_R = 16.0, 20.0, 2.2
T_B  = '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.6" opacity="0.95"/>' % (
    NUDGE_X, gy, NUDGE_X, gy + B_STEM, INT_COL)
T_B += '<circle cx="%d" cy="%.1f" r="%.1f" fill="%s"/>' % (NUDGE_X, gy + B_DROP, B_R, INT_COL)

# C — filled diamond centred on the grey curve.
C_RX, C_RY = 5.2, 7.0
T_C = '<path d="%s Z" fill="%s" stroke="none"/>' % (poly([
    (NUDGE_X, gy - C_RY), (NUDGE_X + C_RX, gy), (NUDGE_X, gy + C_RY), (NUDGE_X - C_RX, gy)]), INT_COL)

# D — open caret, same footprint as A, stroked instead of filled.
T_D = '<path d="M %.1f %.1f L %d %.1f L %.1f %.1f" fill="none" stroke="%s" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>' % (
    NUDGE_X - A_hw, abut + A_h, NUDGE_X, abut, NUDGE_X + A_hw, abut + A_h, INT_COL)

# E — no glyph. A stretch of the estimate itself changes hue, nothing else.
#     Drawn as an overdraw of the identical path at the identical per-band width,
#     so weight, join and cap are bit-for-bit the navy line's.
E_HALF = 14.0
def hue_shift(x0, x1, col):
    out = ""
    for i in range(len(widths)):
        lo, hi = max(bounds[i], x0), min(bounds[i + 1], x1)
        if hi - lo < 0.5: continue
        pts = [(x, estimate(x)) for x in
               [lo + j * (hi - lo) / max(1, int(hi - lo)) for j in range(int(hi - lo) + 1)]]
        out += ('<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" '
                'stroke-linejoin="round" stroke-linecap="round"/>' % (poly(pts), col, widths[i]))
    return out
T_E = hue_shift(NUDGE_X - E_HALF, NUDGE_X + E_HALF, INT_COL)

# F — my proposal: a highlighter swipe across the moment.
#     The site is built on a highlighter palette; a swipe over an instant is the
#     one mark this figure can make that needs no explaining, because everyone
#     already knows what a highlighter means. It is a fill, not a line and not a
#     dot, so it cannot be confused with the olive ticks; it is vertical, like
#     'now', so it reads as a moment in time rather than an object; and it holds
#     at any size because it is an area. A hairline core keeps it from going soft.
F_W = 13.0
F_TOP = min(estimate(NUDGE_X) - err_env(NUDGE_X), gy) - 9
F_BOT = max(estimate(NUDGE_X) + err_env(NUDGE_X), gy) + 13
T_F  = '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" opacity="0.30"/>' % (
    NUDGE_X - F_W / 2, F_TOP, F_W, F_BOT - F_TOP, F_W / 2, INT_COL)
T_F += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.5" opacity="0.85"/>' % (
    NUDGE_X, F_TOP + 4, NUDGE_X, F_BOT - 4, INT_COL)

TREATMENTS = [("A", T_A), ("B", T_B), ("C", T_C), ("D", T_D), ("E", T_E), ("F", T_F)]
RECOMMENDED = "F"

# ------------------------------------------------------------------- the crops --
WX0, WX1 = 515, 685        # the window, centred on x=600
WY0, WY1 = 218, 268
SCALE    = 2.75
CW, CH   = (WX1 - WX0) * SCALE, (WY1 - WY0) * SCALE     # 467.5 x 137.5
MARGIN, GAPX, GAPY, LBL = 24, 46, 30, 20
COLS = 2
SHEET_W = MARGIN * 2 + CW * COLS + GAPX * (COLS - 1)
ROWS = (len(TREATMENTS) + COLS - 1) // COLS
SHEET_H = MARGIN * 2 + ROWS * (LBL + CH) + (ROWS - 1) * GAPY

def crop(letter, marker, idx):
    r, c = divmod(idx, COLS)
    tx = MARGIN + c * (CW + GAPX)
    ty = MARGIN + r * (LBL + CH + GAPY)
    cid = "clip%s" % letter
    est = V["est_svg"] + marker if letter == "E" else V["est_svg"]
    mk  = "" if letter == "E" else marker
    s  = '<text x="%.1f" y="%.1f" class="mo-txt" font-size="13" font-weight="700" fill="#111118">%s</text>\n' % (
        tx, ty + 13, letter)
    s += '<g clip-path="url(#%s)">\n' % cid
    s += '  <g transform="translate(%.1f,%.1f) scale(%.4f) translate(%.1f,%.1f)">\n' % (
        tx, ty + LBL, SCALE, -WX0, -WY0)
    s += '    <rect x="%d" y="%d" width="%d" height="%d" fill="#f5f2ec"/>\n' % (WX0, WY0, WX1-WX0, WY1-WY0)
    s += '    <rect x="%d" y="%d" width="%d" height="%d" fill="url(#moGmin)"/>\n' % (WX0, WY0, WX1-WX0, WY1-WY0)
    s += '    <path d="%s" fill="rgba(26,44,107,0.07)" stroke="none"/>\n' % V["band_outer"]
    s += '    <path d="%s" fill="rgba(26,44,107,0.09)" stroke="none"/>\n' % V["band_inner"]
    s += '    <path d="%s" fill="none" stroke="rgba(17,17,24,0.30)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>\n' % V["ts_d"]
    s += "    %s\n    %s\n    %s\n    %s\n" % (V["strand_svg"], V["ask_svg"], est, mk)
    s += "  </g>\n</g>\n"
    s += '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="rgba(17,17,24,0.18)" stroke-width="1"/>\n' % (
        tx, ty + LBL, CW, CH)
    return s, (cid, tx, ty + LBL)

crops, clips = "", ""
for i, (letter, marker) in enumerate(TREATMENTS):
    body, (cid, cx, cy) = crop(letter, marker, i)
    crops += body
    clips += '<clipPath id="%s"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath>\n' % (
        cid, cx, cy, CW, CH)

# ------------------------------- the full figure, with the recommendation in it --
full = V["HTML"]
rec_marker = dict(TREATMENTS)[RECOMMENDED]
assert V["nudge_svg"] in full, "v21's marker string not found in its own fragment"
full = full.replace(V["nudge_svg"], rec_marker)
full = full.replace(".rv21-", ".mo-rv21-").replace('class="rv21-', 'class="mo-rv21-')

HTML = """<!-- research-viz-marker-options -->
<style>
  .mo-wrap {{ --paper:#f5f2ec; --ink:#111118; font-family:'Space Mono', monospace; background:#f5f2ec; }}
  .mo-wrap svg {{ display:block; width:100%; height:auto; }}
  .mo-txt {{ font-family:'Space Mono', monospace; }}
  .mo-rule {{ border:0; border-top:1px solid rgba(17,17,24,0.15); margin:0; }}
</style>

<div class="mo-wrap">
  <svg viewBox="0 0 {sw:.0f} {sh:.0f}" role="img" aria-label="Six treatments of the intervention marker, each shown on the same zoomed crop of the figure around x=600, labelled A to F">
    <defs>
      <pattern id="moGmin" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="rgba(80,140,200,0.20)" stroke-width="1"/></pattern>
      {clips}
    </defs>
    <rect width="{sw:.0f}" height="{sh:.0f}" fill="#f5f2ec"/>
    {crops}
  </svg>
  <hr class="mo-rule"/>
{full}
</div>
""".format(sw=SHEET_W, sh=SHEET_H, clips=clips, crops=crops, full=full)

with _real_open(OUT, "w") as f:
    f.write(HTML.encode("ascii", "xmlcharrefreplace").decode("ascii"))

print("wrote", OUT, len(HTML), "bytes")
print("crop window x %d..%d  y %d..%d  at %.2fx -> %.1f x %.1f px each" % (
    WX0, WX1, WY0, WY1, SCALE, CW, CH))
print("sheet %.0f x %.0f, %d treatments in %d cols" % (SHEET_W, SHEET_H, len(TREATMENTS), COLS))
print("grey true state at x=600 = %.3f (abut edge %.3f)   estimate = %.3f" % (gy, abut, ey))
print("recommended = %s, applied to the full figure below the sheet" % RECOMMENDED)
for letter, marker in TREATMENTS:
    print("  %s: %d chars, %d path(s), %d line(s), %d circle(s), %d rect(s)" % (
        letter, len(marker), marker.count("<path"), marker.count("<line"),
        marker.count("<circle"), marker.count("<rect")))
