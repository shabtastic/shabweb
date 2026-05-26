#!/usr/bin/env node
/**
 * rebuild-from-corpus.js — Full graph rebuild from vault full-text extractions.
 *
 * Usage:
 *   node rebuild-from-corpus.js [options]
 *
 * Options:
 *   --pass <n>        Run specific pass: 1, 2, 3, or all (default: all)
 *   --start-pass <n>  Resume from pass N without wiping graph
 *   --limit <n>       Max papers per pass (for testing)
 *   --dry-run         Extract but do not save
 *   --opus            Use claude-opus-4-7 instead of claude-sonnet-4-6
 *
 * Environment:
 *   ANTHROPIC_API_KEY  required
 *   CORPUS_REPO        path to research-corpus repo (default: ~/projects/research-corpus)
 */

import 'dotenv/config';
import fs   from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { program } from 'commander';
import { c, loadGraph, saveGraph, computePaperWeight, extractConcepts, mergeIntoGraph, rebuildLayout } from './lib.js';

const __dirname    = path.dirname(fileURLToPath(import.meta.url));
const HOME         = process.env.HOME;
const CORPUS_REPO  = process.env.CORPUS_REPO || path.join(HOME, 'projects/research-corpus');
const VAULT_DIR    = path.join(CORPUS_REPO, 'vault');
const CATALOG_PATH = path.join(CORPUS_REPO, 'corpus-catalog.json');
const PUBS_PATH    = path.join(__dirname, '..', '..', 'data', 'publications.json');
const GRAPH_DIR    = path.join(__dirname, '..');
const PROPOSALS_PATH = path.join(GRAPH_DIR, 'draft-proposals.json');

const EXCLUDED_KEYWORDS = ['scicomm', 'commentary', 'unlisted'];

program
  .name('rebuild-from-corpus')
  .description('Rebuild graph.json from vault full-text extractions')
  .option('--pass <n>',       'pass to run: 1, 2, 3, or all', 'all')
  .option('--start-pass <n>', 'resume from pass N without wiping graph')
  .option('--limit <n>',      'max papers per pass (testing)')
  .option('--dry-run',        'extract without saving', false)
  .option('--opus',           'use claude-opus-4-7', false);

/**
 * Build the three-pass paper universe from publications.json + corpus-catalog.json.
 * Returns { pass1, pass2, pass3 } sorted deterministically by pub_key.
 *
 * Pass 1: keywords includes "selected", next_action === "have_local"
 * Pass 2: no "selected" keyword,       next_action === "have_local"
 * Pass 3: next_action === "have_draft"  (regardless of selected)
 */
function loadCorpusUniverse() {
  if (!fs.existsSync(PUBS_PATH))    throw new Error(`publications.json not found: ${PUBS_PATH}`);
  if (!fs.existsSync(CATALOG_PATH)) throw new Error(`corpus-catalog.json not found: ${CATALOG_PATH}`);

  const publications   = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
  const catalog        = JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf-8'));
  const catalogEntries = catalog.entries;

  const pass1 = [], pass2 = [], pass3 = [];

  for (const pub of publications) {
    const kw = pub.keywords || [];

    if (EXCLUDED_KEYWORDS.some(k => kw.includes(k))) continue;

    const entry = catalogEntries[pub.id];
    if (!entry) continue;

    const nextAction = entry.acquisition?.next_action;
    if (!['have_local', 'have_draft'].includes(nextAction)) continue;

    const sha = entry.final_output?.sha;
    if (!sha) continue;

    const isDraft    = nextAction === 'have_draft';
    const isSelected = kw.includes('selected');

    const paper = { ...pub, sha, isDraft, isSelected };

    if (isDraft) {
      pass3.push(paper);
    } else if (isSelected) {
      pass1.push(paper);
    } else {
      pass2.push(paper);
    }
  }

  const byId = (a, b) => a.id.localeCompare(b.id);
  pass1.sort(byId); pass2.sort(byId); pass3.sort(byId);

  return { pass1, pass2, pass3 };
}

