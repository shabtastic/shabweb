"""Turn the homepage approach figure into editable-shape data for build.js.

Prints JSON: the figure's viewBox and its elements sorted into the six steps
the slide reveals one click at a time. build.js draws each element as a
native shape and groups each step, so every curve and label stays editable.

The SVG comes straight from figures/approach.py, so the slide version
follows the homepage one. Every word is Shabnam's, verbatim: lines that
belong together (a two-line label) are merged into one text box, never
reworded.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "figures"))
import approach  # noqa: E402

PAPER = (0xF5, 0xF2, 0xEC)

# Reveal order. Each element goes to the first step whose test it passes.
STEPS = [
    "A person's true internal state",
    "Signals",
    "Our best guess",
    "Now and the forecast",
    "Intervention",
    "Timescales",
]


def parse_color(v):
    """'#rrggbb' or 'rgba(r,g,b,a)' -> ('RRGGBB', alpha); None for none."""
    if not v or v == "none":
        return None
    if v.startswith("#"):
        return v[1:].upper(), 1.0
    m = re.match(r"rgba?\(([^)]*)\)", v)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        r, g, b = (int(float(p)) for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return f"{r:02X}{g:02X}{b:02X}", a
    raise ValueError(f"colour {v!r}")


def flatten(color):
    """Text colour with alpha, composited onto paper (text transparency
    doesn't survive Google Slides)."""
    hexv, a = color
    rgb = [int(hexv[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(c * a + p * (1 - a)):02X}" for c, p in zip(rgb, PAPER))


def paint(attrs, key):
    c = parse_color(attrs.get(key))
    if c is None:
        return None
    op = float(attrs.get("opacity", 1))
    return {"color": c[0], "alpha": round(c[1] * op, 4)}


def path_points(d):
    """SVG path data (M L H V Q Z, absolute) -> list of subpaths."""
    toks = re.findall(r"[MLHVQZ]|-?\d*\.?\d+(?:e-?\d+)?", d)
    subs, cur, x, y, i, closed = [], None, 0.0, 0.0, 0, False
    while i < len(toks):
        c = toks[i]; i += 1
        if c == "M":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            cur = [{"x": x, "y": y}]; subs.append(cur)
        elif c == "L":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            cur.append({"x": x, "y": y})
        elif c == "H":
            x = float(toks[i]); i += 1
            cur.append({"x": x, "y": y})
        elif c == "V":
            y = float(toks[i]); i += 1
            cur.append({"x": x, "y": y})
        elif c == "Q":
            x1, y1, x, y = (float(t) for t in toks[i:i + 4]); i += 4
            cur.append({"x": x, "y": y, "q": [x1, y1]})
        elif c == "Z":
            closed = True
        else:
            raise ValueError(f"path command {c!r}")
    return subs, closed


def step_of(el):
    """Which reveal step an element belongs to."""
    t = el["t"]
    fill = (el.get("fill") or {}).get("color")
    stroke = (el.get("stroke") or {}).get("color")
    text = " ".join(l["text"] for l in el.get("lines", []))
    if t == "text":
        if text.startswith(("a person", "(that we")):
            return 0
        if text.startswith(("measurable", "physiology", "observable", "behavior", "individual")):
            return 1
        if text.startswith("our best guess"):
            return 2
        if text.startswith(("now", "without")):
            return 3
        if text.startswith(("the right", "in the right", "intervention", "a higher",
                            "desired", "(internal")):
            return 4
        if text in ("seconds", "hours", "days", "weeks", "years"):
            return 5
        raise ValueError(f"no step for text {text!r}")
    if stroke == "111118" and t == "path":            # grey true-state curve
        return 0
    if fill in ("FF7792", "D9822B", "587722") or stroke in ("FF7792", "D9822B", "587722"):
        return 1                                       # strands, their ends, ticks
    if t == "path" and fill == "1A2C6B" and len(el["subs"][0]) > 10:
        return 2                                       # sampling band
    if t == "path" and stroke == "1A2C6B" and not el["stroke"].get("dash") and el.get("bracket") is None:
        return 2                                       # the estimate itself
    if t == "line" and stroke == "111118":             # the 'now' divider
        return 3
    if t == "path" and fill == "1A2C6B":               # forecast cone
        return 3
    if stroke == "5A6C9E" or (t == "circle" and stroke == "111118"):
        return 3                                       # path and end without intervention
    if fill == "8E24AA" or stroke == "8E24AA":         # the highlighter swipe
        return 4
    if (t == "path" and el["stroke"].get("dash")) or stroke == "FFFF77" or (t == "circle" and fill == "1A2C6B"):
        return 4                                       # path and end with intervention
    if el.get("bracket"):
        return 5
    raise ValueError(f"no step for {el}")


def walk(node, inherited, out):
    attrs = {**inherited, **node.attrib}
    tag = node.tag.split("}")[-1]
    if tag in ("svg", "g"):
        # presentation attributes inherit; opacity on a <g> isn't used here
        keep = {k: v for k, v in attrs.items()
                if k in ("fill", "stroke", "stroke-width", "text-anchor", "font-weight", "font-size")}
        for child in node:
            walk(child, keep, out)
        return
    el = None
    if tag == "path":
        subs, closed = path_points(attrs["d"])
        el = {"t": "path", "subs": subs, "closed": closed}
        if re.fullmatch(r"M[\d. ]+V[\d. ]+H[\d. ]+V[\d. ]+", attrs["d"]):
            el["bracket"] = True                       # a timescale bracket
    elif tag == "circle":
        el = {"t": "circle", **{k: float(attrs[k]) for k in ("cx", "cy", "r")}}
    elif tag == "line":
        el = {"t": "line", **{k: float(attrs[k]) for k in ("x1", "y1", "x2", "y2")}}
    elif tag == "rect":
        el = {"t": "rect", **{k: float(attrs.get(k, 0)) for k in ("x", "y", "width", "height", "rx")}}
    elif tag == "text":
        c = parse_color(attrs.get("fill", "#111118"))
        el = {"t": "text", "x": float(attrs["x"]), "anchor": attrs.get("text-anchor", "start"),
              "lines": [{"text": "".join(node.itertext()), "y": float(attrs["y"]),
                         "size": float(attrs["font-size"]),
                         "bold": attrs.get("font-weight") == "700",
                         "color": flatten(c)}]}
    if el is None:
        return
    if el["t"] != "text":
        el["fill"] = None if el["t"] == "line" else paint(attrs, "fill")
        el["stroke"] = paint(attrs, "stroke")
        if el["stroke"]:
            el["stroke"]["width"] = float(attrs.get("stroke-width", 1))
            if attrs.get("stroke-dasharray"):
                el["stroke"]["dash"] = attrs["stroke-dasharray"]
    out.append(el)


def merge_text(els):
    """Fold consecutive text lines that share x, anchor and step into one
    box, so a two-line label edits as one piece."""
    out = []
    for el in els:
        prev = out[-1] if out else None
        if (el["t"] == "text" and prev and prev["t"] == "text"
                and prev["x"] == el["x"] and prev["anchor"] == el["anchor"]
                and prev["step"] == el["step"]
                and 0 < el["lines"][0]["y"] - prev["lines"][-1]["y"] < 2.2 * el["lines"][0]["size"]):
            prev["lines"] += el["lines"]
        else:
            out.append(el)
    return out


def main():
    root = ET.fromstring(approach.SVG)
    vb = [float(v) for v in root.attrib["viewBox"].split()]
    els = []
    walk(root, {}, els)
    for el in els:
        el["step"] = step_of(el)
    els = merge_text(els)
    # Space Mono is wider than the homepage's serif, so the left-column
    # signal labels ("measurable / physiology") fill their whole gutter and
    # touch the strands at x=70. Right-align them a few px short of the
    # strands instead.
    for el in els:
        if el["t"] == "text" and el["step"] == 1 and el["x"] < 70:
            el["anchor"], el["x"] = "end", 64.0
    steps = [{"name": n, "items": [e for e in els if e["step"] == i]} for i, n in enumerate(STEPS)]
    json.dump({"viewBox": vb[2:], "steps": steps}, sys.stdout)


if __name__ == "__main__":
    main()
