# v4 Concept-Extraction Pipeline Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps found in self-critique of the new full-text/candidate/dedup/lift concept-extraction pipeline (`graph/tool/{extract-fulltext.js,candidate_generation.py,dedup_candidates.py,classify_candidates.py,lift_concepts.js}`) before running it across the full 42-paper corpus and merging results into `graph/graph.json`.

**Architecture:** No new architecture — this hardens the existing 5-stage pipeline in place. Each task is either (a) a deterministic code fix in `lift_concepts.js` closing a specific validation gap, (b) a new Python script extending the existing embedding-based validation pattern, or (c) an empirical calibration/integration pass using the now-hardened pipeline.

**Tech Stack:** Node (ESM) for orchestration + Anthropic API calls, Python 3 + `sentence-transformers` (`all-MiniLM-L6-v2`, already installed) for embedding-based checks — same split already established across the pipeline.

**Revision note (2026-07-28):** This plan went through one round of adversarial review against the real codebase before execution. That review found: (1) a critical bug — `lift_concepts.js` overwrites `lift-output.json`/`lift-audit.json` on every run instead of merging, which would have silently broken three downstream steps that assumed cumulative results across incremental `--papers` batches; (2) the original `paperWeight` fix didn't match how the existing graph was actually built (`rebuild-from-corpus.js` gives selected/pass-1 papers a flat `1.0`, bypassing `computePaperWeight()` — the plan applied `computePaperWeight()` unconditionally) and would have imported a pre-existing `'science-comm'` vs `'scicomm'` key-mismatch bug in `lib.js` without fixing it; (3) the audit trail's `reuse_rejected` records never captured the actual similarity value that failed, only the static threshold — making the later recalibration step unable to do what it claimed. All three are fixed in the task list below (see Task 1, Task 2, Task 6). The false "these files are gitignored" claim is also fixed. Tasks are renumbered from the original 7 to 8 to fit the new foundational Task 1.

## Global Constraints

- No test framework in this toolchain (matches `research-corpus`'s own convention — "no test framework, verification via smoke-runs with expected output"). Every task's "test" is: run the script, inspect the printed/JSON output against a stated expectation.
- Nothing in this plan writes to `graph/graph.json` directly except Task 8's `promote_lift_output.js`, and even that only stages proposals into `graph/draft-proposals.json` — the actual merge still requires a human running the existing `review-draft-proposals.js` and approving per-paper. `graph/graph.json` is git-tracked, so a bad approved merge is still recoverable via `git diff`/`git checkout` before that's committed.
- `graph/candidates.json`, `graph/lift-output.json`, `graph/lift-audit.json`, and `graph/lift-run-summary.json` are generated working files, same category as the already-gitignored `graph/draft-proposals.json` — Task 1 Step 3 adds them to `.gitignore` to match (as of this plan's authoring, only `graph/draft-proposals.json` is actually listed there — the other three are currently untracked-but-not-ignored, which is low-risk since every commit step in this plan uses `git add <specific file>`, never `git add -A`, but should still be fixed for consistency).
- Every new/modified script keeps the existing `c.log`/`c.warn`/`c.ok`/`c.err` console-helper convention from `graph/tool/lib.js` — don't introduce a second logging style.

---

### Task 1: Make `lift_concepts.js` results additive across runs

**Problem (found in adversarial review, CRITICAL):** `main()` always starts from `const results = {}` and unconditionally overwrites `graph/lift-output.json` on every run. Task 7 (widening test coverage) runs the pipeline in incremental `--papers` batches — an 8-paper batch, then a 14-paper batch — expecting the file to accumulate to 22 papers. As originally written, the second run would wipe the first 8 papers' results, since nothing reads the existing file before writing. This silently breaks Task 7 Step 2 (reviews "the full 22-paper audit" that won't exist), Task 7 Step 3 (references "Step 1's full 22-paper batch" when Step 1 was never a 22-paper command), and Task 8 Step 2 (expects 22 promoted proposals, would see at most 14).

**Files:**
- Modify: `graph/tool/lift_concepts.js`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing new.
- Produces: `graph/lift-output.json` now accumulates across runs — each paper's entry is either added (new) or replaced (re-run of an already-lifted paper), and papers from prior runs not included in the current `--papers`/`--limit` selection are preserved untouched.

- [ ] **Step 1: Load existing `lift-output.json` before overwriting it**

In `graph/tool/lift_concepts.js`, find in `main()`:

```js
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = 'claude-sonnet-4-6';
  const results = {};
```

Replace with:

```js
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = 'claude-sonnet-4-6';

  // Load existing output so incremental --papers batches accumulate instead
  // of clobbering prior runs' results — downstream steps (widening test
  // coverage, promote_lift_output.js) depend on this file being cumulative
  // across multiple invocations, not a snapshot of only the latest one.
  let results = {};
  if (fs.existsSync(OUTPUT_PATH)) {
    try { results = JSON.parse(fs.readFileSync(OUTPUT_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }
```

The per-paper loop already does `results[id] = lifted;`, which naturally overwrites-by-key for a re-run of an already-present paper and adds new keys otherwise — no other change needed for the accumulation itself.

- [ ] **Step 2: Fix the `0.65` vs `0.6` inconsistency between the prompt text and the hard-check constant, while touching this file**

The `SYSTEM_PROMPT` tells the model reuse requires similarity "at least ~0.65," but the actual enforced constant is `REUSE_MIN_SIMILARITY = 0.6`. Found by adversarial review; not the focus of this task, but a one-line fix worth making now rather than leaving a misleading prompt in place. In `graph/tool/lift_concepts.js`, find in `SYSTEM_PROMPT`:

```
1. REUSE — only when similarity to nearest_existing is at least ~0.65 AND it's genuinely the
```

Replace `~0.65` with `~0.6`:

```
1. REUSE — only when similarity to nearest_existing is at least ~0.6 AND it's genuinely the
```

- [ ] **Step 3: Add the four generated working files to `.gitignore`**

In `.gitignore`, find the existing entry (search for `draft-proposals.json` to locate it — it's under the graph-tool-generated-files section per `graph/tool/rebuild-from-corpus.js`'s `PROPOSALS_PATH`). Add three lines immediately after it:

```
graph/candidates.json
graph/lift-output.json
graph/lift-audit.json
graph/lift-run-summary.json
```

- [ ] **Step 4: Verify accumulation works**

```bash
cd graph/tool
node lift_concepts.js --papers Sukumar2017overcoming
node -e "console.log(Object.keys(require('../lift-output.json')))"
# Expected: ["Sukumar2017overcoming"]
node lift_concepts.js --papers Wang2016autism
node -e "console.log(Object.keys(require('../lift-output.json')))"
# Expected: ["Sukumar2017overcoming", "Wang2016autism"] — both present, not just the latest
```

- [ ] **Step 5: Commit**

```bash
git add graph/tool/lift_concepts.js .gitignore
git commit -m "graph: make lift_concepts.js output additive across runs, fix prompt/threshold mismatch, gitignore generated files"
```

---

### Task 2: Thread `paperWeight` into node/edge weight scaling — matching how the existing graph was actually built

**Problem:** The original `extractConcepts()` in `lib.js` scaled raw weight by `paperWeight`. The new `lift_concepts.js` never computes or applies `paperWeight` at all. **Revised per adversarial review:** the original version of this task applied `computePaperWeight()` unconditionally to every paper, but `rebuild-from-corpus.js:169-171` (the script that built the *existing* 352-node graph) gives selected/pass-1 papers a flat `paperWeight = 1.0`, bypassing `computePaperWeight()` entirely — only non-selected papers get the computed value. Applying `computePaperWeight()` to every paper without that rule would put new-pipeline weights on a *different* scale than the existing graph for every selected paper, which is the opposite of this task's goal. The review also found `computePaperWeight()` in `lib.js` has a pre-existing bug — its `typeWeights` dict uses the key `'science-comm'`, but real data uses `pubType: 'scicomm'` (no hyphen), so scicomm papers silently fall through to the `?? 0.50` default instead of the intended `0.30`. This task now imports and depends on that function, so it fixes the typo rather than knowingly building on top of a bug.

**Files:**
- Modify: `graph/tool/lift_concepts.js`
- Modify: `graph/tool/lib.js`

**Interfaces:**
- Consumes: `computePaperWeight(meta)` — exported from `graph/tool/lib.js:94`, takes `{pubType, authorPosition, year}`, returns a number (not reliably bounded to 0.1–1.0 — a middle-author, pre-2015, `scicomm`-typed paper computes below 0.1; this task's own clamp re-bounds the result regardless, so the exact unclamped range doesn't matter downstream).
- Produces: every paper's entry in `graph/lift-output.json` gains a top-level `paperWeight` number field (read by Task 8's `promote_lift_output.js`).

