// Tests for cv.html's publication display rule.
//
// Run directly, no test runner:   node data/test-pub-trim.mjs
//
// cv.html shows a *slice* of the selected publications — the last
// WINDOW_YEARS, capped at MAX_ENTRIES per subsection — while the "View full
// CV" links carry the complete record. That means tuning either number, or a
// routine `node data/sync-bib.js` that adds a few recent papers, can silently
// push an older paper off the page. Nothing about that failure is visible: no
// error, no console warning, just one fewer row.
//
// So the cases that would actually matter to a reader are asserted here
// against the real data/publications.json. Two are hard requirements Shabnam
// stated explicitly; the rest guard the rule's edges.
//
// The rule itself is extracted from cv.html between marker comments rather
// than duplicated, so this can't drift from what the page runs. If the markers
// move or disappear, this fails loudly instead of testing a stale copy.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const html = readFileSync(join(root, 'cv.html'), 'utf8');
const pubs = JSON.parse(readFileSync(join(root, 'data', 'publications.json'), 'utf8'));

function extract(name) {
  const start = `// ── ${name} (start) ──`;
  const end = `// ── ${name} (end) ──`;
  const a = html.indexOf(start);
  const b = html.indexOf(end);
  if (a < 0 || b < 0) {
    throw new Error(`cv.html is missing the ${name} markers (start=${a}, end=${b})`);
  }
  return html.slice(a + start.length, b);
}

// PRESENTATION_TYPES lives outside the marked blocks; BUCKETS references it.
const PRESENTATION_TYPES = ['talk', 'poster', 'symposium', 'invited-talk'];
const { trimForDisplay, WINDOW_YEARS, MAX_ENTRIES } = new Function(
  `${extract('PUB-TRIM')}; return { trimForDisplay, WINDOW_YEARS, MAX_ENTRIES };`
)();
const BUCKETS = new Function(
  'PRESENTATION_TYPES',
  `${extract('BUCKETS')}; return BUCKETS;`
)(PRESENTATION_TYPES);

let failures = 0;
function check(name, cond, detail) {
  if (cond) { console.log(`  ok   ${name}`); return; }
  failures++;
  console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
}

// Mirror cv.html's own ordering before trimming.
const selected = pubs.filter(p => p.keywords && p.keywords.includes('selected'));
selected.sort((a, b) => b.year - a.year || b.paperWeight - a.paperWeight);

const shown = {};
for (const b of BUCKETS) {
  shown[b.id] = trimForDisplay(selected.filter(p => b.types.includes(p.pubType)));
}
const allShown = Object.values(shown).flat();
const has = (id) => allShown.some(p => p.id === id);

// ── The two papers that must not disappear ────────────────────────────────

// Knutson2024brain is Shabnam's explicit "must always show" — it anchors the
// neuroforecasting line. An earlier design that stopped as soon as it had N
// entries dropped it, because it halted at 2025-26 and never reached 2024.
check('Knutson2024brain is shown', has('Knutson2024brain'),
  `preprints shown: ${shown['pub-list-preprints'].map(p => p.year + ' ' + p.id).join(', ')}`);

// Nandy2024semantic carries a Best Paper Award. At the previous 5-year/8-entry
// setting it fell one slot outside the cap, so the page showed an Honorable
// Mention while hiding an outright win.
check('the Best Paper Award paper is shown', has('Nandy2024semantic'),
  `proceedings shown: ${shown['pub-list-proceedings'].map(p => p.year + ' ' + p.id).join(', ')}`);

// Any award is a reason a paper matters more than its date suggests, so the
// rule shouldn't quietly drop one. This will fail if a future sync pushes an
// awarded paper out — at which point it's a judgement call, not a bug, but it
// should be a deliberate one.
{
  const awarded = selected.filter(p => p.addendum);
  const dropped = awarded.filter(p => !has(p.id));
  check('no awarded paper is silently dropped', dropped.length === 0,
    dropped.map(p => `${p.year} ${p.id} (${p.addendum})`).join('; '));
}

// ── The rule's edges ──────────────────────────────────────────────────────

check('both bounds are actually applied', (() => {
  const pre = selected.filter(p => p.pubType === 'preprint');
  const out = trimForDisplay(pre);
  return out.length <= MAX_ENTRIES && out.length < pre.length;
})(), `WINDOW_YEARS=${WINDOW_YEARS}, MAX_ENTRIES=${MAX_ENTRIES}`);

check('empty input returns empty, does not throw',
  trimForDisplay([]).length === 0);

// Every selected entry must land in some subsection. cv.html console.warns on
// an orphan, but nobody reads the console; a new pubType from the bib would
// otherwise vanish from the page entirely.
{
  const bucketed = new Set(BUCKETS.flatMap(b => b.types));
  const orphans = [...new Set(selected.filter(p => !bucketed.has(p.pubType)).map(p => p.pubType))];
  check('every selected pubType has a subsection', orphans.length === 0,
    `unbucketed: ${orphans.join(', ')}`);
}

// A single mistyped year must not drag the cutoff forward and empty the list.
{
  const real = selected.filter(p => p.pubType === 'preprint');
  const withTypo = [{ ...real[0], id: 'typo', year: 2062 }, ...real];
  const out = trimForDisplay(withTypo);
  check('a mistyped future year does not empty the subsection',
    out.length > 1, `got ${out.length} entries`);
}

// Ordering is what makes the cap meaningful — newest survives the slice.
check('output stays newest-first', (() => {
  const out = shown['pub-list-preprints'];
  return out.every((p, i) => i === 0 || out[i - 1].year >= p.year);
})());

// A subsection whose entries are all ancient renders nothing, so its heading
// hides rather than standing over an empty list.
check('an all-stale subsection trims to empty',
  trimForDisplay([{ id: 'x', year: 1999, pubType: 'journal' }]).length === 0);

console.log(failures === 0
  ? `\nall pub-trim tests passed (${allShown.length} entries shown at ${WINDOW_YEARS}yr/${MAX_ENTRIES})`
  : `\n${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
