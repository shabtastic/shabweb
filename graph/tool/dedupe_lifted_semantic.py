#!/usr/bin/env python3
"""
dedupe_lifted_semantic.py — Second-pass sibling dedup for graph/lift-output.json,
catching semantic duplicates that lift_concepts.js's literal source-candidate-
overlap check (dedupeSiblingNodes in lift_concepts.js) can't see — two new
nodes from the same paper describing the same concept via disjoint phrasing
(e.g. "reward magnitude" vs "payoff size") share zero source candidates but
should still merge.

Run AFTER lift_concepts.js, before promote_lift_output.js.

Usage:
    python3 dedupe_lifted_semantic.py [--threshold 0.8]
"""
import json
import os
import re
import sys
import argparse

from sentence_transformers import SentenceTransformer
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIFT_OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'lift-output.json')


def clean_label(label):
    return re.sub(r'\s+', ' ', label.replace('\n', ' ')).strip()


def merge_pair(keep, dupe):
    keep_srcs = set(keep.get('source_candidates') or [])
    dupe_srcs = set(dupe.get('source_candidates') or [])
    keep['source_candidates'] = list(keep_srcs | dupe_srcs)


def dedupe_paper(paper_result, model, threshold):
    nodes = paper_result.get('nodes') or []
    new_nodes = [n for n in nodes if not n.get('reuse_existing') or n.get('reuse_existing') == 'null']
    if len(new_nodes) < 2:
        return 0

    labels = [clean_label(n['label']) for n in new_nodes]
    embs = model.encode(labels, show_progress_bar=False)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    embs_normed = embs / (norms + 1e-9)
    sims = embs_normed @ embs_normed.T

    # Union-find over pairs above threshold (same merge strategy as the JS
    # literal-overlap version: bigger source_candidates list wins).
    parent = {n['id']: n['id'] for n in new_nodes}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    n = len(new_nodes)
    merge_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= threshold:
                union(new_nodes[i]['id'], new_nodes[j]['id'])

    groups = {}
    for node in new_nodes:
        root = find(node['id'])
        groups.setdefault(root, []).append(node)

    id_remap = {}
    survivors = []
    for group in groups.values():
        if len(group) == 1:
            survivors.append(group[0])
            continue
        group.sort(key=lambda n: len(n.get('source_candidates') or []), reverse=True)
        keep = group[0]
        for dupe in group[1:]:
            print(f'    merged semantic sibling "{dupe["id"]}" into "{keep["id"]}"', file=sys.stderr)
            merge_pair(keep, dupe)
            id_remap[dupe['id']] = keep['id']
            merge_count += 1
        survivors.append(keep)

    reuse_nodes = [n for n in nodes if n.get('reuse_existing') and n.get('reuse_existing') != 'null']
    paper_result['nodes'] = survivors + reuse_nodes
    for e in paper_result.get('edges') or []:
        e['a'] = id_remap.get(e['a'], e['a'])
        e['b'] = id_remap.get(e['b'], e['b'])
    paper_result['edges'] = [e for e in (paper_result.get('edges') or []) if e['a'] != e['b']]

    return merge_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.8)
    args = parser.parse_args()

    with open(LIFT_OUTPUT_PATH) as f:
        results = json.load(f)

    print('Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    total_merges = 0
    for paper_id, paper_result in results.items():
        if 'error' in paper_result:
            continue
        merges = dedupe_paper(paper_result, model, args.threshold)
        total_merges += merges
        if merges:
            print(f'  {paper_id} — {merges} semantic merge(s)', file=sys.stderr)

    with open(LIFT_OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\n{total_merges} total semantic sibling merges across all papers.', file=sys.stderr)
    print(f'Updated {LIFT_OUTPUT_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