- [ ] **Step 1: Fix the `'science-comm'` / `'scicomm'` key mismatch in `lib.js`**

In `graph/tool/lib.js`, find in `computePaperWeight()`:

```js
  const typeWeights = {
    'journal':       1.00,
    'conf-full':     0.85,
    'conf-workshop': 0.65,
    'preprint':      0.70,
    'science-comm':  0.30,
    'other':         0.40,
  };
```

Replace `'science-comm'` with `'scicomm'`, matching the real `pubType` value used throughout `data/publications.json`:

```js
  const typeWeights = {
    'journal':       1.00,
    'conf-full':     0.85,
    'conf-workshop': 0.65,
    'preprint':      0.70,
    'scicomm':       0.30,
    'other':         0.40,
  };
```

- [ ] **Step 2: Verify the fix against a real scicomm publication**

```bash
cd graph/tool
node -e "
const { computePaperWeight } = require('./lib.js');
const pubs = require('../../data/publications.json');
const p = pubs.find(x => x.pubType === 'scicomm');
console.log(p.id, p.pubType, computePaperWeight(p));
"
```

Expected: the printed weight reflects the `0.30` type weight (times position/recency factors), not the `0.50` default that would print before this fix — compare by temporarily reverting Step 1's edit if you want to see the before/after difference directly.

- [ ] **Step 3: Import `computePaperWeight` and apply the selected/pass-1 flat-1.0 rule**

In `graph/tool/lift_concepts.js`, change the import at the top:

```js
import { c, loadGraph, computePaperWeight } from './lib.js';
```

Find, in the `main()` loop, the block added by Task 1 Step 1's context — specifically the edge id-remapping loop that already exists right before the node/edge count logging:

```js
      for (const e of lifted.edges || []) {
        if (idRemap.has(e.a)) e.a = idRemap.get(e.a);
        if (idRemap.has(e.b)) e.b = idRemap.get(e.b);
      }
```

Immediately after it, insert — replicating the exact same selected/pass-1 flat-weight rule `rebuild-from-corpus.js:169-171` uses to build the existing graph (this pipeline has no "pass number" concept, so the equivalent condition is simply "is this publication tagged `selected`"):

```js
      const isSelected = (pub.keywords || []).includes('selected');
      const paperWeight = isSelected ? 1.0 : computePaperWeight(pub);
      for (const n of lifted.nodes || []) {
        n.weight = Math.round(Math.max(0.1, Math.min(1.0, n.weight * paperWeight)) * 100) / 100;
      }
      lifted.paperWeight = paperWeight;
```

- [ ] **Step 4: Verify both branches of the rule — a selected paper gets flat 1.0, a non-selected paper gets the computed value**

```bash
cd graph/tool
node -e "
const pubs = require('../../data/publications.json');
console.log('Klenk2026cats selected:', pubs.find(p=>p.id==='Klenk2026cats').keywords.includes('selected'));
console.log('Chen2025learning selected:', pubs.find(p=>p.id==='Chen2025learning').keywords.includes('selected'));
"
node lift_concepts.js --papers Klenk2026cats,Chen2025learning
node -e "
const out = require('../lift-output.json');
console.log('Klenk2026cats paperWeight:', out['Klenk2026cats'].paperWeight);
console.log('Chen2025learning paperWeight:', out['Chen2025learning'].paperWeight);
"
```

