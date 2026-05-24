#!/usr/bin/env node
/**
 * sync-bib.js — Parse CV bib files → publications.json + update graph.json papers
 *
 * Usage:
 *   node data/sync-bib.js                          # default CV path
 *   node data/sync-bib.js --cv-path ~/Documents/cv  # custom path
 *   node data/sync-bib.js --dry-run                 # preview, don't write
 *
 * Zero npm dependencies — uses only Node built-ins.
 */

const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────────────────────────
// CV repo location. Override with --cv-path or CV_PATH env var.
// Local default is ~/projects/cv. CI clones the public repo into /tmp/cv.
const DEFAULT_CV_PATH = process.env.CV_PATH || path.join(
  process.env.HOME || process.env.USERPROFILE,
  'projects', 'cv'
);
const WEBSITE_ROOT = path.resolve(__dirname, '..');
const OUTPUT_JSON  = path.join(WEBSITE_ROOT, 'data', 'publications.json');
const GRAPH_JSON   = path.join(WEBSITE_ROOT, 'graph', 'graph.json');

// Bib files to parse, mapped to publication type
const BIB_SOURCES = [
  { file: 'refs/journals.bib',       pubType: 'journal' },
  { file: 'refs/conference.bib',     pubType: 'conference' },
  { file: 'refs/preprints.bib',      pubType: 'preprint' },
  { file: 'refs/chapters.bib',       pubType: 'chapter' },
  { file: 'refs/scicomm.bib',        pubType: 'scicomm' },
];

// ── LaTeX cleanup ───────────────────────────────────────────────────────────

function cleanLatex(str) {
  if (!str) return '';
  return str
    // Remove LaTeX commands with arguments: \textbf{X} → X, \textit{X} → X
    .replace(/\\text(?:bf|it|rm|sf|tt|sc|up|sl)\{([^}]*)\}/g, '$1')
    .replace(/\\textsubscript\{([^}]*)\}/g, '$1')
    .replace(/\\textsuperscript\{([^}]*)\}/g, '$1')
    .replace(/\\emph\{([^}]*)\}/g, '$1')
    // CV-specific: \cvbibname{X} → X, \cvfnmark{X} → ''
    .replace(/\\cvbibname\{([^}]*)\}/g, '$1')
    .replace(/\\cvfnmark\{[^}]*\}/g, '')
    // \url{X} → X
    .replace(/\\url\{([^}]*)\}/g, '$1')
    // {AI} → AI (brace-protected acronyms)
    .replace(/\{([^}]*)\}/g, '$1')
    // Remaining LaTeX commands: \& → &, \textit → '', etc.
    .replace(/\\&/g, '&')
    .replace(/\\~/g, ' ')
    .replace(/~/g, ' ')
    .replace(/\\/g, '')
    // Collapse whitespace
    .replace(/\s+/g, ' ')
    .trim();
}

// ── BibTeX parser ───────────────────────────────────────────────────────────

function parseBibFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const entries = [];

  // Match @type{key, ... } — handles nested braces
  const entryRegex = /@(\w+)\s*\{([^,]+),/g;
  let match;

  while ((match = entryRegex.exec(content)) !== null) {
    const entryType = match[1].toLowerCase();
    const citeKey = match[2].trim();
    const startIdx = match.index + match[0].length;

    // Find the matching closing brace
    let depth = 1;
    let i = startIdx;
    while (i < content.length && depth > 0) {
      if (content[i] === '{') depth++;
      else if (content[i] === '}') depth--;
      i++;
    }
    const body = content.substring(startIdx, i - 1);

    // Parse fields
    const fields = parseFields(body);
    entries.push({ entryType, citeKey, fields });
  }

  return entries;
}

