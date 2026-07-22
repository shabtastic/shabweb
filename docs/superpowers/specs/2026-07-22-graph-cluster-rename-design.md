# Graph cluster rename & reassignment — design

**Date:** 2026-07-22
**Status:** Approved for implementation planning

## Problem

`graph/graph.json`'s 7 clusters (`meta.clusters`) don't match the 6 research themes already established for `projects.html`, and the clustering itself is broken: cluster 0 ("Psychology / Cognition") is a 161/339-node catch-all. Two separate, inconsistent naming layers exist today:

- `graph.json` `meta.clusters` — raw names (`Psychology / Cognition`, `Computational / Bayesian`, ...), inlined into `index.html` and `graph.html` via `data/inline-graph.js`, drives graph computation.
- `graph.html`'s hard-coded `clusterData` JS block — friendlier display names (`Psychological Flexibility & Self-Regulation`, ...), used for the sidebar/tooltips only. Documented in CLAUDE.md as intentionally separate.

Neither layer matches the 6 projects.html themes (Preference Elicitation and Prediction / Demand Forecasting / Flexible Self-Regulation / Behavior Change / Creative Decision Making / Guiding Generative AI with Psych & Neuro), and several of those theme names were also revised during this design pass.

## New cluster taxonomy (7 clusters)

Replaces the old 7 with a new set: the 6 projects.html themes (several renamed during this design) plus a 7th standalone historical cluster (Social Neuroscience — confirmed not to fold into any theme). Color assignments below preserve the old cluster's color where a clear conceptual successor exists (5 of 7); the remaining 2 take the freed-up colors.

| id | Name | Color | Continuity |
|---|---|---|---|
| 0 | Motivated Learning, Decision Making, & Self Regulation | `--h-slate` `#7777FF` | was "Self-Regulation" (c0) |
| 1 | Creativity & Design | `--h-helio` `#C977FF` | new (freed from dissolved Bayesian/Predictive Brain cluster) |
| 2 | Psychology-Guided Generative AI | `--h-violet` `#FF77E4` | was "Generative AI" (c2) |
| 3 | Intervention Science & Applied Behavior Change | `--h-red` `#FF7792` | was "Applied Interventions" (c3) |
| 4 | Preference Elicitation & Prediction | `#9a7c00` (base `--h-yellow`) | new (freed from dissolved Neuroeconomics cluster) |
| 5 | Social, Cognitive, & Affective Neuroscience | `--h-cheese` `#FFAE77` | was "Social Neuroscience" (c5), renamed to match projects.html's PAST section |
| 6 | Consumer Psychology & Market Forecasting | `--h-mint` `#77FFE4` | was "Consumer & Preference" (c6) |

"Neuroeconomics" and "Computational / Bayesian" are retired as standalone clusters — their content splits across the above by what each paper is actually for (mechanism papers → cluster 0, applied/market papers → cluster 6 or 4), per discussion during brainstorming.

## Paper → cluster assignment (48 papers)

Assignment is by **paper**, not by individual node — see "Node-level reassignment mechanism" below for how paper-level decisions become node-level `cluster` values.

**0. Motivated Learning, Decision Making, & Self Regulation** (6): Hakimi2015enhanced, Hakimi2014activity, Hsiung2022heuristics, Wright2024motivation, Botvinik2020variability, Hsiung2018curiosity

**1. Creativity & Design** (8): Nandy2024semantic, Hakimi2025semantic, Nath2026designrewards, Klenk2023anticipatory, Klenk2026cats, Paredes2024commuter, Hong2024unstuck, kim2026personagrambridgingpersonasproduct

**2. Psychology-Guided Generative AI** (4): Hakimi2025creativity, Hong2023genai, chong2026wowaidesign, zhang2026surpriseaidesign

**3. Intervention Science & Applied Behavior Change** (7): Sinclair2021imagining, Hakimi2021pairing, Hakimi2020behavioral, Harinen2022ml, Sinclair2024pausing, paredes2026unstuck, Sukumar2017overcoming

**4. Preference Elicitation & Prediction** (9): Hakimi2023ml, Hakimi2024cognitive, Zhang2022conjointnet, Chen2025learning, hong2026deconstructingtastehumancenteredai, Sumner2024personalizing, DeCastro2022latent, Gopinath2022hmiway, Filipowicz2023visual

**5. Social, Cognitive, & Affective Neuroscience** (11): Goldin2009neural, Tost2009mri, Tost2009dopamine, Tost2010oxtr, Tost2010acute, Zink2010vasopressin, Zink2011vasopressin, Wang2016autism, Mosner2019neural, Castrellon2022social, Castrellon2022neural

**6. Consumer Psychology & Market Forecasting** (3): Knutson2024brain, Eum2025aidriven, Filipowicz2022familiarity

Total: 48/48 papers in `graph.json` `meta.papers` (Bachman2020journal is not in this list — intentionally excluded from the graph, per existing CLAUDE.md convention).

