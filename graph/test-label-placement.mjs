// Tests for the canvas label placement geometry in graph.html.
//
// Run directly, no test runner:   node graph/test-label-placement.mjs
//
// The function under test lives inside graph.html's inline <script>. Rather
// than duplicate it here (and let the copy drift), the source is extracted
// between the LABEL-PLACEMENT markers and evaluated. If those markers move or
// disappear, this file fails loudly instead of testing a stale copy.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, '..', 'graph.html'), 'utf8');

const START = '// ── LABEL-PLACEMENT (start) ──';
const END = '// ── LABEL-PLACEMENT (end) ──';
const a = html.indexOf(START);
const b = html.indexOf(END);
if (a < 0 || b < 0) {
  throw new Error(`graph.html is missing the LABEL-PLACEMENT markers (start=${a}, end=${b})`);
}
const src = html.slice(a + START.length, b);
const placeLabelBoxes = new Function(`${src}; return placeLabelBoxes;`)();

let failures = 0;
function check(name, cond, detail) {
  if (cond) { console.log(`  ok   ${name}`); return; }
  failures++;
  console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
}

// Any two placed boxes must be disjoint. Returns the offending pair, if any.
function firstOverlap(boxes) {
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const p = boxes[i], q = boxes[j];
      const ox = Math.min(p.x1, q.x1) - Math.max(p.x0, q.x0);
      const oy = Math.min(p.y1, q.y1) - Math.max(p.y0, q.y0);
      if (ox > 0 && oy > 0) return { i, j, ox, oy };
    }
  }
  return null;
}

const item = (x, y, over = {}) =>
  Object.assign({ x, y, r: 5, w: 60, h: 22, required: false }, over);

// 1. A lone label keeps the historical placement: centred under its node.
{
  const [box] = placeLabelBoxes([item(200, 200)], { width: 400, height: 400 });
  check('lone label sits below its node, horizontally centred',
    box.x0 === 200 - 30 && box.y0 === 200 + 5 + 3,
    `got x0=${box.x0}, y0=${box.y0}`);
}

// 2. The reported bug: neighbours exposed by a click land on top of each other.
//    Three nodes within a few pixels — every returned box must be disjoint.
{
  const boxes = placeLabelBoxes(
    [item(200, 200, { required: true }), item(206, 203), item(196, 208)],
    { width: 400, height: 400 });
  check('overlapping neighbours are displaced, not stacked',
    firstOverlap(boxes) === null,
    JSON.stringify(firstOverlap(boxes)));
}

// 3. A pile-up that cannot be resolved: the clicked node's label is still
//    drawn (the user asked for it), the unplaceable extras are dropped.
{
  const items = [item(200, 200, { required: true })];
  for (let i = 0; i < 8; i++) items.push(item(200 + i * 0.5, 200 + i * 0.5));
  const boxes = placeLabelBoxes(items, { width: 400, height: 400 });
  check('required label survives a pile-up', boxes.some(bx => bx.required));
  check('unplaceable optional labels are dropped, never overlapped',
    boxes.length < items.length && firstOverlap(boxes) === null,
    `placed ${boxes.length} of ${items.length}, overlap=${JSON.stringify(firstOverlap(boxes))}`);
}

// 4. Narrow viewports: a node near the edge must not have its label clipped
//    off-canvas. This is the mobile case — the graph is the same width as the
//    labels there, so edge nodes are common.
{
  const boxes = placeLabelBoxes([item(8, 200), item(392, 260)], { width: 400, height: 400 });
  check('labels stay inside the canvas horizontally',
    boxes.every(bx => bx.x0 >= 0 && bx.x1 <= 400),
    boxes.map(bx => `${bx.x0}..${bx.x1}`).join(', '));
}

// 5. A node at the bottom of the drawable band must flip its label upward
//    rather than hang it over the HTML footer below the canvas.
{
  const [box] = placeLabelBoxes([item(200, 380, { required: true })],
    { width: 400, height: 400, top: 40, bottom: 390 });
  check('label near the bottom edge flips above its node',
    box.y1 <= 390, `box spans ${box.y0}..${box.y1}, band ends at 390`);
}

// 6. Same at the top edge — flip down, which is the default slot anyway.
{
  const [box] = placeLabelBoxes([item(200, 45, { required: true })],
    { width: 400, height: 400, top: 40, bottom: 390 });
  check('label near the top edge stays inside the band',
    box.y0 >= 40, `box spans ${box.y0}..${box.y1}, band starts at 40`);
}

// 7. Placement is deterministic — same input, same output. The draw loop runs
//    every frame; a label that hops between candidate slots would flicker.
{
  const items = [item(200, 200, { required: true }), item(204, 202), item(198, 206)];
  const one = JSON.stringify(placeLabelBoxes(items, { width: 400, height: 400 }));
  const two = JSON.stringify(placeLabelBoxes(items, { width: 400, height: 400 }));
  check('placement is deterministic across frames', one === two);
}

console.log(failures === 0 ? '\nall label-placement tests passed' : `\n${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
