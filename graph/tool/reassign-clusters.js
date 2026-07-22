#!/usr/bin/env node
/**
 * reassign-clusters.js — One-shot rename of graph.json's 7 clusters and
 * reassignment of every node's `cluster` field to match, per the paper-level
 * mapping in docs/superpowers/specs/2026-07-22-graph-cluster-rename-design.md.
 *
 * Nodes are voted into their new cluster by the papers that contributed
 * them (graph.json meta.papers[].nodes_contributed), weighted by each
 * paper's paperWeight. Nodes with no contributing paper (orphans) keep
 * their existing cluster id and are printed for manual review — as of
 * 2026-07-22 there are 7 such nodes, all Creativity & Design concepts
 * under-attributed to Nath2026designrewards; see the spec for the planned
 * manual fix-up (Task 2 of this plan).
 *
 * Usage:
 *   node graph/tool/reassign-clusters.js
 */

import { loadGraph, saveGraph, c } from './lib.js';

const NEW_CLUSTERS = [
  { id: 0, name: 'Motivated Learning, Decision Making, & Self Regulation' },
  { id: 1, name: 'Creativity & Design' },
  { id: 2, name: 'Psychology-Guided Generative AI' },
  { id: 3, name: 'Intervention Science & Applied Behavior Change' },
  { id: 4, name: 'Preference Elicitation & Prediction' },
  { id: 5, name: 'Social, Cognitive, & Affective Neuroscience' },
  { id: 6, name: 'Consumer Psychology & Market Forecasting' },
];

// Paper id -> new cluster id, per the approved design spec. All 48 papers
// currently in graph.json meta.papers must appear here exactly once.
const PAPER_CLUSTER = {
  // 0. Motivated Learning, Decision Making, & Self Regulation
  Hakimi2015enhanced: 0, Hakimi2014activity: 0, Hsiung2022heuristics: 0,
  Wright2024motivation: 0, Botvinik2020variability: 0, Hsiung2018curiosity: 0,
  // 1. Creativity & Design
  Nandy2024semantic: 1, Hakimi2025semantic: 1, Nath2026designrewards: 1,
  Klenk2023anticipatory: 1, Klenk2026cats: 1, Paredes2024commuter: 1,
  Hong2024unstuck: 1, kim2026personagrambridgingpersonasproduct: 1,
  // 2. Psychology-Guided Generative AI
  Hakimi2025creativity: 2, Hong2023genai: 2, chong2026wowaidesign: 2,
  zhang2026surpriseaidesign: 2,
  // 3. Intervention Science & Applied Behavior Change
  Sinclair2021imagining: 3, Hakimi2021pairing: 3, Hakimi2020behavioral: 3,
  Harinen2022ml: 3, Sinclair2024pausing: 3, paredes2026unstuck: 3,
  Sukumar2017overcoming: 3,
  // 4. Preference Elicitation & Prediction
  Hakimi2023ml: 4, Hakimi2024cognitive: 4, Zhang2022conjointnet: 4,
  Chen2025learning: 4, hong2026deconstructingtastehumancenteredai: 4,
  Sumner2024personalizing: 4, DeCastro2022latent: 4, Gopinath2022hmiway: 4,
  Filipowicz2023visual: 4,
  // 5. Social, Cognitive, & Affective Neuroscience
  Goldin2009neural: 5, Tost2009mri: 5, Tost2009dopamine: 5, Tost2010oxtr: 5,
  Tost2010acute: 5, Zink2010vasopressin: 5, Zink2011vasopressin: 5,
  Wang2016autism: 5, Mosner2019neural: 5, Castrellon2022social: 5,
  Castrellon2022neural: 5,
  // 6. Consumer Psychology & Market Forecasting
  Knutson2024brain: 6, Eum2025aidriven: 6, Filipowicz2022familiarity: 6,
};

function main() {
  const graph = loadGraph();

  const paperIds = new Set(graph.meta.papers.map(p => p.id));
  const mappedIds = new Set(Object.keys(PAPER_CLUSTER));
  const missing = [...paperIds].filter(id => !mappedIds.has(id));
  const extra = [...mappedIds].filter(id => !paperIds.has(id));
  if (missing.length) throw new Error(`Papers in graph.json with no cluster mapping: ${missing.join(', ')}`);
  if (extra.length) throw new Error(`PAPER_CLUSTER has ids not in graph.json: ${extra.join(', ')}`);

  // Reverse index: node id -> Map<clusterId, summedWeight>
  const votes = new Map();
  for (const paper of graph.meta.papers) {
    const cluster = PAPER_CLUSTER[paper.id];
    const weight = paper.paperWeight ?? 1.0;
    for (const nodeId of paper.nodes_contributed || []) {
      if (!votes.has(nodeId)) votes.set(nodeId, new Map());
      const clusterVotes = votes.get(nodeId);
      clusterVotes.set(cluster, (clusterVotes.get(cluster) || 0) + weight);
    }
  }

  const orphans = [];
  const ties = [];
  const countsBefore = new Array(7).fill(0);
  const countsAfter = new Array(7).fill(0);

  for (const node of graph.nodes) {
    if (node.cluster >= 0 && node.cluster < 7) countsBefore[node.cluster]++;

    const clusterVotes = votes.get(node.id);
    if (!clusterVotes || clusterVotes.size === 0) {
      orphans.push(node.id);
      if (node.cluster >= 0 && node.cluster < 7) countsAfter[node.cluster]++;
      continue;
    }

    let winner = null, winnerWeight = -1, top = [];
    for (const [cluster, weight] of clusterVotes) {
      if (weight > winnerWeight) { winner = cluster; winnerWeight = weight; top = [cluster]; }
      else if (weight === winnerWeight) { top.push(cluster); }
    }
    if (top.length > 1) {
      winner = Math.min(...top);
      ties.push({ node: node.id, candidates: top, chose: winner });
    }
    node.cluster = winner;
    countsAfter[winner]++;
  }

  graph.meta.clusters = NEW_CLUSTERS;
  saveGraph(graph);

  c.head('Cluster reassignment complete');
  c.log('');
  c.log('Node count per cluster (before → after):');
  for (let i = 0; i < 7; i++) {
    c.log(`  ${i}  ${NEW_CLUSTERS[i].name}: ${countsBefore[i]} → ${countsAfter[i]}`);
  }
  c.log('');
  if (orphans.length) {
    c.warn(`${orphans.length} orphan node(s) with no contributing paper — cluster left unchanged:`);
    orphans.forEach(id => c.log(`  - ${id}`));
  }
  if (ties.length) {
    c.warn(`${ties.length} tie(s) broken by lowest cluster id:`);
    ties.forEach(t => c.log(`  - ${t.node}: candidates [${t.candidates.join(',')}] → chose ${t.chose}`));
  } else {
    c.ok('No ties.');
  }
  c.ok('Wrote graph/graph.json');
}

main();
