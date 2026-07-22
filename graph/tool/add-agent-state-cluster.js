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
