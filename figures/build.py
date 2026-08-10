#!/usr/bin/env python3
"""Regenerate the research-visual SVGs and inject them into index.html.

Mirrors data/inline-graph.js: find a marked block, replace its body.
Run after changing any generator, graph/graph.json, or the research-area
text in index.html:

    python3 figures/build.py

Injected content may freely contain ordinary HTML comments -- the approach
and approach-mobile figures already ship a few (production notes baked
into their SVG templates) -- but it must never contain a literal copy of
its own FIGURE:<marker> opener or closer. inject() enforces this with a
ValueError: without the check, a payload containing its own closer would
make a second run of inject() find that embedded copy instead of the real
one and corrupt the file instead of staying idempotent.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
sys.path.insert(0, HERE)


def inject(html, marker, svg):
    """Replace the body between <!-- FIGURE:marker --> and its closer.

    Guards against re-entrancy: if `svg` itself contains a literal copy of
    this marker's opener or closer, the *next* run of inject() would find
    that embedded copy instead of the real one and corrupt the file (either
    truncating the block early or duplicating whatever falls between the
    two closers). Raise loudly here instead of shipping that silently.
    """
    open_tag = "<!-- FIGURE:%s -->" % marker
    close_tag = "<!-- /FIGURE:%s -->" % marker
    if open_tag in svg:
        raise ValueError(
            "svg payload for marker %r contains its own opening marker "
            "%r -- injected content may not contain its own FIGURE markers"
            % (marker, open_tag)
        )
    if close_tag in svg:
        raise ValueError(
            "svg payload for marker %r contains its own closing marker "
            "%r -- injected content may not contain its own FIGURE markers"
            % (marker, close_tag)
        )
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
