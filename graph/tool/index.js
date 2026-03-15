#!/usr/bin/env node
/**
 * hakimi-graph-tool  v2.0
 *
 * Commands:
 *   node index.js orcid              — pull full publication list from ORCID
 *   node index.js search <query>     — search PubMed, arXiv, Semantic Scholar
 *   node index.js add --pdf <path>   — add paper from local PDF
 *   node index.js add --doi <doi>    — add by DOI (fetches full text or abstract)
 *   node index.js add --url <url>    — add from arXiv / PubMed URL
 *   node index.js add --pmid <id>    — add by PubMed ID
 *   node index.js add --text         — paste text via stdin
 *   node index.js list               — list all papers in graph
 *   node index.js stats              — graph statistics
 *   node index.js rebuild            — rerun force layout, save graph.json
 */

import 'dotenv/config';
import fs   from 'fs';
import path from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';
import { program } from 'commander';
import Anthropic from '@anthropic-ai/sdk';
import fetch from 'node-fetch';

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const GRAPH_PATH = path.join(__dirname, '..', 'graph.json');
const ORCID_ID   = process.env.ORCID_ID || '0000-0003-4122-6041';

// ── Console helpers ────────────────────────────────────────────────────────
const c = {
  info:  s => process.stdout.write(`\x1b[36m→\x1b[0m  ${s}\n`),
  ok:    s => process.stdout.write(`\x1b[32m✓\x1b[0m  ${s}\n`),
  warn:  s => process.stdout.write(`\x1b[33m⚠\x1b[0m  ${s}\n`),
  err:   s => process.stdout.write(`\x1b[31m✗\x1b[0m  ${s}\n`),
  head:  s => process.stdout.write(`\x1b[1m${s}\x1b[0m\n`),
  dim:   s => process.stdout.write(`\x1b[2m${s}\x1b[0m\n`),
  log:   s => process.stdout.write(`${s}\n`),
};

// ── Graph I/O ──────────────────────────────────────────────────────────────
function loadGraph() {
  if (!fs.existsSync(GRAPH_PATH)) throw new Error(`graph.json not found at ${GRAPH_PATH}`);
  return JSON.parse(fs.readFileSync(GRAPH_PATH, 'utf8'));
}

function saveGraph(graph) {
  fs.writeFileSync(GRAPH_PATH, JSON.stringify(graph, null, 2));
}

// ── Deduplication ──────────────────────────────────────────────────────────

