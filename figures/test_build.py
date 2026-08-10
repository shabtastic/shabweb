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

def test_inject_is_idempotent_when_payload_contains_marker_like_text():
    """Known limitation, documented not fixed: inject() finds the closer with
    html.find(close_tag, start). If the injected payload itself contains the
    literal closing-marker text, the SECOND run's search stops at the copy
    embedded in the payload instead of the real closer further along, so the
    tail between them gets duplicated instead of the file staying idempotent.
    This asserts what the code actually does today, not what we'd prefer.
    Task 3's fix-round investigation found the real generators do not
    currently emit this literal string (see figures/test_build.py's sibling
    report), so this is a latent risk, not an active bug -- but inject()
    itself has no guard against it.
    """
    src = "a<!-- FIGURE:x -->OLD<!-- /FIGURE:x -->b"
    payload = "NEW<!-- /FIGURE:x -->TAIL"
    once = build.inject(src, "x", payload)
    assert once == "a<!-- FIGURE:x -->NEW<!-- /FIGURE:x -->TAIL<!-- /FIGURE:x -->b", once
    twice = build.inject(once, "x", payload)
    assert twice != once, "expected the documented corruption, not true idempotency"
    assert twice == (
        "a<!-- FIGURE:x -->NEW<!-- /FIGURE:x -->TAIL<!-- /FIGURE:x -->TAIL<!-- /FIGURE:x -->b"
    ), twice

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
