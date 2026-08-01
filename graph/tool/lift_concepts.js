#!/usr/bin/env node
/**
 * lift_concepts.js — The one LLM step in the v4 full-text pipeline. Takes
 * each paper's already-scored candidate pool (candidate_generation.py +
 * dedup_candidates.py + classify_candidates.py) and asks Claude to select,
 * merge, and lift them into graph-ready concepts — narrow scope compared to
 * the old extractConcepts() in lib.js, which read raw text and did everything
 * in one shot.
 *
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

import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import Anthropic from '@anthropic-ai/sdk';
import { c, loadGraph, computePaperWeight } from './lib.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CANDIDATES_PATH = path.join(__dirname, '..', 'candidates.json');
const PUBS_PATH = path.join(__dirname, '..', '..', 'data', 'publications.json');
const OUTPUT_PATH = path.join(__dirname, '..', 'lift-output.json');
const SUMMARY_PATH = path.join(__dirname, '..', 'lift-run-summary.json');
const AUDIT_PATH = path.join(__dirname, '..', 'lift-audit.json');

const TOP_CANDIDATES_PER_PAPER = 15;

const SYSTEM_PROMPT = `You are refining candidate concepts for a cognitive neuroscientist working across multiple
disciplines — behavioral science, design, generative AI, and consumer psychology, in addition
to neuroscience. Evaluate each paper on its own terms; a design contribution or a behavioral-
economics finding has equal scientific standing here to a neural mechanism.

You are given a paper's metadata and a list of candidate phrases already extracted from its full
text and pre-scored against the existing graph (frequency, nearest existing node + similarity,
predicted cluster + confidence, predicted abstraction level + confidence).

Your job is narrow: decide what to keep, what to merge, and what to lift — not to invent from
scratch.

For each candidate, or group of clearly-related candidates (e.g. "reward rate", "reward-rate",
"reward rate ratio" are variants of one construct — merge them), decide:

1. REUSE — only when similarity to nearest_existing is at least ~0.6 AND it's genuinely the
   same underlying construct, not just topically adjacent. Two things "about the same population"
   or "about the same broad topic" (e.g. both mention autism, both mention reward) are NOT
   automatically the same concept — check what nearest_existing's own label actually claims
   before reusing it. A low similarity score (below ~0.55) is real evidence against reuse; don't
   override it just because the phrase sounds related. When genuinely unsure, prefer creating a
   new node over a wrong merge — a bad reuse corrupts an existing concept's meaning, a missed
   reuse just costs one extra node.
2. LIFT — if the phrase is too paper-specific (a stimulus, task name, or raw variable) but
   represents a real generalizable concept, output the general form instead of the literal
   phrase. Prefer terms implied by the candidate pool; only introduce a term absent from every
   candidate when the paper's actual contribution clearly isn't captured by any surviving
   candidate — this should be rare, not your default.
3. SKIP — sentence fragments, author names, generic single words with no independent scientific
   standing, or study-specific artifacts with no meaningful generalization.

CLUSTER AND LEVEL: predicted_cluster/predicted_level are statistical priors from candidate-phrase
similarity alone — they don't see the paper's actual topic. When confidence is low (below ~0.5),
they're often wrong for genuinely ambiguous words (e.g. "reward" alone matches both behavioral-
choice and RL-reward-shaping papers) — use the paper's title/venue to resolve these, don't just
trust the number. When confidence is high, trust it unless the paper context clearly contradicts it.

QUANTITY: 3-8 concepts per paper; prefer fewer, more central ones over exhaustively covering
every surviving candidate.

Return ONLY valid JSON, no markdown fences:
{
  "nodes": [{
    "id": "snake_case_max_3_words",
    "label": "display\\nlabel",
    "reuse_existing": "existing_node_id or null",
    "source_candidates": ["phrase1", "phrase2"],
    "weight": 0.0-1.0,
    "cluster": 0-7,
    "level": "theory"|"construct"|"method"|"mechanism"|"domain"
  }],
  "edges": [{"a": "node_id", "b": "node_id", "strength": 0.0-1.0}]
}`;

export function buildUserPrompt(pub, candidates) {
  const trimmed = candidates.slice(0, TOP_CANDIDATES_PER_PAPER).map(x => ({
    phrase: x.phrase,
    freq: x.freq,
    nearest_existing: x.nearest_existing.id,
    similarity: x.nearest_existing.similarity,
    predicted_cluster: x.predicted_cluster.name,
    cluster_confidence: x.predicted_cluster.confidence,
    predicted_level: x.predicted_level.value,
    level_confidence: x.predicted_level.confidence,
  }));

  const payload = {
    paper: { title: pub.title, venue: pub.venue, year: pub.year },
    candidates: trimmed,
  };

  return `${JSON.stringify(payload, null, 2)}\n\nRespond with the JSON object only. Do not add any text before or after it.`;
}

async function liftPaper(client, pub, candidates, model) {
  const response = await client.messages.create({
    model,
    max_tokens: 1500,
    temperature: 0,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: buildUserPrompt(pub, candidates) }],
  });
  const raw = response.content.map(b => b.text || '').join('');
  const clean = raw.replace(/```json|```/g, '').trim();
  return JSON.parse(clean);
}

// Sometimes the model splits one repeated candidate phrase into several
// nearly-identical new nodes instead of one (seen in practice: a single
// dominant "crime-type bias" candidate group split into 4 overlapping
// nodes). Literal source_candidate overlap catches this without needing
// embeddings — nodes sharing a source phrase within the same paper are
// describing the same underlying finding, not distinct concepts. Union-find
// over overlap, keep the node with the most source candidates per group.
export function dedupeSiblingNodes(lifted, audit, paperId) {
  const nodes = lifted.nodes || [];
  const newNodes = nodes.filter(n => !n.reuse_existing || n.reuse_existing === 'null');
  if (newNodes.length < 2) return lifted;

  const parent = new Map(newNodes.map(n => [n.id, n.id]));
  function find(x) { while (parent.get(x) !== x) x = parent.get(x); return x; }
  function union(a, b) { const ra = find(a), rb = find(b); if (ra !== rb) parent.set(ra, rb); }

  for (let i = 0; i < newNodes.length; i++) {
    for (let j = i + 1; j < newNodes.length; j++) {
      const a = new Set(newNodes[i].source_candidates || []);
      const overlaps = (newNodes[j].source_candidates || []).some(p => a.has(p));
      if (overlaps) union(newNodes[i].id, newNodes[j].id);
    }
  }

  const groups = new Map();
  for (const n of newNodes) {
    const root = find(n.id);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(n);
  }

  const idRemap = new Map();
  const survivors = [];
  for (const group of groups.values()) {
    if (group.length === 1) { survivors.push(group[0]); continue; }
    group.sort((a, b) => (b.source_candidates?.length || 0) - (a.source_candidates?.length || 0));
    const keep = group[0];
    const merged = new Set(keep.source_candidates || []);
    for (const dupe of group.slice(1)) {
      const detail = `merged sibling node "${dupe.id}" into "${keep.id}" — shared source candidates`;
      c.warn(`    ✗ ${detail}`);
      audit.push({ paper_id: paperId, action: 'sibling_merged', node_id: dupe.id, detail });
      (dupe.source_candidates || []).forEach(p => merged.add(p));
      idRemap.set(dupe.id, keep.id);
    }
    keep.source_candidates = [...merged];
    survivors.push(keep);
  }

  const reuseNodes = nodes.filter(n => n.reuse_existing && n.reuse_existing !== 'null');
  lifted.nodes = [...survivors, ...reuseNodes];
  lifted.edges = (lifted.edges || [])
    .map(e => ({ ...e, a: idRemap.get(e.a) || e.a, b: idRemap.get(e.b) || e.b }))
    .filter(e => e.a !== e.b);
  return lifted;
}

const REUSE_MIN_SIMILARITY = 0.6;
const CLUSTER_TRUST_THRESHOLD = 0.5;

// Same principle as validateReuse: when the classical cluster predictor was
// already confident, don't let the model quietly override it. Confirmed in
// practice — Sukumar2017overcoming's ambiguous "reward" correctly got
// reassigned from a low-confidence (~0.4) wrong prediction, but
// Castrellon2022social's "crime-type bias" got moved OFF a correct
// higher-confidence (0.5-0.75) prediction onto an unrelated cluster. Only
// let paper-context override low-confidence classical predictions.
export function validateCluster(lifted, candidatesByPhrase, audit, paperId) {
  for (const n of lifted.nodes || []) {
    const preds = (n.source_candidates || [])
      .map(p => candidatesByPhrase.get(p)?.predicted_cluster)
      .filter(Boolean);
    if (!preds.length) continue;
    const best = preds.reduce((a, b) => (b.confidence > a.confidence ? b : a));
    if (best.confidence >= CLUSTER_TRUST_THRESHOLD && best.id !== n.cluster) {
      const detail = `overrode cluster ${n.cluster} -> ${best.id} (${best.name}) — classical prediction was confident (${best.confidence})`;
      c.warn(`    ✗ ${detail}`);
      audit.push({ paper_id: paperId, action: 'cluster_overridden', node_id: n.id, detail, confidence: best.confidence, threshold: CLUSTER_TRUST_THRESHOLD });
      n.cluster = best.id;
    }
  }
  return lifted;
}

// Don't trust the model's own reuse_existing claim — verify it against the
// real dedup similarity scores. A prompt instruction is a request the model
// can still override on topical pattern-matching (seen in practice: merging
// distinct constructs that just share a surface topic); this is a hard
// check instead of another sentence of persuasion.
export function validateReuse(lifted, candidatesByPhrase, audit, paperId) {
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

async function main() {
  const args = process.argv.slice(2);
  const limitArg = args.find((a, i) => args[i - 1] === '--limit');
  const papersArg = args.find((a, i) => args[i - 1] === '--papers');
  const limit = limitArg ? parseInt(limitArg, 10) : null;
  const onlyPapers = papersArg ? papersArg.split(',') : null;

  if (!process.env.ANTHROPIC_API_KEY) {
    c.err('ANTHROPIC_API_KEY not set.');
    process.exit(1);
  }

  const candidatesByPaper = JSON.parse(fs.readFileSync(CANDIDATES_PATH, 'utf-8'));
  const publications = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
  const pubIndex = Object.fromEntries(publications.map(p => [p.id, p]));
  const graph = loadGraph();
  const existingIds = new Set(graph.nodes.map(n => n.id));

  let paperIds = Object.keys(candidatesByPaper).filter(id => candidatesByPaper[id]?.length);
  if (onlyPapers) paperIds = paperIds.filter(id => onlyPapers.includes(id));
  if (limit) paperIds = paperIds.slice(0, limit);

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = 'claude-sonnet-4-6';

  // Load existing output so incremental --papers batches accumulate instead
  // of clobbering prior runs' results — downstream steps (widening test
  // coverage, promote_lift_output.js) depend on this file being cumulative
  // across multiple invocations, not a snapshot of only the latest one.
  let results = {};
  if (fs.existsSync(OUTPUT_PATH)) {
    try { results = JSON.parse(fs.readFileSync(OUTPUT_PATH, 'utf-8')); }
    catch { c.warn('lift-output.json unreadable, starting fresh — prior results discarded'); }
  }

  let audit = [];
  if (fs.existsSync(AUDIT_PATH)) {
    try { audit = JSON.parse(fs.readFileSync(AUDIT_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }

  const allWeights = [];
  const allStrengths = [];

  for (let i = 0; i < paperIds.length; i++) {
    const id = paperIds[i];
    const pub = pubIndex[id];
    c.head(`\n[${i + 1}/${paperIds.length}] ${id}`);
    audit = audit.filter(a => a.paper_id !== id);
    try {
      const lifted = await liftPaper(client, pub, candidatesByPaper[id], model);

      const candidatesByPhrase = new Map(candidatesByPaper[id].map(c => [c.phrase, c]));
      validateReuse(lifted, candidatesByPhrase, audit, id);
      validateCluster(lifted, candidatesByPhrase, audit, id);
      dedupeSiblingNodes(lifted, audit, id);

      // Normalize reuse_existing → the node's real id, so downstream merge
      // logic (mergeIntoGraph's existing-id dedup) treats it as a boost,
      // not a new node with an invented placeholder id. Edges reference the
      // model's original invented id, so remap those too or they dangle.
      const idRemap = new Map();
      for (const n of lifted.nodes || []) {
        if (n.reuse_existing && n.reuse_existing !== 'null' && n.reuse_existing !== n.id) {
          idRemap.set(n.id, n.reuse_existing);
          n.id = n.reuse_existing;
        }
      }
      for (const e of lifted.edges || []) {
        if (idRemap.has(e.a)) e.a = idRemap.get(e.a);
        if (idRemap.has(e.b)) e.b = idRemap.get(e.b);
      }

      const isSelected = (pub.keywords || []).includes('selected');
      const paperWeight = isSelected ? 1.0 : computePaperWeight(pub);
      for (const n of lifted.nodes || []) {
        n.weight = Math.round(Math.max(0.1, Math.min(1.0, n.weight * paperWeight)) * 100) / 100;
      }
      lifted.paperWeight = paperWeight;

      for (const e of lifted.edges || []) {
        e.strength = Math.round(Math.max(0.1, Math.min(1.0, e.strength)) * 100) / 100;
      }

      (lifted.nodes || []).forEach(n => allWeights.push(n.weight));
      (lifted.edges || []).forEach(e => allStrengths.push(e.strength));

      const newCount = (lifted.nodes || []).filter(n => !existingIds.has(n.id)).length;
      const reuseCount = (lifted.nodes || []).length - newCount;
      c.ok(`  ${lifted.nodes?.length || 0} nodes (${newCount} new, ${reuseCount} reuse), ${lifted.edges?.length || 0} edges`);
      (lifted.nodes || []).forEach(n => c.dim(`    ${existingIds.has(n.id) ? '~' : '+'} ${n.id}  [${n.source_candidates?.join(', ')}]`));

      results[id] = lifted;
    } catch (e) {
      c.err(`  FAILED: ${e.message}`);
      results[id] = { error: e.message };
    }
    if (i < paperIds.length - 1) await new Promise(r => setTimeout(r, 1500));
  }

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
  fs.writeFileSync(AUDIT_PATH, JSON.stringify(audit, null, 2));
  c.log(`Wrote ${AUDIT_PATH} — ${audit.length} correction(s) accumulated across all runs, for spot-checking over- and under-aggressiveness`);
  c.warn('Nothing merged into graph.json — run dedupe_lifted_semantic.py next, then the review step.');
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) main();
