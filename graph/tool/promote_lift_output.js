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