Key boundary rules established during brainstorming (for future papers, so this doesn't need to be re-litigated):
- **Cluster 4 vs. 6** (Preference Elicitation vs. Consumer Psychology & Market Forecasting): individual/decision-maker-level preference *methods* → cluster 4; aggregate/market-level demand or adoption *outcomes* → cluster 6.
- **Cluster 0 vs. 3** (Motivated Learning/Self-Reg vs. Intervention Science): understanding/mechanism-focused → cluster 0; applied/intervention-tested → cluster 3.
- **Cluster 1 vs. 2** (Creativity & Design vs. Psychology-Guided GenAI): studies/supports human creative cognition (even if AI-assisted) → cluster 1; psych/neuro theory is used to shape or tune the generative AI system itself → cluster 2. This one had several close calls decided case-by-case (e.g. Hong2024unstuck and kim2026personagram landed in cluster 1 despite involving GenAI tooling; chong2026wowaidesign and zhang2026surpriseaidesign landed in cluster 2).

## Node-level reassignment mechanism

`graph.json` nodes (not papers) carry the actual `cluster` field that drives `graph.html`'s rendering and the `c0`–`c6` CSS classes. Papers only relate to clusters indirectly via `nodes_contributed`, and a single node can be contributed by multiple papers that may now sit in different target clusters.

A new script, `graph/tool/reassign-clusters.js`, will:

1. Build a reverse index: node id → list of contributing papers (with each paper's `paperWeight`).
2. For each node, compute a weighted vote across the *new* target cluster of each contributing paper (weight = that paper's `paperWeight`; ties broken by lowest new cluster id, logged as a warning).
3. Write the winning cluster id to `node.cluster`.
4. **Orphan nodes** (no contributing paper found in `nodes_contributed` — confirmed 7 exist today: `reward_hacking`, `creative_agency`, `design_decision`, `feedback_utility`, `reward_shaping`, `mdp_design`, `goal_alignment`) keep their current `cluster` value unchanged, but are printed in the summary for manual review. All 7 read as Creativity & Design concepts (likely under-attributed to Nath2026designrewards) — worth hand-assigning to cluster 1 after the script runs, rather than leaving them on stale cluster ids.
5. Print a summary: node count per new cluster (sanity check that no cluster ends up as a new catch-all), the orphan list above, and any close-vote ties (for optional spot-check).
6. Update `meta.clusters` to the new 7-entry id/name list.

This is a deterministic data transformation, not an LLM classification pass, so it doesn't require the extraction-prompt review gate that applies to concept-extraction batch runs.

## Files affected

1. `graph/graph.json` — `meta.clusters` renamed; node `cluster` fields reassigned via the script above.
2. `node data/inline-graph.js` — re-run after the graph.json change to resync the inlined `graphData` blocks in `index.html` and `graph.html`.
3. `graph.html`'s hard-coded `clusterData` block (~line 9201) — manually updated: new `name`, `short`, `desc`, `color`/`hex_r/g/b` per the table above. This block is intentionally separate from `graph.json` per existing CLAUDE.md convention and does not get touched by `inline-graph.js`.
4. `graph.html`'s cluster sidebar HTML (`.cluster-name` divs, ~line 433–441) — update the two hard-coded names shown as static markup (`Neuroeconomics`, `Social Neuroscience` visible in current source) if any cluster names appear outside the JS `clusterData` block.
5. `projects.html`'s `.project-cluster` chip text — currently hard-coded per project-item (`Generative AI`, `Interventions`, `Consumer & Preference`, `Neuroeconomics`, `Social Neuroscience`, `Self-Regulation`, `Predictive Brain`). Each occurrence needs updating to the matching new cluster's short name, and the CSS `.c0`–`.c6` class assigned to each `project-item` needs updating to the new id numbering in the table above.
6. `CLAUDE.md` — update the "Research clusters" table and the "Cluster color tokens" section to the new 7-cluster list once implementation is verified.

## Out of scope / explicit follow-ups (not part of this work)

- **Concept extraction gap**: Hsiung2018curiosity and Klenk2023anticipatory are both in `graph.json` `meta.papers` but have empty `nodes_contributed` (never extracted) — they're invisible in `graph.html` regardless of cluster assignment. Tracked as a separate follow-up.
- **Poster/presentation papers**: `presentations.bib` is not read by `sync-bib.js` and no paper in the graph has `pubType` of presentation/poster — posters currently do not influence the graph at all (confirmed during this session; corrects an earlier assumption that they were included but downweighted). Hakimi2018ccn (CCN 2018 poster) is the concrete example of something that could be added later. Tracked as a separate follow-up.
- **Bib metadata staleness**: a 2026-07-16 CV-repo commit fixed the DOI/title for zhang2026surpriseaidesign and added a "Best Paper Award (Honorable Mention)" addendum to Nath2026designrewards, but `data/publications.json` hasn't been re-synced since 2026-07-04. No new papers are affected — just metadata. A `node data/sync-bib.js` run at some point would pick this up; not required for this work.
- **site-content.md sync**: unrelated in-progress edits to `site-content.md` (index.html hero/about/research copy, projects.html theme descriptions) are a separate, already-partially-applied thread from earlier in this session — not part of this spec.

## Verification plan

After implementation:
1. `node graph/tool/reassign-clusters.js` output shows a reasonable node distribution across the 7 new clusters (no cluster anywhere near the old 161/339 catch-all skew).
2. `node data/inline-graph.js` runs clean and `index.html`/`graph.html` inlined blocks match `graph.json`.
3. Load `graph.html` locally (`npx serve .`) and spot-check: cluster sidebar shows the 7 new names, node colors match the new cluster assignments, the "projects →" overlay for a couple of clusters shows the expected papers from the table above.
4. Load `projects.html` and confirm `.project-cluster` chips show the new names with correct colors.
