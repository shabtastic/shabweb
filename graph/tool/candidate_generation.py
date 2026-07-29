#!/usr/bin/env python3
"""
candidate_generation.py — KeyBERT-style candidate concept generation.

For each corpus-matched graph paper's full-text extraction
(research-corpus/vault/extracted-full/<sha>.txt), generates candidate
1-3 word phrases via frequency-filtered n-gram extraction, then ranks
them by cosine similarity to a chunk-pooled whole-document embedding
(all-MiniLM-L6-v2 has a 256-token window, so a single document-level
embedding requires mean-pooling over overlapping chunks, not one shot).

Output: graph/candidates.json — top-N ranked candidates per paper, for
manual inspection before the LLM lifting step (nothing here touches
graph.json).

Usage:
    python3 candidate_generation.py [--top-n 40] [--limit N]
"""
import json
import os
import re
import sys
import argparse
from collections import Counter

from sentence_transformers import SentenceTransformer
import numpy as np

HOME = os.environ['HOME']
CORPUS_REPO = os.environ.get('CORPUS_REPO', os.path.join(HOME, 'projects/research-corpus'))
FULLTEXT_DIR = os.path.join(CORPUS_REPO, 'vault', 'extracted-full')
CATALOG_PATH = os.path.join(CORPUS_REPO, 'corpus-catalog.json')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBS_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'data', 'publications.json')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'candidates.json')

PRESENTATION_TYPES = {'talk', 'poster', 'symposium', 'invited-talk'}
EXCLUDED_KEYWORDS = {'scicomm', 'commentary', 'unlisted'}

CHUNK_WORDS = 150
MIN_FREQ = 2
MAX_NGRAM = 3

STOPWORDS = set("""
a an the of and to in on for from with at by as is are this that it its what
how why when where about into onto via using use can may do does vs versus
we our us they their them he she his her i you your not no yes if then than
also however therefore thus while because since between among across within
such other another each all both either neither more most less least very
one two three first second third study studies participants participant
paper article research results result finding findings method methods
discussion introduction conclusion conclusions abstract figure figures
table tables supplementary appendix et al fig eq ref refs section
data analysis analyses significant significantly effect effects p value
were was been being have has had would could should might will shall
et al doi http https www com org edu supplement supplementary note notes
keyword keywords index terms author authors affiliation correspondence
""".split())

CAND_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]{1,}")


def load_universe():
    with open(PUBS_PATH) as f:
        pubs = json.load(f)
    with open(CATALOG_PATH) as f:
        catalog = json.load(f)['entries']

    papers = []
    for pub in pubs:
        kw = set(pub.get('keywords') or [])
        if kw & EXCLUDED_KEYWORDS:
            continue
        if pub.get('pubType') in PRESENTATION_TYPES:
            continue
        entry = catalog.get(pub['id'])
        if not entry:
            continue
        if entry.get('acquisition', {}).get('next_action') != 'have_local':
            continue
        sha = (entry.get('final_output') or {}).get('sha')
        if not sha:
            continue
        papers.append({**pub, 'sha': sha})
    papers.sort(key=lambda p: p['id'])
    return papers


def author_surnames(pub):
    surnames = set()
    for a in pub.get('authors') or []:
        last = a.split(',')[0].strip().lower()
        for part in re.split(r'[\s\-]+', last):
            if len(part) >= 3:
                surnames.add(part)
    return surnames


def tokenize(text):
    return [m.group(0).lower() for m in CAND_RE.finditer(text)]


def generate_ngrams(tokens, banned):
    counts = Counter()
    n = len(tokens)
    for i in range(n):
        if tokens[i] in STOPWORDS or tokens[i] in banned or len(tokens[i]) < 3:
            continue
        for size in range(1, MAX_NGRAM + 1):
            if i + size > n:
                break
            window = tokens[i:i + size]
            if window[-1] in STOPWORDS or window[-1] in banned or len(window[-1]) < 3:
                continue
            if any(w in banned for w in window):
                continue
            phrase = ' '.join(window)
            counts[phrase] += 1
    return counts


def chunk_document_embedding(model, text):
    words = text.split()
    if not words:
        return None
    chunks = [' '.join(words[i:i + CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]
    embeddings = model.encode(chunks, show_progress_bar=False, batch_size=32)
    return np.mean(embeddings, axis=0)


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top-n', type=int, default=40)
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()

    papers = load_universe()
    if args.limit:
        papers = papers[:args.limit]

    print(f'Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    results = {}
    for i, pub in enumerate(papers):
        txt_path = os.path.join(FULLTEXT_DIR, f"{pub['sha']}.txt")
        if not os.path.exists(txt_path):
            print(f'  [{i+1}/{len(papers)}] {pub["id"]} — SKIP (no full-text extraction)', file=sys.stderr)
            continue

        with open(txt_path) as f:
            text = f.read()

        banned = author_surnames(pub)
        tokens = tokenize(text)
        ngram_counts = generate_ngrams(tokens, banned)
        survivors = {p: c for p, c in ngram_counts.items() if c >= MIN_FREQ}

        if not survivors:
            print(f'  [{i+1}/{len(papers)}] {pub["id"]} — 0 candidates survived frequency filter', file=sys.stderr)
            results[pub['id']] = []
            continue

        doc_emb = chunk_document_embedding(model, text)
        candidates = list(survivors.keys())
        cand_embs = model.encode(candidates, show_progress_bar=False, batch_size=64)

        scored = [
            {'phrase': c, 'freq': survivors[c], 'score': round(cosine(doc_emb, e), 4)}
            for c, e in zip(candidates, cand_embs)
        ]
        scored.sort(key=lambda x: x['score'], reverse=True)
        top = scored[:args.top_n]

        results[pub['id']] = top
        print(f'  [{i+1}/{len(papers)}] {pub["id"]} — {len(survivors)} candidates → top {len(top)}', file=sys.stderr)

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nWrote {OUTPUT_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
