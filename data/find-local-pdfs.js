#!/usr/bin/env node
/**
 * find-local-pdfs.js — Cross-reference local PDFs against publications.json.
 *
 * Scans a fixed set of local directories for PDF files, then for each
 * publication picks the best filename match using title-keyword overlap,
 * first-author surname, and year. Prints a triaged report:
 *
 *   ✓ strong  — high confidence (score ≥ 0.85); apply to corpus directly
 *   ?  weak   — ambiguous (0.45–0.85); needs a manual look
 *   ✗ none   — nothing local that resembles this paper
 *
 * No PDF parsing or external API calls in this pass — filename-only.
 * A second pass (PDF-text or metadata-based) can add precision later.
 *
 * Usage:
 *   node data/find-local-pdfs.js                # report only
 *   node data/find-local-pdfs.js --tsv > out    # machine-readable
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBS_PATH = path.join(__dirname, 'publications.json');
import { ROOTS } from './corpus-roots.js';

const HOME = process.env.HOME;

const TSV = process.argv.includes('--tsv');
const STRONG_T = 0.75;
const WEAK_T   = 0.40;

const STOP = new Set([
  'the','a','an','of','and','to','in','on','for','from','with','at','by','as',
  'is','are','this','that','it','its','what','how','why','when','where','about',
  'into','onto','via','using','use','can','may','do','does','vs','versus',
  'paper','manuscript','draft','preprint','final',
]);

function tokens(s) {
  // Split camelCase, PascalCase, and letter↔digit boundaries before
  // lower-casing. Without this, filenames like "Goldin2009NeuralBases.pdf"
  // collapse to a single un-matchable token.
  const split = (s || '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .replace(/([A-Za-z])(\d)/g, '$1 $2')
    .replace(/(\d)([A-Za-z])/g, '$1 $2');
  return split
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .split(' ')
    .filter(w => w.length >= 3 && !STOP.has(w));
}

const DOC_RE = /\.(pdf|docx?|pages|rtf|tex)$/i;
function walk(dir, out = []) {
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); }
  catch { return out; }
  for (const ent of ents) {
    // Skip the usual junk
    if (ent.name === '.git' || ent.name === 'node_modules' ||
        ent.name === '.DS_Store' || ent.name.startsWith('._')) continue;
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, out);
    else if (ent.isFile() && DOC_RE.test(ent.name)) out.push(p);
  }
  return out;
}

function authorSurnames(pub) {
  // "Goldin, P. R." → "goldin"
  return (pub.authors || []).map(a => {
    const s = a.toLowerCase().replace(/,.*$/, '').trim().split(/\s+/).pop() || '';
    return s.length >= 4 ? s : '';
  }).filter(Boolean);
}

function score(pub, pdfPath) {
  // Tokenize against the full path (filename + parent dirs) because authors
  // often file papers under topic/year folders rather than encoding everything
  // in the filename ("Publications/2009/manuscript.pdf").
  const fname      = path.basename(pdfPath);
  const fullPath   = pdfPath;
  const fullLower  = fullPath.toLowerCase();
  const tToks = new Set(tokens(pub.title));
  const fToks = new Set(tokens(fullPath));
  if (!tToks.size || !fToks.size) return 0;
  let overlap = 0;
  for (const t of tToks) if (fToks.has(t)) overlap++;
  let s = overlap / tToks.size;

  // Bonus: any author surname in path. Diminishing returns: cap at +0.35.
  let authorBonus = 0;
  for (const sn of authorSurnames(pub)) {
    if (fullLower.includes(sn)) authorBonus += 0.18;
  }
  s += Math.min(authorBonus, 0.35);

  // Bonus: matching year anywhere in path
  if (pub.year && fullLower.includes(String(pub.year))) s += 0.15;

  // Smaller bonus for "Hakimi" specifically in the path — most files in
  // her archive will be tagged with her name and that's not very informative,
  // so only count it once and weakly.
  if (fullLower.includes('hakimi')) s += 0.05;

  return s;
}

function classify(s) {
  if (s >= STRONG_T) return 'strong';
  if (s >= WEAK_T)   return 'weak';
  return 'none';
}

function relHome(p) { return p.startsWith(HOME) ? '~' + p.slice(HOME.length) : p; }

function main() {
  if (!fs.existsSync(PUBS_PATH)) {
    console.error(`Missing ${PUBS_PATH}`);
    process.exit(1);
  }
  const pubs = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));

  const pdfs = ROOTS.flatMap(r => fs.existsSync(r) ? walk(r) : []);
  // Tally by extension for the recon header
  const byExt = {};
  for (const p of pdfs) {
    const m = p.match(/\.([^.]+)$/);
    const k = (m ? m[1] : '?').toLowerCase();
    byExt[k] = (byExt[k] || 0) + 1;
  }
  const tally = Object.entries(byExt).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${v} .${k}`).join(', ');
  console.error(`Scanned ${pdfs.length} documents across ${ROOTS.length} roots (${tally}).\n`);

  const rows = [];
  for (const pub of pubs) {
    let best = null, bestScore = 0;
    const all = [];
    for (const p of pdfs) {
      const s = score(pub, p);
      if (s >= 0.25) all.push({ p, s }); // collect runners-up for review
      if (s > bestScore) { bestScore = s; best = p; }
    }
    all.sort((a, b) => b.s - a.s);
    rows.push({
      pub,
      best,
      bestScore,
      tier: classify(bestScore),
      runners: all.slice(1, 4).filter(r => r.s >= WEAK_T - 0.1),
    });
  }

  if (TSV) {
    console.log('tier\tscore\tyear\ttitle\tmatch_path');
    for (const r of rows) {
      const pathStr = r.best ? relHome(r.best) : '';
      console.log(`${r.tier}\t${r.bestScore.toFixed(2)}\t${r.pub.year ?? ''}\t${r.pub.title.replace(/\t/g, ' ')}\t${pathStr}`);
    }
    return;
  }

  // Pretty print, grouped by tier
  const groups = { strong: [], weak: [], none: [] };
  for (const r of rows) groups[r.tier].push(r);

  console.log(`Strong matches (≥${STRONG_T}): ${groups.strong.length}`);
  for (const r of groups.strong) {
    console.log(`  ✓ ${r.pub.year} ${r.bestScore.toFixed(2)}  "${r.pub.title.slice(0, 70)}"`);
    console.log(`        → ${relHome(r.best)}`);
  }

  console.log(`\nWeak matches (${WEAK_T}–${STRONG_T}, review): ${groups.weak.length}`);
  for (const r of groups.weak) {
    console.log(`  ? ${r.pub.year} ${r.bestScore.toFixed(2)}  "${r.pub.title.slice(0, 70)}"`);
    console.log(`        → ${relHome(r.best)}`);
    for (const rn of r.runners.slice(0, 2)) {
      console.log(`        · ${rn.s.toFixed(2)}  ${relHome(rn.p)}`);
    }
  }

  console.log(`\nNo filename match (need content/PDF lookup): ${groups.none.length}`);
  for (const r of groups.none) {
    console.log(`  ✗ ${r.pub.year}  "${r.pub.title.slice(0, 70)}"`);
  }

  // ── Inventory pile: Hakimi-tagged documents grouped by inferred year.
  // The point isn't matching — it's so the user can browse the corpus
  // and tag papers/abstracts/chapters manually.
  console.log('\n──────────────────────────────────────────────────');
  console.log('Inventory: documents that look like Shabnam-authored artifacts');
  console.log('──────────────────────────────────────────────────');
  const hakimiDocs = pdfs.filter(p => /hakimi/i.test(p));
  const byYear = {};
  const noYear = [];
  for (const p of hakimiDocs) {
    const m = p.match(/(19|20)\d{2}/);
    if (m) {
      const y = m[0];
      (byYear[y] ||= []).push(p);
    } else {
      noYear.push(p);
    }
  }
  const years = Object.keys(byYear).sort((a, b) => b.localeCompare(a));
  for (const y of years) {
    console.log(`\n  ${y} (${byYear[y].length})`);
    for (const p of byYear[y]) console.log(`    ${relHome(p)}`);
  }
  if (noYear.length) {
    console.log(`\n  no-year (${noYear.length})`);
    for (const p of noYear) console.log(`    ${relHome(p)}`);
  }

  // ── Likely abstracts and book chapters — substring scan on filename
  const abstractDocs = pdfs.filter(p => /abstract/i.test(path.basename(p)));
  const chapterDocs  = pdfs.filter(p => /(chapter|book)/i.test(p));
  console.log('\n──────────────────────────────────────────────────');
  console.log(`Likely abstracts (${abstractDocs.length}) and book chapters (${chapterDocs.length})`);
  console.log('──────────────────────────────────────────────────');
  console.log(`\n  ABSTRACTS:`);
  for (const p of abstractDocs) console.log(`    ${relHome(p)}`);
  console.log(`\n  CHAPTERS:`);
  for (const p of chapterDocs) console.log(`    ${relHome(p)}`);

  console.log(`\nSummary: ${groups.strong.length}/${rows.length} strong, ${groups.weak.length} weak, ${groups.none.length} missing by filename. ${hakimiDocs.length} Hakimi-tagged docs total.`);
}

main();