// ── Draft proposals ───────────────────────────────────────────────────────────
function writeDraftProposal(paperId, extracted, meta, paperWeight, model) {
  let proposals = { proposals: [] };
  if (fs.existsSync(PROPOSALS_PATH)) {
    try { proposals = JSON.parse(fs.readFileSync(PROPOSALS_PATH, 'utf-8')); }
    catch { /* start fresh if corrupt */ }
  }

  // Replace any existing proposal for this paper (idempotent)
  proposals.proposals = proposals.proposals.filter(p => p.paper_id !== paperId);

  proposals.proposals.push({
    paper_id:          paperId,
    extracted_at:      new Date().toISOString(),
    model,
    paper_weight:      paperWeight,
    extraction_source: meta.extraction_source,
    nodes:             extracted.nodes || [],
    edges:             extracted.edges || [],
    paper_meta:        extracted.paper || {},
    reviewed:          false,
  });

  fs.writeFileSync(PROPOSALS_PATH, JSON.stringify(proposals, null, 2));
  c.ok(`  Draft proposal written for ${paperId}`);
}

// ── Retry logic ───────────────────────────────────────────────────────────────
async function extractConceptsWithRetry(text, graph, paperWeight, model, maxAttempts = 3) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await extractConcepts(text, graph, paperWeight, model);
    } catch (e) {
      const isJsonError = e instanceof SyntaxError || e.message?.includes('JSON');
      const isApiError  = e.status === 429 || (e.status >= 500 && e.status < 600);

      if (isJsonError && attempt < maxAttempts) {
        c.warn(`  JSON parse error (attempt ${attempt}/${maxAttempts}) — retrying…`);
        await new Promise(r => setTimeout(r, 3000));
        continue;
      }
      if (isApiError && attempt < maxAttempts) {
        const wait = attempt * 15;
        c.warn(`  API error ${e.status} — backing off ${wait}s (attempt ${attempt}/${maxAttempts})…`);
        await new Promise(r => setTimeout(r, wait * 1000));
        continue;
      }
      throw e;
    }
  }
  // Unreachable in normal flow, but guards against falling off the loop silently
  throw new Error(`extractConcepts failed after ${maxAttempts} attempts`);
}