function parseFields(body) {
  const fields = {};
  // Match field = {value} or field = value
  const fieldRegex = /(\w+)\s*=\s*/g;
  let m;

  while ((m = fieldRegex.exec(body)) !== null) {
    const key = m[1].toLowerCase();
    const afterEquals = body.substring(m.index + m[0].length).trimStart();

    let value;
    if (afterEquals[0] === '{') {
      // Brace-delimited: find matching close
      let depth = 1, j = 1;
      while (j < afterEquals.length && depth > 0) {
        if (afterEquals[j] === '{') depth++;
        else if (afterEquals[j] === '}') depth--;
        j++;
      }
      value = afterEquals.substring(1, j - 1);
    } else {
      // Unquoted (number or macro like `dec`)
      const endMatch = afterEquals.match(/^([^,}\n]+)/);
      value = endMatch ? endMatch[1].trim() : '';
    }

    fields[key] = value;
  }

  return fields;
}

// ── Author parsing ──────────────────────────────────────────────────────────

function parseAuthors(authorField) {
  if (!authorField) return [];
  // Split on " and " (bibtex convention)
  return authorField
    .split(/\s+and\s+/i)
    .map(a => cleanLatex(a).trim())
    .filter(Boolean);
}

function getAuthorPosition(authors) {
  const hakimiIdx = authors.findIndex(a =>
    /hakimi/i.test(a)
  );
  if (hakimiIdx < 0) return 'middle';
  if (hakimiIdx === 0) return 'first';
  if (hakimiIdx === authors.length - 1) return 'last';
  if (hakimiIdx === 1) return 'second';
  return 'middle';
}

function checkEqualContrib(fields) {
  // usera field indicates custom author formatting (often equal contribution)
  if (fields.usera && /equalcontrib/i.test(fields.usera)) {
    // Check if Hakimi is among the equal-contrib authors
    if (/hakimi/i.test(fields.usera.split('equalcontrib')[0])) {
      return true;
    }
  }
  return false;
}

function formatAuthorsForDisplay(authors) {
  return authors.map(a => {
    // "Last, First" → "Last, F." for display, but bold Hakimi
    const parts = a.split(',').map(s => s.trim());
    if (parts.length === 2) {
      return `${parts[0]}, ${parts[1]}`;
    }
    return a;
  });
}

// ── Paper weight (mirrors graph/tool/index.js logic) ────────────────────────

const TYPE_WEIGHTS = {
  journal: 1.0,
  conference: 0.85,
  preprint: 0.7,
  chapter: 0.65,
  scicomm: 0.3,
};

const POS_WEIGHTS = {
  first: 1.0,
  'shared-first': 1.0,
  last: 0.8,
  second: 0.6,
  middle: 0.4,
};

function computePaperWeight(pubType, authorPosition, year) {
  const tw = TYPE_WEIGHTS[pubType] || 0.5;
  const pw = POS_WEIGHTS[authorPosition] || 0.4;
  const recency = year >= 2020 ? 1.0 : year >= 2015 ? 0.8 : 0.6;
  return Math.round(tw * pw * recency * 100) / 100;
}

// ── DOI → URL ───────────────────────────────────────────────────────────────

function doiToUrl(doi) {
  if (!doi) return null;
  const cleaned = doi.replace(/^https?:\/\/doi\.org\//, '');
  // Skip arXiv DOIs — we'll use the arxiv URL instead
  if (cleaned.startsWith('10.48550/arXiv.')) return null;
  return `https://doi.org/${cleaned}`;
}

function extractArxivId(fields) {
  // Check DOI for arXiv pattern
  if (fields.doi && fields.doi.includes('arXiv.')) {
    return fields.doi.replace(/.*arXiv\./, '');
  }
  // Check note/url for arxiv links
  const note = fields.note || '';
  const urlField = fields.url || '';
  const combined = note + ' ' + urlField;
  const arxivMatch = combined.match(/arxiv\.org\/abs\/(\d+\.\d+)/i);
  return arxivMatch ? arxivMatch[1] : null;
}

function getBestUrl(fields) {
  const doi = fields.doi ? cleanLatex(fields.doi) : null;
  const arxivId = extractArxivId(fields);
  const doiUrl = doiToUrl(doi);

  // Prefer DOI URL, fall back to arXiv, then note/url field
  if (doiUrl) return doiUrl;
  if (arxivId) return `https://arxiv.org/abs/${arxivId}`;

  // Check note for OSF or other URLs
  const note = fields.note || '';
  const urlMatch = note.match(/https?:\/\/[^\s}]+/);
  if (urlMatch) return urlMatch[0];

  if (fields.url) return cleanLatex(fields.url);

  return null;
}

