# Launch & Update Checklist

Two kinds of tasks: things to do **before first launch**, and things to revisit
**whenever the graph or animation changes**. Both are tracked here.

---

## Before first launch

### Content
- [ ] Replace `Your Name` in `index.html` (hero, nav logo, footer, `<title>`)
- [ ] Fill in hero tagline if it needs personalising
- [ ] Update About section body text
- [ ] Fill in Research cards (003 is a working paper — update status when ready)
- [ ] Populate Projects list with real links
- [ ] Fill in CV section (education, experience, publications)
- [ ] Update contact links (Scholar, GitHub, Twitter/X, LinkedIn)
- [ ] Set correct email in contact section
- [ ] Update footer copyright name

### Graph
- [ ] Run `node index.js orcid` and add any missing papers
- [ ] Run `node index.js rebuild` to recompute layout
- [ ] Commit `graph.json`
- [ ] **Review `graph.html`** — verify all clusters, papers table, and node descriptions
      are accurate for the current graph (see *graph.html update checklist* below)

### Technical
- [ ] Confirm `graph.json` is served at `./graph.json` relative to `index.html`
      (both files in the same directory, or adjust the fetch path in the `<script>`)
- [ ] Confirm `graph.html` is linked correctly from footer and HUD
- [ ] Test on mobile (responsive breakpoints at 900px)
- [ ] Check custom cursor is hidden on touch devices if needed
- [ ] Verify fonts load (Cormorant Garamond + Space Mono via Google Fonts)
- [ ] Test admin panel (press `\`` to open) — add/remove a node, confirm live merge works
- [ ] Set a real CV PDF download link

---

## graph.html update checklist

Run this any time one of the following happens:

| Trigger | What to check in graph.html |
|---|---|
| New paper added to `graph.json` | Papers table — new row with correct year, title, venue, DOI link, and concept tags |
| New nodes added | Cluster cards — new node tags appear in the right cluster card |
| Cluster names or descriptions changed | `CLUSTER_META` array at top of `graph.html` `<script>` |
| Phase names or logic changed | *Five States of Mind* section — names, ranges, and descriptions |
| Animation model changed | *How It Works* pillars — update any description that no longer matches the code |
| Pre-launch | Full read-through of all five sections |

### Quick review steps

1. Open `graph.html` in a browser alongside the live site
2. Hover nodes in the canvas — verify tooltip labels, clusters, and paper attribution are correct
3. Read the five phase cards — names must match the `PHASES` array in `index.html`
4. Check the Papers table — every paper in `graph.json → meta.papers` should have a row
5. Check cluster cards — node count in legend should match `graph.json`
6. Confirm "explore the graph →" link in `index.html` HUD and footer points to the right file

---

## After any deploy

- [ ] Smoke-test the live URL — topology canvas loads, labels appear
- [ ] Click "explore the graph →" — `graph.html` opens and canvas renders
- [ ] Confirm `graph.json` is accessible (no 404 in network tab)
- [ ] Check HUD is visible and phase label updates after ~10 seconds
