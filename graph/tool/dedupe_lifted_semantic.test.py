#!/usr/bin/env python3
"""
dedupe_lifted_semantic.test.py — plain-assert test suite for the pure
functions in dedupe_lifted_semantic.py (is_antonym_pair, _normalize_word,
clean_label). No test framework (matches this project's zero-dependency
convention) — run directly from graph/tool/:
    python3 dedupe_lifted_semantic.test.py
Prints a checkmark or cross per case (with a message on failure), exits 1
on any failure.

Deliberately does NOT test dedupe_paper() or main() — both require loading
the real sentence-transformers model and are covered by this pipeline's
existing smoke-run verification convention instead. Importing this module
still triggers dedupe_lifted_semantic.py's own `from sentence_transformers
import SentenceTransformer` at the top of that file (Python executes a
module top-to-bottom on import) — this is a real but small one-time cost
(no model weights are loaded; SentenceTransformer(...) is only
instantiated inside main(), which this test file never calls).
"""
import sys

from dedupe_lifted_semantic import is_antonym_pair, _normalize_word, clean_label

failures = 0


def test(name, fn, expected):
    global failures
    try:
        actual = fn()
        assert actual == expected, f'expected {expected!r}, got {actual!r}'
        print(f'  ✓ {name}')
    except AssertionError as e:
        failures += 1
        print(f'  ✗ {name}')
        print(f'    {e}')
    except Exception as e:
        failures += 1
        print(f'  ✗ {name}')
        print(f'    unexpected {type(e).__name__}: {e}')


print('is_antonym_pair')

test('goal-aligned vs goal-agnostic (the motivating bug case)',
     lambda: is_antonym_pair('Goal-Aligned Reward', 'Goal-Agnostic Reward'), True)

test('high vs low anxiety (textbook antonym pair, scores higher than the bug case)',
     lambda: is_antonym_pair('High Anxiety', 'Low Anxiety'), True)

test('reward magnitude vs reward size (true near-duplicate, not antonym)',
     lambda: is_antonym_pair('Reward Magnitude', 'Reward Size'), False)

test('amygdala activity vs hippocampal volume (unrelated, zero word overlap)',
     lambda: is_antonym_pair('Amygdala Activity', 'Hippocampal Volume'), False)

test('aligned rewards vs agnostic reward (plural-mismatch case, requires normalization fix)',
     lambda: is_antonym_pair('Aligned Rewards', 'Agnostic Reward'), True)

test('mixed case is antonym-insensitive',
     lambda: is_antonym_pair('HIGH Anxiety', 'low ANXIETY'), True)

test('multi-word diff is never flagged even if one differing word is an antonym',
     lambda: is_antonym_pair('Positive Valence Signal', 'Negative Affect Cue'), False)

test('identical labels are not an antonym pair',
     lambda: is_antonym_pair('Reward Rate', 'Reward Rate'), False)

test('order-independent (frozenset-based comparison)',
     lambda: is_antonym_pair('Low Anxiety', 'High Anxiety'), True)

print('_normalize_word')

test('short word (len<=4) left unchanged even if it ends in s',
     lambda: _normalize_word('bias'), 'bias')

test('ss-ending word left unchanged',
     lambda: _normalize_word('class'), 'class')

test('plural word above length threshold gets singularized',
     lambda: _normalize_word('rewards'), 'reward')

test('non-plural word left unchanged',
     lambda: _normalize_word('aligned'), 'aligned')

print('clean_label')

test('newline replaced with space',
     lambda: clean_label('Goal-Aligned\nReward'), 'Goal-Aligned Reward')

test('multiple whitespace collapsed and trimmed',
     lambda: clean_label('  Extra   Spaces  \n Here '), 'Extra Spaces Here')

print(f'\n{"All tests passed." if failures == 0 else f"{failures} test(s) failed."}')
sys.exit(0 if failures == 0 else 1)
