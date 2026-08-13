# Research visual — known follow-ups

Recorded 2026-08-13, at the end of the implementation branch. The feature is
built, reviewed, and passing; none of these blocked merge. They are written
down so they are not rediscovered from scratch.

Design doc: `2026-08-06-homepage-research-visual-design.md`
Plan: `../plans/2026-08-09-homepage-research-visual.md`

## Needs Shabnam's decision

**Two tab stops per area node.** Each node is a `role="button"` group with
`tabindex="0"` that *contains* a real `<a href="projects.html#…">` around the
title. Nesting interactive elements is an ARIA anti-pattern. Both stops are
operable and correctly labeled, so the page works — but the final review added
a consequence the earlier reviews missed: ARIA's children-presentational rule
for `button` means assistive tech may drop those eight links from its link
list entirely, not merely announce them twice.

Fixing it spans three layers: move `role="button"`/`aria-expanded` off the
group and onto the marker, and change the CSS reveal selector from
`[aria-expanded="true"] + .ag-card` to something like
`g:has([aria-expanded="true"]) + .ag-card`. Deferred because a three-layer
restructure late in the branch carried more regression risk than the defect,
and because whether the link list matters is a judgment about her visitors.

## Copy, still outstanding by design

- **The section title.** Written by Shabnam via `site-content.md`, the normal
  site copy route. The figure reserves 34px of headroom (`TOP_PAD`) so it drops
  in with zero relayout.
- **One connective line** between the approach figure and the area graph. The
  spec's reasoning: the page split means this asserts the relationship once
  rather than carrying meaning for eight areas.

## Deliberately not done

- **Animation.** Both figures ship static. `index.html`'s hero already runs a
  canvas animation; a second animated element is a separate decision.
- **Tablet polish** between 420px and 1000px, where the mobile figure sits
  centered with whitespace either side. Judged acceptable.
- **Context as geometry.** It lives only in her sentence ("in the right
  context"). Everything the figure draws unfolds over time; context is the
  dimension that doesn't.

## Minor engineering backlog

From the final whole-branch review; none affect behavior today.

- `inject()` has no guard for multiple or cross-nested markers of different
  names (it guards a payload containing its own markers).
- No test asserts SVG `<defs>` id uniqueness across the three injected blocks.
  They are unique today; nothing enforces it.
- The generators do real work at import time rather than inside functions.
- `CLAUDE.md`'s graph node/edge/cluster counts are stale (they predate this
  work and drift with every graph change).
- The click script re-sets a `tabindex="0"` the generator already emits.
- `area_graph.py`'s grid parser raises an uncaught `AssertionError` on a
  malformed grid title, so a corrupted page yields a traceback rather than a
  clean test failure. Exit code is 1 either way.
- A stale `figures/__pycache__` can make `test_sync.py` report a false
  staleness failure. Documented in `figures/README.md`, including the ordering
  that matters: clear the cache and re-run the test *before* running
  `build.py`, or you bake stale output into the page.

## Not verified by machine

The final review could not run a browser or a screen reader. The responsive
behavior was measured with Playwright during implementation at 375, 999, 1000
and 1280px, but no visual design pass and no assistive-technology pass has been
done on the merged result.
