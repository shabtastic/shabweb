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
const AX_BASE = 'http://export.arxiv.org/api/query';
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

// arXiv Atom feed → parse just the fields we care about.
function parseArxiv(xml) {
  const entries = [];
  // Split on <entry> blocks; the feed wraps each result in one.
  const blocks = xml.split('<entry>').slice(1);
  for (const block of blocks) {
    const body = block.split('</entry>')[0];
    const title = (body.match(/<title[^>]*>([\s\S]*?)<\/title>/) || [, ''])[1].trim().replace(/\s+/g, ' ');
    const id    = (body.match(/<id[^>]*>([\s\S]*?)<\/id>/) || [, ''])[1].trim();
    const date  = (body.match(/<published[^>]*>([\s\S]*?)<\/published>/) || [, ''])[1].trim();
    const year  = date ? parseInt(date.slice(0, 4), 10) : null;
    // id is the abstract URL: http(s)://arxiv.org/abs/<id>v<n>
    const m = id.match(/arxiv\.org\/abs\/([^v\s]+)/i);
    const arxivId = m ? m[1] : null;
    entries.push({ title, year, arxivId, url: id });
  }
  return entries;
}

async function searchArxiv(title) {
  const params = new URLSearchParams({
    search_query: `ti:"${title.replace(/"/g, '')}"`,
    max_results: '5',
    sortBy: 'relevance',
    sortOrder: 'descending',
  });
  const r = await fetch(`${AX_BASE}?${params}`, { headers: { 'User-Agent': USER_AGENT } });
  if (r.status === 429) { await new Promise(res => setTimeout(res, 4000)); return searchArxiv(title); }
  if (!r.ok) throw new Error(`arXiv ${r.status}`);
  return parseArxiv(await r.text());
}

function classifyArxiv(pub, candidate) {
  if (!candidate?.title) return { tier: 'no-title', sim: 0 };
  const sim = jaccard(pub.title, candidate.title);
  const yearOk = candidate.year && pub.year && Math.abs(candidate.year - pub.year) <= 1;
  const normEqual = normalize(pub.title) === normalize(candidate.title);
  if (normEqual) return { tier: 'strong', sim, yearOk };
  if (sim >= 0.85 && yearOk) return { tier: 'strong', sim, yearOk };
  if (sim >= 0.65) return { tier: 'weak', sim, yearOk };
  return { tier: 'reject', sim, yearOk };
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

  console.log(`Looking up ${missing.length} papers via Crossref, then arXiv as fallback…\n`);
  const results = [];

  for (const pub of missing) {
    let candidate = null, cls = null, resolved = null, source = null, err = null;
    // Crossref pass
    try {
      const hits = await searchCrossref(pub.title, pub.year);
      let best = null, bestSim = -1;
      for (const h of hits) {
        const sim = jaccard(pub.title, candidateTitle(h));
        if (sim > bestSim) { best = h; bestSim = sim; }
      }
      const c = classifyMatch(pub, best);
      if (c.tier === 'strong' && best.DOI) {
        candidate = best; cls = c; source = 'crossref';
        resolved = { url: `https://doi.org/${best.DOI}`, doi: best.DOI };
      } else {
        candidate = best; cls = c; source = 'crossref';
      }
    } catch (e) { err = `crossref: ${e.message}`; }
    await new Promise(r => setTimeout(r, 600));

    // arXiv fallback only if Crossref didn't yield a strong match
    if (!resolved) {
      try {
        const axHits = await searchArxiv(pub.title);
        let axBest = null, axBestSim = -1;
        for (const h of axHits) {
          const sim = jaccard(pub.title, h.title || '');
          if (sim > axBestSim) { axBest = h; axBestSim = sim; }
        }
        const c = classifyArxiv(pub, axBest);
        if (c.tier === 'strong' && axBest.arxivId) {
          candidate = axBest; cls = c; source = 'arxiv';
          resolved = { url: axBest.url, arxivId: axBest.arxivId };
        } else if (c.tier === 'weak' && cls?.tier !== 'weak') {
          candidate = axBest; cls = c; source = 'arxiv';
        }
      } catch (e) { err = err ? `${err}; arxiv: ${e.message}` : `arxiv: ${e.message}`; }
      await new Promise(r => setTimeout(r, 3500)); // arXiv etiquette: 1 req / 3s
    }

    results.push({ pub, candidate, cls, resolved, source, error: err });
  }

  // Report
  const strong = results.filter(r => r.cls?.tier === 'strong');
  const weak   = results.filter(r => r.cls?.tier === 'weak');
  const none   = results.filter(r => r.cls && r.cls.tier !== 'strong' && r.cls.tier !== 'weak');
  const errs   = results.filter(r => r.error);

  console.log(`Strong matches (will apply): ${strong.length}`);
  for (const r of strong) {
    console.log(`  ✓ ${r.pub.year} "${r.pub.title.slice(0,70)}"`);
    const tag = r.resolved.doi ? '[DOI]' : r.resolved.arxivId ? '[arXiv]' : '';
    console.log(`      → ${r.resolved.url}  ${tag}  (${r.source})`);
  }
  console.log(`\nWeak matches (review manually): ${weak.length}`);
  for (const r of weak) {
    const c = r.candidate;
    const ct = r.source === 'arxiv' ? c.title : candidateTitle(c);
    const cy = r.source === 'arxiv' ? c.year  : candidateYear(c);
    const id = r.source === 'arxiv' ? `arXiv:${c.arxivId}` : `DOI:${c.DOI || '—'}`;
    console.log(`  ? ${r.pub.year} "${r.pub.title.slice(0,70)}"`);
    console.log(`      candidate: "${(ct || '').slice(0,70)}" (sim ${r.cls.sim.toFixed(2)}, year ${cy ?? '?'}, ${id}, src ${r.source})`);
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
