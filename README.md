# shabnam-hakimi.com

Personal research website. Built with vanilla HTML/CSS/JS + Three.js.
No build step — open `index.html` in a browser or serve from any static host.

## File structure

```
/
├── index.html          ← main site (hero, about, research, CV, contact)
├── graph.html          ← public explanation of the knowledge graph topology
├── README.md           ← this file
├── LAUNCH.md           ← pre-launch and update checklists
└── graph/
    ├── graph.json      ← canonical semantic graph data (commit this)
    ├── editor.html     ← visual graph editor
    ├── README.md       ← CLI tool docs
    └── tool/           ← node CLI for adding papers
```

## Development

No build step. Serve locally to enable `graph.json` fetch:

```bash
npx serve .
# or
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Keeping graph.html in sync

`graph.html` is the public explanation of the topology animation. Parts of it
update automatically from `graph.json`; parts are written prose that can drift.

| Changed | Automatic? | What to do |
|---|---|---|
| New paper added via CLI | ✅ Papers table + node tags | Just verify the new row looks right |
| New nodes added | ✅ Cluster node tags | Check they land in the right cluster card |
| Cluster names or descriptions | ❌ | Edit `CLUSTER_META` in `graph.html` `<script>` |
| Phase names or logic | ❌ | Edit *Five States of Mind* section in `graph.html` |
| Animation model changed | ❌ | Edit *How It Works* pillars in `graph.html` |
| Pre-launch / any deploy | — | Full read-through of all five sections |

See `LAUNCH.md` for the complete checklist.
