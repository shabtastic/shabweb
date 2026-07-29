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
