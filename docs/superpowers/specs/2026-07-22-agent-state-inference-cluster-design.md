# Agent State Inference — 8th graph cluster — design

**Date:** 2026-07-22
**Status:** Draft — awaiting approval

## Problem

`site-content.md`'s projects.html draft has a theme, "Agent State Inference," that isn't one of the 7 graph clusters shipped in the 2026-07-22 cluster rename (see `docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md`). Its three papers (Sumner2024personalizing, DeCastro2022latent, Gopinath2022hmiway) currently sit inside cluster 4 "Preference Elicitation & Prediction." `site-content.md` frames the theme as methodologically distinct — "the focus is on inference and simulation infrastructure, not persuasion" — so folding it into Preference Elicitation blurs a real distinction, the same kind of over-broad grouping this session already split apart elsewhere (e.g. pulling "Creativity & Design" out from under "decision making").

## Decision

Add an 8th cluster: **id 7, "Agent State Inference,"** color `#AAFF77` (new `--h-lime` token — fills the one hue gap in the current 7-color highlighter palette, which spans yellow/slate/heliotrope/violet/red/orange/mint but has nothing in the pure lime/green range).

## Node split

Verified via `graph/graph.json` in the (unmerged) `graph-cluster-rename-impl` branch: the three papers contribute exactly 16 nodes, and **all 16 belong only to these three papers** — zero overlap with any other paper remaining in cluster 4. This is a clean cut, not a weighted-vote situation; no node-reassignment algorithm is needed, just a direct move.

Nodes moving from cluster 4 → cluster 7: `alert_fatigue`, `bounded_rationality`, `cognitive_inference`, `distracted_driving`, `driver_assistance`, `hmi_personalization`, `human_machine_teaming`, `impulsivity`, `inhibitory_control`, `inverse_rl`, `latent_driver_rep`, `policy_personalization`, `recurrent_nn`, `risky_driving`, `sensation_seeking`, `shared_autonomy`.

## Files affected

1. **`graph/graph.json`** — add `{id: 7, name: "Agent State Inference"}` to `meta.clusters`; set `cluster: 7` on the 16 nodes listed above.
2. **`node data/inline-graph.js`** — re-run to resync `index.html`/`graph.html` inlined blocks (unchanged mechanism from the prior rename).
3. **`graph.html`**:
   - Two hardcoded-`7` bugs must be fixed or an 8th cluster's nodes will silently vanish from sidebar counts: `const clusterCounts = new Array(7).fill(0);` (~line 9338) → must size off `graphData.meta.clusters.length`, and `if (n.cluster < 7)` (~line 9339) → must use the same dynamic length, not a literal `7`.
   - Optional/cheap: the `|| 7` fallback literal at ~line 9231 (`const numClusters = graphData.meta?.clusters?.length || 7;`) should become `|| 8` or, better, just removed as a magic-number fallback now that it's provably wrong the moment cluster count changes again — flag for the plan to decide.
   - Add an 8th static `.cluster-item` block (swatch `#AAFF77`, name "Agent State Inference", a one-sentence desc, `data-cluster="7"`, `id="cluster-count-7"`) to the sidebar markup alongside the existing 7.
   - Add an 8th entry to the hardcoded `clusterData` JS array (name/short/desc/color/hex_r/g/b), matching the existing single-line-literal style.
4. **`projects.html`**:
   - Add `.c7 { --cc: var(--h-lime); }` after the existing `.c0`–`.c6` block (line 40).
   - Add `--h-lime: #AAFF77;` to the `:root` palette variable block alongside the other `--h-*` tokens.
   - Fix the prose literal "...grouped into seven conceptual clusters..." (line 560) → "eight."
   - No project-item chip changes needed yet — the current Ongoing/Past/Tools structure has no project representing this theme (Agent State Inference's papers aren't referenced by any existing project-item). This surfaces properly once the 6/7/8-theme projects.html rebuild happens (separate, already-tracked follow-up).
5. **`cv.html`** — add `--h-lime: #AAFF77;` to its `:root` palette block for consistency (cv.html carries the full palette even though it doesn't use `.c0`–`.c6` classes itself).
6. **`extracurriculars.html`** — fix the prose literal "...highlighter palette tied to seven research clusters..." (line 472) → "eight."
7. **`CLAUDE.md`** — add row 7 to the "Research clusters" table; add `--h-lime: #AAFF77 /* lime green */` to the Design system highlighter palette block.

## Out of scope

- Adding an "Agent State Inference" project-item to projects.html's chip UI — blocked on the broader page rebuild, not this change.
- Renaming `--h-lime` if a better name surfaces (e.g. matching the existing naming style more closely — "electric lime," "highlighter lime," etc.) — pick one now, don't bikeshed; can rename trivially later since it's one CSS custom property.

## Verification plan

1. `graph/graph.json`: `meta.clusters.length === 8`; exactly 16 nodes have `cluster === 7`; total node count unchanged (339).
2. `graph.html` sidebar shows 8 cluster items with correct counts (cluster-count-7 should read "16 concepts" or similar, not blank/zero — this is the regression the hardcoded-7 fix prevents).
3. `graph.html`'s "projects →" overlay for cluster 7 shows exactly the 3 papers (Sumner2024personalizing, DeCastro2022latent, Gopinath2022hmiway).
4. `projects.html` and `extracurriculars.html` no longer say "seven" anywhere referring to cluster count.
