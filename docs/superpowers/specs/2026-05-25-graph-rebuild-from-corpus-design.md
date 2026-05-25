# Graph rebuild from corpus — design

**Date:** 2026-05-25
**Status:** Approved for implementation planning

## Problem

The current `graph/graph.json` has 275 nodes, 482 edges, and 50 papers, but **24 of those 50 papers have empty `nodes_contributed`** (never had concept extraction). The 26 papers that *do* have contributions had them derived from title + abstract only via the legacy DOI-based add flow, not full text.

With the research-corpus pipeline now stable — vault contains 232 archived files including full-text extractions in `vault/extracted/<sha>.txt` — we can rebuild the graph from full paper text. This produces a denser, more accurate concept graph and closes the long-standing TODO in CLAUDE.md ("19 of 45 publications still have no graph nodes").

## Constraints

1. **No patents in the graph.** Patents live in `patents.bib`, which `sync-bib.js` doesn't read, so they're already absent from `publications.json` and thus the graph universe. The constraint just means we never reach for them.
2. **No scicomm / commentary in the graph.** `sync-bib.js` already excludes them from `graph.json.meta.papers` (commit `af83298`). The rebuild honors the same filter.
3. **Drafts cannot be made publicly available.** Three entries (`Wright2024motivation`, `Sinclair2024pausing`, `Knutson2024brain`) have `keywords: ["draft"]` in `publications.json` and `have_draft` status in the corpus. The draft files live in the gitignored `vault/originals/` of the private corpus repo — that part is fine. The risk is that concept extraction from a draft could surface ideas that aren't yet in the public OSF preprint linked from `publications.json`. Drafts therefore need a separate review buffer before their contributions reach the public graph.
4. **Cost.** Using Sonnet 4.6 keeps the full rebuild under ~$3 in API tokens.

## Graph universe

The graph extracts concepts from papers that meet **all** of:

- Present in `~/projects/website/data/publications.json`
- Has `keywords` that does **not** include `scicomm`, `commentary`, or `unlisted`
- Has a corresponding entry in `~/projects/research-corpus/corpus-catalog.json` with `acquisition.next_action ∈ {have_local, have_draft}` and a non-null `final_output.sha`

As of 2026-05-25, this yields **47 papers**:

| Bucket | Count | Extraction pass |
|---|---|---|
| `selected`, not-draft | 16 | Pass 1 — anchor |
| Non-`selected`, not-draft | 26 | Pass 2 — fill |
| Drafts (Wright, Sinclair, Knutson) | 3 | Pass 3 — extract + flag for review |
| Excluded: scicomm/commentary/unlisted | 4 | not extracted |
| Excluded: not in publications.json (patents, posters, presentations) | 38 | not eligible |

## Architecture

Two new scripts in `~/projects/website/graph/tool/`:

### `rebuild-from-corpus.js`

A full rebuild of `graph/graph.json` from corpus full-text. Reads the corpus catalog and extracted text via a `CORPUS_REPO` env var (default `~/projects/research-corpus`). Outputs:

- Overwrites `graph/graph.json` with fresh `nodes`, `edges`, `meta.papers`. Preserves `meta.clusters` (the 7 cluster definitions are stable design artifacts, not extracted data).
- Writes `graph/draft-proposals.json` (gitignored) for Pass 3 outputs awaiting review.

The script is **idempotent** at the pass level: each pass writes after every paper, so re-running picks up where it left off. A `--start-pass N` flag allows surgical re-runs.

### `review-draft-proposals.js`

Interactive CLI to inspect and selectively promote draft-extracted nodes/edges from `draft-proposals.json` into `graph.json`. For each proposal, prompts: approve / reject / defer. Marks proposals reviewed after a complete pass.

## Three-pass execution

Each pass uses the same `extractConcepts()` core logic (largely reused from the existing `graph/tool/index.js`), with model and prompt parameters varying.

### Model

**Default: Claude Sonnet 4.6** (`claude-sonnet-4-6`). Adequate for concept extraction at ~5× lower cost than Opus. An `--opus` flag escalates a specific paper to Opus 4.7 if the Sonnet output is sparse or incoherent.

### Pass 1 — Anchor (16 selected non-draft papers)

- `paperWeight` floored at **1.0** regardless of author position or pub type. Selected status overrides the standard `computePaperWeight()` math.
- Full extraction: create new nodes + edges freely.
- These papers establish the core graph vocabulary that subsequent passes build on.
- Processed in deterministic order (sorted by `pub_key`) so re-runs land in the same state.

### Pass 2 — Fill (26 non-selected non-draft papers)

- `paperWeight` computed normally (author position, pub type, recency).
- Full extraction: can still create new nodes; supports the structure laid down in Pass 1.
- Existing-node-reuse instruction in the prompt (already present in current `extractConcepts`) discourages near-duplicate nodes.

