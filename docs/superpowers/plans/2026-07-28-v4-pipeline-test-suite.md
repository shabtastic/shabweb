# v4 Pipeline Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight, dependency-free unit test suite covering the pure/deterministic functions added during the v4-concept-extraction-hardening work, so future changes to threshold logic, merge logic, and the antonym guard can be verified in seconds instead of requiring another full agent-driven review cycle.

**Architecture:** Two independent test files, one per language already in use in `graph/tool/` — no new frameworks, no new dependencies. JS uses Node's built-in `assert` module; Python uses plain `assert` statements. Both print PASS/FAIL per case and exit non-zero on any failure, matching the project's existing zero-dependency, no-build-step convention.

**Tech Stack:** Node (ESM, `"type": "module"` already set in `graph/tool/package.json`), Python 3 (stdlib only for the tests themselves — `dedupe_lifted_semantic.py` imports `sentence_transformers`/`numpy` at module level, but the test file only imports three pure functions from it, never instantiates the model).

## Global Constraints

- No test framework (jest, mocha, pytest, etc.) — matches this project's established convention, explicitly documented in the prior hardening plan's Global Constraints ("No test framework in this toolchain... verification is smoke-runs with expected output"). This plan extends that convention with plain-assert test *files*, not a framework.
- Every JS file keeps the existing `c.log`/`c.warn`/`c.ok`/`c.err` console-helper convention from `graph/tool/lib.js` for any *production* code touched — the new test files themselves may use plain `console.log`/`print`, since they're test harnesses, not pipeline stages.
- Nothing in this plan touches `graph/graph.json`, calls the Anthropic API, or loads the `sentence-transformers` model — every test target is a pure function operating on plain objects/strings.
- This plan executes on the same branch/worktree as the prior hardening plan (`v4-concept-extraction-hardening`, at `/Users/shabnam/projects/website/.worktrees/v4-hardening`) — do not create a new worktree.

---

### Task 1: Export testable functions from `lift_concepts.js`, add JS test suite

**Problem:** `graph/tool/lift_concepts.js` has four pure, deterministic functions (`validateReuse`, `validateCluster`, `dedupeSiblingNodes`, `buildUserPrompt`) that are currently plain top-level `function` declarations with no `export` keyword — a test file in the same ESM module system (`"type": "module"` is already set in `graph/tool/package.json`) cannot import them without that keyword. `graph/tool/lib.js`'s `computePaperWeight` is already exported and needs no source change, just test coverage.

Note on scope vs. the original ask: the "selected paper gets a flat 1.0 weight" rule is not inside `computePaperWeight()` — it's a two-line wrapper at the call site in `lift_concepts.js`'s `main()` (`const isSelected = ...; const paperWeight = isSelected ? 1.0 : computePaperWeight(pub);`), and `main()` is explicitly out of scope (it does real API/file I/O). So this task instead tests two cases that exercise `computePaperWeight()`'s own type/position/recency math directly.

**Files:**
- Modify: `graph/tool/lift_concepts.js:97,137,197,219`
- Create: `graph/tool/lift_concepts.test.js`

**Interfaces:**
- Consumes: `validateReuse(lifted, candidatesByPhrase, audit, paperId)`, `validateCluster(lifted, candidatesByPhrase, audit, paperId)`, `dedupeSiblingNodes(lifted, audit, paperId)`, `buildUserPrompt(pub, candidates)` — all four take/mutate plain objects, no I/O. `computePaperWeight(meta)` from `graph/tool/lib.js` — already exported, pure, returns a number.
- Produces: `node graph/tool/lift_concepts.test.js` exits 0 with all cases printed `✓`, or exits 1 with failing cases printed `✗` plus a message.

- [ ] **Step 1: Add `export` to the four target functions**

In `graph/tool/lift_concepts.js`, make these four exact one-word insertions (add `export ` immediately before `function`, changing nothing else on the line):

Line 97, currently:
```js
function buildUserPrompt(pub, candidates) {
```
becomes:
```js
export function buildUserPrompt(pub, candidates) {
```

Line 137, currently:
```js
function dedupeSiblingNodes(lifted, audit, paperId) {
```
becomes:
```js
export function dedupeSiblingNodes(lifted, audit, paperId) {
```

Line 197, currently:
```js
function validateCluster(lifted, candidatesByPhrase, audit, paperId) {
```
becomes:
```js
export function validateCluster(lifted, candidatesByPhrase, audit, paperId) {
```

