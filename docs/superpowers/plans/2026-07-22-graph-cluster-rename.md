# Graph Cluster Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `graph/graph.json`'s 7 broken/misaligned clusters with a new taxonomy matching the site's 6 research themes plus a standalone historical cluster, reassign every node and paper accordingly, and propagate the rename to every hand-maintained copy of cluster names across the site.

**Architecture:** A one-shot Node script (`graph/tool/reassign-clusters.js`) renames `graph.json`'s `meta.clusters` and reassigns every node's `cluster` field via a weighted vote of the papers that contributed it, using a paper→cluster mapping hard-coded in the script. `data/inline-graph.js` (existing) then resyncs the inlined copies in `index.html`/`graph.html`. Everywhere else a cluster name is hand-typed outside `graph.json` — `graph.html`'s static sidebar markup, its separate `clusterData` JS block, `projects.html`'s chip labels, and `CLAUDE.md` — gets a direct text edit.

**Tech Stack:** Plain Node.js (ESM, `"type": "module"`), no test framework in this codebase — verification is by running scripts and inspecting printed output / rendering the page, matching the existing pattern in `graph/tool/classify-levels.js` and `graph/tool/rebuild-from-corpus.js`.

## Global Constraints

- New cluster taxonomy (id, name, color — from `docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md`):
  | id | Name | Short (chip label) | Color |
  |---|---|---|---|
  | 0 | Motivated Learning, Decision Making, & Self Regulation | Self-Regulation | `#7777FF` (`--h-slate`) |
  | 1 | Creativity & Design | Creativity & Design | `#C977FF` (`--h-helio`) |
  | 2 | Psychology-Guided Generative AI | Generative AI | `#FF77E4` (`--h-violet`) |
  | 3 | Intervention Science & Applied Behavior Change | Interventions | `#FF7792` (`--h-red`) |
  | 4 | Preference Elicitation & Prediction | Preference Elicitation | `#9a7c00` (dark amber; base `--h-yellow` `#FFFF77`) |
  | 5 | Social, Cognitive, & Affective Neuroscience | Social Neuroscience | `#FFAE77` (`--h-cheese`) |
  | 6 | Consumer Psychology & Market Forecasting | Consumer & Preference | `#77FFE4` (`--h-mint`) |
