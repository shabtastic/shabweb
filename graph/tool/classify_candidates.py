#!/usr/bin/env python3
"""
classify_candidates.py — Assign cluster + abstraction level to each
candidate via k-NN against the existing 352 graph nodes' embeddings,
weighted by similarity. No LLM: both fields are already present on every
existing node, so this is a closed classification problem, not generation.

Reads/writes graph/candidates.json in place, adding `predicted_cluster`
and `predicted_level` (each with a confidence score) to every candidate.

Usage:
    python3 classify_candidates.py [--k 8]
"""
import json
import os
import re
import sys
import argparse
from collections import defaultdict

from sentence_transformers import SentenceTransformer
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PATH = os.path.join(SCRIPT_DIR, '..', 'graph.json')
CANDIDATES_PATH = os.path.join(SCRIPT_DIR, '..', 'candidates.json')


def clean_label(label):
    return re.sub(r'\s+', ' ', label.replace('\n', ' ')).strip()


def weighted_vote(sims, labels, k):
    """Top-k neighbors by similarity, vote weighted by similarity score.
    Returns (winning_label, confidence) where confidence is the winner's
    vote share among the k neighbors (0-1)."""
    top_idx = np.argsort(sims)[-k:]
    votes = defaultdict(float)
    for i in top_idx:
        votes[labels[i]] += sims[i]
    total = sum(votes.values())
    winner = max(votes, key=votes.get)
    confidence = votes[winner] / total if total > 0 else 0.0
    return winner, round(float(confidence), 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--k', type=int, default=8)
    args = parser.parse_args()

    with open(GRAPH_PATH) as f:
        graph = json.load(f)
    with open(CANDIDATES_PATH) as f:
        candidates_by_paper = json.load(f)

    nodes = graph['nodes']
    cluster_names = {c['id']: c['name'] for c in graph['meta']['clusters']}

    print('Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    node_labels = [clean_label(n['label']) for n in nodes]
    node_clusters = [n['cluster'] for n in nodes]
    node_levels = [n['level'] for n in nodes]
    node_embs = model.encode(node_labels, show_progress_bar=False, batch_size=64)
    node_embs_normed = node_embs / (np.linalg.norm(node_embs, axis=1, keepdims=True) + 1e-9)

    total = 0
    for paper_id, cands in candidates_by_paper.items():
        if not cands:
            continue
        phrases = [c['phrase'] for c in cands]
        cand_embs = model.encode(phrases, show_progress_bar=False, batch_size=64)
        cand_embs_normed = cand_embs / (np.linalg.norm(cand_embs, axis=1, keepdims=True) + 1e-9)

        sims_matrix = cand_embs_normed @ node_embs_normed.T  # [n_candidates, n_nodes]

        for c, sims in zip(cands, sims_matrix):
            cluster_id, cluster_conf = weighted_vote(sims, node_clusters, args.k)
            level, level_conf = weighted_vote(sims, node_levels, args.k)
            c['predicted_cluster'] = {'id': int(cluster_id), 'name': cluster_names.get(cluster_id, '?'), 'confidence': cluster_conf}
            c['predicted_level'] = {'value': level, 'confidence': level_conf}
            total += 1

        print(f'  {paper_id} — classified {len(cands)} candidates', file=sys.stderr)

    with open(CANDIDATES_PATH, 'w') as f:
        json.dump(candidates_by_paper, f, indent=2)

    print(f'\nClassified {total} candidates (k={args.k}).', file=sys.stderr)
    print(f'Updated {CANDIDATES_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
