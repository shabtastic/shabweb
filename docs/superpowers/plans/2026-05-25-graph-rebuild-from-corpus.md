# Graph Rebuild from Corpus — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `graph/graph.json` from vault full-text extractions via a three-pass Sonnet 4.6 extraction pipeline, with a gitignored draft-review buffer for three draft papers.

**Architecture:** Extract shared graph utilities into `graph/tool/lib.js`, import them from `index.js` (no behavior change), then build `rebuild-from-corpus.js` (three-pass CLI) and `review-draft-proposals.js` (interactive review CLI) on top of lib.js. The corpus catalog drives pass bucketing; vault extracted-text files drive concept extraction. Pass 3 (drafts) writes to gitignored `graph/draft-proposals.json` instead of `graph.json`.

**Tech Stack:** Node.js ESM, `@anthropic-ai/sdk` (claude-sonnet-4-6 default, claude-opus-4-7 via `--opus`), `commander`, `readline`, `dotenv`, `fs/path`.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `graph/tool/lib.js` | Shared graph utilities (extractConcepts, mergeIntoGraph, computePaperWeight, rebuildLayout, loadGraph, saveGraph, console helpers) |
| Modify | `graph/tool/index.js` | Import from lib.js; remove duplicated local definitions |
| Create | `graph/tool/rebuild-from-corpus.js` | Three-pass extraction CLI |
| Create | `graph/tool/review-draft-proposals.js` | Interactive draft review CLI |
| Modify | `.gitignore` (website root) | Add `graph/draft-proposals.json` |

---

## Task 1: Create `graph/tool/lib.js`

Extract the shared functions from `index.js` into a reusable module. Two changes relative to the originals: (1) `extractConcepts` gains a `model` parameter (default `claude-sonnet-4-6`), (2) `mergeIntoGraph` adds `extraction_source` and uses `nodes_contributed` (snake_case, matching the schema per CLAUDE.md).

**Files:**
- Create: `graph/tool/lib.js`

- [ ] **Step 1: Create lib.js**

