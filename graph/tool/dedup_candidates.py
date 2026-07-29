#!/usr/bin/env python3
"""
dedup_candidates.py — Score each Phase 2 candidate against the existing
352-node graph via embedding similarity, so the lifting step gets a real
number ("87% similar to existing node risk_perception") instead of an LLM
eyeballing a 352-item ID list and hoping it notices a near-synonym.

Reads graph/candidates.json (from candidate_generation.py) and graph/graph.json,
writes graph/candidates.json in place with a `nearest_existing` field added
to every candidate.

Usage:
    python3 dedup_candidates.py [--threshold 0.75]
"""
import json
import os
import re
import sys
import argparse

from sentence_transformers import SentenceTransformer
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PATH = os.path.join(SCRIPT_DIR, '..', 'graph.json')
CANDIDATES_PATH = os.path.join(SCRIPT_DIR, '..', 'candidates.json')


def clean_label(label):
    return re.sub(r'\s+', ' ', label.replace('\n', ' ')).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.75)
    args = parser.parse_args()

    with open(GRAPH_PATH) as f:
        graph = json.load(f)
    with open(CANDIDATES_PATH) as f:
        candidates_by_paper = json.load(f)

    nodes = graph['nodes']
    print(f'Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    node_labels = [clean_label(n['label']) for n in nodes]
    node_embs = model.encode(node_labels, show_progress_bar=False, batch_size=64)
    node_norms = np.linalg.norm(node_embs, axis=1, keepdims=True)
    node_embs_normed = node_embs / (node_norms + 1e-9)

    likely_dupe = 0
    total = 0
    for paper_id, cands in candidates_by_paper.items():
        if not cands:
            continue
        phrases = [c['phrase'] for c in cands]
        cand_embs = model.encode(phrases, show_progress_bar=False, batch_size=64)
        cand_norms = np.linalg.norm(cand_embs, axis=1, keepdims=True)
        cand_embs_normed = cand_embs / (cand_norms + 1e-9)

        sims = cand_embs_normed @ node_embs_normed.T  # [n_candidates, n_nodes]
        best_idx = np.argmax(sims, axis=1)
        best_sim = sims[np.arange(len(phrases)), best_idx]

        for c, idx, sim in zip(cands, best_idx, best_sim):
            c['nearest_existing'] = {
                'id': nodes[idx]['id'],
                'label': node_labels[idx],
                'similarity': round(float(sim), 4),
                'likely_duplicate': bool(sim >= args.threshold),
            }
            total += 1
            if sim >= args.threshold:
                likely_dupe += 1

    with open(CANDIDATES_PATH, 'w') as f:
        json.dump(candidates_by_paper, f, indent=2)

    print(f'\nScored {total} candidates against {len(nodes)} existing nodes.', file=sys.stderr)
    print(f'{likely_dupe} flagged as likely duplicates (similarity >= {args.threshold}).', file=sys.stderr)
    print(f'Updated {CANDIDATES_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
