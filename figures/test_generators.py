"""Plain-assert tests. Run: python3 figures/test_generators.py"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import approach, approach_mobile, area_graph

def test_approach_viewbox():
    s = approach.svg_fragment()
    assert s.startswith("<svg"), s[:40]
    assert 'viewBox="0 0 1040 482"' in s

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
