"""Fails if index.html's injected SVG is stale, or if any figure text is
not verbatim from the research grid. Run: python3 figures/test_sync.py"""
import os, re, sys, html as _html
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import approach, approach_mobile, area_graph

SRC = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()


def block(marker):
    o, c = "<!-- FIGURE:%s -->" % marker, "<!-- /FIGURE:%s -->" % marker
    return SRC[SRC.index(o) + len(o):SRC.index(c)]


def test_injected_matches_generators():
    for marker, mod in (("approach", approach),
                        ("approach-mobile", approach_mobile),
                        ("area-graph", area_graph)):
        assert block(marker) == mod.svg_fragment(), (
            "%s is stale in index.html — run python3 figures/build.py" % marker)


def flatten(s):
    """Unescape HTML entities, then collapse whitespace. Applied to both
    sides of the grid-vs-SVG title comparison so an entity that's literal
    on one side (index.html's &amp;) and a real character on the other
    (Python str) never causes a false mismatch."""
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()


def join_title_lines(lines):
    """Rejoin wrapped <text class="ag-title"> line contents into one string.

    Most line breaks are ordinary word wraps (area_graph.py's wrap(), which
    only ever breaks at whitespace) and need a space reinserted between
    lines. But the two due-left/due-right nodes use wrap_tight(), which may
    ALSO break immediately after a hyphen already present in the word (e.g.
    "Psychology-Guided" -> lines "Psychology-" then "Guided") with no space
    in the original text at that point. So: don't insert a space when the
    previous line already ends in "-" — that hyphen is real title text, not
    a wrap artifact, and the next line continues the same word.
    """
    out = ""
    for i, ln in enumerate(lines):
        if i == 0:
            out = ln
        elif out.endswith("-"):
            out += ln
        else:
            out += " " + ln
    return out


def area_titles_from_svg(drawn):
    """The title actually drawn for each area node, as one flat string.

    Each area's title is split across one or more sibling
    <text class="ag-title">...</text> elements — the wrap points area_graph.py
    chose for that title's line length — all wrapped in a single
    <a href="projects.html#...">...</a> click target. A substring check
    against the raw SVG markup would either miss a real mismatch (if the
    corrupted text happens to still appear as a substring somewhere) or
    reject a correct page (if a legitimately wrapped title never appears as
    one contiguous substring). So this reconstructs each area's title by
    concatenating its <text class="ag-title"> line contents in document
    order (see join_title_lines for the hyphen-wrap subtlety), unescaping
    entities the same way as the grid side, and returns one string per area
    node — order-independent, ready for a set/multiset comparison against
    the grid's <h3> titles.
    """
    titles = []
    for a_body in re.findall(
        r'<a href="projects\.html#[^"]*">(.*?)</a>', drawn, re.S
    ):
        lines = re.findall(
            r'<text class="ag-title"[^>]*>(.*?)</text>', a_body, re.S
        )
        titles.append(flatten(join_title_lines(lines)))
    return titles


def test_area_titles_are_verbatim():
    grid = SRC[SRC.index('<div class="research-grid">'):]
    grid = grid[:grid.index("</section>")]
    titles = [
        flatten(re.sub(r"<[^>]+>", "", t))
        for t in re.findall(r"<h3>(.*?)</h3>", grid, re.S)
    ]
    assert len(titles) == 8, len(titles)

    drawn = block("area-graph")
    svg_titles = area_titles_from_svg(drawn)
    assert len(svg_titles) == 8, (
        "expected 8 area titles drawn in the area-graph SVG, found %d: %r"
        % (len(svg_titles), svg_titles)
    )

    # Multiset comparison, not positional: the SVG's ring order is a layout
    # decision (circular graph position), not the grid's 01-08 order, so the
    # two lists are matched as sets of titles, not index-by-index.
    assert sorted(titles) == sorted(svg_titles), (
        "research-grid <h3> titles don't match what's drawn in the "
        "area-graph SVG — run python3 figures/build.py if the drawing is "
        "just stale, or fix the mismatched title if it isn't:\n"
        "  grid titles: %r\n  svg titles:  %r" % (sorted(titles), sorted(svg_titles))
    )


def test_no_placeholder_title_in_figures():
    for marker in ("approach", "approach-mobile", "area-graph"):
        b = block(marker).lower()
        for bad in ("lorem", "tbd", "placeholder", "untitled"):
            assert bad not in b, (marker, bad)


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e))
    print(("%d failure(s)" % fails) if fails else "all passed")
    sys.exit(1 if fails else 0)
