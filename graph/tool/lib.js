// graph/tool/lib.js
import fs   from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Anthropic from '@anthropic-ai/sdk';

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
export const GRAPH_PATH = path.join(__dirname, '..', 'graph.json');

// ── Console helpers ───────────────────────────────────────────────────────────
export const c = {
  info:  s => process.stdout.write(`\x1b[36m→\x1b[0m  ${s}\n`),
  ok:    s => process.stdout.write(`\x1b[32m✓\x1b[0m  ${s}\n`),
  warn:  s => process.stdout.write(`\x1b[33m⚠\x1b[0m  ${s}\n`),
  err:   s => process.stdout.write(`\x1b[31m✗\x1b[0m  ${s}\n`),
  head:  s => process.stdout.write(`\x1b[1m${s}\x1b[0m\n`),
  dim:   s => process.stdout.write(`\x1b[2m${s}\x1b[0m\n`),
  log:   s => process.stdout.write(`${s}\n`),
};

// ── Graph I/O ─────────────────────────────────────────────────────────────────
export function loadGraph() {
  if (!fs.existsSync(GRAPH_PATH)) throw new Error(`graph.json not found at ${GRAPH_PATH}`);
  return JSON.parse(fs.readFileSync(GRAPH_PATH, 'utf8'));
}

export function saveGraph(graph) {
  fs.writeFileSync(GRAPH_PATH, JSON.stringify(graph, null, 2));
}

// ── Paper weighting ───────────────────────────────────────────────────────────
export function computePaperWeight(meta) {
  const typeWeights = {
    'journal':       1.00,
    'conf-full':     0.85,
    'conf-workshop': 0.65,
    'preprint':      0.70,
    'science-comm':  0.30,
    'other':         0.40,
  };
  const typeW = typeWeights[meta.pubType] ?? 0.50;

  const posWeights = {
    'first':        1.0,
    'shared-first': 1.0,
    'last':         0.8,
    'second':       0.6,
    'middle':       0.4,
  };
  const posW = posWeights[meta.authorPosition] ?? 0.5;

  const year = parseInt(meta.year) || 2000;
  const recencyW = year >= 2020 ? 1.0 : year >= 2015 ? 0.8 : 0.6;

  return Math.round(typeW * posW * recencyW * 100) / 100;
}

