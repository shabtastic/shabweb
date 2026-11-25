// The homepage approach figure ("Better estimates of internal states for
// better interventions") as native, editable shapes: every curve, band, tick,
// bracket and label is its own object, each of the six steps is a group, and
// the groups come in one click at a time.
//
// The geometry comes from figures/approach.py via approach_shapes.py, so the
// slide follows the homepage figure. Every word is Shabnam's, verbatim.
const { execFileSync } = require("child_process");
const path = require("path");

const MONO = "Space Mono";
const SANS_BOLD = "DM Sans"; // the figure's bold phrases: DM Sans, bold
const STEP_TAG = /^§(\d+)\|([^§]*)§/; // objectName prefix: §step|step name§

function figureData() {
  return JSON.parse(execFileSync("python3", [path.join(__dirname, "approach_shapes.py")]));
}

const transp = (a) => Math.round((1 - a) * 100);
const DASH = { "4 4": "dash", "2 4": "sysDot" };

// Draw the figure on `slide` with its top-left at (x, y) inches, `w` wide.
function addApproachFigure(slide, { x, y, w }) {
  const { viewBox, steps } = figureData();
  const s = w / viewBox[0];            // inches per SVG px
  const pt = (px) => px * s * 72;      // SVG px -> points
  const X = (v) => x + v * s, Y = (v) => y + v * s;
  const line = (st) => st ? { color: st.color, transparency: transp(st.alpha),
    width: pt(st.width), ...(st.dash ? { dashType: DASH[st.dash] || "dash" } : {}) } : { type: "none" };
  const fill = (f) => f ? { color: f.color, transparency: transp(f.alpha) } : undefined;

  steps.forEach((step, k) => {
    let n = 0;
    const name = (what) => `§${k}|${step.name}§${what} ${++n}`;
    for (const el of step.items) {
      if (el.t === "path") {
        const pts = el.subs.flat();
        const xs = pts.flatMap((p) => [p.x, ...(p.q ? [p.q[0]] : [])]);
        const ys = pts.flatMap((p) => [p.y, ...(p.q ? [p.q[1]] : [])]);
        const x0 = Math.min(...xs), y0 = Math.min(...ys);
        const bw = Math.max(Math.max(...xs) - x0, 0.5), bh = Math.max(Math.max(...ys) - y0, 0.5);
        const points = el.subs.flatMap((sub) => sub.map((p, i) => ({
          x: (p.x - x0) * s, y: (p.y - y0) * s,
          ...(i === 0 ? { moveTo: true } : {}),
          ...(p.q ? { curve: { type: "quadratic", x1: (p.q[0] - x0) * s, y1: (p.q[1] - y0) * s } } : {}),
        })));
        if (el.closed) points.push({ close: true });
        slide.addShape("custGeom", { x: X(x0), y: Y(y0), w: bw * s, h: bh * s, points,
          fill: fill(el.fill), line: line(el.stroke), objectName: name(el.closed ? "Band" : "Line") });
      } else if (el.t === "circle") {
        slide.addShape("ellipse", { x: X(el.cx - el.r), y: Y(el.cy - el.r), w: 2 * el.r * s, h: 2 * el.r * s,
          fill: fill(el.fill), line: line(el.stroke), objectName: name("Dot") });
      } else if (el.t === "line") {
        const x1 = Math.min(el.x1, el.x2), y1 = Math.min(el.y1, el.y2);
        slide.addShape("line", { x: X(x1), y: Y(y1), w: Math.abs(el.x2 - el.x1) * s, h: Math.abs(el.y2 - el.y1) * s,
          flipV: (el.x2 - el.x1) * (el.y2 - el.y1) < 0, line: line(el.stroke), objectName: name("Tick") });
      } else if (el.t === "rect") {
        slide.addShape("roundRect", { x: X(el.x), y: Y(el.y), w: el.width * s, h: el.height * s,
          rectRadius: el.rx * s, fill: fill(el.fill), line: { type: "none" }, objectName: name("Highlighter swipe") });
      } else if (el.t === "text") {
        // One box per label; lines keep the SVG's baseline spacing.
        const first = el.lines[0];
        const runs = el.lines.map((l, i) => ({ text: l.text, options: {
          fontFace: l.bold ? SANS_BOLD : MONO, bold: l.bold, fontSize: +pt(l.size).toFixed(1), color: l.color,
          lineSpacing: +pt(i ? l.y - el.lines[i - 1].y : l.size * 1.2).toFixed(1),
          breakLine: i < el.lines.length - 1 } }));
        const widest = Math.max(...el.lines.map((l) => l.text.length * 0.62 * pt(l.size) / 72));
        const bx = X(el.x) - widest * { start: 0, middle: 0.5, end: 1 }[el.anchor];
        const top = Y(first.y) - (pt(first.size * 1.2) * 0.8) / 72;
        const h = (pt(el.lines[el.lines.length - 1].y - first.y) + pt(first.size * 1.2)) / 72;
        slide.addText(runs, { x: bx, y: top, w: widest, h, margin: 0, wrap: false, valign: "top",
          align: { start: "left", middle: "center", end: "right" }[el.anchor], isTextBox: true,
          objectName: name(`Label "${first.text.slice(0, 24)}"`) });
      }
    }
  });
}