### Pass 3 — Drafts (3 papers, gated)

- Same extraction logic. `paperWeight` follows the same rule as Passes 1/2: selected entries (Wright, Knutson) floor at 1.0; non-selected entries (Sinclair) use `computePaperWeight()`.
- Output goes to `graph/draft-proposals.json`, **not** `graph.json`.
- Until reviewed, nothing from drafts appears on the public graph.
- If a draft is later upgraded to `have_local` (final paper published), it should be moved from Pass 3 to Pass 1/2 on the next rebuild — the catalog's `next_action` field is the source of truth.

## Draft review workflow

`graph/draft-proposals.json` schema:

```json
{
  "proposals": [
    {
      "paper_id": "Knutson2024brain",
      "extracted_at": "2026-05-25T22:00:00Z",
      "model": "claude-sonnet-4-6",
      "paper_weight": 1.0,
      "nodes": [
        { "id": "demand_neuroforecasting", "label": "demand\nneuroforecasting", "weight": 0.7, "cluster": 4, "level": "construct" }
      ],
      "edges": [
        { "a": "demand_neuroforecasting", "b": "anticipation", "strength": 0.8 }
      ],
      "reviewed": false
    }
  ]
}
```

`review-draft-proposals.js` walks each proposal, for each new node and edge prompts a/r/d (approve/reject/defer). Approved items are merged into `graph.json` via the same `mergeIntoGraph()` logic Passes 1/2 use. Rejected items are dropped from the proposals file. Deferred items stay for a future review session.

## Schema changes

`graph/graph.json` gets one new field per `meta.papers[]` entry:

```json
"extraction_source": "full-text" | "title-abstract"
```

This records whether a paper's contributions came from vault full-text (the new normal) or fallback title-abstract extraction (used only if `vault/extracted/<sha>.txt` is unexpectedly missing). Future re-extractions can identify upgrade candidates.

No other schema changes. `nodes_contributed`, `paperWeight`, `cluster`, `level`, etc. all preserved as-is.

## Data flow

```
~/projects/research-corpus/                          (private repo)
  corpus-catalog.json                                ← reads pub_key → sha mapping
  vault/extracted/<sha>.txt                          ← reads full text input

~/projects/website/data/publications.json            (public, derived from CV bib)
                                                     ← reads keywords filter (scicomm/commentary/unlisted)

~/projects/website/graph/graph.json                  (public output)
                                                     ← writes nodes, edges, meta.papers
~/projects/website/graph/draft-proposals.json        (gitignored review buffer)
                                                     ← writes Pass 3 outputs
```

## Error handling

- **Missing `vault/extracted/<sha>.txt`**: fall back to title+abstract extraction via the catalog's `title` + (if available) the publication's abstract. Mark `extraction_source: "title-abstract"`. Log warning. Currently affects 0 papers (vault has all 47).
- **Invalid JSON from model**: retry once with the same prompt. If still invalid, skip the paper and log a single-line error with `pub_key` + Claude's response prefix. The script continues. A `--skipped-papers` flag re-runs just the skipped ones.
- **Anthropic API error (rate limit, transient 5xx)**: exponential backoff retry, max 3 attempts.
- **No `ANTHROPIC_API_KEY`**: exit early with clear error before any API call.
- **Resumability**: each Pass's results are written incrementally (after every successful paper), so killing and restarting picks up where it left off without re-doing completed work.

## Rollout

1. Implement `rebuild-from-corpus.js` and `review-draft-proposals.js`.
2. Verify on a tiny subset (e.g., `--limit 2 --pass 1`): one selected paper + one draft. Inspect schema correctness end-to-end.
3. Full run: ~47 API calls. Wall time ~15–20 min. Cost ~$3 with Sonnet.
4. User runs `review-draft-proposals.js` to triage the ~3 drafts' contributions.
5. Run `data/inline-graph.js` to sync `graph.json` into `index.html` + `graph.html` inlined blocks.
6. Commit + push → Vercel auto-deploys.

## Out of scope

- **build-corpus.js becoming vault-aware** (so it doesn't blow away have_local matches when scan roots are empty). Tracked as a followup in `corpus-roots.js` comments. Not blocking this work.
- **PDF surfacing on cv.html** (the v3 work). Has its own separate design decision pending.
- **Level (theory/construct/method/mechanism/domain) reclassification** of new nodes. The extraction prompt already requests a `level` per node; `graph/tool/classify-levels.js` can post-process if needed.
- **Cluster reassignment** for existing publications based on rebuilt graph topology. The cv.html cluster pills come from `sync-bib.js` mapping `part_of` → cluster, not from graph extraction. These channels stay independent for now.