// ── Claude concept extraction ─────────────────────────────────────────────────
export async function extractConcepts(text, graph, paperWeight = 1.0, model = 'claude-sonnet-4-6') {
  const client      = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const existingIds = graph.nodes.map(n => n.id);
  const clusterGuide = graph.meta.clusters.map(cl => `${cl.id}=${cl.name}`).join(', ');
  const maxClusterId = Math.max(...graph.meta.clusters.map(cl => cl.id));

  c.info(`Sending to Claude for concept extraction (model: ${model}, paperWeight: ${paperWeight})…`);

  const response = await client.messages.create({
    model,
    max_tokens: 2000,
    system: `You are a research knowledge-graph builder for a cognitive neuroscientist's published work. Extract concepts that represent durable scientific knowledge — constructs, theories, and mechanisms that appear in the Introduction and Discussion of review articles in this research area.

EXISTING NODE IDs — reuse wherever semantically appropriate.
Do NOT create a new node if an existing one covers the same concept, even if the wording differs.
Examples of what NOT to do: adding "risk_perception" when "perceived_risk" exists; adding "belief_updating" when "belief_revision" exists; adding "episodic_simulation" when "episodic_sim" exists.
When in doubt, REUSE the existing node and add edges to/from it instead.

${existingIds.join(', ')}

Cluster guide: ${clusterGuide}
Use cluster 0 as default for anything that doesn't fit neatly.

PAPER WEIGHT: ${paperWeight} (scale 0–1, reflecting publication type, author position, and recency)
This paper's importance to the researcher's intellectual identity is ${paperWeight >= 0.8 ? 'high' : paperWeight >= 0.5 ? 'moderate' : 'lower'}.
Scale your raw node weight scores accordingly — a weight of 1.0 in a paperWeight=0.5 paper
should translate to a node weight of ~0.5 in the final graph.
So: final_node_weight = your_raw_score × ${paperWeight} (clamped to 0.1–1.0).

Return ONLY valid JSON, no markdown fences:
{
  "nodes": [{"id":"snake_case_max_3_words","label":"display\\nlabel","weight":0.0-1.0,"cluster":0-${maxClusterId},"level":"construct"}],
  "edges": [{"a":"node_id","b":"node_id","strength":0.0-1.0}],
  "paper": {"title":"...","year":2024,"venue":"...","doi":"..."}
}

EXTRACTION RULE: Extract what the study contributes, not how it was designed.

A node belongs in the graph only if it has independent scientific standing — it would appear in a review article's Introduction or Discussion written by a different lab, in a field ontology, or as a useful search term for learning about this research area.

Study artifacts — stimuli, IVs, DV operationalizations, domain context descriptors, study-specific task names — should almost never become nodes. For each one, first ask: is there a more general version with independent scientific standing? If yes, extract that instead. Skip only when no meaningful generalization exists.

Lifting examples (specific → general):
- Defendant race used as IV → decision_bias (specific IV → construct it operationalizes)
- Neurosynth decoding used in analysis → neural_decoding (specific tool → general method)
- Design outcome differentiability (DV) → creative_divergence (DV label → established construct)
- Large infrequent purchase (domain framing) → choice_prediction (context → scientific contribution)
- OXTR genotype (specific variant) → imaging_genetics (variable → research approach)

Skip examples (no generalizable concept exists):
- Powertrain features shown to participants → skip (pure stimulus choice)
- Mock juror task → skip (extract legal_decision_making as the construct instead)

For methods: extract if the technique has cross-lab standing and is central to the paper's scientific argument (fMRI, conjoint analysis, drift-diffusion modeling, neural decoding). Skip tools that are incidental to the analysis.

LEVEL — assign exactly one:
"theory"     Frameworks/models spanning multiple findings. e.g. predictive processing, drift-diffusion model
"construct"  Scientific concepts generalizing across labs and studies. e.g. temporal discounting, cognitive flexibility, imaging genetics. NOT study-specific variables.
"method"     Cross-study instruments and analysis techniques. e.g. fMRI, conjoint analysis, eye tracking. NOT study-specific tasks.
"mechanism"  Biological substrates: brain regions, circuits, neurochemicals, genetic variants. e.g. amygdala, dopamine, oxytocin system
"domain"     Application areas or populations. e.g. adolescent development, consumer choice

QUANTITY: 5–12 new nodes maximum; prefer fewer, more central nodes. weight = raw centrality × paperWeight. strength = theoretical coupling tightness. label: lowercase, use \\n if > 12 chars. id: snake_case, max 3 words, unique.`,
    messages: [{ role: 'user', content: text.slice(0, 10000) + '\n\nRespond with the JSON object only. Do not add any text before or after it.' }],
  });

  const raw   = response.content.map(b => b.text || '').join('');
  const clean = raw.replace(/```json|```/g, '').trim();
  return JSON.parse(clean);
}

