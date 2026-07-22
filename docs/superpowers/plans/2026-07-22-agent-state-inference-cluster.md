# Agent State Inference 8th Cluster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 3 driver/agent-inference papers (Sumner2024personalizing, DeCastro2022latent, Gopinath2022hmiway) out of graph cluster 4 ("Preference Elicitation & Prediction") into their own new cluster 7 ("Agent State Inference"), and propagate the new cluster everywhere cluster metadata is hand-maintained.

**Architecture:** A direct one-shot edit to `graph/graph.json` (add cluster 7, move 16 specific node ids from `cluster: 4` to `cluster: 7` — no voting algorithm needed, the split is already unambiguous), followed by the existing `data/inline-graph.js` resync, then hand edits to every other file that hardcodes cluster metadata or count.

**Tech Stack:** Plain Node.js (ESM), no test framework — verification by running scripts and inspecting output, matching the codebase's existing pattern.

## Global Constraints

- New cluster: `{id: 7, name: "Agent State Inference"}`, color `#AAFF77`, new CSS token `--h-lime: #AAFF77;`.
- Exactly these 16 node ids move from `cluster: 4` to `cluster: 7`, and no others: `alert_fatigue`, `bounded_rationality`, `cognitive_inference`, `distracted_driving`, `driver_assistance`, `hmi_personalization`, `human_machine_teaming`, `impulsivity`, `inhibitory_control`, `inverse_rl`, `latent_driver_rep`, `policy_personalization`, `recurrent_nn`, `risky_driving`, `sensation_seeking`, `shared_autonomy`.
- Total node count must remain 339 (this is a relabel, not an add/remove).
- Out of scope: adding an "Agent State Inference" chip/project-item to projects.html — no such item exists yet in the current Ongoing/Past/Tools structure; deferred to the page's eventual 6/7/8-theme rebuild.

---

### Task 1: Add cluster 7 and move the 16 nodes in graph.json

**Files:**
- Create: `graph/tool/add-agent-state-cluster.js`
- Modify: `graph/graph.json` (written by running the script)

**Interfaces:**
- Consumes: `loadGraph()`, `saveGraph(graph)`, `c` from `graph/tool/lib.js` (same helpers used by `reassign-clusters.js` and `classify-levels.js`).
- Produces: `graph/graph.json` with an 8th entry in `meta.clusters` and the 16 named nodes reassigned to `cluster: 7`.

- [ ] **Step 1: Write the script**

```js
#!/usr/bin/env node
/**
 * add-agent-state-cluster.js — One-shot addition of an 8th cluster,
 * "Agent State Inference," splitting it out of cluster 4 (Preference
 * Elicitation & Prediction). Per docs/superpowers/specs/2026-07-22-
 * agent-state-inference-cluster-design.md: the 16 nodes below are
 * contributed exclusively by Sumner2024personalizing, DeCastro2022latent,
 * and Gopinath2022hmiway, with zero overlap with any other paper in
 * cluster 4 — this is a clean, unambiguous move, not a vote.
 *
 * Usage:
 *   node graph/tool/add-agent-state-cluster.js
 */

import { loadGraph, saveGraph, c } from './lib.js';

const NEW_CLUSTER = { id: 7, name: 'Agent State Inference' };

const NODES_TO_MOVE = [
  'alert_fatigue', 'bounded_rationality', 'cognitive_inference',
  'distracted_driving', 'driver_assistance', 'hmi_personalization',
  'human_machine_teaming', 'impulsivity', 'inhibitory_control',
  'inverse_rl', 'latent_driver_rep', 'policy_personalization',
  'recurrent_nn', 'risky_driving', 'sensation_seeking', 'shared_autonomy',
];

function main() {
  const graph = loadGraph();

  if (graph.meta.clusters.some(cl => cl.id === 7)) {
    throw new Error('Cluster 7 already exists — script already run, aborting to avoid double-processing.');
  }

  const nodeById = new Map(graph.nodes.map(n => [n.id, n]));
  const missing = NODES_TO_MOVE.filter(id => !nodeById.has(id));
  if (missing.length) throw new Error(`Nodes not found in graph.json: ${missing.join(', ')}`);

  const notInFour = NODES_TO_MOVE.filter(id => nodeById.get(id).cluster !== 4);
  if (notInFour.length) {
    throw new Error(`Expected these nodes to be in cluster 4 before the move: ${notInFour.map(id => `${id} (currently ${nodeById.get(id).cluster})`).join(', ')}`);
  }

  for (const id of NODES_TO_MOVE) {
    nodeById.get(id).cluster = 7;
  }

  graph.meta.clusters.push(NEW_CLUSTER);
  saveGraph(graph);

  c.head('Agent State Inference cluster added');
  c.log('');
  c.ok(`Added cluster 7: "${NEW_CLUSTER.name}"`);
  c.ok(`Moved ${NODES_TO_MOVE.length} nodes from cluster 4 to cluster 7`);
  c.log('');
  c.log('Total clusters: ' + graph.meta.clusters.length);
  c.log('Total nodes: ' + graph.nodes.length);
}

main();
```