// Normalise a DOI for comparison (lowercase, trim whitespace)
function normDOI(doi) {
  return doi?.toLowerCase().trim().replace(/^https?:\/\/doi\.org\//,'');
}

// Normalise a title for fuzzy comparison
function normTitle(t) {
  return t?.toLowerCase().replace(/[^a-z0-9 ]/g,'').replace(/\s+/g,' ').trim();
}

// Levenshtein-based similarity ratio (0–1)
function titleSimilarity(a, b) {
  a = normTitle(a); b = normTitle(b);
  if (!a || !b) return 0;
  if (a === b) return 1;
  // Quick length gate
  const longer = a.length > b.length ? a : b;
  const shorter = a.length > b.length ? b : a;
  if (longer.length === 0) return 1;
  if (shorter.length / longer.length < 0.5) return 0;
  // Levenshtein
  const dp = Array.from({length: shorter.length+1}, (_,i) => i);
  for (let j = 1; j <= longer.length; j++) {
    let prev = j;
    for (let i = 1; i <= shorter.length; i++) {
      const val = longer[j-1] === shorter[i-1]
        ? dp[i-1]
        : 1 + Math.min(dp[i-1], dp[i], prev);
      dp[i-1] = prev;
      prev = val;
    }
    dp[shorter.length] = prev;
  }
  return 1 - dp[shorter.length] / longer.length;
}

/**
 * Check whether a paper is already in the graph.
 * Returns { duplicate: true, match: paperEntry, reason: string }
 * or      { duplicate: false }
 *
 * Identity chain (in priority order):
 *   1. DOI match
 *   2. arXiv ID match (handles preprint ↔ published same paper)
 *   3. Title similarity > 0.92
 */
function findDuplicate(graph, candidate) {
  const papers = graph.meta.papers || [];
  const cDOI   = normDOI(candidate.doi);
  const cArXiv = candidate.arxivId;
  const cTitle = normTitle(candidate.title);

  for (const p of papers) {
    // 1. DOI
    if (cDOI && normDOI(p.doi) === cDOI) {
      return { duplicate: true, match: p, reason: `same DOI (${p.doi})` };
    }
    // 2. arXiv ID
    if (cArXiv && p.arxivId && cArXiv === p.arxivId) {
      return { duplicate: true, match: p, reason: `same arXiv ID (${p.arxivId})` };
    }
    // 3. Title similarity
    if (cTitle && titleSimilarity(cTitle, normTitle(p.title)) > 0.92) {
      return { duplicate: true, match: p, reason: `very similar title` };
    }
  }
  return { duplicate: false };
}

/**
 * If a paper was added as an arXiv preprint and the journal version is now
 * being added, update the existing entry with the journal DOI/venue/year.
 */
function updateExistingPaper(graph, existing, newMeta) {
  const idx = graph.meta.papers.findIndex(p => p.id === existing.id);
  if (idx === -1) return;
  const p = graph.meta.papers[idx];
  let updated = false;
  if (newMeta.doi   && !p.doi)   { p.doi   = newMeta.doi;   updated = true; }
  if (newMeta.venue && !p.venue) { p.venue  = newMeta.venue; updated = true; }
  if (newMeta.year  && !p.year)  { p.year   = newMeta.year;  updated = true; }
  if (newMeta.url   && !p.url)   { p.url    = newMeta.url;   updated = true; }
  if (newMeta.arxivId && !p.arxivId) { p.arxivId = newMeta.arxivId; updated = true; }
  // If we now have a journal DOI, mark it no longer abstract-only if applicable
  if (newMeta.doi && p.abstractOnly === true && !newMeta.abstractOnly) {
    p.abstractOnly = false; updated = true;
  }
  if (updated) graph.meta.papers[idx] = p;
  return updated;
}

/**
 * Merge search results from multiple sources into deduplicated cards.
 * Groups by DOI first, then arXiv ID, then fuzzy title.
 * Within each group keeps the entry with the best access.
 */
function deduplicateResults(results) {
  const groups = [];

  for (const r of results) {
    const rDOI   = normDOI(r.doi);
    const rArXiv = r.arxivId;
    const rTitle = normTitle(r.title);

    let group = groups.find(g =>
      (rDOI   && normDOI(g.doi)     === rDOI)   ||
      (rArXiv && g.arxivId          === rArXiv)  ||
      (rTitle && titleSimilarity(rTitle, normTitle(g.title)) > 0.92)
    );

    if (group) {
      // Merge IDs and sources
      if (r.doi     && !group.doi)     group.doi     = r.doi;
      if (r.arxivId && !group.arxivId) group.arxivId = r.arxivId;
      if (r.pmid    && !group.pmid)    group.pmid    = r.pmid;
      if (r.pdfUrl  && !group.pdfUrl)  group.pdfUrl  = r.pdfUrl;
      if (r.openAccess) group.openAccess = true;
      if (!group.abstract && r.abstract) group.abstract = r.abstract;
      if (!group.authors  && r.authors)  group.authors  = r.authors;
      if (!group.year     && r.year)     group.year     = r.year;
      group.sources = [...new Set([...(group.sources||[group.source]), r.source])];
    } else {
      groups.push({ ...r, sources: [r.source] });
    }
  }

  // Sort: open access with PDF first, then by year desc
  return groups.sort((a, b) => {
    if (a.pdfUrl && !b.pdfUrl) return -1;
    if (!a.pdfUrl && b.pdfUrl) return 1;
    if (a.openAccess && !b.openAccess) return -1;
    if (!a.openAccess && b.openAccess) return 1;
    return (b.year || 0) - (a.year || 0);
  });
}
async function fetchORCIDWorks(orcidId) {
  c.info(`Fetching publication list from ORCID: ${orcidId}`);
  const res = await fetch(
    `https://pub.orcid.org/v3.0/${orcidId}/works`,
    { headers: { Accept: 'application/json' } }
  );
  if (!res.ok) throw new Error(`ORCID API returned ${res.status}`);
  const data = await res.json();

  const works = (data.group || []).map(g => {
    const summary = g['work-summary']?.[0];
    if (!summary) return null;
    const title = summary.title?.title?.value;
    const year  = summary['publication-date']?.year?.value;
    const type  = summary.type;
    // Extract DOI if present
    const ids   = summary['external-ids']?.['external-id'] || [];
    const doiObj = ids.find(x => x['external-id-type'] === 'doi');
    const doi    = doiObj?.['external-id-value'];
    const url    = summary.url?.value || (doi ? `https://doi.org/${doi}` : null);
    return { title, year, type, doi, url };
  }).filter(Boolean);

  return works;
}

// ── PubMed ─────────────────────────────────────────────────────────────────
async function searchPubMed(query, maxResults = 8) {
  const searchRes = await fetch(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(query)}&retmax=${maxResults}&retmode=json`
  );
  const searchData = await searchRes.json();
  const ids = searchData.esearchresult?.idlist || [];
  if (!ids.length) return [];

  const summRes = await fetch(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${ids.join(',')}&retmode=json`
  );
  const summData = await summRes.json();

  return ids.map(id => {
    const p = summData.result?.[id];
    if (!p) return null;
    return {
      source:  'PubMed',
      title:   p.title,
      year:    p.pubdate?.split(' ')?.[0],
      authors: (p.authors || []).map(a => a.name).join(', '),
      pmid:    id,
      doi:     p.elocationid?.replace('doi: ', ''),
      url:     `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
    };
  }).filter(Boolean);
}

async function fetchPubMedFull(pmid) {
  // 1. Fetch summary to get year, DOI, PMC ID
  const summRes = await fetch(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${pmid}&retmode=json`
  );
  const summData = await summRes.json();
  const p = summData.result?.[pmid] || {};
  const year  = p.pubdate?.match(/\d{4}/)?.[0];
  const doi   = p.elocationid?.replace('doi: ','') || null;
  const pmcId = p.articleids?.find(a => a.idtype === 'pmc')?.value?.replace('PMC','');

  // 2. Try PMC full text XML if available
  if (pmcId) {
    c.info(`PMC full text available (PMC${pmcId}) — fetching…`);
    try {
      const pmcRes = await fetch(
        `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=${pmcId}&rettype=full&retmode=xml`
      );
      if (pmcRes.ok) {
        const xml  = await pmcRes.text();
        // Strip XML tags for plain text
        const text = xml
          .replace(/<[^>]+>/g, ' ')
          .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&')
          .replace(/\s+/g,' ').trim();
        if (text.length > 2000) {
          c.ok(`Got PMC full text: ${text.length} chars`);
          return { text, year, doi, url: `https://pmc.ncbi.nlm.nih.gov/articles/PMC${pmcId}/`, pmcId };
        }
      }
    } catch(e) { c.warn(`PMC fetch failed: ${e.message}`); }
  }

  // 3. Fall back to abstract
  c.warn('No PMC full text — using abstract');
  const absRes = await fetch(
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=${pmid}&retmode=text&rettype=abstract`
  );
  const text = await absRes.text();
  return { text, year, doi, url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`, abstractOnly: true };
}

// ── arXiv ──────────────────────────────────────────────────────────────────
async function searchArXiv(query, maxResults = 6) {
  const res = await fetch(
    `https://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}&max_results=${maxResults}`
  );
  const xml = await res.text();
  const entries = xml.match(/<entry>([\s\S]*?)<\/entry>/g) || [];
  return entries.map(e => {
    const title   = e.match(/<title>([\s\S]*?)<\/title>/)?.[1]?.trim().replace(/\s+/g, ' ');
    const id      = e.match(/<id>([\s\S]*?)<\/id>/)?.[1]?.trim();
    const summary = e.match(/<summary>([\s\S]*?)<\/summary>/)?.[1]?.trim();
    const authors = (e.match(/<name>([\s\S]*?)<\/name>/g) || [])
      .map(a => a.replace(/<\/?name>/g,'')).join(', ');
    const arxivId = id?.match(/(\d+\.\d+)/)?.[1];
    return {
      source:   'arXiv',
      title,
      authors,
      abstract: summary?.slice(0, 220) + (summary?.length > 220 ? '…' : ''),
      url:      id,
      arxivId,
      openAccess: true,
    };
  });
}

async function fetchArXivFullText(arxivId) {
  // Try PDF first
  const pdfUrl = `https://arxiv.org/pdf/${arxivId}.pdf`;
  c.info(`Fetching arXiv PDF: ${pdfUrl}`);
  try {
    const pdfRes = await fetch(pdfUrl, { headers: { 'User-Agent': 'graph-tool/2.0' } });
    if (pdfRes.ok) {
      const buf     = Buffer.from(await pdfRes.arrayBuffer());
      const tmpPath = path.join(__dirname, '.tmp_arxiv.pdf');
      fs.writeFileSync(tmpPath, buf);
      const text = await extractPDFText(tmpPath);
      fs.unlinkSync(tmpPath);
      return { text, url: pdfUrl, arxivId };
    }
  } catch(e) { c.warn(`PDF fetch failed: ${e.message}`); }

  // Fall back to abstract
  c.warn('Full text unavailable — using abstract');
  const res = await fetch(`https://export.arxiv.org/api/query?id_list=${arxivId}`);
  const xml = await res.text();
  const title   = xml.match(/<title>([\s\S]*?)<\/title>/)?.[1]?.trim();
  const summary = xml.match(/<summary>([\s\S]*?)<\/summary>/)?.[1]?.trim();
  return { text: `${title}\n\n${summary}`, url: `https://arxiv.org/abs/${arxivId}`, arxivId, abstractOnly: true };
}

// ── Semantic Scholar ───────────────────────────────────────────────────────
async function searchSemanticScholar(query, maxResults = 8) {
  const res = await fetch(
    `https://api.semanticscholar.org/graph/v1/paper/search?query=${encodeURIComponent(query)}&fields=title,abstract,year,authors,externalIds,openAccessPdf&limit=${maxResults}`,
    { headers: { 'User-Agent': 'graph-tool/2.0' } }
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.data || []).map(p => ({
    source:     'Semantic Scholar',
    title:      p.title,
    year:       p.year,
    authors:    (p.authors || []).map(a => a.name).join(', '),
    doi:        p.externalIds?.DOI,
    pmid:       p.externalIds?.PubMed,
    arxivId:    p.externalIds?.ArXiv,
    openAccess: !!p.openAccessPdf,
    pdfUrl:     p.openAccessPdf?.url,
    abstract:   p.abstract?.slice(0, 220) + (p.abstract?.length > 220 ? '…' : ''),
  }));
}

// ── DOI resolution ─────────────────────────────────────────────────────────
async function fetchByDOI(doi) {
  // 1. Unpaywall — find open-access PDF
  c.info(`Looking up open-access PDF via Unpaywall: ${doi}`);
  try {
    const res = await fetch(
      `https://api.unpaywall.org/v2/${encodeURIComponent(doi)}?email=graph-tool@example.com`
    );
    if (res.ok) {
      const data = await res.json();
      const oa   = data.best_oa_location;
      if (oa?.url_for_pdf) {
        c.info(`Open-access PDF found: ${oa.url_for_pdf}`);
        const pdfRes = await fetch(oa.url_for_pdf, { headers: { 'User-Agent': 'graph-tool/2.0' } });
        if (pdfRes.ok) {
          const buf     = Buffer.from(await pdfRes.arrayBuffer());
          const tmpPath = path.join(__dirname, '.tmp_doi.pdf');
          fs.writeFileSync(tmpPath, buf);
          const text = await extractPDFText(tmpPath);
          fs.unlinkSync(tmpPath);
          return { text, title: data.title, year: data.year, url: oa.url_for_pdf, doi };
        }
      }
      // Fall back to abstract via Semantic Scholar
      c.warn('No open-access PDF — fetching abstract from Semantic Scholar');
      return await fetchSemanticScholarByDOI(doi, data.title, data.year);
    }
  } catch(e) { c.warn(`Unpaywall error: ${e.message}`); }

  return await fetchSemanticScholarByDOI(doi);
}

async function fetchSemanticScholarByDOI(doi, title, year, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    const res = await fetch(
      `https://api.semanticscholar.org/graph/v1/paper/${encodeURIComponent(doi)}?fields=title,abstract,year,openAccessPdf`,
      { headers: { 'User-Agent': 'graph-tool/2.0' } }
    );
    if (res.status === 429) {
      const wait = attempt * 8;
      c.warn(`Semantic Scholar rate limited — waiting ${wait}s (attempt ${attempt}/${retries})…`);
      await new Promise(r => setTimeout(r, wait * 1000));
      continue;
    }
    if (!res.ok) throw new Error(`Semantic Scholar: ${res.status}`);
    const data = await res.json();
    const text = [data.title || title, data.abstract].filter(Boolean).join('\n\n');
    return {
      text,
      title:        data.title  || title,
      year:         data.year   || year,
      url:          data.openAccessPdf?.url || `https://doi.org/${doi}`,
      doi,
      abstractOnly: !data.openAccessPdf,
    };
  }
  throw new Error('Semantic Scholar rate limit exceeded after retries — try again in a minute');
}

// ── PDF text extraction ────────────────────────────────────────────────────
async function extractPDFText(filePath) {
  c.info(`Extracting text from PDF: ${path.basename(filePath)}`);
  const { default: pdfParse } = await import('pdf-parse');
  const buf  = fs.readFileSync(filePath);
  const data = await pdfParse(buf);
  c.ok(`Extracted ${data.text.length} characters`);
  return data.text;
}

// ── Paper weighting ────────────────────────────────────────────────────────

/**
 * Compute a single paperWeight scalar (0–1) from:
 *   - Publication type (journal, conf-full, conf-workshop, preprint, etc.)
 *   - Author position (first/shared-first, last, second, middle)
 *   - Recency (step function: 2020+=1.0, 2015-2019=0.8, <2015=0.6)
 *
 * This scalar is passed to Claude so it scales raw node weights,
 * and is also used during node accumulation in mergeIntoGraph.
 */
function computePaperWeight(meta) {
  // ── Publication type ────────────────────────────────────────────
  const typeWeights = {
    'journal':        1.00,
    'conf-full':      0.85,
    'conf-workshop':  0.65,
    'preprint':       0.70,
    'science-comm':   0.30,
    'other':          0.40,
  };
  const typeW = typeWeights[meta.pubType] ?? 0.50;

  // ── Author position ─────────────────────────────────────────────
  // position: 'first' | 'shared-first' | 'last' | 'second' | 'middle'
  const posWeights = {
    'first':        1.0,
    'shared-first': 1.0,
    'last':         0.8,
    'second':       0.6,
    'middle':       0.4,
  };
  const posW = posWeights[meta.authorPosition] ?? 0.5;

  // ── Recency ─────────────────────────────────────────────────────
  const year = parseInt(meta.year) || 2000;
  const recencyW = year >= 2020 ? 1.0 : year >= 2015 ? 0.8 : 0.6;

  const weight = typeW * posW * recencyW;
  return Math.round(weight * 100) / 100; // 2 decimal places
}

// ── Claude concept extraction ──────────────────────────────────────────────
async function extractConcepts(text, graph, paperWeight = 1.0) {
  const client      = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const existingIds = graph.nodes.map(n => n.id);
  const clusterGuide = graph.meta.clusters.map(c => `${c.id}=${c.name}`).join(', ');

  c.info(`Sending to Claude for concept extraction (paperWeight: ${paperWeight})…`);

  const response = await client.messages.create({
    model: 'claude-opus-4-5',
    max_tokens: 2000,
    system: `You are a research knowledge-graph builder. Extract key concepts (nodes) and theoretical relationships (edges) from academic paper text.

EXISTING NODE IDs — do NOT duplicate, but reference them freely in edges:
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
  "nodes": [{"id":"snake_case_max_3_words","label":"display\\nlabel","weight":0.0-1.0,"cluster":0-6}],
  "edges": [{"a":"node_id","b":"node_id","strength":0.0-1.0}],
  "paper": {"title":"...","year":2024,"venue":"...","doi":"..."}
}

Guidelines:
- Only NEW nodes not in the existing list above
- Edges may link new↔new or new↔existing nodes
- weight = raw centrality × paperWeight (already factored in above)
- strength = theoretical coupling tightness
- 5–20 nodes and 5–30 edges; quality over quantity
- label: use \\n to wrap if display text > 12 chars`,
    messages: [{ role: 'user', content: text.slice(0, 10000) }],
  });

  const raw   = response.content.map(b => b.text || '').join('');
  const clean = raw.replace(/```json|```/g, '').trim();
  return JSON.parse(clean);
}

// ── Graph merge ────────────────────────────────────────────────────────────
function mergeIntoGraph(graph, extracted, meta, paperWeight = 1.0) {
  const existingIds = new Set(graph.nodes.map(n => n.id));
  let newNodes = 0, newEdges = 0, boostedNodes = 0;

  (extracted.nodes || []).forEach(n => {
    // Clamp weight to valid range
    n.weight = Math.max(0.1, Math.min(1.0, n.weight));

    if (existingIds.has(n.id)) {
      // ── Accumulation: node already exists — boost its weight ──────────
      // Weighted average: existing weight gets 2/3 say, new evidence 1/3.
      // This means a concept appearing repeatedly across papers rises,
      // but a single low-weight paper can't dramatically change an
      // already well-established node.
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
      // Strengthen existing edge if this paper also asserts it
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
    title:            paper.title        || meta.title  || 'Unknown',
    year:             paper.year         || meta.year,
    venue:            paper.venue        || meta.venue,
    doi:              paper.doi          || meta.doi,
    arxivId:          meta.arxivId,
    url:              meta.url,
    abstractOnly:     meta.abstractOnly  || false,
    pubType:          meta.pubType,
    authorPosition:   meta.authorPosition,
    paperWeight,
    added:            new Date().toISOString(),
    nodesContributed: (extracted.nodes || []).map(n => n.id),
  });

  return { newNodes, newEdges, boostedNodes };
}

// ── Force layout ───────────────────────────────────────────────────────────
function rebuildLayout(graph) {
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

// ── Display helpers ────────────────────────────────────────────────────────
function printPaper(p, i) {
  c.log('');
  c.head(`${i != null ? i+'. ' : ''}${p.title || '(no title)'}`);
  const sources = p.sources?.length > 1 ? p.sources.join(', ') : (p.source || '');
  const meta = [sources, p.year, p.authors].filter(Boolean).join(' · ');
  if (meta) c.dim(`   ${meta}`);
  if (p.doi)        c.dim(`   DOI:   ${p.doi}`);
  if (p.pmid)       c.dim(`   PMID:  ${p.pmid}`);
  if (p.arxivId)    c.dim(`   arXiv: ${p.arxivId}`);
  if (p.openAccess) c.log(`   \x1b[32m[open access${p.pdfUrl ? ' — PDF available' : ''}]\x1b[0m`);
  if (p.abstract)   c.dim(`   ${p.abstract}`);
  // Best add command
  const addCmd = p.doi     ? `node index.js add --doi ${p.doi}` :
                 p.arxivId ? `node index.js add --url https://arxiv.org/abs/${p.arxivId}` :
                 p.pmid    ? `node index.js add --pmid ${p.pmid}` : null;
  if (addCmd) c.log(`   \x1b[2m→ ${addCmd}\x1b[0m`);
}

// ── Commands ───────────────────────────────────────────────────────────────

program.name('graph').description('Manage the research knowledge graph').version('2.0.0');

// ── orcid ──────────────────────────────────────────────────────────────────
program
  .command('orcid')
  .description(`Pull full publication list from ORCID (ID: ${ORCID_ID})`)
  .option('--id <id>', 'override ORCID ID')
  .option('--add-all', 'automatically add all papers not yet in graph')
  .action(async (opts) => {
    const id = opts.id || ORCID_ID;
    let works;
    try {
      works = await fetchORCIDWorks(id);
    } catch(e) {
      c.err(`ORCID fetch failed: ${e.message}`);
      process.exit(1);
    }

    c.ok(`Found ${works.length} works on ORCID\n`);
    const graph = loadGraph();
    const inGraph = new Set(
      (graph.meta.papers || []).map(p => p.doi).filter(Boolean)
    );

    const missing = works.filter(w => w.doi && !inGraph.has(w.doi));
    const noAccess = works.filter(w => !w.doi);

    works.forEach((w, i) => {
      const status = inGraph.has(w.doi) ? '\x1b[32m[in graph]\x1b[0m' : '\x1b[33m[not added]\x1b[0m';
      c.log(`${i+1}. ${w.title || '(no title)'}`);
      c.dim(`   ${w.year || '?'} · ${w.type || ''} · ${status}`);
      if (w.doi) c.dim(`   DOI: ${w.doi}  →  node index.js add --doi ${w.doi}`);
      else       c.dim(`   (no DOI — use node index.js add --text to paste manually)`);
      c.log('');
    });

    c.log(`\nSummary: ${inGraph.size} already in graph, ${missing.length} not yet added, ${noAccess.length} have no DOI`);
    if (missing.length) {
      c.log('\nTo add all missing papers:');
      missing.forEach(w => c.dim(`  node index.js add --doi ${w.doi}  # ${w.title?.slice(0,60)}`));
    }
  });

// ── search ─────────────────────────────────────────────────────────────────
program
  .command('search <query>')
  .description('Search PubMed, arXiv, and Semantic Scholar')
  .option('-a, --author <n>', 'filter by author name')
  .option('-n, --max <n>',    'max results per source', '5')
  .action(async (query, opts) => {
    const max = parseInt(opts.max);
    const q   = opts.author ? `${query} ${opts.author}` : query;
    const authorFilter = opts.author ? ` AND ${opts.author}[Author]` : '';

    const [pubmed, arxiv, ss] = await Promise.allSettled([
      searchPubMed(q + authorFilter, max),
      searchArXiv(q, max),
      searchSemanticScholar(q, max),
    ]);

    const raw = [
      ...(pubmed.status === 'fulfilled' ? pubmed.value : []),
      ...(arxiv.status  === 'fulfilled' ? arxiv.value  : []),
      ...(ss.status     === 'fulfilled' ? ss.value     : []),
    ];

    if (!raw.length) { c.warn('No results found.'); return; }

    const results = deduplicateResults(raw);
    const graph   = loadGraph();

    c.log(`\nFound ${results.length} unique papers (from ${raw.length} raw results):\n`);
    results.forEach((r, i) => {
      const dup = findDuplicate(graph, r);
      if (dup.duplicate) {
        c.log(`\x1b[2m${i+1}. ${r.title || '(no title)'}\x1b[0m \x1b[32m[already in graph — ${dup.reason}]\x1b[0m`);
      } else {
        printPaper(r, i+1);
      }
    });
  });

// ── add ────────────────────────────────────────────────────────────────────
program
  .command('add')
  .description('Add a paper to the graph')
  .option('--pdf <path>',            'local PDF file')
  .option('--doi <doi>',             'DOI')
  .option('--url <url>',             'arXiv or PubMed URL')
  .option('--pmid <id>',             'PubMed ID')
  .option('--text',                  'paste text via stdin (end with Ctrl+D)')
  .option('--title <t>',             'override paper title')
  .option('--year <y>',              'publication year')
  .option('--venue <v>',             'journal or conference name')
  .option('--pub-type <type>',       'journal | conf-full | conf-workshop | preprint | science-comm | other')
  .option('--author-pos <pos>',      'first | shared-first | last | second | middle')
  .option('--force',                 'overwrite existing entry if already in graph')
  .option('--dry-run',               'extract without saving')
  .action(async (opts) => {
    if (!process.env.ANTHROPIC_API_KEY) {
      c.err('ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.');
      process.exit(1);
    }

    let source = {};

    try {
      if (opts.pdf) {
        source.text = await extractPDFText(opts.pdf);
        source.url  = opts.pdf;
      } else if (opts.doi) {
        source = await fetchByDOI(opts.doi);
      } else if (opts.pmid) {
        c.info(`Fetching PubMed full text: ${opts.pmid}`);
        source = await fetchPubMedFull(opts.pmid);
        if (!source.url) source.url = `https://pubmed.ncbi.nlm.nih.gov/${opts.pmid}/`;
      } else if (opts.url) {
        const arxivMatch = opts.url.match(/arxiv\.org\/(?:abs|pdf)\/(\d+\.\d+)/);
        const pmidMatch  = opts.url.match(/pubmed\.ncbi\.nlm\.nih\.gov\/(\d+)/);
        if (arxivMatch) {
          source = await fetchArXivFullText(arxivMatch[1]);
        } else if (pmidMatch) {
          source = await fetchPubMedFull(pmidMatch[1]);
        } else {
          c.err('URL not recognised as arXiv or PubMed. Use --doi or --pdf instead.');
          process.exit(1);
        }
      } else if (opts.text) {
        c.info('Paste paper text, then press Ctrl+D:');
        const chunks = [];
        for await (const chunk of process.stdin) chunks.push(chunk);
        source.text = Buffer.concat(chunks).toString();
      } else {
        c.err('Specify one of: --pdf, --doi, --url, --pmid, --text');
        process.exit(1);
      }
    } catch(e) {
      c.err(`Failed to fetch paper: ${e.message}`);
      process.exit(1);
    }

    if (!source.text?.trim()) {
      c.err('No text extracted from source.');
      process.exit(1);
    }

    c.info(`${source.text.length} chars extracted`);
    if (source.abstractOnly) {
      c.warn('Abstract only (full text not available open-access)');
    } else if (source.text.length < 3000) {
      c.warn(`⚠ Thin text (${source.text.length} chars) — likely abstract-only despite no flag`);
      c.warn('  Consider finding the PDF and re-running with --pdf sources/<file>.pdf --force');
    }

    const graph = loadGraph();

    // ── Duplicate check ──────────────────────────────────────────────────
    const candidateMeta = {
      doi:      opts.doi   || source.doi,
      arxivId:  source.arxivId,
      title:    opts.title || source.title,
    };
    const dup = findDuplicate(graph, candidateMeta);
    if (dup.duplicate) {
      const isPreprint = dup.match.arxivId && !dup.match.doi && candidateMeta.doi;
      if (opts.force) {
        // Remove the paper record only — keep all nodes intact.
        // Re-extraction will boost existing nodes and add any new ones.
        c.warn(`  --force: re-processing "${dup.match.title}" (${dup.reason})`);
        const oldIdx = graph.meta.papers.findIndex(p => p.id === dup.match.id);
        if (oldIdx !== -1) graph.meta.papers.splice(oldIdx, 1);
        c.info(`  Paper record removed — nodes kept, will be boosted by re-extraction`);
        // Fall through to re-extraction below
      } else if (isPreprint) {
        // arXiv preprint → published journal version: update metadata only
        const updated = updateExistingPaper(graph, dup.match, {
          doi:      candidateMeta.doi,
          venue:    opts.venue,
          year:     opts.year ? parseInt(opts.year) : source.year,
          url:      source.url,
        });
        if (updated) {
          saveGraph(graph);
          c.ok(`Updated existing preprint entry "${dup.match.title}" with journal metadata (${dup.reason})`);
        } else {
          c.warn(`Already in graph as "${dup.match.title}" (${dup.reason}) — nothing new to update`);
        }
        return;
      } else {
        c.warn(`Already in graph: "${dup.match.title}" (${dup.reason}) — skipping`);
        c.warn(`Use --force to overwrite`);
        return;
      }
    }

    // ── Compute paper weight ─────────────────────────────────────────────
    const paperWeight = computePaperWeight({
      pubType:        opts.pubType   || 'journal',
      authorPosition: opts.authorPos || 'middle',
      year:           opts.year      || source.year,
    });
    c.info(`Paper weight: ${paperWeight} (type:${opts.pubType||'journal'} × pos:${opts.authorPos||'middle'} × year:${opts.year||source.year||'?'})`);

    let extracted;
    try {
      extracted = await extractConcepts(source.text, graph, paperWeight);
    } catch(e) {
      c.err(`Concept extraction failed: ${e.message}`);
      process.exit(1);
    }

    c.log('');
    c.ok(`Extracted ${extracted.nodes?.length || 0} new nodes, ${extracted.edges?.length || 0} new edges`);
    if (extracted.paper?.title) c.ok(`Paper identified: ${extracted.paper.title}`);

    if (extracted.nodes?.length) {
      c.log('\nNew nodes:');
      extracted.nodes.forEach(n =>
        c.log(`  \x1b[32m+\x1b[0m ${n.id.padEnd(28)} cluster:${n.cluster}  weight:${n.weight}`)
      );
    }

    if (opts.dryRun) { c.warn('\nDry run — nothing saved.'); return; }

    const meta = {
      title:          opts.title    || source.title,
      year:           opts.year     ? parseInt(opts.year) : source.year,
      venue:          opts.venue,
      doi:            opts.doi      || source.doi,
      arxivId:        source.arxivId,
      url:            source.url,
      abstractOnly:   source.abstractOnly,
      pubType:        opts.pubType  || 'journal',
      authorPosition: opts.authorPos || 'middle',
    };

    const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, extracted, meta, paperWeight);
    rebuildLayout(graph);
    saveGraph(graph);
    c.log('');
    c.ok(`Saved. Graph: ${graph.nodes.length} nodes, ${graph.edges.length} edges`);
    c.ok(`Added ${newNodes} new nodes, ${newEdges} new edges, boosted ${boostedNodes} existing nodes`);
  });

// ── list ───────────────────────────────────────────────────────────────────
program
  .command('list')
  .description('List all papers in the graph')
  .action(() => {
    const graph = loadGraph();
    const papers = graph.meta.papers || [];
    if (!papers.length) { c.log('No papers added yet.'); return; }
    c.log(`\n${papers.length} papers in graph:\n`);
    papers.forEach((p, i) => {
      c.head(`${i+1}. ${p.title}`);
      c.dim(`   ${p.year||'?'} · ${p.venue||''}`);
      if (p.doi) c.dim(`   DOI: ${p.doi}`);
      if (p.abstractOnly) c.log(`   \x1b[33m[abstract only]\x1b[0m`);
      c.dim(`   Nodes: ${(p.nodesContributed||[]).join(', ') || '—'}`);
      c.log('');
    });
  });

// ── stats ──────────────────────────────────────────────────────────────────
program
  .command('stats')
  .description('Graph statistics')
  .action(() => {
    const g = loadGraph();
    c.log('\nGraph stats:');
    c.log(`  Nodes:  ${g.nodes.length}`);
    c.log(`  Edges:  ${g.edges.length}`);
    c.log(`  Papers: ${(g.meta.papers||[]).length}`);
    c.log('\nNodes by cluster:');
    const counts = {};
    g.nodes.forEach(n => { counts[n.cluster] = (counts[n.cluster]||0)+1; });
    g.meta.clusters.forEach(cl => c.log(`  [${cl.id}] ${cl.name}: ${counts[cl.id]||0}`));
    const deg = {};
    g.edges.forEach(e => { deg[e.a]=(deg[e.a]||0)+1; deg[e.b]=(deg[e.b]||0)+1; });
    const top = Object.entries(deg).sort((a,b)=>b[1]-a[1]).slice(0,8);
    c.log('\nTop nodes by degree:');
    top.forEach(([id,d]) => c.log(`  ${id.padEnd(28)} ${d} connections`));
  });

// ── rebuild ────────────────────────────────────────────────────────────────
program
  .command('rebuild')
  .description('Re-run force layout and save graph.json')
  .action(() => {
    const graph = loadGraph();
    rebuildLayout(graph);
    saveGraph(graph);
    c.ok(`Layout rebuilt for ${graph.nodes.length} nodes. graph.json saved.`);
  });

// ── import-cv ──────────────────────────────────────────────────────────────
program
  .command('import-cv')
  .description('Parse a CV PDF and batch-import all papers into the graph')
  .option('--pdf <path>', 'path to CV PDF (required)')
  .option('--dry-run',    'extract and plan without saving anything')
  .option('--delay <ms>', 'ms to wait between papers (default 3000)', '3000')
  .action(async (opts) => {
    if (!process.env.ANTHROPIC_API_KEY) {
      c.err('ANTHROPIC_API_KEY not set.');
      process.exit(1);
    }
    if (!opts.pdf) {
      c.err('--pdf <path> is required');
      process.exit(1);
    }

    const cvPath = path.resolve(opts.pdf);
    if (!fs.existsSync(cvPath)) {
      c.err(`CV file not found: ${cvPath}`);
      process.exit(1);
    }

    const delay = ms => new Promise(r => setTimeout(r, ms));
    const delayMs = parseInt(opts.delay);

    // ── Step 1: Extract CV text and parse paper list via Claude ────────────
    c.head('\nStep 1: Parsing CV with Claude…');
    const cvText = await extractPDFText(cvPath);

    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    const parseRes = await client.messages.create({
      model: 'claude-opus-4-5',
      max_tokens: 4000,
      system: `You are parsing an academic CV to extract a complete publication list.

For each paper, extract:
- title: full title
- doi: DOI if present (clean, no URL prefix like https://doi.org/)
- arxivId: arXiv ID if present (e.g. "2602.06197" from arxiv.org/abs/2602.06197 or DOI 10.48550/arXiv.XXXX)
- osf: OSF URL if present (e.g. "https://osf.io/xd9mk/")
- year: publication year (integer)
- venue: journal or conference name
- pubType: one of journal | conf-full | conf-workshop | preprint | science-comm | other
  - Use section headings:
    - "Peer-Reviewed Journal Publications" → journal
    - "Peer-Reviewed Conference Proceedings" → conf-full
      EXCEPT: if the venue contains "Workshop", "Adjunct", or "W@" → conf-workshop
    - "Preprints & Working Papers" → preprint
    - "Science Communication" → science-comm
- authorPosition: one of first | shared-first | last | second | middle
  - Look for "Hakimi, S" or "Hakimi S" or "Hakimi" in the author list
  - If marked with * (equal contribution) AND Hakimi is listed first or second → shared-first
  - If Hakimi is the very last author listed → last
  - If Hakimi is second in the list → second
  - If Hakimi is first (not shared) → first
  - Otherwise → middle
  - NOTE: "others, including Hakimi" or similar phrasing → middle

Return ONLY valid JSON, no markdown fences:
{
  "papers": [
    {
      "title": "...",
      "doi": "...",
      "arxivId": "...",
      "osf": "...",
      "year": 2024,
      "venue": "...",
      "pubType": "journal",
      "authorPosition": "first"
    }
  ]
}

Include ALL papers across ALL sections. Do not skip any.
For doi: if the paper has a DOI like 10.48550/arXiv.2602.06197, include it as the doi AND extract "2602.06197" as the arxivId.
Leave fields null if not present.`,
      messages: [{ role: 'user', content: cvText.slice(0, 15000) }],
    });

    let cvPapers;
    try {
      const raw   = parseRes.content.map(b => b.text||'').join('');
      const clean = raw.replace(/```json|```/g,'').trim();
      cvPapers    = JSON.parse(clean).papers;
    } catch(e) {
      c.err(`Failed to parse CV response: ${e.message}`);
      process.exit(1);
    }

    c.ok(`Found ${cvPapers.length} papers in CV`);
    c.log('');

    // ── Step 2: Plan — show what will be added, skipped, or looked up ──────
    c.head('Step 2: Checking against existing graph…');
    const graph = loadGraph();

    const toAdd    = [];
    const skipped  = [];
    const noDOI    = [];

    for (const p of cvPapers) {
      const dup = findDuplicate(graph, p);
      if (dup.duplicate) {
        skipped.push({ paper: p, reason: dup.reason });
      } else if (!p.doi && !p.arxivId && !p.osf) {
        noDOI.push(p);
      } else {
        toAdd.push(p);
      }
    }

    c.log(`  → ${toAdd.length} to add`);
    c.log(`  → ${skipped.length} already in graph`);
    c.log(`  → ${noDOI.length} have no DOI or arXiv ID (will attempt title search)`);

    if (noDOI.length) {
      c.log('\nPapers with no identifier (will try Semantic Scholar title search):');
      noDOI.forEach(p => c.dim(`   • ${p.title}`));
      for (const p of noDOI) {
        try {
          await delay(1500);
          const q   = encodeURIComponent(p.title);
          const res = await fetch(
            `https://api.semanticscholar.org/graph/v1/paper/search?query=${q}&fields=title,externalIds&limit=1`,
            { headers: { 'User-Agent': 'graph-tool/2.0' } }
          );
          if (res.ok) {
            const data = await res.json();
            const hit  = data.data?.[0];
            if (hit?.externalIds?.DOI) {
              p.doi = hit.externalIds.DOI;
              c.ok(`  Resolved DOI for "${p.title.slice(0,55)}…": ${p.doi}`);
              toAdd.push(p);
              continue;
            }
            if (hit?.externalIds?.ArXiv) {
              p.arxivId = hit.externalIds.ArXiv;
              c.ok(`  Resolved arXiv for "${p.title.slice(0,55)}…": ${p.arxivId}`);
              toAdd.push(p);
              continue;
            }
          }
        } catch(e) { /* skip */ }
        c.warn(`  Could not resolve: ${p.title.slice(0,60)}…`);
        p._unresolved = true;
      }
    }

    if (opts.dryRun) {
      c.warn('\nDry run — nothing saved. Papers that would be added:');
      toAdd.forEach((p, i) => {
        const pw = computePaperWeight(p);
        c.log(`  ${i+1}. [w=${pw}] ${p.title.slice(0,70)}`);
      });
      return;
    }

    // ── Step 3: Batch add ──────────────────────────────────────────────────
    c.head(`\nStep 3: Adding ${toAdd.length} papers…`);
    c.log('');

    const results = {
      added:       [],
      fullText:    [],
      abstractOnly:[],
      thinText:    [],
      failed:      [],
    };

    for (let i = 0; i < toAdd.length; i++) {
      const p  = toAdd[i];
      const pw = computePaperWeight(p);
      c.head(`[${i+1}/${toAdd.length}] ${p.title.slice(0,70)}`);
      c.dim(`  type:${p.pubType} · pos:${p.authorPosition} · year:${p.year} · weight:${pw}`);

      // Fetch text
      let source;
      try {
        if (p.doi && p.doi.includes('10.48550/arXiv.') || p.arxivId) {
          // arXiv paper — fetch via arXiv
          const arxivId = p.arxivId || p.doi.replace('10.48550/arXiv.','');
          source = await fetchArXivFullText(arxivId);
        } else if (p.doi) {
          source = await fetchByDOI(p.doi);
        } else if (p.osf) {
          // OSF preprint — just use abstract from Semantic Scholar title search
          c.warn('  OSF preprint — fetching abstract via title search');
          const q   = encodeURIComponent(p.title);
          const res = await fetch(
            `https://api.semanticscholar.org/graph/v1/paper/search?query=${q}&fields=title,abstract,year&limit=1`,
            { headers: { 'User-Agent': 'graph-tool/2.0' } }
          );
          if (res.ok) {
            const data = await res.json();
            const hit  = data.data?.[0];
            if (hit?.abstract) {
              source = { text: `${hit.title}\n\n${hit.abstract}`, year: hit.year || p.year, abstractOnly: true, url: p.osf };
            }
          }
          if (!source) throw new Error('No abstract found');
        } else {
          throw new Error('No identifier');
        }
      } catch(e) {
        c.warn(`  Fetch failed: ${e.message} — skipping`);
        results.failed.push({ paper: p, reason: e.message });
        await delay(delayMs);
        continue;
      }

      // ── Text quality check ───────────────────────────────────────────
      const THIN_TEXT_THRESHOLD = 3000; // chars — below this is likely abstract-length
      const isThin = !source.abstractOnly && source.text.length < THIN_TEXT_THRESHOLD;

      if (source.abstractOnly) {
        c.warn('  Abstract only');
        results.abstractOnly.push({ paper: p, chars: source.text.length });
      } else if (isThin) {
        c.warn(`  ⚠ Thin text (${source.text.length} chars) — likely abstract-only despite no flag`);
        results.thinText.push({ paper: p, chars: source.text.length });
      } else {
        c.ok(`  Full text: ${source.text.length} chars`);
        results.fullText.push(p.title);
      }

      // Dedup check (in case something resolved mid-run)
      const dup = findDuplicate(graph, { doi: p.doi, title: p.title });
      if (dup.duplicate) {
        c.warn(`  Duplicate detected mid-run (${dup.reason}) — skipping`);
        await delay(delayMs);
        continue;
      }

      // Extract concepts
      let extracted;
      try {
        extracted = await extractConcepts(source.text, graph, pw);
      } catch(e) {
        c.warn(`  Extraction failed: ${e.message}`);
        results.failed.push({ paper: p, reason: e.message });
        await delay(delayMs);
        continue;
      }

      // Merge
      const meta = {
        title:          source.title || p.title,
        year:           source.year  || p.year,
        venue:          p.venue,
        doi:            p.doi,
        arxivId:        source.arxivId,
        url:            source.url,
        abstractOnly:   source.abstractOnly || false,
        pubType:        p.pubType,
        authorPosition: p.authorPosition,
      };

      const { newNodes, newEdges, boostedNodes } = mergeIntoGraph(graph, extracted, meta, pw);
      rebuildLayout(graph);
      saveGraph(graph);

      results.added.push(p.title);
      c.ok(`  +${newNodes} nodes, +${newEdges} edges, ↑${boostedNodes} boosted — graph: ${graph.nodes.length} nodes`);
      c.log('');

      // Polite delay between papers
      if (i < toAdd.length - 1) await delay(delayMs);
    }

    // ── Step 4: Summary report ─────────────────────────────────────────────
    c.head('\n── Import complete ──────────────────────────────────');
    c.log(`  Added:        ${results.added.length} papers`);
    c.log(`  Full text:    ${results.fullText.length}`);
    c.log(`  Thin text:    ${results.thinText.length} ⚠`);
    c.log(`  Abstract only:${results.abstractOnly.length}`);
    c.log(`  Failed:       ${results.failed.length}`);
    c.log(`  Skipped:      ${skipped.length} (already in graph)`);
    c.log(`  Graph now:    ${graph.nodes.length} nodes, ${graph.edges.length} edges`);

    if (results.thinText.length) {
      c.log('\n⚠  Thin text — full PDF needed for good extraction:');
      c.log('   Drop PDFs in sources/ then re-add with --force:\n');
      results.thinText.forEach(({paper, chars}) => {
        const flag = `--pub-type ${paper.pubType} --author-pos ${paper.authorPosition}`;
        c.log(`   # ${paper.title.slice(0,65)} (${chars} chars)`);
        if (paper.doi) {
          c.log(`   node index.js add --pdf sources/<file>.pdf ${flag} --force`);
        }
        c.log('');
      });
    }

    if (results.abstractOnly.length) {
      c.log('\nAbstract only — consider adding PDFs manually:');
      results.abstractOnly.forEach(({paper, chars}) => {
        c.log(`  • ${paper.title.slice(0,70)} (${chars} chars)`);
      });
    }

    if (results.failed.length) {
      c.log('\nFailed — add these manually:');
      results.failed.forEach(({paper, reason}) =>
        c.log(`  • ${paper.title.slice(0,60)} — ${reason}`)
      );
    }
  });

program.parse();
