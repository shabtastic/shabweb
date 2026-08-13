# Homepage research visual — brainstorm mockups (2026-07-26 → 2026-07-28)

Lo-fi mockup iterations for a new homepage representation of the research
program, replacing the flat 8-box `.research-grid` on index.html. Built in the
visual-companion browser during brainstorming (Opus subagent drew; Shabnam
directed). **Still in brainstorming — no design doc yet, no implementation.**

## Where things stand (v11 = current)

`research-viz-lofi-v11.html` is the latest. Shabnam's last words: the
information is "mostly there"; she was about to **mark up v11 by hand**
(labels to move/change) when we paused. Resume by asking for that markup.

To view any mockup: restart the companion server
(`superpowers/6.2.0/skills/brainstorming/scripts/start-server.sh --project-dir <worktree>`)
and copy the html into the new session's `content/` dir — or just open the file;
it's a fragment, so wrap in any html shell if styling looks bare.

## The design as converged (v11)

A hand-sketched, graph-paper "state estimation" figure, near-label-free,
plain-language (technical vocab reserved for research page). Left → right:

1. **Diverse signal strands** with distinct morphologies (spiky quasi-ECG
   heart, slow skin drift, rounded breath, darty gaze, bursty behavior,
   stepped choices, sparse "asking" droplets at ALL timescales), family margin
   names at left origins. Some strands have **sensor gaps** (discontinuities
   in sampling, never in the state).
2. **Inter-signal web**: quiet arcs between strands — solid = known couplings
   (gaze↔choice the strongest), dotted+"?" = biologically expected,
   not yet characterized (what the ML learns).
3. **Two curves**: faint grey continuous TRUE STATE (never uncertain, never
   broken — uncertainty is in sampling, not the state) + bold ink-blue
   ESTIMATE "triangulated from many signals", wearing a sampling-uncertainty
   band that tightens at each junction and converges onto the true state.
4. **Junction parity** — no proxy prioritized a priori; ONE evidence-earned
   exception: gaze gets the hero junction at the choices plateau
   ("gaze ↔ choice: strong evidence").
5. **Nested containment timescale brackets** below (seconds ⊂ minutes ⊂ hours
   ⊂ days ⊂ years, shared left origin) covering the observed span only.
6. **"now" divider + prediction zone**: true state fades at now; the estimate
   projects a widening dotted forecast cone to an **outcome-of-interest**
   marker; two ghost futures (drift "without it" vs bend to better outcome
   "with the nudge"). Chain: signals → web → triangulated estimate →
   predicted outcome → nudge at right moment → better outcome.

## Hard-won principles (don't regress these)

- **Layperson language everywhere**; 8 cluster names are the only taxonomy text.
- **No unexplained glyphs** (a circle-with-dots "model node" died in v5);
  no floating labels — every label sits at its referent.
- **No dashes for uncertainty** — dashed lines read as discontinuity and
  contradict "the state persists through sampling gaps". Use the band.
- **Compositionality**: the estimate's shape genuinely derives from the
  signals (curves are computed by the gen_v*.py generators, not hand-faked).
- **Utility is prediction-target-dependent**, never a fixed ranking
  (v9 has an alternative "rotating dominance" junction design with per-target
  tags — kept for reference, superseded by v10's parity+gaze).
- Consistent everyday time units; nested containment, not sequential segments.

## Still to do (in brainstorming)

1. Shabnam's markup of v11 → label moves/rewording pass.
2. Layer the **8 cluster-colored area pins** back on (removed in v4 to iterate
   on the base; colors/names must match the site taxonomy in CLAUDE.md).
3. Homepage integration questions not yet discussed: placement (replace
   `.research-grid`?), static SVG vs animated canvas, interactivity
   (pins linking to projects/graph?), mobile behavior.
4. Then: design doc → spec review → writing-plans → implementation.

Generators: `gen_v6.py` … `gen_v11.py` (each extends the previous; v11 is
current). Top-of-file constants are the tuning knobs.