Expected: whichever of the two is `selected: true` shows `paperWeight: 1`; the other shows a `computePaperWeight()`-derived value (not exactly 1, unless it coincidentally computes to that).

- [ ] **Step 5: Commit**

```bash
git add graph/tool/lift_concepts.js graph/tool/lib.js
git commit -m "graph: scale lifted node weight by paperWeight matching rebuild-from-corpus.js's selected/pass-1 rule, fix scicomm key-mismatch bug"
```

---

### Task 3: Clamp edge-strength values and emit a distribution summary

**Problem:** Node `weight` and edge `strength` are pure LLM-generated numbers with zero validation — unlike `reuse_existing` and `cluster`, which now have hard checks. There's no evidence they're wrong, but nobody has looked, either. (Node `weight` is already clamped as part of Task 2 Step 3's scaling line; this task adds the missing edge-`strength` clamp and a distribution report for both.)

**Files:**
- Modify: `graph/tool/lift_concepts.js`

**Interfaces:**
- Consumes: nothing new.
- Produces: `graph/lift-run-summary.json`, weight/strength distribution stats for the just-completed run (not cumulative across runs — this is a diagnostic snapshot, unlike `lift-output.json`/`lift-audit.json` which do need to accumulate).

- [ ] **Step 1: Clamp edge strength**

In `graph/tool/lift_concepts.js`, right after the `paperWeight` scaling block added in Task 2 Step 3, add:

```js
      for (const e of lifted.edges || []) {
        e.strength = Math.round(Math.max(0.1, Math.min(1.0, e.strength)) * 100) / 100;
      }
```

- [ ] **Step 2: Collect distribution stats across the run**

Near the top of `main()`, after the `results` loading block from Task 1 Step 1, add:

```js
  const allWeights = [];
  const allStrengths = [];
```

Inside the per-paper loop, right after the clamping added in Step 1, add:

```js
      (lifted.nodes || []).forEach(n => allWeights.push(n.weight));
      (lifted.edges || []).forEach(e => allStrengths.push(e.strength));
```

- [ ] **Step 3: Write the summary at the end of the run**

Find the end of `main()`:

```js
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(results, null, 2));
  c.log(`\nWrote ${OUTPUT_PATH}`);
  c.warn('Nothing merged into graph.json — inspect lift-output.json, then run the review step.');
```

Replace with:

```js
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(results, null, 2));
  c.log(`\nWrote ${OUTPUT_PATH}`);

  function stats(arr) {
    if (!arr.length) return null;
    const sorted = [...arr].sort((a, b) => a - b);
    const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
    return {
      count: arr.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      mean: Math.round(mean * 1000) / 1000,
      median: sorted[Math.floor(sorted.length / 2)],
    };
  }
  const summary = { node_weight: stats(allWeights), edge_strength: stats(allStrengths) };
  fs.writeFileSync(SUMMARY_PATH, JSON.stringify(summary, null, 2));
  c.log(`Wrote ${SUMMARY_PATH} — weight/strength distribution for spot-checking outliers`);
  c.warn('Nothing merged into graph.json — inspect lift-output.json, then run the review step.');
```

Add the new path constant near the top of the file, alongside the existing `OUTPUT_PATH`:

```js
const SUMMARY_PATH = path.join(__dirname, '..', 'lift-run-summary.json');
```

- [ ] **Step 4: Run and sanity-check the summary**

```bash
cd graph/tool
node lift_concepts.js --papers Sukumar2017overcoming,Tost2010oxtr,Wang2016autism
cat ../lift-run-summary.json
```

Expected: `node_weight.min` >= 0.1 and `<=` 1.0, `edge_strength.min` >= 0.1 and `<=` 1.0 (clamping is working). If `mean` for either is suspiciously close to `min` or `max` (e.g. everything bunched at 0.85), that's a sign the model isn't differentiating — worth a manual look before Task 7's full run, but not necessarily a blocker.

- [ ] **Step 5: Commit**

```bash
git add graph/tool/lift_concepts.js
git commit -m "graph: clamp edge-strength values and emit a distribution summary for spot-checking"
```

---

### Task 4: Semantic (embedding-based) sibling-node dedup

**Problem:** `dedupeSiblingNodes()` in `lift_concepts.js:125` only merges new nodes that share a *literal* source-candidate phrase. It would miss two nodes describing the same concept via disjoint phrasing (e.g. one sourced from "reward magnitude", another from "payoff size" — zero string overlap, same underlying idea).

**Files:**
- Create: `graph/tool/dedupe_lifted_semantic.py`
- Modify: `graph/tool/lift_concepts.js` (final console message only, pointing at the new step)

**Interfaces:**
- Consumes: `graph/lift-output.json` (written by `lift_concepts.js`), specifically each paper's `nodes[]` array where non-reuse nodes have `{id, label, weight, cluster, level, source_candidates}`.
- Produces: rewrites `graph/lift-output.json` in place, merging any pair of new nodes *within the same paper* whose label embeddings are >= threshold similar — same merge semantics as the existing literal-overlap version (keep the node with more `source_candidates`, combine the lists, remap edges, drop self-loops).

- [ ] **Step 1: Write the script**

Create `graph/tool/dedupe_lifted_semantic.py`:

```python
#!/usr/bin/env python3
"""
dedupe_lifted_semantic.py — Second-pass sibling dedup for graph/lift-output.json,
catching semantic duplicates that lift_concepts.js's literal source-candidate-
overlap check (dedupeSiblingNodes in lift_concepts.js) can't see — two new
nodes from the same paper describing the same concept via disjoint phrasing
(e.g. "reward magnitude" vs "payoff size") share zero source candidates but
should still merge.

Run AFTER lift_concepts.js, before promote_lift_output.js.

Usage:
    python3 dedupe_lifted_semantic.py [--threshold 0.8]
"""
import json
import os
import re
import sys
import argparse

from sentence_transformers import SentenceTransformer
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIFT_OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'lift-output.json')


def clean_label(label):
    return re.sub(r'\s+', ' ', label.replace('\n', ' ')).strip()


def merge_pair(keep, dupe):
    keep_srcs = set(keep.get('source_candidates') or [])
    dupe_srcs = set(dupe.get('source_candidates') or [])
    keep['source_candidates'] = list(keep_srcs | dupe_srcs)


def dedupe_paper(paper_result, model, threshold):
    nodes = paper_result.get('nodes') or []
    new_nodes = [n for n in nodes if not n.get('reuse_existing') or n.get('reuse_existing') == 'null']
    if len(new_nodes) < 2:
        return 0

    labels = [clean_label(n['label']) for n in new_nodes]
    embs = model.encode(labels, show_progress_bar=False)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    embs_normed = embs / (norms + 1e-9)
    sims = embs_normed @ embs_normed.T

    # Union-find over pairs above threshold (same merge strategy as the JS
    # literal-overlap version: bigger source_candidates list wins).
    parent = {n['id']: n['id'] for n in new_nodes}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    n = len(new_nodes)
    merge_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= threshold:
                union(new_nodes[i]['id'], new_nodes[j]['id'])

    groups = {}
    for node in new_nodes:
        root = find(node['id'])
        groups.setdefault(root, []).append(node)

    id_remap = {}
    survivors = []
    for group in groups.values():
        if len(group) == 1:
            survivors.append(group[0])
            continue
        group.sort(key=lambda n: len(n.get('source_candidates') or []), reverse=True)
        keep = group[0]
        for dupe in group[1:]:
            print(f'    merged semantic sibling "{dupe["id"]}" into "{keep["id"]}"', file=sys.stderr)
            merge_pair(keep, dupe)
            id_remap[dupe['id']] = keep['id']
            merge_count += 1
        survivors.append(keep)

    reuse_nodes = [n for n in nodes if n.get('reuse_existing') and n.get('reuse_existing') != 'null']
    paper_result['nodes'] = survivors + reuse_nodes
    for e in paper_result.get('edges') or []:
        e['a'] = id_remap.get(e['a'], e['a'])
        e['b'] = id_remap.get(e['b'], e['b'])
    paper_result['edges'] = [e for e in (paper_result.get('edges') or []) if e['a'] != e['b']]

    return merge_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.8)
    args = parser.parse_args()

    with open(LIFT_OUTPUT_PATH) as f:
        results = json.load(f)

    print('Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    total_merges = 0
    for paper_id, paper_result in results.items():
        if 'error' in paper_result:
            continue
        merges = dedupe_paper(paper_result, model, args.threshold)
        total_merges += merges
        if merges:
            print(f'  {paper_id} — {merges} semantic merge(s)', file=sys.stderr)

    with open(LIFT_OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\n{total_merges} total semantic sibling merges across all papers.', file=sys.stderr)
    print(f'Updated {LIFT_OUTPUT_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Calibrate the threshold against a known non-duplicate pair first**

Before trusting `--threshold 0.8` on real data, verify it doesn't over-merge, the same way `dedup_candidates.py`'s threshold was originally sanity-checked: confirm two clearly-different existing node labels stay below threshold, and two near-synonyms land above it.

```bash
cd graph/tool
python3 -c "
from sentence_transformers import SentenceTransformer
import numpy as np
model = SentenceTransformer('all-MiniLM-L6-v2')
pairs = [('reward magnitude', 'payoff size'), ('amygdala activity', 'hippocampal volume')]
for a, b in pairs:
    ea, eb = model.encode([a, b])
    sim = np.dot(ea, eb) / (np.linalg.norm(ea) * np.linalg.norm(eb))
    print(f'{a!r} vs {b!r}: {sim:.3f}')
"
```

Expected: `reward magnitude` vs `payoff size` scores meaningfully high (likely >= 0.6, since they're near-synonyms in this context) — if it's below 0.8, the chosen threshold is too strict to catch this exact motivating case, and should be lowered (try 0.7) before proceeding. `amygdala activity` vs `hippocampal volume` (two real but unrelated neuroscience concepts) should score clearly lower — confirms the threshold isn't so loose it merges genuinely distinct mechanisms.

- [ ] **Step 3: Run on the 8 already-tested papers and confirm no regressions**

```bash
cd graph/tool
node lift_concepts.js --papers Sukumar2017overcoming,Wang2016autism,kim2026personagrambridgingpersonasproduct,Filipowicz2022familiarity,zhang2026surpriseaidesign,Castrellon2022social,Tost2010oxtr,Chen2025learning
python3 dedupe_lifted_semantic.py --threshold 0.8
cat ../lift-output.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(k, len(v.get('nodes',[]))) for k,v in d.items()]"
```

Expected: node counts per paper are equal to or lower than before this task (semantic merges only ever reduce count), and none of the 8 papers' node counts drop to 0 (a drop to 0 would mean the threshold is too aggressive and merged everything into one node — investigate before proceeding if that happens).

- [ ] **Step 4: Update `lift_concepts.js`'s final console message to mention the new step**

In `graph/tool/lift_concepts.js`, find:

```js
  c.warn('Nothing merged into graph.json — inspect lift-output.json, then run the review step.');
