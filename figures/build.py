#!/usr/bin/env python3
"""Regenerate the research-visual SVGs and inject them into index.html.

Mirrors data/inline-graph.js: find a marked block, replace its body.
Run after changing any generator, graph/graph.json, or the research-area
text in index.html:

    python3 figures/build.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
sys.path.insert(0, HERE)


def inject(html, marker, svg):
    """Replace the body between <!-- FIGURE:marker --> and its closer."""
    open_tag = "<!-- FIGURE:%s -->" % marker
    close_tag = "<!-- /FIGURE:%s -->" % marker
    start = html.find(open_tag)
    if start == -1:
        raise ValueError("missing marker %r in target" % open_tag)
    end = html.find(close_tag, start)
    if end == -1:
        raise ValueError("missing closing marker %r" % close_tag)
    return html[:start + len(open_tag)] + svg + html[end:]


def main():
    import approach, approach_mobile, area_graph
    html = open(INDEX, encoding="utf-8").read()
    for marker, svg in (
        ("approach",        approach.svg_fragment()),
        ("approach-mobile", approach_mobile.svg_fragment()),
        ("area-graph",      area_graph.svg_fragment()),
    ):
        html = inject(html, marker, svg)
        print("injected FIGURE:%s (%d bytes)" % (marker, len(svg)))
    open(INDEX, "w", encoding="utf-8").write(html)
    print("wrote", INDEX)


if __name__ == "__main__":
    main()
