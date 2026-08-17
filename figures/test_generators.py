"""Plain-assert tests. Run: python3 figures/test_generators.py"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import approach, approach_mobile, area_graph

def test_approach_viewbox():
    s = approach.svg_fragment()
    assert s.startswith("<svg"), s[:40]
    # 448 = 482 - the 34px TOP_PAD that reserved room for a title inside the
    # figure; the title is HTML now, so the band is gone.
    assert 'viewBox="0 0 1040 448"' in s

def test_mobile_viewbox():
    s = approach_mobile.svg_fragment()
    assert s.startswith("<svg"), s[:40]
    assert 'viewBox="0 0 336 329"' in s

def test_area_graph_viewbox():
    # Width (1040) is fixed; height is solved dynamically by the label-placement
    # solver (it depends on how much room the longest area title/description
    # needs), so only the width half of the viewBox is asserted here.
    s = area_graph.svg_fragment()
    assert s.startswith("<svg"), s[:40]
    assert 'viewBox="0 0 1040 ' in s, s[:80]

def test_no_generator_writes_html_on_import():
    # importing must not have written any mockup file into figures/
    stray = [f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
             if f.endswith(".html")]
    assert stray == [], stray

def test_paths_resolve_inside_this_repo():
    import area_graph, area_graph_data
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (area_graph.INDEX_PATH, area_graph_data.GRAPH_PATH):
        assert os.path.abspath(p).startswith(root + os.sep), p
        assert os.path.exists(p), p

def test_every_node_links_to_projects():
    # projects.html's real anchor ids include a hyphenated one
    # (section-agent-state), so the class matches [a-z-]+, not just [a-z]+.
    s = area_graph.svg_fragment()
    hrefs = re.findall(r'href="(projects\.html#section-[a-z-]+)"', s)
    assert len(hrefs) == 8, hrefs
    assert len(set(hrefs)) == 8, "duplicate hrefs: %r" % hrefs

def test_nodes_are_expandable_buttons():
    s = area_graph.svg_fragment()
    assert s.count('aria-expanded="false"') == 8, s.count('aria-expanded="false"')
    assert s.count('role="button"') == 8

def test_the_link_lives_in_the_card_not_the_button():
    # The link into projects.html used to wrap each node's title INSIDE the
    # role="button" group -- an <a> nested in a button, which is an ARIA
    # anti-pattern (two tab stops per node, and the children-presentational
    # rule lets assistive tech drop the eight links from its link list). It
    # now lives inside the card instead. Two things must hold, and neither is
    # implied by test_every_node_links_to_projects, which only counts hrefs:
    #   1. no <a> anywhere inside a button group, or the anti-pattern is back;
    #   2. exactly one <a> per card, carrying that area's own anchor.
    s = area_graph.svg_fragment()
    for g_body in re.findall(r'<g role="button"[^>]*>(.*?)</g>', s, re.S):
        assert "<a " not in g_body and "<a>" not in g_body, (
            "a link is nested inside a role=button group: %r" % g_body[:120]
        )
    for cid in area_graph.CIDS:
        marker = 'id="ag-card-%d"' % cid
        i = s.index(marker)
        card = s[s.rindex("<g", 0, i) : s.index("</g>", i)]
        hrefs = re.findall(r'<a href="(projects\.html#[^"]+)"', card)
        assert hrefs == ["projects.html#%s" % area_graph.SECTION_ANCHOR[cid]], (
            "card %d should hold exactly its own projects link, got %r"
            % (cid, hrefs)
        )

def test_card_names_where_it_goes():
    # The card is the click target, so it must carry a visible affordance
    # saying so -- an unlabeled clickable panel is the failure mode this
    # replaced the title-link with. One .ag-link row per card, and its text
    # is LINK_LABEL, which is graph.html's existing string rather than new
    # copy invented for the figure.
    s = area_graph.svg_fragment()
    rows = re.findall(r'<text class="ag-link"[^>]*>(.*?)</text>', s, re.S)
    assert len(rows) == 8, rows
    assert set(rows) == {area_graph.esc(area_graph.LINK_LABEL)}, rows

def test_area_graph_has_accessible_name():
    # Task 4 finding: the area graph is interactive (click/keyboard), so
    # role="img" (used by the two decorative-ish approach figures) would be
    # wrong -- it needs a name via role="group" + aria-label instead, and
    # that label must land on the SVG root, not some inner group.
    s = area_graph.svg_fragment()
    root = s[: s.index(">") + 1]
    assert 'role="group"' in root, root
    assert 'aria-label="' in root, root
    assert 'role="img"' not in root, root

def test_each_button_is_followed_by_its_card():
    # Tasks 5 and 6 depend on this adjacency: the CSS selector that reveals a
    # description is [aria-expanded="true"] + .ag-card, so the card must be the
    # button group's IMMEDIATE next sibling. Checked per-area and by matching
    # id (not just "some </g> precedes some ag-card somewhere") so a stray
    # <g></g> inserted between a specific button and its own card is caught,
    # not just masked by a different area's correctly-adjacent pair.
    s = area_graph.svg_fragment()
    assert s.count('class="ag-card"') == 8, s.count('class="ag-card"')
    for cid in area_graph.CIDS:
        marker = 'aria-controls="ag-card-%d"' % cid
        i = s.index(marker)
        close = s.index("</g>", i)  # close of this button group
        # Next opening <g tag after that close, attributes or not (a bare
        # "<g></g>" has no space before ">", so search on "<g" not "<g ").
        nxt = s.index("<g", close)
        expected = '<g class="ag-card" id="ag-card-%d"' % cid
        assert s[nxt : nxt + len(expected)] == expected, (
            "card for area %d is not the button's immediate next sibling" % cid
        )

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