Line 219, currently:
```js
function validateReuse(lifted, candidatesByPhrase, audit, paperId) {
```
becomes:
```js
export function validateReuse(lifted, candidatesByPhrase, audit, paperId) {
```

No other line in the file changes. `main()` still calls these four functions exactly as before (unqualified, since they're in the same module) — `export` does not change local call syntax, only what other modules can import.

- [ ] **Step 2: Verify the file still runs without a syntax error after the export additions**

```bash
cd graph/tool
node --check lift_concepts.js
```

Expected: no output, exit code 0 (a syntax check, not a real run — this does not call the Anthropic API).

- [ ] **Step 3: Write the test file**

Create `graph/tool/lift_concepts.test.js`:

```js
#!/usr/bin/env node
/**
 * lift_concepts.test.js — plain-assert test suite for the pure functions
 * in lift_concepts.js and lib.js. No test framework (matches this
 * project's zero-dependency convention) — run directly:
 *   node lift_concepts.test.js
 * Prints PASS/FAIL per case, exits 1 on any failure.
 *
 * Deliberately does NOT test liftPaper() or main() — both require a real
 * Anthropic API call and are covered by this pipeline's existing smoke-run
 * verification convention instead.
 */

import assert from 'assert';
import { validateReuse, validateCluster, dedupeSiblingNodes, buildUserPrompt } from './lift_concepts.js';
import { computePaperWeight } from './lib.js';

let failures = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
  } catch (err) {
    failures++;
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
  }
}

console.log('validateReuse');

test('rejects reuse when best matching similarity is below REUSE_MIN_SIMILARITY (0.6)', () => {
  const lifted = { nodes: [{ id: 'n1', reuse_existing: 'existing_x', source_candidates: ['phrase a'] }] };
  const candidatesByPhrase = new Map([['phrase a', { nearest_existing: { id: 'existing_x', similarity: 0.5 } }]]);
  const audit = [];
  validateReuse(lifted, candidatesByPhrase, audit, 'paper1');
  assert.strictEqual(lifted.nodes[0].reuse_existing, null);
  assert.strictEqual(audit.length, 1);
  assert.strictEqual(audit[0].action, 'reuse_rejected');
  assert.strictEqual(audit[0].best_similarity, 0.5);
});

test('accepts reuse when similarity clears REUSE_MIN_SIMILARITY', () => {
  const lifted = { nodes: [{ id: 'n2', reuse_existing: 'existing_y', source_candidates: ['phrase b'] }] };
  const candidatesByPhrase = new Map([['phrase b', { nearest_existing: { id: 'existing_y', similarity: 0.8 } }]]);
  const audit = [];
  validateReuse(lifted, candidatesByPhrase, audit, 'paper1');
  assert.strictEqual(lifted.nodes[0].reuse_existing, 'existing_y');
  assert.strictEqual(audit.length, 0);
});

console.log('validateCluster');

test('overrides cluster when classical prediction is confident and disagrees', () => {
  const lifted = { nodes: [{ id: 'n3', cluster: 2, source_candidates: ['phrase c'] }] };
  const candidatesByPhrase = new Map([['phrase c', { predicted_cluster: { id: 5, name: 'Social, Cognitive, & Affective Neuroscience', confidence: 0.75 } }]]);
  const audit = [];
  validateCluster(lifted, candidatesByPhrase, audit, 'paper1');
  assert.strictEqual(lifted.nodes[0].cluster, 5);
  assert.strictEqual(audit.length, 1);
  assert.strictEqual(audit[0].action, 'cluster_overridden');
});

test('leaves cluster alone when classical confidence is below CLUSTER_TRUST_THRESHOLD (0.5)', () => {
  const lifted = { nodes: [{ id: 'n4', cluster: 2, source_candidates: ['phrase d'] }] };
  const candidatesByPhrase = new Map([['phrase d', { predicted_cluster: { id: 5, name: 'X', confidence: 0.3 } }]]);
  const audit = [];
  validateCluster(lifted, candidatesByPhrase, audit, 'paper1');
  assert.strictEqual(lifted.nodes[0].cluster, 2);
  assert.strictEqual(audit.length, 0);
});

console.log('dedupeSiblingNodes');

test('merges sibling nodes sharing a literal source_candidate phrase, remaps edges, drops self-loops', () => {
  const lifted = {
    nodes: [
      { id: 'a', source_candidates: ['shared', 'x1', 'x2'], reuse_existing: null },
      { id: 'b', source_candidates: ['shared', 'y1'], reuse_existing: null },
    ],
    edges: [{ a: 'b', b: 'external', strength: 0.7 }],
  };
  const audit = [];
  dedupeSiblingNodes(lifted, audit, 'paper1');
  assert.strictEqual(lifted.nodes.length, 1);
  assert.strictEqual(lifted.nodes[0].id, 'a');
  assert.deepStrictEqual([...lifted.nodes[0].source_candidates].sort(), ['shared', 'x1', 'x2', 'y1']);
  assert.deepStrictEqual(lifted.edges, [{ a: 'a', b: 'external', strength: 0.7 }]);
  assert.strictEqual(audit.length, 1);
  assert.strictEqual(audit[0].action, 'sibling_merged');
  assert.strictEqual(audit[0].node_id, 'b');
});

test('does not merge nodes with disjoint source_candidates', () => {
  const lifted = {
    nodes: [
      { id: 'p', source_candidates: ['only-p'], reuse_existing: null },
      { id: 'q', source_candidates: ['only-q'], reuse_existing: null },
    ],
    edges: [],
  };
  const audit = [];
  dedupeSiblingNodes(lifted, audit, 'paper1');
  assert.strictEqual(lifted.nodes.length, 2);
  assert.strictEqual(audit.length, 0);
});

console.log('buildUserPrompt');

test('truncates to TOP_CANDIDATES_PER_PAPER (15) and maps candidate fields correctly', () => {
  const pub = { title: 'Test Paper', venue: 'Test Venue', year: 2024 };
  const candidates = Array.from({ length: 17 }, (_, i) => ({
    phrase: `phrase ${i}`,
    freq: i,
    nearest_existing: { id: `node_${i}`, similarity: 0.5 },
    predicted_cluster: { name: 'Cluster X', confidence: 0.6 },
    predicted_level: { value: 'construct', confidence: 0.7 },
  }));
  const prompt = buildUserPrompt(pub, candidates);
  const jsonPart = prompt.slice(0, prompt.indexOf('\n\nRespond'));
  const parsed = JSON.parse(jsonPart);
  assert.strictEqual(parsed.paper.title, 'Test Paper');
  assert.strictEqual(parsed.candidates.length, 15);
  assert.strictEqual(parsed.candidates[0].nearest_existing, 'node_0');
  assert.strictEqual(parsed.candidates[0].predicted_cluster, 'Cluster X');
});

console.log('computePaperWeight');

test('journal, first-author, recent paper scores at the ceiling', () => {
  const w = computePaperWeight({ pubType: 'journal', authorPosition: 'first', year: 2024 });
  assert.strictEqual(w, 1);
});

test('conf-workshop, middle-author, older paper scores low', () => {
  const w = computePaperWeight({ pubType: 'conf-workshop', authorPosition: 'middle', year: 2017 });
  assert.strictEqual(w, 0.21);
});

console.log(`\n${failures === 0 ? 'All tests passed.' : `${failures} test(s) failed.`}`);
process.exit(failures === 0 ? 0 : 1);
```

- [ ] **Step 4: Run the test suite and verify all 9 cases pass**

```bash
cd graph/tool
node lift_concepts.test.js
```

Expected: 9 lines each starting `✓` (2 under `validateReuse`, 2 under `validateCluster`, 2 under `dedupeSiblingNodes`, 1 under `buildUserPrompt`, 2 under `computePaperWeight`), ending with `All tests passed.` and exit code 0 (`echo $?` after the run should print `0`).

Note: `validateReuse`, `validateCluster`, and `dedupeSiblingNodes` each call `c.warn(...)` in the production code whenever they make a correction, and that warning is printed to stdout with its own leading `✗` character (e.g. `⚠      ✗ merged sibling node "b" into "a"…`) as part of the pipeline's normal audit-logging behavior — this is expected and is not a test failure. Three of the nine passing tests will each have one of these interleaved warning lines above their `✓` line. Do not treat a `✗`-prefixed line as a failing test on its own — a genuinely failing test prints `✗` immediately followed by its own test *name* (via the `test()` helper), and the run's real pass/fail signal is the exit code plus the final `All tests passed.` / `N test(s) failed.` line.

- [ ] **Step 5: Verify a genuine failure is caught (sanity-check the harness itself)**

Temporarily break one assertion to confirm the runner actually detects failures, then revert:

```bash
cd graph/tool
sed -i.bak "s/assert.strictEqual(w, 1);/assert.strictEqual(w, 999);/" lift_concepts.test.js
node lift_concepts.test.js; echo "exit code: $?"
mv lift_concepts.test.js.bak lift_concepts.test.js
node lift_concepts.test.js; echo "exit code: $?"
```

Expected: first run shows a `✗` line whose test name is "journal, first-author, recent paper scores at the ceiling" (under `computePaperWeight`) with an assertion-mismatch message below it, and `exit code: 1`; second run (after revert) shows all `✓` again (plus the three expected `c.warn` lines from Step 4's note) with `exit code: 0`. Confirm `git diff graph/tool/lift_concepts.test.js` is empty after the revert (the `.bak` file must not be left behind or committed).

- [ ] **Step 6: Commit**

```bash
git add graph/tool/lift_concepts.js graph/tool/lift_concepts.test.js
git commit -m "graph: add plain-assert test suite for lift_concepts.js's pure validation/merge/prompt-building functions"
```

---

### Task 2: Add Python test suite for `dedupe_lifted_semantic.py`

**Problem:** `is_antonym_pair`, `_normalize_word`, and `clean_label` in `graph/tool/dedupe_lifted_semantic.py` are the functions this session's adversarial review process spent the most effort hand-verifying (the antonym-guard bug and its fix) — right now that verification only exists as one-off `python3 -c "..."` commands typed during code review, not as a repeatable file. Unlike the JS side, no source changes are needed here — these three functions are already plain module-level `def`s, importable without restructuring (this was confirmed during the hardening work's own code review, which imported `is_antonym_pair` this same way to independently verify it).

**Files:**
- Create: `graph/tool/dedupe_lifted_semantic.test.py`

**Interfaces:**
- Consumes: `is_antonym_pair(label_a, label_b)`, `_normalize_word(w)`, `clean_label(label)` from `graph/tool/dedupe_lifted_semantic.py` — all three are pure string functions, no model/file I/O.
- Produces: `python3 dedupe_lifted_semantic.test.py` (run from `graph/tool/`) exits 0 with all cases printed with a checkmark, or exits 1 with failing cases marked and a message.

- [ ] **Step 1: Write the test file**

Create `graph/tool/dedupe_lifted_semantic.test.py`:

```python
#!/usr/bin/env python3
"""
dedupe_lifted_semantic.test.py — plain-assert test suite for the pure
functions in dedupe_lifted_semantic.py (is_antonym_pair, _normalize_word,
clean_label). No test framework (matches this project's zero-dependency
convention) — run directly from graph/tool/:
    python3 dedupe_lifted_semantic.test.py
Prints PASS/FAIL per case, exits 1 on any failure.

Deliberately does NOT test dedupe_paper() or main() — both require loading
the real sentence-transformers model and are covered by this pipeline's
existing smoke-run verification convention instead. Importing this module
still triggers dedupe_lifted_semantic.py's own `from sentence_transformers
import SentenceTransformer` at the top of that file (Python executes a
module top-to-bottom on import) — this is a real but small one-time cost
(no model weights are loaded; SentenceTransformer(...) is only
instantiated inside main(), which this test file never calls).
"""
import sys

from dedupe_lifted_semantic import is_antonym_pair, _normalize_word, clean_label

failures = 0


def test(name, actual, expected):
    global failures
    try:
        assert actual == expected, f'expected {expected!r}, got {actual!r}'
        print(f'  ✓ {name}')
    except AssertionError as e:
        failures += 1
        print(f'  ✗ {name}')
        print(f'    {e}')


print('is_antonym_pair')

test('goal-aligned vs goal-agnostic (the motivating bug case)',
     is_antonym_pair('Goal-Aligned Reward', 'Goal-Agnostic Reward'), True)

test('high vs low anxiety (textbook antonym pair, scores higher than the bug case)',
     is_antonym_pair('High Anxiety', 'Low Anxiety'), True)

test('reward magnitude vs reward size (true near-duplicate, not antonym)',
     is_antonym_pair('Reward Magnitude', 'Reward Size'), False)

test('amygdala activity vs hippocampal volume (unrelated, zero word overlap)',
     is_antonym_pair('Amygdala Activity', 'Hippocampal Volume'), False)

test('aligned rewards vs agnostic reward (plural-mismatch case, requires normalization fix)',
     is_antonym_pair('Aligned Rewards', 'Agnostic Reward'), True)

test('mixed case is antonym-insensitive',
     is_antonym_pair('HIGH Anxiety', 'low ANXIETY'), True)

test('multi-word diff is never flagged even if one differing word is an antonym',
     is_antonym_pair('Positive Valence Signal', 'Negative Affect Cue'), False)

test('identical labels are not an antonym pair',
     is_antonym_pair('Reward Rate', 'Reward Rate'), False)

test('order-independent (frozenset-based comparison)',
     is_antonym_pair('Low Anxiety', 'High Anxiety'), True)

print('_normalize_word')

test('short word (len<=4) left unchanged even if it ends in s',
     _normalize_word('bias'), 'bias')

test('ss-ending word left unchanged',
     _normalize_word('class'), 'class')

test('plural word above length threshold gets singularized',
     _normalize_word('rewards'), 'reward')

test('non-plural word left unchanged',
     _normalize_word('aligned'), 'aligned')

print('clean_label')

test('newline replaced with space',
     clean_label('Goal-Aligned\nReward'), 'Goal-Aligned Reward')

test('multiple whitespace collapsed and trimmed',
     clean_label('  Extra   Spaces  \n Here '), 'Extra Spaces Here')

print(f'\n{"All tests passed." if failures == 0 else f"{failures} test(s) failed."}')
sys.exit(0 if failures == 0 else 1)
```

- [ ] **Step 2: Run the test suite and verify all 15 cases pass**

```bash
cd graph/tool
python3 dedupe_lifted_semantic.test.py
```

Expected: 15 lines each starting with a checkmark (9 under `is_antonym_pair`, 4 under `_normalize_word`, 2 under `clean_label`), ending with `All tests passed.` and exit code 0 (`echo $?` after the run should print `0`).

- [ ] **Step 3: Verify a genuine failure is caught (sanity-check the harness itself)**

```bash
cd graph/tool
sed -i.bak "s/_normalize_word('bias'), 'bias')/_normalize_word('bias'), 'WRONG')/" dedupe_lifted_semantic.test.py
python3 dedupe_lifted_semantic.test.py; echo "exit code: $?"
mv dedupe_lifted_semantic.test.py.bak dedupe_lifted_semantic.test.py
python3 dedupe_lifted_semantic.test.py; echo "exit code: $?"
```

Expected: first run shows one failing case under `_normalize_word` with an assertion message and `exit code: 1`; second run (after revert) shows all cases passing with `exit code: 0`. Confirm `git diff graph/tool/dedupe_lifted_semantic.test.py` is empty after the revert.

- [ ] **Step 4: Commit**

```bash
git add graph/tool/dedupe_lifted_semantic.test.py
git commit -m "graph: add plain-assert test suite for dedupe_lifted_semantic.py's antonym-guard and label-cleaning functions"
```

---

## Post-plan state

After both tasks: the four hand-verified-during-review pure functions in `lift_concepts.js` (`validateReuse`, `validateCluster`, `dedupeSiblingNodes`, `buildUserPrompt`) plus `computePaperWeight` from `lib.js`, and the three pure functions in `dedupe_lifted_semantic.py` (`is_antonym_pair`, `_normalize_word`, `clean_label`) all have a fast, repeatable, dependency-free regression check — `node graph/tool/lift_concepts.test.js` (well under a second, no API calls) and `python3 graph/tool/dedupe_lifted_semantic.test.py` (a few seconds, not model-loading-slow but not instant either — importing `dedupe_lifted_semantic.py` for its three pure functions still triggers that file's own top-level `from sentence_transformers import SentenceTransformer`/`import numpy as np`, which costs real cold-start time even though `SentenceTransformer(...)` is never instantiated; the Python test file is dependency-free in its *own* logic but transitively requires `sentence_transformers`+`numpy` to be installed, same as the rest of `graph/tool/`). Explicitly not covered (by design, matching the project's existing smoke-run convention for anything requiring real I/O): `liftPaper()`/`main()` in `lift_concepts.js` (Anthropic API), `dedupe_paper()`'s embedding-scoring path and `main()` in `dedupe_lifted_semantic.py` (sentence-transformers model), `loadCorpusUniverse()` and `mergeIntoGraph()`/`rebuildLayout()` in `lib.js` (real file I/O; the latter two predate this session's work).