```

Replace with:

```js
  c.warn('Nothing merged into graph.json — run dedupe_lifted_semantic.py next, then the review step.');
```

- [ ] **Step 5: Commit**

```bash
git add graph/tool/dedupe_lifted_semantic.py graph/tool/lift_concepts.js
git commit -m "graph: add embedding-based semantic sibling dedup, catching disjoint-phrasing duplicates the literal-overlap check misses"
```

---

### Task 5: Reduce LLM non-determinism and document the residual limitation

**Problem:** Identical re-runs of `lift_concepts.js` on the same paper can produce different cluster assignments (observed directly with `kim2026personagrambridgingpersonasproduct`). The validation layers make *wrong* outputs self-correcting, but they don't make the *raw* output itself stable.

**Files:**
- Modify: `graph/tool/lift_concepts.js`

**Interfaces:** none — this is a same-shape internal change plus a doc comment.

- [ ] **Step 1: Set temperature to 0 on the API call**

In `graph/tool/lift_concepts.js`, find `liftPaper()`:

```js
async function liftPaper(client, pub, candidates, model) {
  const response = await client.messages.create({
    model,
    max_tokens: 1500,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: buildUserPrompt(pub, candidates) }],
  });
```

Add `temperature: 0`:

```js
async function liftPaper(client, pub, candidates, model) {
  const response = await client.messages.create({
    model,
    max_tokens: 1500,
    temperature: 0,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: buildUserPrompt(pub, candidates) }],
  });