// Post-process a slide's XML: wrap each step's shapes in a named group and
// fade the groups in one click at a time. pptxgenjs writes neither groups nor
// animations.
function groupAndAnimate(xml) {
  const shapeRe = /<p:sp>(?:(?!<\/p:sp>)[\s\S])*?<\/p:sp>/g;
  const shapes = xml.match(shapeRe) || [];
  const nameOf = (sp) => (sp.match(/<p:cNvPr id="\d+" name="([^"]*)"/) || [])[1] || "";
  const tagged = shapes.filter((sp) => STEP_TAG.test(nameOf(sp)));
  if (!tagged.length) return xml;
  const byStep = new Map(), stepNames = [];
  for (const sp of tagged) {
    const [, k, stepName] = nameOf(sp).match(STEP_TAG);
    stepNames[k] = stepName;
    if (!byStep.has(+k)) byStep.set(+k, []);
    let out = sp.replace(/(<p:cNvPr id="\d+" name=")§[^§]*§/, "$1");
    // Round ends and joins on the curves, as on the homepage: the estimate
    // is five segments that thicken toward 'now', and square ends show seams.
    if (/name="Line \d+"/.test(out)) {
      out = out.replace(/<a:ln w="(\d+)"[^>]*>([\s\S]*?)<\/a:ln>/, (m, w, inner) =>
        `<a:ln w="${w}" cap="rnd">${inner.replace(/(<a:headEnd|$)/, "<a:round/>$1")}</a:ln>`);
    }
    byStep.get(+k).push(out);
  }
  let nextId = 900;
  const groups = [...byStep.entries()].sort((a, b) => a[0] - b[0]).map(([k, members]) => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const sp of members) {
      const m = sp.match(/<a:off x="(-?\d+)" y="(-?\d+)"\/>\s*<a:ext cx="(\d+)" cy="(\d+)"\/>/);
      const [ox, oy, cx, cy] = m.slice(1).map(Number);
      x0 = Math.min(x0, ox); y0 = Math.min(y0, oy); x1 = Math.max(x1, ox + cx); y1 = Math.max(y1, oy + cy);
    }
    const id = nextId++;
    const box = `<a:off x="${x0}" y="${y0}"/><a:ext cx="${x1 - x0}" cy="${y1 - y0}"/>` +
      `<a:chOff x="${x0}" y="${y0}"/><a:chExt cx="${x1 - x0}" cy="${y1 - y0}"/>`;
    return { id, xml: `<p:grpSp><p:nvGrpSpPr><p:cNvPr id="${id}" name="${k + 1} · ${stepNames[k]}"/>` +
      `<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>${box}</a:xfrm></p:grpSpPr>` +
      members.join("") + "</p:grpSp>" };
  });
  // Tagged shapes are contiguous (the figure is drawn in one go), so the
  // groups replace the run in place and the z-order holds.
  const start = xml.indexOf(tagged[0]);
  const last = tagged[tagged.length - 1];
  const end = xml.indexOf(last) + last.length;
  xml = xml.slice(0, start) + groups.map((g) => g.xml).join("") + xml.slice(end);

  let t = 3;
  const click = (spid) => {
    const [a, b, c, d, e] = [t++, t++, t++, t++, t++];
    const tgt = `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>`;
    return `<p:par><p:cTn id="${a}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>` +
      `<p:par><p:cTn id="${b}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>` +
      `<p:par><p:cTn id="${c}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="clickEffect">` +
      `<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>` +
      `<p:set><p:cBhvr><p:cTn id="${d}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt}` +
      `<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>` +
      `<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${e}" dur="500"/>${tgt}</p:cBhvr></p:animEffect>` +
      `</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>`;
  };
  const timing = `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>` +
    `<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>` +
    groups.map((g) => click(g.id)).join("") +
    `</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>` +
    `<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>` +
    `</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>`;
  return xml.replace("</p:clrMapOvr>", `</p:clrMapOvr>${timing}`);
}

module.exports = { addApproachFigure, groupAndAnimate };