// ── Venue extraction ────────────────────────────────────────────────────────

function getVenue(fields, entryType) {
  if (entryType === 'article') return fields.journal || '';
  if (entryType === 'inproceedings') return fields.booktitle || '';
  if (entryType === 'incollection') return fields.booktitle || '';
  if (entryType === 'unpublished') return 'Preprint';
  if (entryType === 'misc') return fields.journal || '';
  return '';
}

// ── Pub-type refinement ─────────────────────────────────────────────────────

function refinePubType(defaultType, fields, entryType) {
  // Conference entries: detect workshop vs full paper
  if (defaultType === 'conference') {
    const venue = (fields.booktitle || '').toLowerCase();
    if (venue.includes('workshop')) return 'conf-workshop';
    return 'conf-full';
  }
  // Chapters: detect commentary vs book chapter
  if (defaultType === 'chapter') {
    const kw = (fields.keywords || '').toLowerCase();
    if (kw.includes('commentary')) return 'commentary';
    if (kw.includes('bookchapter') || entryType === 'incollection') return 'book-chapter';
    return 'commentary';
  }
  return defaultType;
}

// ── Main ────────────────────────────────────────────────────────────────────

function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const cvPathArg = args.find((_, i) => args[i - 1] === '--cv-path');
  const cvPath = cvPathArg || DEFAULT_CV_PATH;

  if (!fs.existsSync(cvPath)) {
    console.error(`CV path not found: ${cvPath}`);
    console.error('Use --cv-path to specify location');
    process.exit(1);
  }

  console.log(`Reading bib files from: ${cvPath}`);

  const publications = [];

  for (const { file, pubType } of BIB_SOURCES) {
    const filePath = path.join(cvPath, file);
    if (!fs.existsSync(filePath)) {
      console.warn(`  Skipping missing file: ${file}`);
      continue;
    }

    const entries = parseBibFile(filePath);
    console.log(`  ${file}: ${entries.length} entries`);

    for (const { entryType, citeKey, fields } of entries) {
      // Honor `keywords = {unlisted}` to keep an entry out of publications.json
      // (and therefore cv.html). Used for things like the thesis that live in
      // chapters.bib for the corpus pipeline but shouldn't render publicly.
      const rawKw = (fields.keywords || '').toLowerCase();
      if (rawKw.split(',').map(s => s.trim()).includes('unlisted')) continue;

      const authors = parseAuthors(fields.author);
      let authorPosition = getAuthorPosition(authors);
      if (authorPosition === 'first' && checkEqualContrib(fields)) {
        authorPosition = 'shared-first';
      }
      // Also check if second/third author is equal contrib
      if (authorPosition !== 'first' && checkEqualContrib(fields)) {
        authorPosition = 'shared-first';
      }

      const year = parseInt(fields.year, 10) || 0;
      const refinedType = refinePubType(pubType, fields, entryType);
      const doi = fields.doi ? cleanLatex(fields.doi) : null;
      const arxivId = extractArxivId(fields);

      const pub = {
        id: citeKey,
        title: cleanLatex(fields.title),
        authors: formatAuthorsForDisplay(authors),
        year,
        venue: cleanLatex(getVenue(fields, entryType)),
        doi: doi && !doi.startsWith('10.48550/arXiv.') ? doi : undefined,
        arxivId: arxivId || undefined,
        url: getBestUrl(fields),
        pubType: refinedType,
        authorPosition,
        paperWeight: computePaperWeight(refinedType, authorPosition, year),
        keywords: (fields.keywords || '').split(',').map(k => k.trim()).filter(Boolean),
        addendum: fields.addendum ? cleanLatex(fields.addendum) : undefined,
        part_of: fields.part_of ? cleanLatex(fields.part_of) : undefined,
      };

      // Remove undefined fields
      Object.keys(pub).forEach(k => pub[k] === undefined && delete pub[k]);

      publications.push(pub);
    }
  }

  // Sort by year (newest first), then by author position weight
  publications.sort((a, b) => {
    if (b.year !== a.year) return b.year - a.year;
    return b.paperWeight - a.paperWeight;
  });

  console.log(`\nTotal: ${publications.length} publications`);

  // Summary by type
  const byType = {};
  publications.forEach(p => { byType[p.pubType] = (byType[p.pubType] || 0) + 1; });
  Object.entries(byType).forEach(([t, n]) => console.log(`  ${t}: ${n}`));

  if (dryRun) {
    console.log('\n-- Dry run, not writing files --');
    console.log(JSON.stringify(publications.slice(0, 3), null, 2));
    console.log(`... and ${publications.length - 3} more`);
    return;
  }

  // Write publications.json
  const pubJson = JSON.stringify(publications, null, 2);
  fs.writeFileSync(OUTPUT_JSON, pubJson + '\n', 'utf-8');
  console.log(`\nWrote ${OUTPUT_JSON}`);

  // Update graph.json meta.papers[]
  if (fs.existsSync(GRAPH_JSON)) {
    const graph = JSON.parse(fs.readFileSync(GRAPH_JSON, 'utf-8'));
    const existingPapers = (graph.meta && graph.meta.papers) || [];
    const existingById = new Map(existingPapers.map(p => [p.id, p]));

    // Also index by normalized title for fuzzy matching (handles ID mismatches)
    const normalizeTitle = t => (t || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const existingByTitle = new Map(
      existingPapers.map(p => [normalizeTitle(p.title), p])
    );

    // Build updated papers list: preserve existing entries (they may have
    // nodesContributed from concept extraction), add new ones
    const updatedPapers = [];
    for (const pub of publications) {
      const existing = existingById.get(pub.id)
        || existingByTitle.get(normalizeTitle(pub.title));
      if (existing) {
        // Merge: update metadata, preserve nodes_contributed and added date
        // Handle both field name conventions (snake_case and camelCase)
        const nodes = existing.nodes_contributed || existing.nodesContributed || [];
        const merged = {
          ...existing,
          id: pub.id, // use bib cite key as canonical ID going forward
          title: pub.title,
          year: pub.year,
          venue: pub.venue,
          doi: pub.doi,
          arxivId: pub.arxivId,
          url: pub.url || existing.url,
          pubType: pub.pubType,
          authorPosition: pub.authorPosition,
          paperWeight: pub.paperWeight,
          nodes_contributed: nodes,
        };
        // Remove camelCase variant if present
        delete merged.nodesContributed;
        updatedPapers.push(merged);
      } else {
        // New paper — no concept extraction yet
        updatedPapers.push({
          id: pub.id,
          title: pub.title,
          year: pub.year,
          venue: pub.venue,
          doi: pub.doi,
          arxivId: pub.arxivId,
          url: pub.url,
          pubType: pub.pubType,
          authorPosition: pub.authorPosition,
          paperWeight: pub.paperWeight,
          nodes_contributed: [],
          added: new Date().toISOString(),
        });
      }
    }

    graph.meta.papers = updatedPapers;

    // Clean undefined values from papers
    graph.meta.papers.forEach(p => {
      Object.keys(p).forEach(k => p[k] === undefined && delete p[k]);
    });

    fs.writeFileSync(GRAPH_JSON, JSON.stringify(graph, null, 2) + '\n', 'utf-8');
    console.log(`Updated ${GRAPH_JSON} — ${updatedPapers.length} papers`);

    const withNodes = updatedPapers.filter(p => p.nodes_contributed && p.nodes_contributed.length > 0).length;
    const withoutNodes = updatedPapers.length - withNodes;
    console.log(`  ${withNodes} with concept nodes, ${withoutNodes} awaiting extraction`);
  } else {
    console.warn(`Graph file not found: ${GRAPH_JSON} — skipping graph update`);
  }
}

main();
