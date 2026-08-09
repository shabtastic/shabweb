# figures/

Generators for the homepage research visual. **These are the source of truth —
never hand-edit the injected SVG in index.html.**

- `approach.py`         desktop approach figure (1040x482)
- `approach_mobile.py`  narrow-screen variant (336x329), imports approach.py
- `area_graph_data.py`  graph.json loading, cluster pair weights, layout solver
- `area_graph.py`       eight-area graph; scrapes index.html for area titles
- `build.py`            regenerates all three and injects them into index.html

Regenerate after changing any generator, or after `graph/graph.json` or the
research-area text in index.html changes:

    python3 figures/build.py

Tests: `python3 figures/test_generators.py`

Design doc: docs/superpowers/specs/2026-08-06-homepage-research-visual-design.md
Mockup history: docs/superpowers/mockups/homepage-research-viz/
