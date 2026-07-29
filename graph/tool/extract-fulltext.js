#!/usr/bin/env node
/**
 * extract-fulltext.js — Full-document text extraction for the 42 corpus-matched
 * graph papers (pass1+pass2 of loadCorpusUniverse()), for the hybrid
 * TF-IDF/embedding concept-extraction rebuild.
 *
 * Distinct from research-corpus's extract-text.js, which caps at pages 1-2 /
 * 20KB for cheap matching/triage across ~1300 files. This script reads whole
 * documents (all pages, references stripped) for the much smaller graph-paper
 * set, and writes to a separate vault/extracted-full/ cache so the matching
 * pipeline's lightweight cache is untouched.
 *
 * Usage:
 *   node extract-fulltext.js              # extract uncached graph papers only
 *   node extract-fulltext.js --force      # re-extract everything
 *   node extract-fulltext.js --dry-run    # list what would be extracted
 *   node extract-fulltext.js --limit <n>  # cap how many papers to process
 *
 * Environment:
 *   CORPUS_REPO  path to research-corpus repo (default: ~/projects/research-corpus)
 */

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { c, VAULT_DIR, loadCorpusUniverse } from './lib.js';

const ORIGINALS_DIR = path.join(VAULT_DIR, 'originals');
const CACHE_DIR      = path.join(VAULT_DIR, 'extracted-full');
const MAX_BYTES       = 150 * 1024;
// pdftotext -layout on two-column PDFs merges a heading from either column
// onto the same physical line as trailing text from the other column, so the
// heading can land at line-start OR after a big column-gap whitespace run —
// never mid-word in running prose. Exact-case match (not case-insensitive)
// avoids false positives on lowercase "references" inside a sentence. Take
// the LAST match (references sections are always near the end) so an
// accidental earlier false-positive doesn't truncate real body content.
const REFS_HEADING_RE = /(?:^|\s{2,})(References|REFERENCES|Bibliography|BIBLIOGRAPHY)\b/gm;

const FORCE   = process.argv.includes('--force');
const DRY_RUN = process.argv.includes('--dry-run');
const limitArg = process.argv.find((a, i) => process.argv[i - 1] === '--limit');
const LIMIT   = limitArg ? parseInt(limitArg, 10) : null;

fs.mkdirSync(CACHE_DIR, { recursive: true });

function findOriginal(sha) {
  const candidates = fs.readdirSync(ORIGINALS_DIR).filter(f => f.startsWith(sha + '.'));
  return candidates.length ? path.join(ORIGINALS_DIR, candidates[0]) : null;
}

function extractPDF(filePath) {
  const buf = execFileSync(
    'pdftotext',
    ['-layout', '-enc', 'UTF-8', filePath, '-'],
    { stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }
  );
  return { text: buf.toString('utf8'), extractor: 'pdftotext-full' };
}

function extractTextUtil(filePath) {
  const buf = execFileSync(
    'textutil',
    ['-convert', 'txt', '-stdout', filePath],
    { stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }
  );
  return { text: buf.toString('utf8'), extractor: 'textutil' };
}

function extractPlain(filePath) {
  return { text: fs.readFileSync(filePath, 'utf8'), extractor: 'plain' };
}

function extractFullText(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.pdf') return extractPDF(filePath);
  if (ext === '.docx' || ext === '.doc' || ext === '.rtf' || ext === '.pages') return extractTextUtil(filePath);
  if (ext === '.tex') return extractPlain(filePath);
  throw new Error(`No full-text extractor for ${ext}`);
}

function stripReferences(text) {
  const matches = [...text.matchAll(REFS_HEADING_RE)];
  if (!matches.length) return text;
  const last = matches[matches.length - 1];
  return text.slice(0, last.index);
}

function main() {
  const { pass1, pass2 } = loadCorpusUniverse();
  const papers = [...pass1, ...pass2];
  c.head(`\nFull-text extraction for ${papers.length} corpus-matched graph papers`);

  const batch = LIMIT ? papers.slice(0, LIMIT) : papers;
  let extracted = 0, cached = 0, failed = 0, missing = 0;

  for (const pub of batch) {
    const txtPath  = path.join(CACHE_DIR, `${pub.sha}.txt`);
    const metaPath = path.join(CACHE_DIR, `${pub.sha}.meta.json`);

    if (!FORCE && fs.existsSync(metaPath)) { cached++; continue; }

    const original = findOriginal(pub.sha);
    if (!original) {
      c.warn(`  [missing] ${pub.id} — no vault/originals/${pub.sha}.*`);
      missing++;
      continue;
    }

    if (DRY_RUN) { c.dim(`  would extract: ${pub.id} (${path.basename(original)})`); continue; }

    try {
      const { text, extractor } = extractFullText(original);
      const stripped  = stripReferences(text);
      const truncated = Buffer.from(stripped, 'utf8').slice(0, MAX_BYTES).toString('utf8');

      fs.writeFileSync(txtPath, truncated);
      fs.writeFileSync(metaPath, JSON.stringify({
        pub_id: pub.id,
        source_path: original,
        extractor,
        raw_chars: text.length,
        stripped_chars: stripped.length,
        written_chars: truncated.length,
        references_stripped: stripped.length < text.length,
        extracted_at: new Date().toISOString(),
      }, null, 2));

      c.ok(`  ${pub.id} — ${truncated.length.toLocaleString()} chars (${extractor}${stripped.length < text.length ? ', refs stripped' : ''})`);
      extracted++;
    } catch (err) {
      c.err(`  [failed] ${pub.id}: ${err.message}`);
      failed++;
    }
  }

  c.log(`\nDone. extracted=${extracted} cached=${cached} missing=${missing} failed=${failed}`);
  if (DRY_RUN) c.warn('Dry run — nothing written.');
}

main();
