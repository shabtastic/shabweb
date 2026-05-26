#!/usr/bin/env node
/**
 * review-draft-proposals.js — Review draft-extracted nodes before merging into graph.json.
 *
 * Reads graph/draft-proposals.json (gitignored). For each unreviewed proposal:
 *   [a]pprove → merges nodes/edges into graph.json
 *   [r]eject  → marks reviewed, not added to graph
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

  try {
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
          abstractOnly:     proposal.extraction_source === 'title-abstract',
          pubType:          pub.pubType,
          authorPosition:   pub.authorPosition,
          extraction_source: proposal.extraction_source,
        };
        const extractedShape = { nodes: proposal.nodes, edges: proposal.edges, paper: proposal.paper_meta };
        const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, extractedShape, meta, proposal.paper_weight);
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

      // Persist proposals file after each decision (safe resumption if interrupted)
      fs.writeFileSync(PROPOSALS_PATH, JSON.stringify(proposals, null, 2));
    }
  } finally {
    rl.close();
  }

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
