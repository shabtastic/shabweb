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

def test_inject_raises_when_payload_contains_its_own_closer():
    """Guarded, not silently corrupted: a payload containing a literal copy
    of the closing marker would, without the guard, make a SECOND run's
    html.find(close_tag, start) stop at the copy embedded in the payload
    instead of the real closer further along -- truncating/duplicating
    content instead of staying idempotent. inject() now raises immediately
    on the first run instead of shipping that landmine.
    """
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    payload = "NEW<!-- /FIGURE:x -->TAIL"
    try:
        build.inject(src, "x", payload)
    except ValueError:
        return
    raise AssertionError("expected ValueError for a payload containing its own closer")

def test_inject_raises_when_payload_contains_its_own_opener():
    """Symmetric guard: a payload containing a literal copy of the opening
    marker would corrupt a subsequent run just as badly (a later inject()
    call for the same marker would find the embedded opener instead of, or
    in addition to, the real one). Guarded the same way as the closer.
    """
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    payload = "NEW<!-- FIGURE:x -->TAIL"
    try:
        build.inject(src, "x", payload)
    except ValueError:
        return
    raise AssertionError("expected ValueError for a payload containing its own opener")

def test_inject_raises_on_missing_opener():
    try:
        build.inject("no markers here", "x", "NEW")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a missing opening marker")

def test_inject_raises_on_missing_closer():
    try:
        build.inject("a<!-- FIGURE:x -->OLD", "x", "NEW")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a missing closing marker")

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
