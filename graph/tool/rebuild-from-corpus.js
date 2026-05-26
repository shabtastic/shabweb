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