```

- [ ] **Step 2: Document the residual limitation in the file header**

In `graph/tool/lift_concepts.js`, find the file header comment's `Usage:` block:

```js
 * Writes to graph/lift-output.json (NOT graph.json — nothing here merges
 * automatically; review the output, then a separate step wires it into
 * draft-proposals.json for review-draft-proposals.js).
 *
 * Usage:
 *   node lift_concepts.js [--limit N] [--papers id1,id2,...]
 */
```

Replace with (adds a new paragraph between the "Writes to..." paragraph and `Usage:`, and closes the block correctly):

```js
 * Writes to graph/lift-output.json (NOT graph.json — nothing here merges
 * automatically; review the output, then a separate step wires it into
 * draft-proposals.json for review-draft-proposals.js).
 *
 * Non-determinism: temperature is set to 0, which substantially reduces but
 * does not eliminate run-to-run variance (the API doesn't guarantee bitwise
 * determinism even at temperature 0). validateReuse/validateCluster/
 * dedupeSiblingNodes make WRONG outputs self-correcting, but don't guarantee
 * the same paper produces byte-identical output on a re-run. If exact
 * reproducibility becomes a requirement, the next step would be running each
 * paper N times and taking a majority vote on cluster/reuse decisions — not
 * implemented here as of 2026-07-28.
 *
 * Usage:
 *   node lift_concepts.js [--limit N] [--papers id1,id2,...]
 */
```

- [ ] **Step 3: Verify determinism improved (not perfect) with a repeat run**

```bash
cd graph/tool
node lift_concepts.js --papers kim2026personagrambridgingpersonasproduct > /tmp/run1.log 2>&1
cp ../lift-output.json /tmp/lift-output-run1.json
node lift_concepts.js --papers kim2026personagrambridgingpersonasproduct > /tmp/run2.log 2>&1
diff <(python3 -m json.tool /tmp/lift-output-run1.json) <(python3 -m json.tool ../lift-output.json)
```

Expected: fewer or no differences compared to before this change (can't guarantee zero-diff — that's the documented limitation, not a bug to chase further here).

- [ ] **Step 4: Commit**

```bash
git add graph/tool/lift_concepts.js
git commit -m "graph: set temperature=0 for lifting calls, document residual non-determinism"
```

---

### Task 6: Build a validation-actions audit trail

**Problem:** `validateReuse`, `validateCluster`, and `dedupeSiblingNodes` currently only report their corrections via `c.warn()` console output — nothing structured is persisted. There's no way to review, after the fact, whether the hard checks are themselves being too aggressive versus correctly catching real errors, without having watched the terminal live during the run. **Revised per adversarial review:** the original version of this task's `reuse_rejected` audit record only embedded the static `REUSE_MIN_SIMILARITY` threshold constant, never the actual similarity value that was checked and failed — making it impossible to later judge, from the audit file alone, how close a rejected reuse actually was to the threshold. Fixed below by capturing the real near-miss value.

**Files:**
- Modify: `graph/tool/lift_concepts.js`

**Interfaces:**
- Produces: `graph/lift-audit.json` — a flat array of `{paper_id, action, node_id, detail}` records, accumulated across runs the same way `lift-output.json` is (Task 1's pattern) — re-running a paper replaces its prior audit entries, papers not in the current run keep theirs.

- [ ] **Step 1: Have each validation function push into a shared audit array, capturing real values not just the threshold constant**

In `graph/tool/lift_concepts.js`, change each validation function's signature to accept an `audit` array and push a record alongside the existing `c.warn()` call. Find `validateReuse`:

```js
function validateReuse(lifted, candidatesByPhrase) {
  for (const n of lifted.nodes || []) {
    if (!n.reuse_existing || n.reuse_existing === 'null') continue;
    const supported = (n.source_candidates || []).some(phrase => {
      const cand = candidatesByPhrase.get(phrase);
      return cand && cand.nearest_existing.id === n.reuse_existing
        && cand.nearest_existing.similarity >= REUSE_MIN_SIMILARITY;
    });
    if (!supported) {
      c.warn(`    ✗ rejected reuse "${n.reuse_existing}" for [${n.source_candidates?.join(', ')}] — no source candidate scored >= ${REUSE_MIN_SIMILARITY} against it`);
      n.reuse_existing = null;
    }
  }
  return lifted;
}
```

Replace with — this version computes the actual best (highest) similarity found among the node's source candidates against its claimed `reuse_existing` id, and records that real number, not just the static threshold:

```js
function validateReuse(lifted, candidatesByPhrase, audit, paperId) {
  for (const n of lifted.nodes || []) {
    if (!n.reuse_existing || n.reuse_existing === 'null') continue;
    const matchingSims = (n.source_candidates || [])
      .map(phrase => candidatesByPhrase.get(phrase))
      .filter(cand => cand && cand.nearest_existing.id === n.reuse_existing)
      .map(cand => cand.nearest_existing.similarity);
    const bestSim = matchingSims.length ? Math.max(...matchingSims) : null;
    const supported = bestSim !== null && bestSim >= REUSE_MIN_SIMILARITY;
    if (!supported) {
      const detail = `rejected reuse "${n.reuse_existing}" for [${n.source_candidates?.join(', ')}] — best matching similarity was ${bestSim === null ? 'n/a (no source candidate matched this id at all)' : bestSim}, needed >= ${REUSE_MIN_SIMILARITY}`;
      c.warn(`    ✗ ${detail}`);
      audit.push({ paper_id: paperId, action: 'reuse_rejected', node_id: n.id, detail, best_similarity: bestSim, threshold: REUSE_MIN_SIMILARITY });
      n.reuse_existing = null;
    }
  }
  return lifted;
}
```

Apply the same pattern to `validateCluster` — find:

```js
    if (best.confidence >= CLUSTER_TRUST_THRESHOLD && best.id !== n.cluster) {
      c.warn(`    ✗ overrode cluster ${n.cluster} → ${best.id} (${best.name}) for "${n.id}" — classical prediction was confident (${best.confidence})`);
      n.cluster = best.id;
    }
