#!/usr/bin/env node
/**
 * inline-graph.js — Re-inline graph/graph.json into the HTML pages.
 *
 * graph.json is the canonical source. index.html and graph.html each contain
 * a `<script type="application/json" id="graph-data">…</script>` block whose
 * body must be kept in sync with graph.json.
 *
 * Run after any change to graph.json (e.g., `node graph/tool/index.js add`,
 * `node data/sync-bib.js`).
 *
 *   node data/inline-graph.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const GRAPH_JSON = path.join(ROOT, 'graph', 'graph.json');

// index.html only consumes nodes/edges/layout for the hero contour animation;
// it never reads meta.papers or meta.clusters. graph.html consumes both
// (cluster overlay + paper list). Stripping meta from index.html keeps bib
// metadata out of the landing page source.
const TARGETS = [
  { file: path.join(ROOT, 'index.html'),  fields: ['version', 'nodes', 'edges', 'layout'] },
  { file: path.join(ROOT, 'graph.html'),  fields: null /* full payload */ },
];
const OPEN_TAG  = '<script type="application/json" id="graph-data">';
const CLOSE_TAG = '</script>';

function inlineInto(file, payload) {
  const src = fs.readFileSync(file, 'utf-8');
  const start = src.indexOf(OPEN_TAG);
  if (start === -1) return { file, status: 'no-marker' };
  const afterOpen = start + OPEN_TAG.length;
  const end = src.indexOf(CLOSE_TAG, afterOpen);
  if (end === -1) return { file, status: 'no-close' };
  const next = src.slice(0, afterOpen) + '\n' + payload + '\n' + src.slice(end);
  if (next === src) return { file, status: 'unchanged' };
  fs.writeFileSync(file, next, 'utf-8');
  return { file, status: 'updated' };
}

function projectPayload(graph, fields) {
  if (!fields) return graph;
  const out = {};
  for (const k of fields) if (k in graph) out[k] = graph[k];
  return out;
}

function main() {
  if (!fs.existsSync(GRAPH_JSON)) {
    console.error(`Missing ${GRAPH_JSON}`);
    process.exit(1);
  }
  const graph = JSON.parse(fs.readFileSync(GRAPH_JSON, 'utf-8'));

  for (const { file, fields } of TARGETS) {
    const projected = projectPayload(graph, fields);
    const raw = JSON.stringify(projected, null, 2);
    // Defensive: keep any future stray "</script>" inside a JSON string from
    // ending the inline block early. (Currently no such strings exist.)
    const safe = raw.replace(/<\/script>/gi, '<\\/script>');
    const r = inlineInto(file, safe);
    const name = path.relative(ROOT, r.file);
    const note = fields ? ` (${fields.join(', ')})` : '';
    if (r.status === 'updated') {
      console.log(`updated  ${name}${note}`);
    } else if (r.status === 'unchanged') {
      console.log(`ok       ${name}${note} (already in sync)`);
    } else {
      console.warn(`skipped  ${name} — ${r.status}`);
    }
  }
}

main();
