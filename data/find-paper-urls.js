#!/usr/bin/env node
/**
 * find-paper-urls.js — Look up missing DOI/URL for publications via Crossref.
 *
 * Scans data/publications.json for entries lacking `url`, `doi`, and `arxivId`,
 * queries the Crossref REST API by title, and writes the resolved DOI URL
 * back when the match is high-confidence.
 *
 * Default run is a DRY review — prints proposed updates, writes nothing.
 * Pass --apply to write into publications.json.
 *
 *   node data/find-paper-urls.js          # review (no writes)
 *   node data/find-paper-urls.js --apply  # apply confirmed matches
 *
 * Match acceptance: normalized title equality OR Jaccard similarity >= 0.85
 * AND year within ±1. Anything weaker is flagged for manual review and
 * NOT applied even with --apply.
 *
 * No API key required. Polite User-Agent identifies the requester per
 * Crossref's etiquette guidance.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBS_PATH = path.join(__dirname, 'publications.json');
const APPLY = process.argv.includes('--apply');

const CR_BASE = 'https://api.crossref.org/works';
const USER_AGENT = 'shabnamhakimi.com find-paper-urls (mailto:shabnamhakimi@gmail.com)';

function normalize(s) {
  return (s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function jaccard(a, b) {
  const A = new Set(normalize(a).split(' ').filter(Boolean));
  const B = new Set(normalize(b).split(' ').filter(Boolean));
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const t of A) if (B.has(t)) inter++;
  return inter / (A.size + B.size - inter);
}

function candidateTitle(item) {
  // Crossref returns title as array of strings (rarely > 1 element)
  const t = Array.isArray(item.title) ? item.title.join(' ') : (item.title || '');
  return t;
}
function candidateYear(item) {
  const dp = item['published-print'] || item['published-online'] || item.issued || {};
  return dp['date-parts']?.[0]?.[0] || null;
}

async function searchCrossref(title, year) {
  const params = new URLSearchParams({
    'query.bibliographic': title,
    rows: '5',
    select: 'DOI,title,container-title,issued,published-print,published-online',
  });
  if (year) {
    params.set('filter', `from-pub-date:${year - 1},until-pub-date:${year + 1}`);
  }
  const u = `${CR_BASE}?${params}`;
  const r = await fetch(u, { headers: { 'User-Agent': USER_AGENT } });
  if (r.status === 429) {
    await new Promise(res => setTimeout(res, 2000));
    return searchCrossref(title, year);
  }
  if (!r.ok) throw new Error(`Crossref ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return (await r.json()).message?.items || [];
}

function classifyMatch(pub, candidate) {
  const cTitle = candidate ? candidateTitle(candidate) : '';
  if (!cTitle) return { tier: 'no-title', sim: 0 };
  const cYear  = candidate ? candidateYear(candidate) : null;
  const sim = jaccard(pub.title, cTitle);
  const yearOk = cYear && pub.year && Math.abs(cYear - pub.year) <= 1;
  const normEqual = normalize(pub.title) === normalize(cTitle);
  if (normEqual && yearOk) return { tier: 'strong', sim, yearOk };
  if (sim >= 0.85 && yearOk)  return { tier: 'strong', sim, yearOk };
  if (sim >= 0.65)            return { tier: 'weak',   sim, yearOk };
  return                              { tier: 'reject', sim, yearOk };
}

async function main() {
  const pubs = JSON.parse(fs.readFileSync(PUBS_PATH, 'utf-8'));
  const missing = pubs.filter(p => !p.url && !p.doi && !p.arxivId);
  if (!missing.length) {
    console.log('No papers missing links. Done.');
    return;
  }

  console.log(`Looking up ${missing.length} papers via Crossref…\n`);
  const results = [];

  for (const pub of missing) {
    try {
      const hits = await searchCrossref(pub.title, pub.year);
      let best = null, bestSim = -1;
      for (const h of hits) {
        const sim = jaccard(pub.title, candidateTitle(h));
        if (sim > bestSim) { best = h; bestSim = sim; }
      }
      const cls = classifyMatch(pub, best);
      const resolved = cls.tier === 'strong' && best.DOI
        ? { url: `https://doi.org/${best.DOI}`, doi: best.DOI }
        : null;
      results.push({ pub, candidate: best, cls, resolved });
    } catch (e) {
      results.push({ pub, error: e.message });
    }
    await new Promise(r => setTimeout(r, 600));
  }

  // Report
  const strong = results.filter(r => r.cls?.tier === 'strong');
  const weak   = results.filter(r => r.cls?.tier === 'weak');
  const none   = results.filter(r => r.cls && r.cls.tier !== 'strong' && r.cls.tier !== 'weak');
  const errs   = results.filter(r => r.error);

  console.log(`Strong matches (will apply): ${strong.length}`);
  for (const r of strong) {
    console.log(`  ✓ ${r.pub.year} "${r.pub.title.slice(0,70)}"`);
    console.log(`      → ${r.resolved.url}${r.resolved.doi ? '  [DOI]' : r.resolved.arxivId ? '  [arXiv]' : ''}`);
  }
  console.log(`\nWeak matches (review manually): ${weak.length}`);
  for (const r of weak) {
    const ct = candidateTitle(r.candidate);
    const cy = candidateYear(r.candidate);
    console.log(`  ? ${r.pub.year} "${r.pub.title.slice(0,70)}"`);
    console.log(`      candidate: "${ct.slice(0,70)}" (sim ${r.cls.sim.toFixed(2)}, year ${cy ?? '?'}, DOI ${r.candidate.DOI || '—'})`);
  }
  console.log(`\nNo match: ${none.length}`);
  for (const r of none) {
    console.log(`  ✗ ${r.pub.year} "${r.pub.title.slice(0,70)}"`);
  }
  if (errs.length) {
    console.log(`\nErrors: ${errs.length}`);
    for (const r of errs) console.log(`  ! "${r.pub.title.slice(0,70)}": ${r.error}`);
  }

  if (!APPLY) {
    console.log('\nDry run (no changes written). Re-run with --apply to write strong matches into publications.json.');
    return;
  }

  // Apply strong matches
  const byId = Object.fromEntries(strong.map(r => [r.pub.id, r.resolved]));
  let modified = 0;
  for (const p of pubs) {
    const res = byId[p.id];
    if (!res) continue;
    p.url = res.url;
    if (res.doi) p.doi = res.doi;
    if (res.arxivId) p.arxivId = res.arxivId;
    modified++;
  }
  fs.writeFileSync(PUBS_PATH, JSON.stringify(pubs, null, 2) + '\n', 'utf-8');
  console.log(`\nApplied ${modified} updates to ${path.relative(process.cwd(), PUBS_PATH)}.`);
  console.log('Next: review the diff, run `node data/inline-graph.js` if anything graph-relevant changed, commit.');
}

main().catch(err => { console.error(err); process.exit(1); });
