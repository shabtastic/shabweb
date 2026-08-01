#!/usr/bin/env python3
"""
dedupe_lifted_semantic.py — Second-pass sibling dedup for graph/lift-output.json,
catching semantic duplicates that lift_concepts.js's literal source-candidate-
overlap check (dedupeSiblingNodes in lift_concepts.js) can't see — two new
nodes from the same paper describing the same concept via disjoint phrasing
(e.g. "reward magnitude" vs "payoff size") share zero source candidates but
should still be merged.

Two-tier merging strategy:
  - AUTO_MERGE_THRESHOLD (default 0.75): very-confident semantic duplicates are
    automatically merged using union-find.
  - REVIEW_THRESHOLD (default 0.45): pairs scoring in [review_threshold, auto_threshold)
    are NOT auto-merged, but flagged for human review in graph/lift-semantic-flagged.json.
  - Below 0.45: ignored entirely.

This two-tier approach balances precision (avoiding false merges at high threshold) with
recall (catching true duplicates like "reward magnitude" vs "payoff size" that may score
moderately high, not at the ceiling). The review tier provides visibility into borderline
cases for downstream human judgment.

Note: auto-merges made by this script are NOT recorded in graph/lift-audit.json (that
file only covers lift_concepts.js's own validation corrections) — the review-tier flagged
pairs in graph/lift-semantic-flagged.json are the visibility mechanism for this script's
decisions instead.

Run AFTER lift_concepts.js, before promote_lift_output.js.

Usage:
    python3 dedupe_lifted_semantic.py [--auto-threshold 0.75] [--review-threshold 0.45]
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
FLAGGED_PATH = os.path.join(SCRIPT_DIR, '..', 'lift-semantic-flagged.json')

# Embedding similarity cannot distinguish "same phrase, opposite polarity"
# from "same phrase, true paraphrase" — antonym pairs sharing a stem often
# score HIGHER than genuine synonyms phrased differently (verified: 'high
# anxiety' vs 'low anxiety' = 0.851, higher than the real bug this guards
# against, 'goal-aligned reward' vs 'goal-agnostic reward signal' = 0.721).
# No threshold value can separate these cases; this is a dedicated check.
ANTONYM_PAIRS = {
    frozenset(p) for p in [
        ('aligned', 'agnostic'), ('high', 'low'), ('increased', 'decreased'),
        ('increase', 'decrease'), ('more', 'less'), ('positive', 'negative'),
        ('with', 'without'), ('present', 'absent'), ('before', 'after'),
        ('early', 'late'), ('same', 'different'), ('consistent', 'inconsistent'),
        ('gain', 'loss'), ('active', 'passive'), ('excitatory', 'inhibitory'),
        ('internal', 'external'), ('explicit', 'implicit'), ('short', 'long'),
        ('congruent', 'incongruent'), ('expected', 'unexpected'),
    ]
}


def _normalize_word(w):
    # Light singularization — strip a trailing 's' for words long enough
    # that this won't mangle genuinely-short words (e.g. keep 'bias' as
    # 'bias', not 'bia'). Good enough for the antonym-pair vocabulary here;
    # not a real stemmer. Without this, an incidental plural/qualifier
    # mismatch (e.g. "Aligned Rewards" vs "Agnostic Reward") adds a second
    # differing word and defeats the "exactly one word differs" check below,
    # letting a genuine antonym pair through undetected.
    if len(w) > 4 and w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def is_antonym_pair(label_a, label_b):
    """True if the two labels differ by exactly one word each (after light
    normalization), and that pair of differing words is a known antonym/
    polarity pair — regardless of how similar the labels otherwise are."""
    words_a = {_normalize_word(w) for w in re.findall(r'[a-z]+', label_a.lower())}
    words_b = {_normalize_word(w) for w in re.findall(r'[a-z]+', label_b.lower())}
    diff_a = words_a - words_b
    diff_b = words_b - words_a
    if len(diff_a) == 1 and len(diff_b) == 1:
        pair = frozenset([diff_a.pop(), diff_b.pop()])
        return pair in ANTONYM_PAIRS
    return False


def clean_label(label):
    return re.sub(r'\s+', ' ', label.replace('\n', ' ')).strip()


def merge_pair(keep, dupe):
    keep_srcs = set(keep.get('source_candidates') or [])
    dupe_srcs = set(dupe.get('source_candidates') or [])
    keep['source_candidates'] = list(keep_srcs | dupe_srcs)


def dedupe_paper(paper_result, model, auto_threshold, review_threshold, paper_id):
    nodes = paper_result.get('nodes') or []
    new_nodes = [n for n in nodes if not n.get('reuse_existing') or n.get('reuse_existing') == 'null']
    if len(new_nodes) < 2:
        return 0, []

    labels = [clean_label(n['label']) for n in new_nodes]
    embs = model.encode(labels, show_progress_bar=False)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    embs_normed = embs / (norms + 1e-9)
    sims = embs_normed @ embs_normed.T

    # Union-find over pairs above auto_threshold (same merge strategy as the JS
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
    flagged_pairs = []

    # First pass: auto-merge at high threshold. Antonym/negation pairs are
    # excluded even when their score clears auto_threshold — embedding
    # similarity can't tell "same phrase, opposite polarity" apart from a
    # true paraphrase (see ANTONYM_PAIRS / is_antonym_pair above).
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= auto_threshold and not is_antonym_pair(labels[i], labels[j]):
                union(new_nodes[i]['id'], new_nodes[j]['id'])

    # Second pass: collect review-tier pairs. Normally this is the
    # [review_threshold, auto_threshold) band, but antonym pairs that scored
    # >= auto_threshold were deliberately blocked from auto-merge above and
    # would otherwise fall through this check silently (score < auto_threshold
    # would be False) — so they're pulled in here too, as long as they clear
    # review_threshold, so a human sees them instead of them vanishing.
    for i in range(n):
        for j in range(i + 1, n):
            score = sims[i, j]
            antonym = is_antonym_pair(labels[i], labels[j])
            # Only flag pairs that didn't already get auto-merged
            if score >= review_threshold and (score < auto_threshold or antonym):
                # Check if they're in the same union-find group
                if find(new_nodes[i]['id']) != find(new_nodes[j]['id']):
                    flagged_pairs.append({
                        'paper_id': paper_id,
                        'node_a': new_nodes[i]['id'],
                        'node_b': new_nodes[j]['id'],
                        'label_a': clean_label(new_nodes[i]['label']),
                        'label_b': clean_label(new_nodes[j]['label']),
                        'similarity': float(score)
                    })

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

    # Apply id_remap to flagged pairs so they reference survivors, not merged-away nodes
    for pair in flagged_pairs:
        pair['node_a'] = id_remap.get(pair['node_a'], pair['node_a'])
        pair['node_b'] = id_remap.get(pair['node_b'], pair['node_b'])

    reuse_nodes = [n for n in nodes if n.get('reuse_existing') and n.get('reuse_existing') != 'null']
    paper_result['nodes'] = survivors + reuse_nodes
    for e in paper_result.get('edges') or []:
        e['a'] = id_remap.get(e['a'], e['a'])
        e['b'] = id_remap.get(e['b'], e['b'])
    paper_result['edges'] = [e for e in (paper_result.get('edges') or []) if e['a'] != e['b']]

    return merge_count, flagged_pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto-threshold', type=float, default=0.75,
                        help='Threshold for automatic merging (default 0.75)')
    parser.add_argument('--review-threshold', type=float, default=0.45,
                        help='Threshold for flagging pairs for human review (default 0.45)')
    args = parser.parse_args()
    assert args.review_threshold < args.auto_threshold, (
        'review_threshold must be less than auto_threshold, or antonym pairs '
        'in the gap could silently vanish'
    )

    with open(LIFT_OUTPUT_PATH) as f:
        results = json.load(f)

    print('Loading embedding model…', file=sys.stderr)
    model = SentenceTransformer('all-mpnet-base-v2')

    total_merges = 0
    all_flagged = []

    for paper_id, paper_result in results.items():
        if 'error' in paper_result:
            continue
        merges, flagged = dedupe_paper(paper_result, model, args.auto_threshold, args.review_threshold, paper_id)
        total_merges += merges
        all_flagged.extend(flagged)
        if merges:
            print(f'  {paper_id} — {merges} semantic merge(s)', file=sys.stderr)
        if flagged:
            print(f'  {paper_id} — {len(flagged)} pair(s) flagged for review', file=sys.stderr)

    with open(LIFT_OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)

    # Write flagged pairs for human review
    with open(FLAGGED_PATH, 'w') as f:
        json.dump(all_flagged, f, indent=2)

    print(f'\n{total_merges} total semantic sibling merges across all papers.', file=sys.stderr)
    print(f'{len(all_flagged)} pair(s) flagged for human review.', file=sys.stderr)
    print(f'Updated {LIFT_OUTPUT_PATH}', file=sys.stderr)
    print(f'Wrote {FLAGGED_PATH}', file=sys.stderr)


if __name__ == '__main__':
    main()