```

Replace with:

```js
    if (best.confidence >= CLUSTER_TRUST_THRESHOLD && best.id !== n.cluster) {
      const detail = `overrode cluster ${n.cluster} -> ${best.id} (${best.name}) — classical prediction was confident (${best.confidence})`;
      c.warn(`    ✗ ${detail}`);
      audit.push({ paper_id: paperId, action: 'cluster_overridden', node_id: n.id, detail, confidence: best.confidence, threshold: CLUSTER_TRUST_THRESHOLD });
      n.cluster = best.id;
    }
```

And update `validateCluster`'s signature the same way:

```js
function validateCluster(lifted, candidatesByPhrase, audit, paperId) {
```

And `dedupeSiblingNodes` — find:

```js
    for (const dupe of group.slice(1)) {
      c.warn(`    ✗ merged sibling node "${dupe.id}" into "${keep.id}" — shared source candidates`);
      (dupe.source_candidates || []).forEach(p => merged.add(p));
      idRemap.set(dupe.id, keep.id);
    }
```

Replace with:

```js
    for (const dupe of group.slice(1)) {
      const detail = `merged sibling node "${dupe.id}" into "${keep.id}" — shared source candidates`;
      c.warn(`    ✗ ${detail}`);
      audit.push({ paper_id: paperId, action: 'sibling_merged', node_id: dupe.id, detail });
      (dupe.source_candidates || []).forEach(p => merged.add(p));
      idRemap.set(dupe.id, keep.id);
    }
```

And its signature:

```js
function dedupeSiblingNodes(lifted, audit, paperId) {
```

- [ ] **Step 2: Wire the audit array through `main()`, load-and-merge it the same way Task 1 did for `results`, and write it out**

In `main()`, find the `results` loading block added by Task 1 Step 1, and add an equivalent block for the audit array right after it:

```js
  let audit = [];
  if (fs.existsSync(AUDIT_PATH)) {
    try { audit = JSON.parse(fs.readFileSync(AUDIT_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }
```

Since `audit` is a flat array (not keyed by paper id like `results`), re-running a paper needs to explicitly drop its old entries before appending new ones — otherwise a re-run would duplicate audit records instead of replacing them. Find the top of the per-paper loop:

```js
  for (let i = 0; i < paperIds.length; i++) {
    const id = paperIds[i];
    const pub = pubIndex[id];
    c.head(`\n[${i + 1}/${paperIds.length}] ${id}`);
```

Add right after it:

```js
    audit = audit.filter(a => a.paper_id !== id);
```

Find the three validation calls:

```js
      const candidatesByPhrase = new Map(candidatesByPaper[id].map(c => [c.phrase, c]));
      validateReuse(lifted, candidatesByPhrase);
      validateCluster(lifted, candidatesByPhrase);
      dedupeSiblingNodes(lifted);
```

Replace with:

```js
      const candidatesByPhrase = new Map(candidatesByPaper[id].map(c => [c.phrase, c]));
      validateReuse(lifted, candidatesByPhrase, audit, id);
      validateCluster(lifted, candidatesByPhrase, audit, id);
      dedupeSiblingNodes(lifted, audit, id);
```

Find the end of `main()` (after Task 3's summary-writing block) and add, right before the final `c.warn(...)` line:

```js
  fs.writeFileSync(AUDIT_PATH, JSON.stringify(audit, null, 2));
  c.log(`Wrote ${AUDIT_PATH} — ${audit.length} correction(s) accumulated across all runs, for spot-checking over- and under-aggressiveness`);
```

Add the path constant near `SUMMARY_PATH`:

```js
const AUDIT_PATH = path.join(__dirname, '..', 'lift-audit.json');
```

- [ ] **Step 3: Run and confirm the audit file captures known corrections with real values, and accumulates correctly**

```bash
cd graph/tool
node lift_concepts.js --papers Castrellon2022social
cat ../lift-audit.json
```

Expected: at least one `cluster_overridden` record (this paper reliably triggers the cluster-2-default bug seen in every prior test run) with a real `confidence` number, and at least one `sibling_merged` record (the "crime-type bias" redundancy). If `graph/lift-audit.json` is `[]`, something regressed.

Then verify accumulation and per-paper replacement both work:

```bash
node lift_concepts.js --papers Wang2016autism
node -e "console.log(new Set(require('../lift-audit.json').map(a=>a.paper_id)))"
# Expected: Set contains both Castrellon2022social and Wang2016autism
node lift_concepts.js --papers Castrellon2022social
node -e "console.log(require('../lift-audit.json').filter(a=>a.paper_id==='Castrellon2022social').length)"
# Compare this count to before the re-run — it should reflect only the latest
# run's corrections for this paper, not double-counted with the first run's.
```

- [ ] **Step 4: Commit**

```bash
git add graph/tool/lift_concepts.js
git commit -m "graph: persist validation corrections to lift-audit.json with real similarity/confidence values, accumulated across runs"
```

---

### Task 7: Widen test coverage to a stratified sample and recalibrate thresholds

**Problem:** Only 8 of 42 papers tested (19%), all deliberately picked as stress cases — good for finding bugs, but leaving several `part_of` research-area groupings completely unexercised. `REUSE_MIN_SIMILARITY` (0.6) and `CLUSTER_TRUST_THRESHOLD` (0.5) are each calibrated on 1-2 real examples.

**Files:** none created/modified in this task except possibly the two threshold constants in `graph/tool/lift_concepts.js`, depending on findings.

**Interfaces:** none new.

- [ ] **Step 1: Run the hardened pipeline (Tasks 1-6 applied) on 14 more papers, one from each `part_of` group not yet covered by the original 8**

```bash
cd graph/tool
node lift_concepts.js --papers paredes2026unstuck,Nath2026designrewards,Hakimi2025creativity,Hakimi2024cognitive,Sumner2024personalizing,Hsiung2022heuristics,Hakimi2021pairing,Hakimi2020behavioral,Botvinik2020variability,Hakimi2014activity,Zink2010vasopressin,Tost2009mri,Goldin2009neural,Castrellon2022neural
python3 dedupe_lifted_semantic.py --threshold 0.8
```

Because Task 1 made `lift_concepts.js`'s output additive, this command (only the 14 *new* papers) correctly results in a cumulative 22-paper `graph/lift-output.json` — the original 8 papers' entries from earlier runs are preserved, not wiped. Verify this explicitly before moving on:

```bash
node -e "console.log(Object.keys(require('../lift-output.json')).length)"
# Expected: 22
```

This set (8 original + 14 new) touches every `part_of` grouping in the corpus at least once (verified via the grouping enumerated during plan authoring — `creativity-support`, `design-dm`, `creativity-psych-guide`, `pref-elicit`, `driving-dm`, `information-sampling`, `covid-dm`, the ungrouped `Hakimi2020behavioral`, `methods-imaging`, `imagine-discount`, `neuropeptide-social`, `scz`, `sad-emoreg`, and a second `juror-dm` paper to cross-check `Castrellon2022social`'s earlier result against its sibling).

- [ ] **Step 2: Review `graph/lift-audit.json` for both failure directions**

```bash
cd graph/tool
python3 -c "
import json
audit = json.load(open('../lift-audit.json'))
by_action = {}
for a in audit:
    by_action.setdefault(a['action'], []).append(a)
for action, items in by_action.items():
    print(f'{action}: {len(items)}')
"
```

For every `cluster_overridden` and `sibling_merged` record in the full 22-paper audit, manually read the `detail` field and the corresponding paper's title (`node -e "console.log(require('../../data/publications.json').find(p=>p.id==='<paper_id>').title)"`). Judge each one: was this correction actually right, given the paper's real topic? This is a human judgment call — there's no automatic ground truth for "was this the correct scientific concept," which is exactly why this step exists instead of being automated.

Specifically look for the failure mode not yet observed in the original 8: a `sibling_merged` record where the two merged node labels describe genuinely different sub-concepts that happened to share one candidate phrase by coincidence (over-aggressive merging). If found, note which paper and which node pair — this is evidence the semantic threshold from Task 4 (or the literal-overlap check) is too loose and needs raising.

- [ ] **Step 3: Adjust `REUSE_MIN_SIMILARITY` and `CLUSTER_TRUST_THRESHOLD` if the wider sample warrants it**

Task 6's fix means `reuse_rejected` records now carry a real `best_similarity` field (not just the static threshold), so this cross-reference actually works as intended:

```bash
cd /Users/shabnam/projects/website
node -e "
const audit = require('./graph/lift-audit.json');
audit.filter(a => a.action === 'reuse_rejected').forEach(a => {
  console.log(a.paper_id, '| best_similarity:', a.best_similarity, '| threshold:', a.threshold, '|', a.node_id);
});
audit.filter(a => a.action === 'cluster_overridden').forEach(a => {
  console.log(a.paper_id, '| confidence:', a.confidence, '| threshold:', a.threshold, '|', a.node_id);
});
"
```

If the wider sample shows the current thresholds are still cleanly separating good from bad corrections (no counter-examples found in Step 2), leave them unchanged and note that in the commit message. If a counter-example is found — a correction that should NOT have fired, near the threshold boundary — adjust the relevant constant in `graph/tool/lift_concepts.js` (`REUSE_MIN_SIMILARITY` at the top of the file, `CLUSTER_TRUST_THRESHOLD` alongside it) by a small increment (e.g. 0.05) in the direction that would have prevented the bad correction, then re-run Step 1's 14-paper command to confirm the adjustment doesn't introduce new problems (this remains a safe re-run rather than reprocessing all 22, since Task 1 made output additive).

- [ ] **Step 4: Commit**

If thresholds changed:

```bash
git add graph/tool/lift_concepts.js
git commit -m "graph: recalibrate reuse/cluster thresholds based on 22-paper stratified sample"
```

If thresholds were confirmed unchanged, no commit needed for this step — the audit trail itself (gitignored per Task 1 Step 3) is the evidence, and this task's completion is the review having happened, not necessarily a code change.

---

### Task 8: Build the promote-to-review integration step

**Problem:** Everything so far stops at `graph/lift-output.json`. There's no built path from validated lift output into `graph/graph.json` — the actual merge step doesn't exist yet.

**Files:**
- Create: `graph/tool/promote_lift_output.js`

**Interfaces:**
- Consumes: `graph/lift-output.json` (per-paper `{nodes, edges, paperWeight}`, `nodes[]` each `{id, label, weight, cluster, level, reuse_existing, source_candidates}`).
- Produces: appends entries to `graph/draft-proposals.json` matching the exact shape `review-draft-proposals.js` already expects (`{paper_id, extracted_at, model, paper_weight, extraction_source, nodes, edges, paper_meta, reviewed}` — confirmed against `graph/tool/rebuild-from-corpus.js`'s `writeDraftProposal()` and independently re-confirmed against `review-draft-proposals.js`'s own read logic during adversarial review), stripping the lift-pipeline-only fields (`reuse_existing`, `source_candidates`) that don't belong in `graph.json`'s node schema. Reuses `review-draft-proposals.js` unmodified for the actual approve/reject/defer UI and merge.

- [ ] **Step 1: Write the script**

Create `graph/tool/promote_lift_output.js`:

```js
#!/usr/bin/env node
/**
 * promote_lift_output.js — Converts graph/lift-output.json (validated by
 * lift_concepts.js + dedupe_lifted_semantic.py) into draft-proposals.json
 * entries, so the existing review-draft-proposals.js approve/reject/defer
 * tool can be reused unmodified for the actual graph.json merge.
 *
 * Strips lift-pipeline-only fields (reuse_existing, source_candidates) —
 * graph.json's node schema is {id, label, weight, cluster, level}, nothing
 * else.
 *
 * Usage:
 *   node promote_lift_output.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { c } from './lib.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LIFT_OUTPUT_PATH = path.join(__dirname, '..', 'lift-output.json');
const PROPOSALS_PATH = path.join(__dirname, '..', 'draft-proposals.json');

function cleanNode(n) {
  return { id: n.id, label: n.label, weight: n.weight, cluster: n.cluster, level: n.level };
}

function main() {
  if (!fs.existsSync(LIFT_OUTPUT_PATH)) {
    c.err(`No ${LIFT_OUTPUT_PATH} found. Run lift_concepts.js first.`);
    process.exit(1);
  }

  const liftResults = JSON.parse(fs.readFileSync(LIFT_OUTPUT_PATH, 'utf-8'));

  let proposals = { proposals: [] };
  if (fs.existsSync(PROPOSALS_PATH)) {
    try { proposals = JSON.parse(fs.readFileSync(PROPOSALS_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }

  let promoted = 0, skippedErrors = 0;
  for (const [paperId, result] of Object.entries(liftResults)) {
    if (result.error) { skippedErrors++; continue; }
    if (!result.nodes?.length) continue;

    // Replace any existing proposal for this paper (idempotent re-run).
    proposals.proposals = proposals.proposals.filter(p => p.paper_id !== paperId);

    proposals.proposals.push({
      paper_id: paperId,
      extracted_at: new Date().toISOString(),
      model: 'claude-sonnet-4-6',
      paper_weight: result.paperWeight ?? 1.0,
      extraction_source: 'full-text-v4-lifted',
      nodes: result.nodes.map(cleanNode),
      edges: result.edges || [],
      paper_meta: {},
      reviewed: false,
    });
    promoted++;
    c.ok(`  ${paperId} — promoted (${result.nodes.length} nodes)`);
  }

  fs.writeFileSync(PROPOSALS_PATH, JSON.stringify(proposals, null, 2));
  c.log(`\nPromoted ${promoted} paper(s) to ${PROPOSALS_PATH} (${skippedErrors} skipped due to lift errors).`);
  c.warn('Run review-draft-proposals.js to approve/reject before anything touches graph.json.');
}

main();
```

- [ ] **Step 2: Run it on the 22-paper batch from Task 7 and verify the shape matches what `review-draft-proposals.js` expects**

```bash
cd graph/tool
node promote_lift_output.js
node -e "
const p = require('../draft-proposals.json');
console.log('total proposals:', p.proposals.length);
const first = p.proposals.find(x => x.extraction_source === 'full-text-v4-lifted');
console.log(JSON.stringify(first, null, 2).slice(0, 500));
"
```

Expected: `total proposals` count matches the number of successfully-lifted papers from Task 7 (22, minus any that errored) — this now holds because Task 1 made `lift-output.json` genuinely cumulative. The printed sample proposal has exactly the fields `paper_id, extracted_at, model, paper_weight, extraction_source, nodes, edges, paper_meta, reviewed` — no `reuse_existing` or `source_candidates` leaking through on any node (confirm by checking `first.nodes[0]` has exactly 5 keys: `id, label, weight, cluster, level`).

- [ ] **Step 3: Do one real, careful review pass through `review-draft-proposals.js` on a small subset**

This is the first time anything from this pipeline actually reaches `graph.json` — do it deliberately, not as a rubber-stamp batch-approve.

```bash
cd graph/tool
node review-draft-proposals.js
```

For the first 3-4 proposals shown, cross-reference against `graph/lift-audit.json` for that `paper_id` before deciding — if a paper had a `sibling_merged` or `cluster_overridden` correction, double check that correction still looks right before approving. Defer (`d`) any proposal that looks uncertain rather than guessing; deferred proposals persist for next session per the tool's existing behavior (`review-draft-proposals.js:100-101`).

- [ ] **Step 4: Commit**

```bash
git add graph/tool/promote_lift_output.js
git commit -m "graph: add promote_lift_output.js, wiring the v4 pipeline into the existing draft-proposal review flow"
```

---

## Post-plan state

After all 8 tasks: the pipeline accumulates results correctly across incremental runs instead of silently clobbering prior work, has publication-importance-scaled weights that actually match how the existing graph was built (including a fixed pre-existing `scicomm` weighting bug), clamped and distribution-checked weight/strength values, two independent layers of sibling-node dedup (literal + semantic), reduced (documented, not eliminated) non-determinism, a persistent audit trail with real similarity/confidence values for every automated correction, threshold values re-examined against a genuinely-cumulative 22-paper (52%) stratified sample instead of 1-2 examples, and a working, tested path from `lift-output.json` into `graph.json` via the existing human-reviewed approval flow. The remaining 20 papers not covered by the 22-paper sample still need to run through the same pipeline before a full-corpus merge — that's normal remaining pipeline usage at that point, not a gap in this hardening plan.