- The `.c0`–`.c6` CSS color definitions in `projects.html` (lines 34–40) already match this id→color table exactly — **do not touch that CSS block**, only the `class="... cN"` attribute on individual `project-item` divs that need to move to a different cluster.
- Full 48-paper → cluster mapping is fixed by the approved spec (reproduced in Task 1's code). Do not re-derive or second-guess it.
- Out of scope (do not touch in this plan): `Hsiung2018curiosity`/`Klenk2023anticipatory` concept-extraction gap, `presentations.bib` posters, `data/publications.json` metadata re-sync, `site-content.md` edits, projects.html's 6-theme rebuild.

---

### Task 1: Write and run `graph/tool/reassign-clusters.js`

**Files:**
- Create: `graph/tool/reassign-clusters.js`
- Modify: `graph/graph.json` (written by running the script, not hand-edited)

**Interfaces:**
- Consumes: `loadGraph()`, `saveGraph(graph)`, `c` (console helpers) from `graph/tool/lib.js` — existing exports, already used by `classify-levels.js`.
- Produces: `graph/graph.json` with `meta.clusters` renamed to the 7 entries above and every node's `cluster` field reassigned. Nothing downstream in this plan imports this script as a module — it's a CLI one-shot.

- [ ] **Step 1: Write the script**

```js
#!/usr/bin/env node
/**
 * reassign-clusters.js — One-shot rename of graph.json's 7 clusters and
 * reassignment of every node's `cluster` field to match, per the paper-level
 * mapping in docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md.
 *
 * Nodes are voted into their new cluster by the papers that contributed
 * them (graph.json meta.papers[].nodes_contributed), weighted by each
 * paper's paperWeight. Nodes with no contributing paper (orphans) keep
 * their existing cluster id and are printed for manual review — as of
 * 2026-07-22 there are 7 such nodes, all Creativity & Design concepts
 * under-attributed to Nath2026designrewards; see the spec for the planned
 * manual fix-up (Task 2 of this plan).
 *
 * Usage:
 *   node graph/tool/reassign-clusters.js
 */

import { loadGraph, saveGraph, c } from './lib.js';

const NEW_CLUSTERS = [
  { id: 0, name: 'Motivated Learning, Decision Making, & Self Regulation' },
  { id: 1, name: 'Creativity & Design' },
  { id: 2, name: 'Psychology-Guided Generative AI' },
  { id: 3, name: 'Intervention Science & Applied Behavior Change' },
  { id: 4, name: 'Preference Elicitation & Prediction' },
  { id: 5, name: 'Social, Cognitive, & Affective Neuroscience' },
  { id: 6, name: 'Consumer Psychology & Market Forecasting' },
];

// Paper id -> new cluster id, per the approved design spec. All 48 papers
// currently in graph.json meta.papers must appear here exactly once.
const PAPER_CLUSTER = {
  // 0. Motivated Learning, Decision Making, & Self Regulation
  Hakimi2015enhanced: 0, Hakimi2014activity: 0, Hsiung2022heuristics: 0,
  Wright2024motivation: 0, Botvinik2020variability: 0, Hsiung2018curiosity: 0,
  // 1. Creativity & Design
  Nandy2024semantic: 1, Hakimi2025semantic: 1, Nath2026designrewards: 1,
  Klenk2023anticipatory: 1, Klenk2026cats: 1, Paredes2024commuter: 1,
  Hong2024unstuck: 1, kim2026personagrambridgingpersonasproduct: 1,
  // 2. Psychology-Guided Generative AI
  Hakimi2025creativity: 2, Hong2023genai: 2, chong2026wowaidesign: 2,
  zhang2026surpriseaidesign: 2,
  // 3. Intervention Science & Applied Behavior Change
  Sinclair2021imagining: 3, Hakimi2021pairing: 3, Hakimi2020behavioral: 3,
  Harinen2022ml: 3, Sinclair2024pausing: 3, paredes2026unstuck: 3,
  Sukumar2017overcoming: 3,
  // 4. Preference Elicitation & Prediction
  Hakimi2023ml: 4, Hakimi2024cognitive: 4, Zhang2022conjointnet: 4,
  Chen2025learning: 4, hong2026deconstructingtastehumancenteredai: 4,
  Sumner2024personalizing: 4, DeCastro2022latent: 4, Gopinath2022hmiway: 4,
  Filipowicz2023visual: 4,
  // 5. Social, Cognitive, & Affective Neuroscience
  Goldin2009neural: 5, Tost2009mri: 5, Tost2009dopamine: 5, Tost2010oxtr: 5,
  Tost2010acute: 5, Zink2010vasopressin: 5, Zink2011vasopressin: 5,
  Wang2016autism: 5, Mosner2019neural: 5, Castrellon2022social: 5,
  Castrellon2022neural: 5,
  // 6. Consumer Psychology & Market Forecasting
  Knutson2024brain: 6, Eum2025aidriven: 6, Filipowicz2022familiarity: 6,
};

function main() {
  const graph = loadGraph();

  const paperIds = new Set(graph.meta.papers.map(p => p.id));
  const mappedIds = new Set(Object.keys(PAPER_CLUSTER));
  const missing = [...paperIds].filter(id => !mappedIds.has(id));
  const extra = [...mappedIds].filter(id => !paperIds.has(id));
  if (missing.length) throw new Error(`Papers in graph.json with no cluster mapping: ${missing.join(', ')}`);
  if (extra.length) throw new Error(`PAPER_CLUSTER has ids not in graph.json: ${extra.join(', ')}`);

  // Reverse index: node id -> Map<clusterId, summedWeight>
  const votes = new Map();
  for (const paper of graph.meta.papers) {
    const cluster = PAPER_CLUSTER[paper.id];
    const weight = paper.paperWeight ?? 1.0;
    for (const nodeId of paper.nodes_contributed || []) {
      if (!votes.has(nodeId)) votes.set(nodeId, new Map());
      const clusterVotes = votes.get(nodeId);
      clusterVotes.set(cluster, (clusterVotes.get(cluster) || 0) + weight);
    }
  }

  const orphans = [];
  const ties = [];
  const countsBefore = new Array(7).fill(0);
  const countsAfter = new Array(7).fill(0);

  for (const node of graph.nodes) {
    if (node.cluster >= 0 && node.cluster < 7) countsBefore[node.cluster]++;

    const clusterVotes = votes.get(node.id);
    if (!clusterVotes || clusterVotes.size === 0) {
      orphans.push(node.id);
      if (node.cluster >= 0 && node.cluster < 7) countsAfter[node.cluster]++;
      continue;
    }

    let winner = null, winnerWeight = -1, top = [];
    for (const [cluster, weight] of clusterVotes) {
      if (weight > winnerWeight) { winner = cluster; winnerWeight = weight; top = [cluster]; }
      else if (weight === winnerWeight) { top.push(cluster); }
    }
    if (top.length > 1) {
      winner = Math.min(...top);
      ties.push({ node: node.id, candidates: top, chose: winner });
    }
    node.cluster = winner;
    countsAfter[winner]++;
  }

  graph.meta.clusters = NEW_CLUSTERS;
  saveGraph(graph);

  c.head('Cluster reassignment complete');
  c.log('');
  c.log('Node count per cluster (before → after):');
  for (let i = 0; i < 7; i++) {
    c.log(`  ${i}  ${NEW_CLUSTERS[i].name}: ${countsBefore[i]} → ${countsAfter[i]}`);
  }
  c.log('');
  if (orphans.length) {
    c.warn(`${orphans.length} orphan node(s) with no contributing paper — cluster left unchanged:`);
    orphans.forEach(id => c.log(`  - ${id}`));
  }
  if (ties.length) {
    c.warn(`${ties.length} tie(s) broken by lowest cluster id:`);
    ties.forEach(t => c.log(`  - ${t.node}: candidates [${t.candidates.join(',')}] → chose ${t.chose}`));
  } else {
    c.ok('No ties.');
  }
  c.ok('Wrote graph/graph.json');
}

main();
```

- [ ] **Step 2: Run it**

Run: `node graph/tool/reassign-clusters.js`

Expected output: a "Cluster reassignment complete" header, a before→after count table for all 7 clusters (before-column will show the *old* semantics, e.g. `0 Motivated Learning...: 161 → N` — the 161 is meaningless since it's counting the old cluster 0 catch-all, not a regression), a warning listing exactly 7 orphan nodes (`reward_hacking`, `creative_agency`, `design_decision`, `feedback_utility`, `reward_shaping`, `mdp_design`, `goal_alignment`), and "Wrote graph/graph.json". No ties are expected but the script handles them safely if any occur.

- [ ] **Step 3: Verify no exception was thrown and the paper/id validation passed**

Run: `node graph/tool/reassign-clusters.js` a second time (idempotency check — a second run should reassign nodes to the exact same clusters and reproduce the same after-counts, since it recomputes from scratch each time rather than accumulating state).

Expected: identical output to Step 2 (same after-counts, same orphan list), confirming the script is deterministic and safe to re-run.

- [ ] **Step 4: Commit**

```bash
git add graph/tool/reassign-clusters.js graph/graph.json
git commit -m "graph: rename 7 clusters and reassign nodes per new research-theme taxonomy"
```

---

### Task 2: Manually assign the 7 orphan nodes to Creativity & Design

**Files:**
- Modify: `graph/graph.json`

**Interfaces:**
- Consumes: the orphan list printed by Task 1's script run (`reward_hacking`, `creative_agency`, `design_decision`, `feedback_utility`, `reward_shaping`, `mdp_design`, `goal_alignment`).
- Produces: same 7 nodes now have `cluster: 1`.

- [ ] **Step 1: Edit each of the 7 orphan nodes' `cluster` field to `1`**

Each node object in `graph.json`'s top-level `nodes` array has a `cluster` field. Find each of these 7 node ids and set `"cluster": 1`:
- `reward_hacking` (currently `1` already — leave as-is, confirm it reads `1`)
- `creative_agency` (currently `0` — change to `1`)
- `design_decision` (currently `0` — change to `1`)
- `feedback_utility` (currently `0` — change to `1`)
- `reward_shaping` (currently `3` — change to `1`)
- `mdp_design` (currently `1` already — leave as-is, confirm it reads `1`)
- `goal_alignment` (currently `0` — change to `1`)

Use a targeted edit tool (find each `"id": "<node_id>"` block and change its neighboring `"cluster": N` value to `1`) rather than a blind find/replace, since `"cluster": 0` etc. appears on hundreds of unrelated nodes.

- [ ] **Step 2: Verify with a quick script check**

Run:
```bash
node -e "
const g = JSON.parse(require('fs').readFileSync('graph/graph.json', 'utf8'));
const ids = ['reward_hacking','creative_agency','design_decision','feedback_utility','reward_shaping','mdp_design','goal_alignment'];
const byId = Object.fromEntries(g.nodes.map(n => [n.id, n.cluster]));
for (const id of ids) console.log(id, '->', byId[id]);
"
```

Expected: all 7 lines print `-> 1`.

- [ ] **Step 3: Commit**

```bash
git add graph/graph.json
git commit -m "graph: assign 7 orphan design-reward nodes to Creativity & Design cluster"
```

---

### Task 3: Resync inlined graph data in index.html and graph.html

**Files:**
- Modify: `index.html` (inlined `<script type="application/json" id="graph-data">` block — nodes/edges/layout only)
- Modify: `graph.html` (same tag — full payload including `meta.clusters` and `meta.papers`)

**Interfaces:**
- Consumes: `graph/graph.json` as written by Tasks 1–2.
- Produces: both HTML files' inlined JSON blocks now match `graph/graph.json` byte-for-byte (per field list in `data/inline-graph.js`).

- [ ] **Step 1: Run the existing sync script**

Run: `node data/inline-graph.js`

Expected output: success status for both `index.html` and `graph.html` (no `no-marker`/`no-close` errors — see `data/inline-graph.js` for its own status reporting).

- [ ] **Step 2: Verify the inlined cluster names landed in graph.html**

Run: `grep -A1 '"id": 0' graph.html | head -4`

Expected: shows `"id": 0,` followed by `"name": "Motivated Learning, Decision Making, & Self Regulation"` inside the inlined JSON block (this confirms the *inlined* copy updated — the separate hard-coded `clusterData` JS block and static sidebar markup, handled in Task 4, are NOT touched by this script and will still show old names at this point).

- [ ] **Step 3: Commit**

```bash
git add index.html graph.html
git commit -m "graph: resync inlined graph data after cluster rename"
```

---

### Task 4: Update graph.html's hard-coded cluster sidebar markup and clusterData block

**Files:**
- Modify: `graph.html` (static `.cluster-item` HTML, ~lines 398–451; `clusterData` JS array, ~line 9201)

**Interfaces:**
- Consumes: the id/name/short/color table in Global Constraints above.
- Produces: the sidebar UI (names, descriptions, swatch colors, `data-cluster` attributes) and the `#nd-cluster` tooltip (`clusterData[ci].short`) both show the new taxonomy. `CLUSTER_COLOR`/`CLUSTER_RGB` arrays (built from `clusterData`, consumed by node-rendering code later in the file) automatically pick up the new colors — no other JS changes needed.

- [ ] **Step 1: Replace the 7 static `.cluster-item` blocks**

Find the block starting at `<div id="cluster-list">` (~line 397) through its closing `</div>` before `<!-- ── CLUSTER OVERLAY ── -->` (~line 452). Replace the 7 `.cluster-item` divs with:

```html
      <div class="cluster-item" data-cluster="0" onclick="focusCluster(0)">
        <div class="cluster-swatch" style="background:#7777FF"></div>
        <div class="cluster-body">
          <div class="cluster-name">Motivated Learning, Decision Making, & Self Regulation</div>
          <div class="cluster-desc">How motivation, reward, and self-control shape learning and choice — temporal discounting, satisficing heuristics, and the mechanisms underlying flexible goal pursuit.</div>
          <div class="cluster-count" id="cluster-count-0"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="1" onclick="focusCluster(1)">
        <div class="cluster-swatch" style="background:#C977FF"></div>
        <div class="cluster-body">
          <div class="cluster-name">Creativity & Design</div>
          <div class="cluster-desc">The cognitive and behavioral processes behind creative work — design fixation, idea incubation, semantic exploration, and how creative professionals get unstuck.</div>
          <div class="cluster-count" id="cluster-count-1"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="2" onclick="focusCluster(2)">
        <div class="cluster-swatch" style="background:#FF77E4"></div>
        <div class="cluster-body">
          <div class="cluster-name">Psychology-Guided Generative AI</div>
          <div class="cluster-desc">Using psychological and neuroscientific theory to shape generative AI systems — from prompt engineering grounded in design cognition to physiology-informed image generation.</div>
          <div class="cluster-count" id="cluster-count-2"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="3" onclick="focusCluster(3)">
        <div class="cluster-swatch" style="background:#FF7792"></div>
        <div class="cluster-body">
          <div class="cluster-name">Intervention Science & Applied Behavior Change</div>
          <div class="cluster-desc">Designing, testing, and personalizing behavior-change interventions — from pandemic risk communication to just-in-time creativity prompts.</div>
          <div class="cluster-count" id="cluster-count-3"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="4" onclick="focusCluster(4)">
        <div class="cluster-swatch" style="background:#FFFF77"></div>
        <div class="cluster-body">
          <div class="cluster-name">Preference Elicitation & Prediction</div>
          <div class="cluster-desc">Methods for eliciting and modeling individual preference from behavior, language, and physiology — including how driver and decision-maker traits can be inferred under uncertainty.</div>
          <div class="cluster-count" id="cluster-count-4"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="5" onclick="focusCluster(5)">
        <div class="cluster-swatch" style="background:#FFAE77"></div>
        <div class="cluster-body">
          <div class="cluster-name">Social, Cognitive, & Affective Neuroscience</div>
          <div class="cluster-desc">How social context and emotion modulate cognition — including social learning, moral judgment, empathy, and bias in consequential decisions.</div>
          <div class="cluster-count" id="cluster-count-5"></div>
        </div>
      </div>
      <div class="cluster-item" data-cluster="6" onclick="focusCluster(6)">
        <div class="cluster-swatch" style="background:#77FFE4"></div>
        <div class="cluster-body">
          <div class="cluster-name">Consumer Psychology & Market Forecasting</div>
          <div class="cluster-desc">Neural and behavioral signals that forecast market-level demand and product adoption — from brain activity predicting vehicle sales to familiarity effects on technology uptake.</div>
          <div class="cluster-count" id="cluster-count-6"></div>
        </div>
      </div>
```

Note the swatch colors are unchanged from the current file (`#7777FF`, `#C977FF`, `#FF77E4`, `#FF7792`, `#FFFF77`, `#FFAE77`, `#77FFE4` in that id order) — only `cluster-name`, `cluster-desc`, and the surrounding text change.

- [ ] **Step 2: Replace the `clusterData` JS array**

Find the single-line JSON literal assigned via `JSON.parse(document.getElementById('cluster-data').textContent)` context — the literal array itself sits a few lines above at `[{"id": 0, "name": ...}, ...]` (~line 9201, right before `const clusterData = JSON.parse(...)`). Replace the full array literal with:

```js
[{"id": 0, "name": "Motivated Learning, Decision Making, & Self Regulation", "short": "Self-Regulation", "desc": "How motivation, reward, and self-control shape learning and choice — temporal discounting, satisficing heuristics, and the mechanisms underlying flexible goal pursuit.", "color": "#7777FF", "hex_r": 119, "hex_g": 119, "hex_b": 255}, {"id": 1, "name": "Creativity & Design", "short": "Creativity & Design", "desc": "The cognitive and behavioral processes behind creative work — design fixation, idea incubation, semantic exploration, and how creative professionals get unstuck.", "color": "#C977FF", "hex_r": 201, "hex_g": 119, "hex_b": 255}, {"id": 2, "name": "Psychology-Guided Generative AI", "short": "Generative AI", "desc": "Using psychological and neuroscientific theory to shape generative AI systems — from prompt engineering grounded in design cognition to physiology-informed image generation.", "color": "#FF77E4", "hex_r": 255, "hex_g": 119, "hex_b": 228}, {"id": 3, "name": "Intervention Science & Applied Behavior Change", "short": "Interventions", "desc": "Designing, testing, and personalizing behavior-change interventions — from pandemic risk communication to just-in-time creativity prompts.", "color": "#FF7792", "hex_r": 255, "hex_g": 119, "hex_b": 146}, {"id": 4, "name": "Preference Elicitation & Prediction", "short": "Preference Elicitation", "desc": "Methods for eliciting and modeling individual preference from behavior, language, and physiology — including how driver and decision-maker traits can be inferred under uncertainty.", "color": "#FFFF77", "hex_r": 255, "hex_g": 255, "hex_b": 119}, {"id": 5, "name": "Social, Cognitive, & Affective Neuroscience", "short": "Social Neuroscience", "desc": "How social context and emotion modulate cognition — including social learning, moral judgment, empathy, and bias in consequential decisions.", "color": "#FFAE77", "hex_r": 255, "hex_g": 174, "hex_b": 119}, {"id": 6, "name": "Consumer Psychology & Market Forecasting", "short": "Consumer & Preference", "desc": "Neural and behavioral signals that forecast market-level demand and product adoption — from brain activity predicting vehicle sales to familiarity effects on technology uptake.", "color": "#77FFE4", "hex_r": 119, "hex_g": 255, "hex_b": 228}]
```

This preserves the existing single-line-literal style and `—` em-dash escaping convention already used in that block.

- [ ] **Step 3: Verify in a local server**

Run: `npx serve . -l 5500` (or any static server), then open `http://localhost:5500/graph.html` in a browser.

Expected: the left sidebar shows the 7 new cluster names in the id order above, each with its matching swatch color; hovering/clicking a node shows the new `short` name in the node-detail tooltip; clicking "projects →" on a cluster opens the overlay showing the papers from Task 1's mapping for that cluster (e.g. cluster 5 "Social, Cognitive, & Affective Neuroscience" should list Goldin2009neural, the Tost papers, the Zink papers, Wang2016autism, Mosner2019neural, both Castrellon2022 papers — 11 total).

- [ ] **Step 4: Commit**

```bash
git add graph.html
git commit -m "graph.html: update sidebar and clusterData block to new cluster taxonomy"
```

---

### Task 5: Update projects.html cluster chips

**Files:**
- Modify: `projects.html`

**Interfaces:**
- Consumes: the id/color table in Global Constraints (the `.c0`–`.c6` CSS at lines 34–40 already matches it — not edited here).
- Produces: 4 `project-item` divs get an updated `class` attribute and `.project-cluster` chip text; all other `project-item` divs (including the 3 Tools & Datasets ones) are unchanged because their old chip text/color already matches the new taxonomy at the same id.

- [ ] **Step 1: Update "Neuroeconomics of Self-Control"**

Find:
```html
    <div class="project-item visible c4">
      <div class="project-meta">
        <span class="project-year">2014–2020</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Neuroeconomics of Self-Control</div>
        <p class="project-desc">fMRI investigations of intertemporal choice, dietary self-control, and how the brain values delayed rewards. Postdoctoral work at Duke with Scott Huettel.</p>
        <div class="project-tags">
          <span class="project-cluster">Neuroeconomics</span>
```

Replace with:
```html
    <div class="project-item visible c0">
      <div class="project-meta">
        <span class="project-year">2014–2020</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Neuroeconomics of Self-Control</div>
        <p class="project-desc">fMRI investigations of intertemporal choice, dietary self-control, and how the brain values delayed rewards. Postdoctoral work at Duke with Scott Huettel.</p>
        <div class="project-tags">
          <span class="project-cluster">Self-Regulation</span>
```

- [ ] **Step 2: Update "Social-Affective Neural Computation" — confirm no change needed**

This item is already `class="project-item visible c5"` with chip text `Social Neuroscience`, which matches the new cluster 5 exactly. Skip — no edit.

- [ ] **Step 3: Update "Emotion Regulation in Social Anxiety"**

Find:
```html
    <div class="project-item visible c0">
      <div class="project-meta">
        <span class="project-year">2009–2010</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Emotion Regulation in Social Anxiety</div>
        <p class="project-desc">Cognitive reappraisal as a treatment mechanism in social anxiety disorder; neural correlates of CBT response. Stanford with Philippe Goldin and James Gross.</p>
        <div class="project-tags">
          <span class="project-cluster">Self-Regulation</span>
```

Replace with:
```html
    <div class="project-item visible c5">
      <div class="project-meta">
        <span class="project-year">2009–2010</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Emotion Regulation in Social Anxiety</div>
        <p class="project-desc">Cognitive reappraisal as a treatment mechanism in social anxiety disorder; neural correlates of CBT response. Stanford with Philippe Goldin and James Gross.</p>
        <div class="project-tags">
          <span class="project-cluster">Social Neuroscience</span>
```

- [ ] **Step 4: Update "Predictive Coding & the Bayesian Brain"**

Find:
```html
    <div class="project-item visible c1">
      <div class="project-meta">
        <span class="project-year">2012–2018</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Predictive Coding &amp; the Bayesian Brain</div>
        <p class="project-desc">Theoretical and empirical work on how the brain models its own predictions — with applications to expectation, surprise, and attention. <em>[Placeholder: confirm scope/years.]</em></p>
        <div class="project-tags">
          <span class="project-cluster">Predictive Brain</span>
```

Replace with:
```html
    <div class="project-item visible c0">
      <div class="project-meta">
        <span class="project-year">2012–2018</span>
        <span class="project-status">Completed</span>
      </div>
      <div class="project-body">
        <div class="project-title">Predictive Coding &amp; the Bayesian Brain</div>
        <p class="project-desc">Theoretical and empirical work on how the brain models its own predictions — with applications to expectation, surprise, and attention. <em>[Placeholder: confirm scope/years.]</em></p>
        <div class="project-tags">
          <span class="project-cluster">Self-Regulation</span>
```

- [ ] **Step 5: Update "Computational Aesthetics & Preference"**

Find:
```html
    <div class="project-item visible c6">
      <div class="project-meta">
        <span class="project-year">2023–</span>
        <span class="project-status">Active</span>
      </div>
      <div class="project-body">
        <div class="project-title">Computational Aesthetics &amp; Preference</div>
        <p class="project-desc">Probabilistic models of what people find pleasing, surprising, or wow-worthy in generated artifacts. Extends preference and valuation work from neuroeconomics into the design and AI-generation setting.</p>
        <div class="project-tags">
          <span class="project-cluster">Consumer &amp; Preference</span>
```

Replace with:
```html
    <div class="project-item visible c4">
      <div class="project-meta">
        <span class="project-year">2023–</span>
        <span class="project-status">Active</span>
      </div>
      <div class="project-body">
        <div class="project-title">Computational Aesthetics &amp; Preference</div>
        <p class="project-desc">Probabilistic models of what people find pleasing, surprising, or wow-worthy in generated artifacts. Extends preference and valuation work from neuroeconomics into the design and AI-generation setting.</p>
        <div class="project-tags">
          <span class="project-cluster">Preference Elicitation</span>
```

- [ ] **Step 6: Verify remaining items are untouched**

Run: `grep -n 'project-cluster\|project-item visible c' projects.html`

Expected: 10 `project-item` lines and 10 `project-cluster` lines total. The two "Generative AI for Design Ideation" / "Just-in-Time Creativity Interventions" items and all 3 Tools & Datasets items still read `c2`/`Generative AI` and `c3`/`Interventions` respectively — confirm none of those 5 lines changed.

- [ ] **Step 7: Commit**

```bash
git add projects.html
git commit -m "projects.html: relabel cluster chips to new taxonomy"
```

---

### Task 6: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the id/name/color table in Global Constraints.
- Produces: CLAUDE.md's "Research clusters" table and "Cluster color tokens" note reflect the new taxonomy, so future sessions don't rediscover the mismatch this plan fixed.

- [ ] **Step 1: Replace the "Research clusters" table**

Find:
```markdown
## Research clusters (graph.html + cv.html + projects.html)
| # | Name | Color |
|---|---|---|
| 0 | Self-regulation | `#7777FF` slate blue |
| 1 | Predictive brain | `#C977FF` heliotrope |
| 2 | Generative AI | `#FF77E4` violet web |
| 3 | Interventions | `#FF7792` ultra red |
| 4 | Neuroeconomics | `#FFFF77` laser lemon (display as `#9a7c00`) |
| 5 | Social neuroscience | `#FFAE77` mac & cheese |
| 6 | Consumer & preference | `#77FFE4` mint |
```

Replace with:
```markdown
## Research clusters (graph.html + cv.html + projects.html)
Renamed 2026-07-22 to match the site's research themes; see
`docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md` for the
full paper-to-cluster mapping and the rationale behind each boundary.
| # | Name | Color |
|---|---|---|
| 0 | Motivated Learning, Decision Making, & Self Regulation | `#7777FF` slate blue |
| 1 | Creativity & Design | `#C977FF` heliotrope |
| 2 | Psychology-Guided Generative AI | `#FF77E4` violet web |
| 3 | Intervention Science & Applied Behavior Change | `#FF7792` ultra red |
| 4 | Preference Elicitation & Prediction | `#FFFF77` laser lemon (display as `#9a7c00`) |
| 5 | Social, Cognitive, & Affective Neuroscience | `#FFAE77` mac & cheese |
| 6 | Consumer Psychology & Market Forecasting | `#77FFE4` mint |
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md research clusters table to new taxonomy"
```

---

### Task 7: Final end-to-end verification

**Files:** none modified — verification only.

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: confidence the whole site is internally consistent before considering this done.

- [ ] **Step 1: Confirm graph.json internal consistency**

Run:
```bash
node -e "
const g = JSON.parse(require('fs').readFileSync('graph/graph.json', 'utf8'));
console.log('clusters:', g.meta.clusters.map(c => c.id + ':' + c.name).join(' | '));
console.log('total papers:', g.meta.papers.length);
console.log('total nodes:', g.nodes.length);
const counts = new Array(7).fill(0);
g.nodes.forEach(n => counts[n.cluster]++);
console.log('node distribution:', counts.join(', '));
"
```

Expected: 7 clusters with the new names in id order 0–6; 48 papers; 339 nodes (unchanged from before the rename — this script only reassigns `cluster`, never adds/removes nodes); a node distribution with no single cluster anywhere near the old 161/339 catch-all skew (some imbalance is fine and expected — clusters 2 and 6 have few source papers — but nothing should dominate the way the old cluster 0 did).

- [ ] **Step 2: Confirm index.html is unaffected in content (nodes/edges/layout only, no cluster names)**

Run: `grep -c '"name": "Motivated Learning' index.html`

Expected: `0` — index.html's inlined block deliberately excludes `meta.clusters`/`meta.papers` per `data/inline-graph.js`'s field list, so it should never contain cluster names at all. This confirms Task 3 didn't accidentally leak cluster data into the landing page.

- [ ] **Step 3: Browser check on graph.html and projects.html**

Serve locally (`npx serve .`) and visually confirm:
- `graph.html`: sidebar cluster names/colors match the Global Constraints table; node colors in the force-directed layout visibly regrouped (the old giant cluster-0 blob should no longer dominate); the cluster overlay for at least 2 clusters shows the expected paper list from Task 1.
- `projects.html`: the 4 changed chips (Neuroeconomics of Self-Control → Self-Regulation/c0; Emotion Regulation in Social Anxiety → Social Neuroscience/c5; Predictive Coding & the Bayesian Brain → Self-Regulation/c0; Computational Aesthetics & Preference → Preference Elicitation/c4) render with correct color and text; the 6 unchanged items still render as before.

- [ ] **Step 4: No commit needed** — this task is verification-only. If anything fails, fix it in the relevant earlier task and re-commit there rather than adding a new fixup commit.

---

## Follow-ups (explicitly out of scope, do not implement here)

- Concept extraction for `Hsiung2018curiosity` and `Klenk2023anticipatory` (zero `nodes_contributed`).
- Deciding whether/how to add poster/presentation papers (e.g. Hakimi2018ccn) to the graph — `presentations.bib` isn't read by `sync-bib.js` today.
- Re-running `node data/sync-bib.js` to pick up the 2026-07-16 metadata fixes (DOI/title for zhang2026surpriseaidesign, award addendum for Nath2026designrewards).
- Rebuilding projects.html's 6-theme structure (the version referenced in pre-interruption session notes was never actually saved/committed and needs to be redone from scratch).