// ── Per-paper processor ───────────────────────────────────────────────────────
async function processPaper(pub, graph, opts, passNum) {
  const shaPath = path.join(VAULT_DIR, 'extracted', `${pub.sha}.txt`);

  let text, extractionSource;
  if (fs.existsSync(shaPath)) {
    text = fs.readFileSync(shaPath, 'utf-8');
    extractionSource = 'full-text';
    c.info(`  vault/extracted/${pub.sha}.txt — ${text.length} chars`);
  } else {
    c.warn(`  vault/extracted/${pub.sha}.txt missing — falling back to title+abstract`);
    text = [pub.title, pub.abstract].filter(Boolean).join('\n\n');
    extractionSource = 'title-abstract';
  }

  // Pass 1 papers and any selected paper always get paperWeight 1.0
  const paperWeight = (passNum === 1 || pub.isSelected)
    ? 1.0
    : computePaperWeight({ pubType: pub.pubType, authorPosition: pub.authorPosition, year: pub.year });

  const model = opts.opus ? 'claude-opus-4-7' : 'claude-sonnet-4-6';
  c.info(`  weight:${paperWeight}  model:${model}  source:${extractionSource}`);

  if (opts.dryRun) {
    c.dim('  [dry-run] skipping extraction');
    return;
  }

  const extracted = await extractConceptsWithRetry(text, graph, paperWeight, model);
  c.ok(`  extracted ${extracted.nodes?.length || 0} nodes, ${extracted.edges?.length || 0} edges`);

  if (!extracted.nodes?.length && !extracted.edges?.length) {
    c.warn(`  Empty extraction — skipping paper record (will be retried on next run)`);
    return;
  }

  const meta = {
    id:               pub.id,
    title:            pub.title,
    year:             pub.year,
    venue:            pub.venue,
    doi:              pub.doi,
    arxivId:          pub.arxivId,
    url:              pub.url,
    abstractOnly:     extractionSource === 'title-abstract',
    pubType:          pub.pubType,
    authorPosition:   pub.authorPosition,
    extraction_source: extractionSource,
  };

  if (passNum === 3) {
    writeDraftProposal(pub.id, extracted, meta, paperWeight, model);
  } else {
    const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, extracted, meta, paperWeight);
    saveGraph(graph);
    c.ok(`  +${newNodes} nodes, +${newEdges} edges, ↑${boostedNodes} boosted — total ${graph.nodes.length} nodes`);
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  program.parse();
  const opts = program.opts();

  if (!process.env.ANTHROPIC_API_KEY) {
    c.err('ANTHROPIC_API_KEY not set. Add it to .env or export it.');
    process.exit(1);
  }

  const { pass1, pass2, pass3 } = loadCorpusUniverse();
  c.head('\nGraph Rebuild from Corpus');
  c.log(`  Pass 1 (selected, non-draft): ${pass1.length} papers`);
  c.log(`  Pass 2 (non-selected, non-draft): ${pass2.length} papers`);
  c.log(`  Pass 3 (draft): ${pass3.length} papers`);
  c.log(`  Corpus: ${CORPUS_REPO}`);
  c.log('');

  const startPass = opts.startPass ? parseInt(opts.startPass) : null;
  const passMask  = opts.pass === 'all' ? [1, 2, 3] : [parseInt(opts.pass)];
  const limit     = opts.limit ? parseInt(opts.limit) : null;
  const passMap   = { 1: pass1, 2: pass2, 3: pass3 };

  // Wipe graph only on a fresh full run that includes pass 1 or 2 (no --start-pass).
  // --pass 3 alone only writes to draft-proposals.json, never touches graph.json.
  if (!opts.dryRun && !startPass && (passMask.includes(1) || passMask.includes(2))) {
    const graph = loadGraph();
    const clusterBackup = graph.meta.clusters;
    graph.nodes         = [];
    graph.edges         = [];
    graph.layout        = [];
    graph.meta.papers   = [];
    graph.meta.clusters = clusterBackup;
    saveGraph(graph);
    c.ok('Graph wiped — fresh rebuild starting');
  }

  const graph = loadGraph();

  for (const passNum of passMask) {
    if (startPass && passNum < startPass) continue;

    const papers    = passMap[passNum];
    const alreadyDone = new Set(graph.meta.papers.map(p => p.id));

    const toProcess = papers.filter(pub => {
      if (passNum !== 3 && alreadyDone.has(pub.id)) {
        c.dim(`  [skip] ${pub.id} — already in graph`);
        return false;
      }
      return true;
    });

    const batch = limit ? toProcess.slice(0, limit) : toProcess;
    c.head(`\n── Pass ${passNum} — ${batch.length} papers to process ─────────────────`);

    for (let i = 0; i < batch.length; i++) {
      const pub = batch[i];
      c.head(`\n[${i+1}/${batch.length}] ${pub.id}`);
      c.dim(`  ${pub.title?.slice(0, 80)}`);
      try {
        await processPaper(pub, graph, opts, passNum);
      } catch (e) {
        c.err(`  FAILED: ${e.message}`);
        c.err(`  Skipping ${pub.id} — continuing`);
      }
      if (i < batch.length - 1) await new Promise(r => setTimeout(r, 2000));
    }
  }

  const touchedGraph = passMask.some(p => p !== 3);
  if (!opts.dryRun && touchedGraph) {
    c.head('\nFinalizing layout…');
    rebuildLayout(graph);
    saveGraph(graph);
    c.ok(`Rebuild complete: ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${graph.meta.papers.length} papers`);
  }
  if (!opts.dryRun && passMask.includes(3)) {
    c.warn(`Pass 3 (${pass3.length} drafts) → inspect graph/draft-proposals.json, then run review-draft-proposals.js`);
  }
  if (opts.dryRun) {
    c.warn('Dry run — nothing saved.');
  }
}

main().catch(e => { c.err(e.message); process.exit(1); });
