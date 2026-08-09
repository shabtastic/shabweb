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