- [ ] **Step 2: Run it**

Run: `node graph/tool/add-agent-state-cluster.js`

Expected output: "Agent State Inference cluster added", confirmation of 16 nodes moved, "Total clusters: 8", "Total nodes: 339" (unchanged from before).

- [ ] **Step 3: Verify with a direct query**

Run:
```bash
node -e "
const g = JSON.parse(require('fs').readFileSync('graph/graph.json', 'utf8'));
console.log('clusters:', g.meta.clusters.length);
console.log('cluster 7 nodes:', g.nodes.filter(n => n.cluster === 7).length);
console.log('cluster 4 nodes:', g.nodes.filter(n => n.cluster === 4).length);
console.log('total nodes:', g.nodes.length);
"
```

Expected: `clusters: 8`, `cluster 7 nodes: 16`, `total nodes: 339`. (Cluster 4's remaining count isn't specified here — just confirm it went down by exactly 16 from whatever it was before this task, by comparing to the pre-task count if curious; not a hard assertion.)

- [ ] **Step 4: Commit**

```bash
git add graph/tool/add-agent-state-cluster.js graph/graph.json
git commit -m "graph: add 8th cluster 'Agent State Inference', split from Preference Elicitation & Prediction"
```

---

### Task 2: Resync inlined graph data

**Files:**
- Modify: `index.html`, `graph.html` (inlined `<script type="application/json" id="graph-data">` blocks)

**Interfaces:**
- Consumes: `graph/graph.json` from Task 1.
- Produces: both files' inlined JSON blocks match `graph/graph.json`.

- [ ] **Step 1: Run the existing sync script**

Run: `node data/inline-graph.js`

Expected: success status for both files (same tool used in the prior cluster-rename plan; no changes needed to the tool itself).

- [ ] **Step 2: Verify**

Run: `grep -c '"id": 7' graph.html`

Expected: at least `1` (the new cluster 7 entry appears in the inlined `meta.clusters`).

- [ ] **Step 3: Commit**

```bash
git add index.html graph.html
git commit -m "graph: resync inlined graph data after adding Agent State Inference cluster"
```

---

### Task 3: Fix graph.html's two hardcoded-7 bugs and add the 8th sidebar/clusterData entry

**Files:**
- Modify: `graph.html`

**Interfaces:**
- Consumes: the cluster count now being dynamic (8), color `#AAFF77` for cluster 7.
- Produces: sidebar shows 8 clusters with correct counts; `CLUSTER_COLOR`/`CLUSTER_RGB` arrays (built from `clusterData`) include the 8th color; no cluster silently drops nodes from its count.

- [ ] **Step 1: Fix the hardcoded array size and bound**

Find (around line 9338-9339):
```js
  const clusterCounts = new Array(7).fill(0);
  NODES.forEach(n => { if (n.cluster < 7) clusterCounts[n.cluster]++; });
```

Replace with:
```js
  const clusterCounts = new Array(clusterData.length).fill(0);
  NODES.forEach(n => { if (n.cluster < clusterData.length) clusterCounts[n.cluster]++; });
```

This makes the count table size itself off the actual `clusterData` array (already updated to 8 entries in Step 3 below) instead of a stale literal — the fix that prevents cluster 7's nodes from vanishing from the sidebar.

- [ ] **Step 2: Fix the fallback literal**

Find (around line 9231):
```js
  const numClusters = graphData.meta?.clusters?.length || 7;
```

Replace with:
```js
  const numClusters = graphData.meta?.clusters?.length || 8;
```

