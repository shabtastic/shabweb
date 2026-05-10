#!/usr/bin/env node
/**
 * classify-levels.js — One-shot pass to add a `level` field to every node
 * in graph/graph.json.
 *
 * Levels:
 *   theory     — frameworks / computational models / paradigms
 *   construct  — mid-level psychological / cognitive concepts (default)
 *   method     — research methods, instruments, paradigms
 *   mechanism  — brain regions, neurochemicals, neural circuits
 *   domain     — application areas (driving, consumer choice, etc.)
 *
 * Idempotent: only classifies nodes that don't already have a `level`.
 *
 * Usage:
 *   node graph/tool/classify-levels.js          # classify missing levels
 *   node graph/tool/classify-levels.js --all    # reclassify everything
 *
 * Requires ANTHROPIC_API_KEY in graph/tool/.env (already set up).
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import Anthropic from '@anthropic-ai/sdk';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });
const GRAPH_PATH = path.join(__dirname, '..', 'graph.json');

const VALID_LEVELS = new Set(['theory', 'construct', 'method', 'mechanism', 'domain']);

const SYSTEM_PROMPT = `You are classifying concept nodes in a research knowledge graph by abstraction level.

LEVELS:
- theory     : theoretical frameworks, computational models, mathematical/algorithmic constructs
              examples: "predictive processing", "Bayesian surprise", "reinforcement learning",
              "spreading activation", "information prediction error"
- construct  : mid-level psychological or cognitive concepts that span theory and mechanism
              examples: "risk perception", "creativity", "psychological flexibility",
              "temporal discounting", "social choice", "valence bias"
- method     : research methods, instruments, paradigms, measurement approaches
              examples: "fMRI", "driving simulator", "go/no-go task", "EEG",
              "structural equation modeling"
- mechanism  : neural / biological substrates — brain regions, neurochemicals, circuits, anatomy
              examples: "amygdala", "vasopressin", "dopamine", "subgenual cingulate",
              "prefrontal cortex"
- domain     : application areas, populations, real-world contexts
              examples: "adolescent development", "consumer choice", "driver behavior",
              "advanced driver assistance"

Output ONLY valid JSON: an array of {"id": string, "level": string} pairs.
Use exactly one of: theory | construct | method | mechanism | domain.
When ambiguous between theory and construct, prefer "construct" — it's the
default level for mid-grain psychological concepts.
When ambiguous between method and mechanism for tools that index brain activity
(fMRI, EEG, fNIRS, MEG), classify as "method".`;

function buildUserPrompt(nodes) {
  const lines = nodes.map(n => `${n.id}\t${(n.label || '').replace(/\n/g, ' ')}`);
  return `Classify each of these ${nodes.length} concept nodes. Return JSON only.

id\tlabel
${lines.join('\n')}`;
}

async function classifyAll(nodes) {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const response = await client.messages.create({
    model: 'claude-opus-4-7',
    max_tokens: 16000,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: buildUserPrompt(nodes) }],
  });

  const text = response.content.map(b => b.text || '').join('');
  const clean = text.replace(/```json|```/g, '').trim();
  const parsed = JSON.parse(clean);

  const byId = {};
  for (const item of parsed) {
    if (item && item.id && VALID_LEVELS.has(item.level)) {
      byId[item.id] = item.level;
    }
  }
  return byId;
}

async function main() {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('Missing ANTHROPIC_API_KEY (check graph/tool/.env)');
    process.exit(1);
  }
  if (!fs.existsSync(GRAPH_PATH)) {
    console.error(`Missing ${GRAPH_PATH}`);
    process.exit(1);
  }

  const graph = JSON.parse(fs.readFileSync(GRAPH_PATH, 'utf-8'));
  const reclassifyAll = process.argv.includes('--all');
  const targets = reclassifyAll
    ? graph.nodes
    : graph.nodes.filter(n => !n.level || !VALID_LEVELS.has(n.level));

  if (targets.length === 0) {
    console.log('All nodes already have a valid level. Use --all to reclassify.');
    return;
  }

  console.log(`Classifying ${targets.length} of ${graph.nodes.length} nodes via claude-opus-4-7…`);

  const labels = await classifyAll(targets);

  let assigned = 0, missing = 0;
  for (const node of graph.nodes) {
    const label = labels[node.id];
    if (label) {
      node.level = label;
      assigned++;
    } else if (!node.level) {
      // Fallback so the field is always present
      node.level = 'construct';
      missing++;
    }
  }

  // Tally
  const tally = {};
  for (const n of graph.nodes) tally[n.level] = (tally[n.level] || 0) + 1;

  fs.writeFileSync(GRAPH_PATH, JSON.stringify(graph, null, 2) + '\n', 'utf-8');
  console.log(`Wrote ${GRAPH_PATH}`);
  console.log(`  assigned by model: ${assigned}`);
  if (missing) console.log(`  defaulted to "construct" (model didn't return them): ${missing}`);
  console.log('  Final tally:');
  for (const [k, v] of Object.entries(tally).sort((a, b) => b[1] - a[1])) {
    console.log(`    ${k.padEnd(10)} ${v}`);
  }
  console.log('Next: re-run `node data/inline-graph.js` to sync HTML pages.');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