```js
// graph/tool/lib.js
import fs   from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Anthropic from '@anthropic-ai/sdk';

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
export const GRAPH_PATH = path.join(__dirname, '..', 'graph.json');

// ── Console helpers ───────────────────────────────────────────────────────────
export const c = {
  info:  s => process.stdout.write(`\x1b[36m→\x1b[0m  ${s}\n`),
  ok:    s => process.stdout.write(`\x1b[32m✓\x1b[0m  ${s}\n`),
  warn:  s => process.stdout.write(`\x1b[33m⚠\x1b[0m  ${s}\n`),
  err:   s => process.stdout.write(`\x1b[31m✗\x1b[0m  ${s}\n`),
  head:  s => process.stdout.write(`\x1b[1m${s}\x1b[0m\n`),
  dim:   s => process.stdout.write(`\x1b[2m${s}\x1b[0m\n`),
  log:   s => process.stdout.write(`${s}\n`),
};

// ── Graph I/O ─────────────────────────────────────────────────────────────────
export function loadGraph() {
  if (!fs.existsSync(GRAPH_PATH)) throw new Error(`graph.json not found at ${GRAPH_PATH}`);
  return JSON.parse(fs.readFileSync(GRAPH_PATH, 'utf8'));
}

export function saveGraph(graph) {
  fs.writeFileSync(GRAPH_PATH, JSON.stringify(graph, null, 2));
}

// ── Paper weighting ───────────────────────────────────────────────────────────
export function computePaperWeight(meta) {
  const typeWeights = {
    'journal':       1.00,
    'conf-full':     0.85,
    'conf-workshop': 0.65,
    'preprint':      0.70,
    'science-comm':  0.30,
    'other':         0.40,
  };
  const typeW = typeWeights[meta.pubType] ?? 0.50;

  const posWeights = {
    'first':        1.0,
    'shared-first': 1.0,
    'last':         0.8,
    'second':       0.6,
    'middle':       0.4,
  };
  const posW = posWeights[meta.authorPosition] ?? 0.5;

  const year = parseInt(meta.year) || 2000;
  const recencyW = year >= 2020 ? 1.0 : year >= 2015 ? 0.8 : 0.6;

  return Math.round(typeW * posW * recencyW * 100) / 100;
}

// ── Claude concept extraction ─────────────────────────────────────────────────
export async function extractConcepts(text, graph, paperWeight = 1.0, model = 'claude-sonnet-4-6') {
  const client      = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const existingIds = graph.nodes.map(n => n.id);
  const clusterGuide = graph.meta.clusters.map(cl => `${cl.id}=${cl.name}`).join(', ');

  const response = await client.messages.create({
    model,
    max_tokens: 2000,
    system: `You are a research knowledge-graph builder. Extract key concepts (nodes) and theoretical relationships (edges) from academic paper text.

EXISTING NODE IDs — you MUST reuse these wherever semantically appropriate.
Do NOT create a new node if an existing one covers the same concept, even if the wording differs.
Examples of what NOT to do: adding "risk_perception" when "perceived_risk" exists; adding "belief_updating" when "belief_revision" exists; adding "episodic_simulation" when "episodic_sim" exists.
When in doubt, REUSE the existing node and add edges to/from it instead.

${existingIds.join(', ')}

Cluster guide: ${clusterGuide}
Use cluster 0 as default for anything that doesn't fit neatly.

PAPER WEIGHT: ${paperWeight} (scale 0–1, reflecting publication type, author position, and recency)
This paper's importance to the researcher's intellectual identity is ${paperWeight >= 0.8 ? 'high' : paperWeight >= 0.5 ? 'moderate' : 'lower'}.
Scale your raw node weight scores accordingly — a weight of 1.0 in a paperWeight=0.5 paper
should translate to a node weight of ~0.5 in the final graph.
So: final_node_weight = your_raw_score × ${paperWeight} (clamped to 0.1–1.0).

Return ONLY valid JSON, no markdown fences:
{
  "nodes": [{"id":"snake_case_max_3_words","label":"display\\nlabel","weight":0.0-1.0,"cluster":0-6,"level":"construct"}],
  "edges": [{"a":"node_id","b":"node_id","strength":0.0-1.0}],
  "paper": {"title":"...","year":2024,"venue":"...","doi":"..."}
}

Guidelines:
- ONLY add nodes for concepts genuinely absent from the existing list above
- Prefer edges to existing nodes over creating near-duplicate new nodes
- weight = raw centrality × paperWeight (already factored in above)
- strength = theoretical coupling tightness
- 5–15 new nodes maximum; quality over quantity
- label: lowercase; use \\n to wrap if display text > 12 chars
- id: snake_case, max 3 words, must be unique and not a synonym of any existing id
- level: abstraction level — exactly one of:
    "theory"     (frameworks/computational models — e.g. predictive processing)
    "construct"  (mid-level psych/cognitive concepts — DEFAULT for ambiguous cases)
    "method"     (research methods/instruments — e.g. fMRI, driving simulator)
    "mechanism"  (brain regions/neurochemicals — e.g. amygdala, vasopressin)
    "domain"     (application areas/populations — e.g. adolescent development)
  Prefer "construct" when in doubt; only use mechanism/method when clearly biological/methodological.`,
    messages: [{ role: 'user', content: text.slice(0, 10000) }],
  });

  const raw   = response.content.map(b => b.text || '').join('');
  const clean = raw.replace(/```json|```/g, '').trim();
  return JSON.parse(clean);
}

// ── Graph merge ───────────────────────────────────────────────────────────────
export function mergeIntoGraph(graph, extracted, meta, paperWeight = 1.0) {
  const existingIds = new Set(graph.nodes.map(n => n.id));
  let newNodes = 0, newEdges = 0, boostedNodes = 0;

  (extracted.nodes || []).forEach(n => {
    n.weight = Math.max(0.1, Math.min(1.0, n.weight));

    if (existingIds.has(n.id)) {
      const existing = graph.nodes.find(node => node.id === n.id);
      if (existing) {
        const boosted = Math.min(1.0, existing.weight * 0.67 + n.weight * 0.33);
        if (boosted > existing.weight + 0.01) {
          c.info(`  ↑ ${n.id}: ${existing.weight.toFixed(2)} → ${boosted.toFixed(2)}`);
          existing.weight = Math.round(boosted * 100) / 100;
          boostedNodes++;
        }
      }
      return;
    }

    graph.nodes.push(n);
    existingIds.add(n.id);
    newNodes++;
  });

  const edgeSet = new Set(graph.edges.map(e => `${e.a}|${e.b}`));
  (extracted.edges || []).forEach(e => {
    const key = `${e.a}|${e.b}`, rev = `${e.b}|${e.a}`;
    if (edgeSet.has(key) || edgeSet.has(rev)) {
      const existing = graph.edges.find(ex =>
        (ex.a === e.a && ex.b === e.b) || (ex.a === e.b && ex.b === e.a)
      );
      if (existing) {
        existing.strength = Math.min(1.0,
          Math.round((existing.strength * 0.7 + e.strength * 0.3) * 100) / 100
        );
      }
      return;
    }
    if (!existingIds.has(e.a)) { c.warn(`  Unknown node in edge: ${e.a}`); return; }
    if (!existingIds.has(e.b)) { c.warn(`  Unknown node in edge: ${e.b}`); return; }
    graph.edges.push(e);
    edgeSet.add(key);
    newEdges++;
  });

  const paper = extracted.paper || {};
  graph.meta.papers.push({
    id:               meta.id || `paper_${Date.now()}`,
    title:            paper.title      || meta.title   || 'Unknown',
    year:             paper.year       || meta.year,
    venue:            paper.venue      || meta.venue,
    doi:              paper.doi        || meta.doi,
    arxivId:          meta.arxivId,
    url:              meta.url,
    pubType:          meta.pubType,
    authorPosition:   meta.authorPosition,
    paperWeight,
    extraction_source: meta.extraction_source || 'title-abstract',
    added:            new Date().toISOString(),
    nodes_contributed: (extracted.nodes || []).map(n => n.id),
  });

  return { newNodes, newEdges, boostedNodes };
}

// ── Force layout ──────────────────────────────────────────────────────────────
export function rebuildLayout(graph) {
  c.info('Running force-directed layout…');
  const N = graph.nodes.length;
  const clusterSeeds = [
    {x:0,y:0},{x:-2.8,y:-1.2},{x:2.5,y:-2.2},{x:1.2,y:2.8},
    {x:-1.5,y:2.8},{x:-3.2,y:1.5},{x:3.5,y:1.0},
  ];

  const pos = graph.nodes.map(n => {
    const s = clusterSeeds[n.cluster] || clusterSeeds[0];
    return { x: s.x + (Math.random()-0.5)*2, y: s.y + (Math.random()-0.5)*2, vx:0, vy:0 };
  });

  const REST=1.8, KS=0.12, KR=2.2, DAMP=0.82, BOUNDS=6.5;

  for (let iter = 0; iter < 400; iter++) {
    const cool = 1 - iter/400;
    for (let i = 0; i < N; i++) {
      for (let j = i+1; j < N; j++) {
        const dx=pos[i].x-pos[j].x, dy=pos[i].y-pos[j].y;
        const d=Math.sqrt(dx*dx+dy*dy)+0.01;
        const f=KR/(d*d);
        pos[i].vx+=f*dx/d; pos[i].vy+=f*dy/d;
        pos[j].vx-=f*dx/d; pos[j].vy-=f*dy/d;
      }
    }
    graph.edges.forEach(e => {
      const ai=graph.nodes.findIndex(n=>n.id===e.a);
      const bi=graph.nodes.findIndex(n=>n.id===e.b);
      if (ai<0||bi<0) return;
      const dx=pos[bi].x-pos[ai].x, dy=pos[bi].y-pos[ai].y;
      const d=Math.sqrt(dx*dx+dy*dy)+0.01;
      const rest=REST/(0.5+e.strength);
      const f=KS*(d-rest);
      pos[ai].vx+=f*dx/d; pos[ai].vy+=f*dy/d;
      pos[bi].vx-=f*dx/d; pos[bi].vy-=f*dy/d;
    });
    for (let i=0;i<N;i++) {
      pos[i].vx*=DAMP; pos[i].vy*=DAMP;
      pos[i].x=Math.max(-BOUNDS,Math.min(BOUNDS,pos[i].x+pos[i].vx*cool));
      pos[i].y=Math.max(-BOUNDS,Math.min(BOUNDS,pos[i].y+pos[i].vy*cool));
    }
  }

  graph.layout = graph.nodes.map((n,i) => ({ id:n.id, x:pos[i].x, y:pos[i].y }));
  c.ok(`Layout computed for ${N} nodes`);
}
```

- [ ] **Step 2: Verify the file was written correctly**

```bash
node -e "import('./graph/tool/lib.js').then(m => console.log(Object.keys(m).join(', ')))"
```
Expected output: `GRAPH_PATH, c, loadGraph, saveGraph, computePaperWeight, extractConcepts, mergeIntoGraph, rebuildLayout`

- [ ] **Step 3: Commit**

```bash
git add graph/tool/lib.js
git commit -m "feat: extract shared graph utilities to lib.js"
```

---

## Task 2: Update `graph/tool/index.js` to import from lib.js

Remove the seven locally-defined functions, replace with imports. No behavior changes.

**Files:**
- Modify: `graph/tool/index.js`

- [ ] **Step 1: Replace the console helpers block**

Find and remove lines 32–40 in `index.js` (the `const c = { ... }` block) and replace the `GRAPH_PATH` constant and the seven functions with two import lines at the top of the file, after the existing imports.

Replace:
```js
const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const GRAPH_PATH = path.join(__dirname, '..', 'graph.json');

// ── Console helpers ────────────────────────────────────────────────────────
const c = {
  info:  s => process.stdout.write(`\x1b[36m→\x1b[0m  ${s}\n`),
  ok:    s => process.stdout.write(`\x1b[32m✓\x1b[0m  ${s}\n`),
  warn:  s => process.stdout.write(`\x1b[33m⚠\x1b[0m  ${s}\n`),
  err:   s => process.stdout.write(`\x1b[31m✗\x1b[0m  ${s}\n`),
  head:  s => process.stdout.write(`\x1b[1m${s}\x1b[0m\n`),
  dim:   s => process.stdout.write(`\x1b[2m${s}\x1b[0m\n`),
  log:   s => process.stdout.write(`${s}\n`),
};

// ── Graph I/O ──────────────────────────────────────────────────────────────
function loadGraph() {
  if (!fs.existsSync(GRAPH_PATH)) throw new Error(`graph.json not found at ${GRAPH_PATH}`);
  return JSON.parse(fs.readFileSync(GRAPH_PATH, 'utf8'));
}

function saveGraph(graph) {
  fs.writeFileSync(GRAPH_PATH, JSON.stringify(graph, null, 2));
}
```

With:
```js
const __dirname  = path.dirname(fileURLToPath(import.meta.url));
import { c, GRAPH_PATH, loadGraph, saveGraph, computePaperWeight, extractConcepts, mergeIntoGraph, rebuildLayout } from './lib.js';
```

- [ ] **Step 2: Remove the duplicated function bodies**

Delete these function definitions from `index.js` (they're now imported from lib.js):
- `function computePaperWeight(meta) { ... }` (lines ~439–468)
- `async function extractConcepts(text, graph, paperWeight = 1.0) { ... }` (lines ~471–527)
- `function mergeIntoGraph(graph, extracted, meta, paperWeight = 1.0) { ... }` (lines ~530–601)
- `function rebuildLayout(graph) { ... }` (lines ~604–650)

- [ ] **Step 3: Fix the extractConcepts call in index.js**

`extractConcepts` now takes a 4th parameter `model`. The existing calls in index.js should explicitly pass `'claude-opus-4-5'` to preserve the current behavior.

Find every call to `extractConcepts(` in index.js and change:
```js
extracted = await extractConcepts(source.text, graph, pw);
```
to:
```js
extracted = await extractConcepts(source.text, graph, pw, 'claude-opus-4-5');
```
(There are two such calls — one in `add`, one in `import-cv`.)

- [ ] **Step 4: Fix the `list` command to use `nodes_contributed`**

Find this line in the `list` command:
```js
c.dim(`   Nodes: ${(p.nodesContributed||[]).join(', ') || '—'}`);
```
Replace with:
```js
c.dim(`   Nodes: ${(p.nodes_contributed||p.nodesContributed||[]).join(', ') || '—'}`);
```
(Fallback handles legacy camelCase entries already in graph.json.)

- [ ] **Step 5: Smoke test**

```bash
node graph/tool/index.js stats
```
Expected: prints node/edge/paper counts, no import errors.

```bash
node graph/tool/index.js list 2>&1 | head -20
```
Expected: lists first few papers, no errors.

- [ ] **Step 6: Commit**

```bash
git add graph/tool/index.js
git commit -m "refactor: index.js imports graph utilities from lib.js"
```

---

## Task 3: Add `.gitignore` entry for draft-proposals.json

**Files:**
- Modify: `.gitignore` (website repo root)

- [ ] **Step 1: Add the entry**

Append to `.gitignore`:
```
# Draft proposal buffer — private; reviewed manually before merging into graph.json
graph/draft-proposals.json
```

- [ ] **Step 2: Verify**

```bash
git check-ignore -v graph/draft-proposals.json
```
Expected: prints `.gitignore:N:graph/draft-proposals.json  graph/draft-proposals.json`

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore graph/draft-proposals.json"
```

---

## Task 4: Create `graph/tool/rebuild-from-corpus.js` — corpus loading + paper selection

Build the loadCorpusUniverse function that reads publications.json + corpus-catalog.json and buckets papers into three passes.

**Files:**
- Create: `graph/tool/rebuild-from-corpus.js`

- [ ] **Step 1: Create the file with universe loader**

```js
#!/usr/bin/env node
/**
 * rebuild-from-corpus.js — Full graph rebuild from vault full-text extractions.
 *
 * Usage:
 *   node rebuild-from-corpus.js [options]
 *
 * Options:
 *   --pass <n>        Run specific pass: 1, 2, 3, or all (default: all)
 *   --start-pass <n>  Resume from pass N without wiping graph
 *   --limit <n>       Max papers per pass (for testing)
 *   --dry-run         Extract but do not save
 *   --opus            Use claude-opus-4-7 instead of claude-sonnet-4-6
 *
 * Environment:
 *   ANTHROPIC_API_KEY  required
 *   CORPUS_REPO        path to research-corpus repo (default: ~/projects/research-corpus)
 */

import 'dotenv/config';
import fs   from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { program } from 'commander';
import { c, GRAPH_PATH, loadGraph, saveGraph, computePaperWeight, extractConcepts, mergeIntoGraph, rebuildLayout } from './lib.js';

const __dirname   = path.dirname(fileURLToPath(import.meta.url));
const HOME        = process.env.HOME;
const CORPUS_REPO = process.env.CORPUS_REPO || path.join(HOME, 'projects/research-corpus');
const VAULT_DIR   = path.join(CORPUS_REPO, 'vault');
const CATALOG_PATH = path.join(CORPUS_REPO, 'corpus-catalog.json');
const PUBS_PATH   = path.join(__dirname, '..', '..', 'data', 'publications.json');
const GRAPH_DIR   = path.join(__dirname, '..');
const PROPOSALS_PATH = path.join(GRAPH_DIR, 'draft-proposals.json');

const EXCLUDED_KEYWORDS = ['scicomm', 'commentary', 'unlisted'];

program
  .name('rebuild-from-corpus')
  .description('Rebuild graph.json from vault full-text extractions')
  .option('--pass <n>',       'pass to run: 1, 2, 3, or all', 'all')
  .option('--start-pass <n>', 'resume from pass N without wiping graph')
  .option('--limit <n>',      'max papers per pass (testing)')
  .option('--dry-run',        'extract without saving', false)
  .option('--opus',           'use claude-opus-4-7', false);

/**
 * Build the three-pass paper universe from publications.json + corpus-catalog.json.
 * Returns { pass1, pass2, pass3 } arrays of enriched paper objects.
 *
 * Pass 1: selected keyword, have_local
 * Pass 2: no selected keyword, have_local
 * Pass 3: have_draft (regardless of selected)
 */
function loadCorpusUniverse() {
  if (!fs.existsSync(PUBS_PATH))   throw new Error(`publications.json not found: ${PUBS_PATH}`);
  if (!fs.existsSync(CATALOG_PATH)) throw new Error(`corpus-catalog.json not found: ${CATALOG_PATH}`);

  const publications = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
  const catalog      = JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf-8'));
  const catalogEntries = catalog.entries;

  const pass1 = [], pass2 = [], pass3 = [];

  for (const pub of publications) {
    const kw = pub.keywords || [];

    // Filter: excluded keyword types
    if (EXCLUDED_KEYWORDS.some(k => kw.includes(k))) continue;

    // Must have a corpus entry
    const entry = catalogEntries[pub.id];
    if (!entry) continue;

    const nextAction = entry.acquisition?.next_action;
    if (!['have_local', 'have_draft'].includes(nextAction)) continue;

    const sha = entry.final_output?.sha;
    if (!sha) continue;

    const isDraft    = nextAction === 'have_draft';
    const isSelected = kw.includes('selected');

    const paper = { ...pub, sha, isDraft, isSelected };

    if (isDraft) {
      pass3.push(paper);
    } else if (isSelected) {
      pass1.push(paper);
    } else {
      pass2.push(paper);
    }
  }

  // Deterministic ordering within each pass
  const byId = (a, b) => a.id.localeCompare(b.id);
  pass1.sort(byId); pass2.sort(byId); pass3.sort(byId);

  return { pass1, pass2, pass3 };
}
```

- [ ] **Step 2: Verify the universe loader**

```bash
node -e "
import('./graph/tool/rebuild-from-corpus.js').then(() => {}).catch(() => {});
" 2>&1 | head -5
```

Then run this inline test to check counts:
```bash
node --input-type=module <<'EOF'
import 'dotenv/config';
import fs from 'fs';
import path from 'path';
const HOME = process.env.HOME;
const CORPUS_REPO = process.env.CORPUS_REPO || path.join(HOME, 'projects/research-corpus');
const CATALOG_PATH = path.join(CORPUS_REPO, 'corpus-catalog.json');
const PUBS_PATH = path.join(HOME, 'projects/website/data/publications.json');
const publications = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf-8'));
const EXCLUDED = ['scicomm', 'commentary', 'unlisted'];
let p1=0, p2=0, p3=0, excluded=0, noCatalog=0;
for (const pub of publications) {
  const kw = pub.keywords || [];
  if (EXCLUDED.some(k => kw.includes(k))) { excluded++; continue; }
  const entry = catalog.entries[pub.id];
  if (!entry) { noCatalog++; continue; }
  const action = entry.acquisition?.next_action;
  if (!['have_local','have_draft'].includes(action)) continue;
  if (!entry.final_output?.sha) continue;
  if (action === 'have_draft') p3++;
  else if (kw.includes('selected')) p1++;
  else p2++;
}
console.log(`Pass 1 (selected non-draft): ${p1}`);
console.log(`Pass 2 (non-selected non-draft): ${p2}`);
console.log(`Pass 3 (draft): ${p3}`);
console.log(`Excluded (scicomm/commentary/unlisted): ${excluded}`);
console.log(`No catalog entry: ${noCatalog}`);
EOF
```

Expected: Pass 1 ≈ 16, Pass 2 ≈ 26, Pass 3 = 3 (Wright, Sinclair, Knutson). Total ≈ 45–47.

---

## Task 5: Implement the three-pass extraction loop in `rebuild-from-corpus.js`

**Files:**
- Modify: `graph/tool/rebuild-from-corpus.js` (append to the file from Task 4)

- [ ] **Step 1: Add draft-proposals writer**

Append to `rebuild-from-corpus.js`:

```js
// ── Draft proposals ───────────────────────────────────────────────────────────
function writeDraftProposal(paperId, extracted, meta, paperWeight, model) {
  let proposals = { proposals: [] };
  if (fs.existsSync(PROPOSALS_PATH)) {
    try { proposals = JSON.parse(fs.readFileSync(PROPOSALS_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }

  // Replace any existing proposal for this paper (idempotent)
  proposals.proposals = proposals.proposals.filter(p => p.paper_id !== paperId);

  proposals.proposals.push({
    paper_id:         paperId,
    extracted_at:     new Date().toISOString(),
    model,
    paper_weight:     paperWeight,
    extraction_source: meta.extraction_source,
    nodes:            extracted.nodes || [],
    edges:            extracted.edges || [],
    paper_meta:       extracted.paper || {},
    reviewed:         false,
  });

  fs.writeFileSync(PROPOSALS_PATH, JSON.stringify(proposals, null, 2));
  c.ok(`  Draft proposal written for ${paperId}`);
}
```

- [ ] **Step 2: Add retry-wrapped extractConcepts**

Append to `rebuild-from-corpus.js`:

```js
// ── Retry logic ───────────────────────────────────────────────────────────────
async function extractConceptsWithRetry(text, graph, paperWeight, model, maxAttempts = 3) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await extractConcepts(text, graph, paperWeight, model);
    } catch (e) {
      const isJsonError = e instanceof SyntaxError || e.message?.includes('JSON');
      const isApiError  = e.status === 429 || (e.status >= 500 && e.status < 600);

      if (isJsonError && attempt < maxAttempts) {
        c.warn(`  JSON parse error (attempt ${attempt}/${maxAttempts}) — retrying…`);
        await new Promise(r => setTimeout(r, 3000));
        continue;
      }
      if (isApiError && attempt < maxAttempts) {
        const wait = attempt * 15;
        c.warn(`  API error ${e.status} — backing off ${wait}s (attempt ${attempt}/${maxAttempts})…`);
        await new Promise(r => setTimeout(r, wait * 1000));
        continue;
      }
      throw e;
    }
  }
}
```

- [ ] **Step 3: Add processPaper function**

Append to `rebuild-from-corpus.js`:

```js
// ── Per-paper processor ───────────────────────────────────────────────────────
async function processPaper(pub, graph, opts, passNum) {
  const shaPath = path.join(VAULT_DIR, 'extracted', `${pub.sha}.txt`);

  let text, extractionSource;
  if (fs.existsSync(shaPath)) {
    text = fs.readFileSync(shaPath, 'utf-8');
    extractionSource = 'full-text';
    c.info(`  vault/extracted/${pub.sha}.txt — ${text.length} chars`);
  } else {
    c.warn(`  vault/extracted/${pub.sha}.txt missing — falling back to title+abstract`);
    text = [pub.title, pub.abstract].filter(Boolean).join('\n\n');
    extractionSource = 'title-abstract';
  }

  // Pass 1 and selected papers always get paperWeight 1.0; others computed normally
  const paperWeight = (passNum === 1 || pub.isSelected)
    ? 1.0
    : computePaperWeight({ pubType: pub.pubType, authorPosition: pub.authorPosition, year: pub.year });

  const model = opts.opus ? 'claude-opus-4-7' : 'claude-sonnet-4-6';
  c.info(`  weight:${paperWeight}  model:${model}  source:${extractionSource}`);

  if (opts.dryRun) {
    c.dim('  [dry-run] skipping extraction');
    return;
  }

  const extracted = await extractConceptsWithRetry(text, graph, paperWeight, model);
  c.ok(`  extracted ${extracted.nodes?.length || 0} nodes, ${extracted.edges?.length || 0} edges`);

  const meta = {
    id:               pub.id,
    title:            pub.title,
    year:             pub.year,
    venue:            pub.venue,
    doi:              pub.doi,
    arxivId:          pub.arxivId,
    url:              pub.url,
    pubType:          pub.pubType,
    authorPosition:   pub.authorPosition,
    extraction_source: extractionSource,
  };

  if (passNum === 3) {
    writeDraftProposal(pub.id, extracted, meta, paperWeight, model);
  } else {
    const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, extracted, meta, paperWeight);
    saveGraph(graph);
    c.ok(`  +${newNodes} nodes, +${newEdges} edges, ↑${boostedNodes} boosted — total ${graph.nodes.length} nodes`);
  }
}
```

- [ ] **Step 4: Add the main() function and wire up commander**

Append to `rebuild-from-corpus.js`:

```js
// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  program.parse();
  const opts = program.opts();

  if (!process.env.ANTHROPIC_API_KEY) {
    c.err('ANTHROPIC_API_KEY not set. Add it to .env or export it.');
    process.exit(1);
  }

  const { pass1, pass2, pass3 } = loadCorpusUniverse();
  c.head('\nGraph Rebuild from Corpus');
  c.log(`  Pass 1 (selected, non-draft): ${pass1.length} papers`);
  c.log(`  Pass 2 (non-selected, non-draft): ${pass2.length} papers`);
  c.log(`  Pass 3 (draft): ${pass3.length} papers`);
  c.log(`  Corpus: ${CORPUS_REPO}`);
  c.log('');

  const startPass  = opts.startPass ? parseInt(opts.startPass) : null;
  const passMask   = opts.pass === 'all' ? [1, 2, 3] : [parseInt(opts.pass)];
  const limit      = opts.limit ? parseInt(opts.limit) : null;
  const passMap    = { 1: pass1, 2: pass2, 3: pass3 };

  // Wipe graph only on a fresh full run (no --start-pass)
  if (!opts.dryRun && !startPass) {
    const graph = loadGraph();
    const clusterBackup = graph.meta.clusters;
    graph.nodes        = [];
    graph.edges        = [];
    graph.layout       = [];
    graph.meta.papers  = [];
    graph.meta.clusters = clusterBackup; // clusters are stable design artifacts
    saveGraph(graph);
    c.ok('Graph wiped — fresh rebuild starting');
  }

  const graph = loadGraph();

  for (const passNum of passMask) {
    if (startPass && passNum < startPass) continue;

    const papers = passMap[passNum];
    const alreadyDone = new Set(graph.meta.papers.map(p => p.id));

    const toProcess = papers.filter(pub => {
      if (passNum !== 3 && alreadyDone.has(pub.id)) {
        c.dim(`  [skip] ${pub.id} — already in graph`);
        return false;
      }
      return true;
    });

    const batch = limit ? toProcess.slice(0, limit) : toProcess;
    c.head(`\n── Pass ${passNum} — ${batch.length} papers to process ─────────────────`);

    for (let i = 0; i < batch.length; i++) {
      const pub = batch[i];
      c.head(`\n[${i+1}/${batch.length}] ${pub.id}`);
      c.dim(`  ${pub.title?.slice(0, 80)}`);
      try {
        await processPaper(pub, graph, opts, passNum);
      } catch (e) {
        c.err(`  FAILED: ${e.message}`);
        c.err(`  Skipping ${pub.id} — continuing`);
      }
      if (i < batch.length - 1) await new Promise(r => setTimeout(r, 2000));
    }
  }

  if (!opts.dryRun) {
    c.head('\nFinalizing layout…');
    rebuildLayout(graph);
    saveGraph(graph);
    c.ok(`Rebuild complete: ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${graph.meta.papers.length} papers`);
    if (pass3.length) c.warn(`Pass 3 (${pass3.length} drafts) → inspect graph/draft-proposals.json, then run review-draft-proposals.js`);
  } else {
    c.warn('Dry run — nothing saved.');
  }
}

main().catch(e => { c.err(e.message); process.exit(1); });
```

- [ ] **Step 5: Dry-run smoke test (Pass 1, 1 paper)**

```bash
cd ~/projects/website && node graph/tool/rebuild-from-corpus.js --pass 1 --limit 1 --dry-run
```

Expected output:
- Prints universe counts (Pass 1 ≈ 16, Pass 2 ≈ 26, Pass 3 = 3)
- Shows `[1/1]` with a pub_key
- Prints vault path + char count
- Prints `[dry-run] skipping extraction`
- Ends with `Dry run — nothing saved.`

- [ ] **Step 6: Commit**

```bash
git add graph/tool/rebuild-from-corpus.js
git commit -m "feat: rebuild-from-corpus.js — three-pass full-text graph extraction"
```

---

## Task 6: Create `graph/tool/review-draft-proposals.js`

Interactive CLI to triage draft-extracted nodes before they enter the public graph.

**Files:**
- Create: `graph/tool/review-draft-proposals.js`

- [ ] **Step 1: Create the file**

```js
#!/usr/bin/env node
/**
 * review-draft-proposals.js — Review draft-extracted nodes before merging into graph.json.
 *
 * Reads graph/draft-proposals.json (gitignored). For each unreviewed proposal:
 *   [a]pprove → merges nodes/edges into graph.json
 *   [r]eject  → removes from draft-proposals.json
 *   [d]efer   → leaves for next session
 *
 * Usage:
 *   node review-draft-proposals.js
 */

import 'dotenv/config';
import fs       from 'fs';
import path     from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';
import { c, loadGraph, saveGraph, mergeIntoGraph, rebuildLayout } from './lib.js';

const __dirname      = path.dirname(fileURLToPath(import.meta.url));
const HOME           = process.env.HOME;
const PROPOSALS_PATH = path.join(__dirname, '..', 'draft-proposals.json');
const PUBS_PATH      = path.join(__dirname, '..', '..', 'data', 'publications.json');

async function main() {
  if (!fs.existsSync(PROPOSALS_PATH)) {
    c.err('No draft-proposals.json found. Run rebuild-from-corpus.js --pass 3 first.');
    process.exit(1);
  }

  const proposals    = JSON.parse(fs.readFileSync(PROPOSALS_PATH, 'utf-8'));
  const publications = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
  const pubIndex     = Object.fromEntries(publications.map(p => [p.id, p]));
  const graph        = loadGraph();

  const pending = proposals.proposals.filter(p => !p.reviewed);
  if (!pending.length) {
    c.ok('All proposals have been reviewed. Nothing to do.');
    return;
  }

  c.head(`\n── Draft Proposal Review — ${pending.length} pending ─────────────────`);
  c.log('  Commands: [a]pprove  [r]eject  [d]efer\n');

  const rl  = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = q => new Promise(resolve => rl.question(q, resolve));

  let approved = 0, rejected = 0, deferred = 0;

  for (const proposal of pending) {
    const existingIds = new Set(graph.nodes.map(n => n.id));

    c.head(`\n─── ${proposal.paper_id} ─────────────────────────────────`);
    c.log(`  Extracted: ${proposal.extracted_at}`);
    c.log(`  Model: ${proposal.model}   Weight: ${proposal.paper_weight}   Source: ${proposal.extraction_source}`);

    c.log(`\n  Nodes (${proposal.nodes.length}):`);
    for (const n of proposal.nodes) {
      const tag = existingIds.has(n.id) ? '\x1b[33m~\x1b[0m' : '\x1b[32m+\x1b[0m';
      c.log(`  ${tag} ${n.id.padEnd(30)} cluster:${n.cluster}  weight:${n.weight}  level:${n.level}`);
    }

    c.log(`\n  Edges (${proposal.edges.length}):`);
    const edgesToShow = proposal.edges.slice(0, 8);
    edgesToShow.forEach(e => c.log(`    ${e.a} ↔ ${e.b}  (${e.strength})`));
    if (proposal.edges.length > 8) c.log(`    … and ${proposal.edges.length - 8} more`);

    c.log('');
    const answer = (await ask('  > [a/r/d] ')).trim().toLowerCase();

    if (answer === 'a') {
      const pub  = pubIndex[proposal.paper_id] || {};
      const meta = {
        id:               proposal.paper_id,
        title:            pub.title,
        year:             pub.year,
        venue:            pub.venue,
        doi:              pub.doi,
        arxivId:          pub.arxivId,
        url:              pub.url,
        pubType:          pub.pubType,
        authorPosition:   pub.authorPosition,
        extraction_source: proposal.extraction_source,
      };
      const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, proposal, meta, proposal.paper_weight);
      saveGraph(graph);
      proposal.reviewed = true;
      proposal.decision = 'approved';
      approved++;
      c.ok(`  Approved — +${newNodes} nodes, +${newEdges} edges, ↑${boostedNodes} boosted`);
    } else if (answer === 'r') {
      proposal.reviewed = true;
      proposal.decision = 'rejected';
      rejected++;
      c.warn(`  Rejected — not added to graph`);
    } else {
      deferred++;
      c.dim(`  Deferred — will appear next session`);
    }

    // Persist after each decision (safe resumption if interrupted)
    fs.writeFileSync(PROPOSALS_PATH, JSON.stringify(proposals, null, 2));
  }

  rl.close();

  // If any proposals were approved, rebuild layout
  if (approved > 0) {
    c.head('\nRebuilding layout…');
    rebuildLayout(graph);
    saveGraph(graph);
  }

  c.log(`\nReview complete: ${approved} approved, ${rejected} rejected, ${deferred} deferred`);
  if (approved > 0) {
    c.warn('Run node data/inline-graph.js to sync graph.json into index.html + graph.html');
  }
}

main().catch(e => { c.err(e.message); process.exit(1); });
```

- [ ] **Step 2: Create a minimal test proposals file to verify the script runs**

```bash
cat > /tmp/test-proposals.json << 'EOF'
{
  "proposals": [
    {
      "paper_id": "test_paper",
      "extracted_at": "2026-05-25T00:00:00Z",
      "model": "claude-sonnet-4-6",
      "paper_weight": 0.8,
      "extraction_source": "full-text",
      "nodes": [{"id":"test_node","label":"test\nnode","weight":0.5,"cluster":0,"level":"construct"}],
      "edges": [],
      "paper_meta": {},
      "reviewed": false
    }
  ]
}
EOF
PROPOSALS_OVERRIDE=/tmp/test-proposals.json node -e "
import('./graph/tool/review-draft-proposals.js')
" 2>&1 | head -10
```

Expected: prints the proposal header, nodes, and the `> [a/r/d]` prompt (then exits or waits for input).

- [ ] **Step 3: Commit**

```bash
git add graph/tool/review-draft-proposals.js
git commit -m "feat: review-draft-proposals.js — interactive draft review CLI"
```

---

## Task 7: Full rebuild run + inline sync

Run the actual rebuild against all 47 papers, review drafts, then sync to HTML.

**Files:** None modified by this task — it's execution only.

- [ ] **Step 1: Back up current graph.json**

```bash
cp ~/projects/website/graph/graph.json ~/projects/website/graph/graph.json.bak-$(date +%Y%m%d)
```

- [ ] **Step 2: Dry-run Pass 1 (2 papers) to verify end-to-end schema**

```bash
node graph/tool/rebuild-from-corpus.js --pass 1 --limit 2 --dry-run
```

Expected: shows two pub_keys from Pass 1, vault paths, char counts, then `Dry run — nothing saved.`

- [ ] **Step 3: Run Pass 1 for real (2 papers) and inspect schema**

```bash
node graph/tool/rebuild-from-corpus.js --pass 1 --limit 2
```

Then verify the schema of the output:
```bash
node --input-type=module << 'EOF'
import fs from 'fs';
const g = JSON.parse(fs.readFileSync('graph/graph.json','utf-8'));
const p = g.meta.papers[0];
const requiredFields = ['id','title','year','pubType','authorPosition','paperWeight','extraction_source','added','nodes_contributed'];
const missing = requiredFields.filter(f => !(f in p));
if (missing.length) console.error('MISSING FIELDS:', missing);
else console.log('Schema OK. Sample paper:', JSON.stringify(p, null, 2));
console.log('Nodes:', g.nodes.length, '  Edges:', g.edges.length);
EOF
```

Expected: `Schema OK`, sample paper printed with `extraction_source: "full-text"`, `nodes_contributed: [...]`.

- [ ] **Step 4: Full rebuild (all passes)**

Expected wall time: 15–20 min. Cost: ~$3 with Sonnet 4.6.

```bash
node graph/tool/rebuild-from-corpus.js --pass all
```

Monitor progress — should print `[N/M] pub_key` for each paper across all three passes. Pass 3 will write `graph/draft-proposals.json` instead of modifying `graph.json`.

- [ ] **Step 5: Verify final graph statistics**

```bash
node graph/tool/index.js stats
```

Expected: ~200+ nodes (was 275 before, some churn expected), edges proportional, papers ≈ 44 (all non-draft papers).

- [ ] **Step 6: Review draft proposals**

```bash
node graph/tool/review-draft-proposals.js
```

For each of the three draft papers (Wright, Sinclair, Knutson): read the proposed nodes/edges, decide approve/reject/defer. Approved items merge into graph.json immediately.

- [ ] **Step 7: Sync graph.json into HTML**

```bash
node data/inline-graph.js
```

Expected: updates the inlined `graphData` blocks in `index.html` and `graph.html`.

- [ ] **Step 8: Commit and push**

```bash
git add graph/graph.json index.html graph.html
git add -f graph/draft-proposals.json   # Only if you want to commit reviewed state — skip if still deferred
git status
git commit -m "feat: rebuild graph from corpus full-text (47 papers, 3-pass Sonnet extraction)"
git push origin main
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task that implements it |
|---|---|
| `rebuild-from-corpus.js` with CORPUS_REPO env var | Task 5 |
| Three-pass execution (Pass 1 selected, Pass 2 fill, Pass 3 draft) | Task 5 |
| Pass 1 paperWeight floored at 1.0 | Task 5 (processPaper: `passNum === 1 \|\| pub.isSelected`) |
| Pass 3 output to `draft-proposals.json`, not graph.json | Task 5 (writeDraftProposal) |
| `review-draft-proposals.js` with a/r/d prompts | Task 6 |
| `extraction_source` field in meta.papers[] | Task 1 (lib.js mergeIntoGraph) |
| Idempotent / resumable (--start-pass N, skip already-done) | Task 5 (main: alreadyDone Set) |
| Exponential backoff on API errors | Task 5 (extractConceptsWithRetry) |
| Draft-proposals.json gitignored | Task 3 |
| No scicomm/commentary/unlisted in graph | Task 4 (EXCLUDED_KEYWORDS filter) |
| No patents | Task 4 (patents not in publications.json) |
| meta.clusters preserved across rebuild | Task 5 (main: clusterBackup) |
| `--opus` flag for escalation | Task 5 (processPaper model selection) |
| Fallback to title+abstract if vault/extracted/<sha>.txt missing | Task 5 (processPaper) |
| Run inline-graph.js after rebuild | Task 7 |

**No gaps found.**

**Type consistency:**
- `extractConcepts` signature in lib.js: `(text, graph, paperWeight, model)` — called identically in rebuild-from-corpus.js ✓
- `mergeIntoGraph` signature: `(graph, extracted, meta, paperWeight)` — called identically in index.js, rebuild-from-corpus.js, review-draft-proposals.js ✓
- `proposal.nodes` / `proposal.edges` shape matches what `mergeIntoGraph` reads from `extracted.nodes` / `extracted.edges` ✓
- `nodes_contributed` (snake_case) used in lib.js; index.js `list` command updated to handle both camelCase legacy and snake_case new ✓