(This fallback only fires if `meta.clusters` is ever missing/empty, which doesn't happen in the current data — but per the spec, keep it in sync rather than leave a now-wrong magic number.)

- [ ] **Step 3: Add the 8th static `.cluster-item` block**

Find the closing `</div>` of the last `.cluster-item` (cluster 6, "Consumer & Preference" or whatever its current name is post-rename) inside `<div id="cluster-list">`, and insert immediately after it, before that div's own closing `</div>`:

```html
      <div class="cluster-item" data-cluster="7" onclick="focusCluster(7)">
        <div class="cluster-swatch" style="background:#AAFF77"></div>
        <div class="cluster-body">
          <div class="cluster-name">Agent State Inference</div>
          <div class="cluster-desc">Inferring a person's internal state — attention, workload, cognitive factors — from behavior, and simulating agent preferences to support human-AI teaming in shared tasks like driving.</div>
          <div class="cluster-count" id="cluster-count-7"></div>
        </div>
      </div>
```

- [ ] **Step 4: Add the 8th `clusterData` entry**

Find the `clusterData` array literal (single-line JSON, assigned via `JSON.parse(document.getElementById('cluster-data').textContent)` a few lines below it). Append an 8th object to the array, before its closing `]`:

```js
, {"id": 7, "name": "Agent State Inference", "short": "Agent State Inference", "desc": "Inferring a person's internal state — attention, workload, cognitive factors — from behavior, and simulating agent preferences to support human-AI teaming in shared tasks like driving.", "color": "#AAFF77", "hex_r": 170, "hex_g": 255, "hex_b": 119}
```

(`#AAFF77` → r=170, g=255, b=119 — confirm this arithmetic when inserting: `AA`=170, `FF`=255, `77`=119.)

- [ ] **Step 5: Verify locally**

Serve the site (`npx serve . -l 5511` or similar) and load `graph.html`. Confirm: 8 cluster items in the sidebar, cluster 7 ("Agent State Inference") shows a non-zero count (should read "16 concepts"), and clicking its "projects →" button shows exactly 3 papers (Sumner2024personalizing, DeCastro2022latent, Gopinath2022hmiway).

- [ ] **Step 6: Commit**

```bash
git add graph.html
git commit -m "graph.html: fix hardcoded cluster-7 assumptions, add Agent State Inference sidebar entry"
```

---

### Task 4: Add the lime CSS token and .c7 rule, fix "seven" prose

**Files:**
- Modify: `cv.html`, `projects.html`, `extracurriculars.html`

**Interfaces:**
- Consumes: color `#AAFF77`.
- Produces: `--h-lime` available wherever the palette is defined; `.c7` class available on projects.html for future use; no page claims "seven" clusters anymore.

- [ ] **Step 1: Add `--h-lime` to cv.html's palette block**

Find (in cv.html's `:root` or equivalent palette declaration):
```css
  --h-mint:    #77FFE4;
```

Replace with:
```css
  --h-mint:    #77FFE4;
  --h-lime:    #AAFF77;
```

- [ ] **Step 2: Add `--h-lime` and `.c7` to projects.html**

Find:
```css
  --h-mint:    #77FFE4;
```

Replace with:
```css
  --h-mint:    #77FFE4;
  --h-lime:    #AAFF77;
```

Find:
```css
.c6 { --cc: var(--h-mint);   }
```

Replace with:
```css
.c6 { --cc: var(--h-mint);   }
.c7 { --cc: var(--h-lime);   }
```

- [ ] **Step 3: Fix "seven" prose in projects.html**

Find (line ~560):
```
Force-directed visualization of 50+ publications grouped into seven conceptual clusters, with a marching-squares contour overlay and spreading-activation interaction. The conceptual center of this site.
```

Replace with:
```
Force-directed visualization of 50+ publications grouped into eight conceptual clusters, with a marching-squares contour overlay and spreading-activation interaction. The conceptual center of this site.
```

- [ ] **Step 4: Fix "seven" prose in extracurriculars.html**

Find (line ~472, exact surrounding text may differ slightly — search for "seven research clusters" to locate):
```
...highlighter palette tied to seven research clusters...
```

Replace `seven` with `eight` in that sentence, preserving the rest of the sentence exactly as found.

- [ ] **Step 5: Verify**

Run: `grep -rn "seven" projects.html extracurriculars.html`

Expected: no matches referring to cluster count (if "seven" appears for an unrelated reason, that's fine — just confirm the cluster-count usage is gone).

- [ ] **Step 6: Commit**

```bash
git add cv.html projects.html extracurriculars.html
git commit -m "site: add --h-lime token and .c7 class, update cluster-count prose to eight"
```

---

### Task 5: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: cluster 7's name/color.
- Produces: CLAUDE.md's Research clusters table and highlighter palette both list the 8th cluster/color.

- [ ] **Step 1: Add cluster 7 to the Research clusters table**

Find:
```markdown
| 6 | Consumer Psychology & Market Forecasting | `#77FFE4` mint |
```

Replace with:
```markdown
| 6 | Consumer Psychology & Market Forecasting | `#77FFE4` mint |
| 7 | Agent State Inference | `#AAFF77` lime green |
```

- [ ] **Step 2: Add `--h-lime` to the Design system palette block**

Find:
```markdown
--h-mint:   #77FFE4   /* mint */
```

Replace with:
```markdown
--h-mint:   #77FFE4   /* mint */
--h-lime:   #AAFF77   /* lime green */
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Agent State Inference cluster and --h-lime token to CLAUDE.md"
```

---

### Task 6: Final verification

**Files:** none modified — verification only.

- [ ] **Step 1: Data integrity**

Run:
```bash
node -e "
const g = JSON.parse(require('fs').readFileSync('graph/graph.json', 'utf8'));
console.log('clusters:', g.meta.clusters.map(c => c.id + ':' + c.name).join(' | '));
console.log('nodes:', g.nodes.length, '(expect 339)');
const counts = new Array(8).fill(0);
g.nodes.forEach(n => counts[n.cluster]++);
console.log('distribution:', counts.join(', '));
"
```

Expected: 8 clusters listed ending in `7:Agent State Inference`; 339 nodes; cluster 7 shows 16.

- [ ] **Step 2: Browser check**

Serve locally and confirm in `graph.html`: 8 sidebar entries, cluster 7's swatch is lime green, its count reads "16 concepts", its "projects →" overlay lists exactly the 3 expected papers.

- [ ] **Step 3: No commit needed** — verification only. If anything fails, fix in the relevant earlier task.
