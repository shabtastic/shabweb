"""Run: python3 figures/test_build.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

def test_inject_replaces_between_markers():
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    out = build.inject(src, "x", "NEW")
    assert out == "a<!-- FIGURE:x -->NEW<!-- /FIGURE:x -->b", out

def test_inject_is_idempotent():
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    once = build.inject(src, "x", "NEW")
    assert build.inject(once, "x", "NEW") == once

def test_inject_raises_on_missing_marker():
    try:
        build.inject("no markers here", "x", "NEW")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a missing marker")

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