// ── Graph merge ───────────────────────────────────────────────────────────────
export function mergeIntoGraph(graph, extracted, meta, paperWeight = 1.0) {
  const existingIds = new Set(graph.nodes.map(n => n.id));
  let newNodes = 0, newEdges = 0, boostedNodes = 0;

  (extracted.nodes || []).forEach(n => {
    n.weight = Math.max(0.1, Math.min(1.0, n.weight));

    if (existingIds.has(n.id)) {
      const existing = graph.nodes.find(node => node.id === n.id);
      if (existing) {
        const boosted = Math.min(1.0, existing.weight * 0.67 + n.weight * 0.33);
        if (boosted > existing.weight + 0.01) {
          c.info(`  ↑ ${n.id}: ${existing.weight.toFixed(2)} → ${boosted.toFixed(2)}`);
          existing.weight = Math.round(boosted * 100) / 100;
          boostedNodes++;
        }
      }
      return;
    }

    graph.nodes.push(n);
    existingIds.add(n.id);
    newNodes++;
  });

  const edgeSet = new Set(graph.edges.map(e => `${e.a}|${e.b}`));
  (extracted.edges || []).forEach(e => {
    const key = `${e.a}|${e.b}`, rev = `${e.b}|${e.a}`;
    if (edgeSet.has(key) || edgeSet.has(rev)) {
      const existing = graph.edges.find(ex =>
        (ex.a === e.a && ex.b === e.b) || (ex.a === e.b && ex.b === e.a)
      );
      if (existing) {
        existing.strength = Math.min(1.0,
          Math.round((existing.strength * 0.7 + e.strength * 0.3) * 100) / 100
        );
      }
      return;
    }
    if (!existingIds.has(e.a)) { c.warn(`  Unknown node in edge: ${e.a}`); return; }
    if (!existingIds.has(e.b)) { c.warn(`  Unknown node in edge: ${e.b}`); return; }
    graph.edges.push(e);
    edgeSet.add(key);
    newEdges++;
  });

  const paper = extracted.paper || {};
  graph.meta.papers.push({
    id:               meta.id || `paper_${Date.now()}`,
    title:            paper.title      || meta.title   || 'Unknown',
    year:             paper.year       || meta.year,
    venue:            paper.venue      || meta.venue,
    doi:              paper.doi        || meta.doi,
    arxivId:          meta.arxivId,
    url:              meta.url,
    abstractOnly:     meta.abstractOnly || false,
    pubType:          meta.pubType,
    authorPosition:   meta.authorPosition,
    paperWeight,
    extraction_source: meta.extraction_source || 'title-abstract',
    added:            new Date().toISOString(),
    nodes_contributed: (extracted.nodes || []).map(n => n.id),
  });

  return { newNodes, newEdges, boostedNodes };
}

// ── Force layout ──────────────────────────────────────────────────────────────
export function rebuildLayout(graph) {
  c.info('Running force-directed layout…');
  const N = graph.nodes.length;
  const clusterSeeds = [
    {x:0,y:0},{x:-2.8,y:-1.2},{x:2.5,y:-2.2},{x:1.2,y:2.8},
    {x:-1.5,y:2.8},{x:-3.2,y:1.5},{x:3.5,y:1.0},
  ];

  const pos = graph.nodes.map(n => {
    const s = clusterSeeds[n.cluster] || clusterSeeds[0];
    return { x: s.x + (Math.random()-0.5)*2, y: s.y + (Math.random()-0.5)*2, vx:0, vy:0 };
  });

  const REST=1.8, KS=0.12, KR=2.2, DAMP=0.82, BOUNDS=6.5;

  for (let iter = 0; iter < 400; iter++) {
    const cool = 1 - iter/400;
    for (let i = 0; i < N; i++) {
      for (let j = i+1; j < N; j++) {
        const dx=pos[i].x-pos[j].x, dy=pos[i].y-pos[j].y;
        const d=Math.sqrt(dx*dx+dy*dy)+0.01;
        const f=KR/(d*d);
        pos[i].vx+=f*dx/d; pos[i].vy+=f*dy/d;
        pos[j].vx-=f*dx/d; pos[j].vy-=f*dy/d;
      }
    }
    graph.edges.forEach(e => {
      const ai=graph.nodes.findIndex(n=>n.id===e.a);
      const bi=graph.nodes.findIndex(n=>n.id===e.b);
      if (ai<0||bi<0) return;
      const dx=pos[bi].x-pos[ai].x, dy=pos[bi].y-pos[ai].y;
      const d=Math.sqrt(dx*dx+dy*dy)+0.01;
      const rest=REST/(0.5+e.strength);
      const f=KS*(d-rest);
      pos[ai].vx+=f*dx/d; pos[ai].vy+=f*dy/d;
      pos[bi].vx-=f*dx/d; pos[bi].vy-=f*dy/d;
    });
    for (let i=0;i<N;i++) {
      pos[i].vx*=DAMP; pos[i].vy*=DAMP;
      pos[i].x=Math.max(-BOUNDS,Math.min(BOUNDS,pos[i].x+pos[i].vx*cool));
      pos[i].y=Math.max(-BOUNDS,Math.min(BOUNDS,pos[i].y+pos[i].vy*cool));
    }
  }

  graph.layout = graph.nodes.map((n,i) => ({ id:n.id, x:pos[i].x, y:pos[i].y }));
  c.ok(`Layout computed for ${N} nodes`);
}
