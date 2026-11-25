// Builds hakimi-template.pptx: the website's look (graph paper, ink, highlighter
// bands, DM Sans + Space Mono) as a slide template for Google Slides / Keynote.
//   cd slides && npm install && npm run build
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const pptxgen = require("pptxgenjs");

const OUT = path.join(__dirname, "hakimi-template.pptx");
const GRID = path.join(__dirname, "grid.png");

// ── Tokens (style.css :root) ────────────────────────────────────────────────
const PAPER = "F5F2EC";
const INK = "111118";
const INK_BLUE = "1A2C6B";
const INK_DIM = "787677"; // --ink-dim (ink @ 0.55) flattened onto paper
const INK_FAINT = "D3D0CC"; // --ink-faint (ink @ 0.15) flattened onto paper
const HL = {
  yellow: "FFFF77", slate: "7777FF", helio: "C977FF", violet: "FF77E4",
  red: "FF7792", cheese: "FFAE77", mint: "77FFE4", lime: "AAFF77",
};
// Band opacity per hue, from index.html's .section-label.s-* (--hl-a):
// the blues outweigh the yellows at equal alpha.
const HL_ALPHA = {
  yellow: 0.75, slate: 0.65, helio: 0.55, violet: 0.55,
  red: 0.55, cheese: 0.65, mint: 0.65, lime: 0.65,
};

const SANS = "DM Sans Light"; // the site's headings are DM Sans 300
const MONO = "Space Mono";

// ── Graph paper ─────────────────────────────────────────────────────────────
// 60% of the site's grid strength (--blue-g 0.20 → 0.12, --blue-G 0.42 → 0.25)
// so it stays behind the content. 3840×2160 = 288px per inch on a 13.33" slide;
// major cell 240px (0.83") with 5 minor cells, the site's 80/16 ratio.
function writeGrid(file) {
  const W = 3840, H = 2160, MAJOR = 240, MINOR = 48;
  const paper = [0xf5, 0xf2, 0xec], blue = [80, 140, 200];
  const mix = (a) => paper.map((p, i) => Math.round(p * (1 - a) + blue[i] * a));
  const minor = mix(0.12), major = mix(0.25);
  const kind = (v) => (v % MAJOR < 3 ? 2 : v % MINOR < 2 ? 1 : 0);
  const raw = Buffer.alloc((W * 3 + 1) * H);
  for (let y = 0; y < H; y++) {
    const ky = kind(y), row = y * (W * 3 + 1);
    raw[row] = 0;
    for (let x = 0; x < W; x++) {
      const k = Math.max(ky, kind(x));
      const c = k === 2 ? major : k === 1 ? minor : paper;
      raw.set(c, row + 1 + x * 3);
    }
  }
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const c = Buffer.alloc(4); c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4);
  ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB
  fs.writeFileSync(file, Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]));
}

// ── Layout grid (inches, LAYOUT_WIDE 13.333 × 7.5) ──────────────────────────
const SW = 13.333, SH = 7.5;
const MX = 0.9; // side margin
const CW = SW - 2 * MX; // content width
const EYEBROW_Y = 0.6, TITLE_Y = 0.95, BODY_Y = 2.05, FOOT_Y = 6.92;
const AGENDA = { pt: 22, line: 28, pitch: 46 }; // agenda rows, in points
const MONO_ADV = 0.611; // Space Mono advance width, in em

// The SH mark (nav logo): Space Mono Bold, wide tracking, a yellow band
// through the middle of the letters.
const shMark = () => [
  { rect: { x: MX - 0.03, y: FOOT_Y + 0.085, w: 0.3, h: 0.1,
      fill: { color: HL.yellow, transparency: 22 }, line: { type: "none" } } },
  { text: { text: "SH", options: { x: MX, y: FOOT_Y, w: 0.6, h: 0.27, margin: 0,
      fontFace: MONO, bold: true, fontSize: 10, charSpacing: 2.5, color: INK, valign: "middle" } } },
];
const slideNumber = { x: SW - MX - 1, y: FOOT_Y, w: 1, h: 0.27, align: "right",
  fontFace: MONO, fontSize: 10, color: INK_DIM };

// Eyebrow: the site's .page-eyebrow — a short rule, then wide-tracked caps.
const eyebrow = (y = EYEBROW_Y, text = "EYEBROW LABEL") => [
  { line: { x: MX, y: y + 0.15, w: 0.3, h: 0, line: { color: INK_BLUE, width: 0.75 } } },
  { placeholder: { options: { name: "eyebrow", type: "body", x: MX + 0.45, y, w: 8, h: 0.3,
      margin: 0, fontFace: MONO, fontSize: 12, charSpacing: 4, color: INK_BLUE, valign: "middle" },
      text } },
];
const title = (opts = {}) => ({ placeholder: { options: { name: "title", type: "title",
  x: MX, y: TITLE_Y, w: CW, h: 0.9, margin: 0, fontFace: SANS, fontSize: 36, color: INK,
  align: "left", valign: "top", ...opts }, text: "Slide title" } });
const body = (x, y, w, h, text = "Body text") => ({ placeholder: { options: {
  name: "body", type: "body", x, y, w, h, margin: 0, fontFace: MONO, fontSize: 16, color: INK,
  valign: "top", lineSpacingMultiple: 1.25, paraSpaceAfter: 8 }, text } });
// Figure panel: the grid shows around it, never behind the data.
const panel = (x, y, w, h, dark) => ({ rect: { x, y, w, h,
  fill: { color: dark ? INK : "FFFFFF" }, line: { color: dark ? INK : INK_FAINT, width: 0.75 } } });
const pic = (name, x, y, w, h, dark) => ({ placeholder: { options: { name, type: "pic",
  x: x + 0.15, y: y + 0.15, w: w - 0.3, h: h - 0.3, color: dark ? PAPER : INK_DIM,
  fontFace: MONO, fontSize: 12 }, text: "Drop figure here" } });
const caption = (name, x, y, w) => ({ placeholder: { options: { name, type: "body",
  x, y, w, h: 0.32, margin: 0, fontFace: MONO, fontSize: 11, color: INK_DIM, valign: "top" },
  text: "Caption or source" } });

function defineLayouts(pres) {
  const bg = { path: GRID };
  const foot = { slideNumber };

  pres.defineSlideMaster({ title: "Title", background: bg, objects: [
    ...eyebrow(2.15, "TALK · VENUE · DATE"),
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.6, w: 10.8, h: 2.1,
        margin: 0, fontFace: SANS, fontSize: 54, color: INK, align: "left", valign: "top", lineSpacingMultiple: 0.95 },
        text: "Talk title" } },
    { placeholder: { options: { name: "byline", type: "body", x: MX, y: 5.2, w: 9, h: 0.9,
        margin: 0, fontFace: MONO, fontSize: 14, color: INK_DIM, valign: "top", lineSpacingMultiple: 1.3 },
        text: "Shabnam Hakimi, Ph.D." } },
  ] });

  pres.defineSlideMaster({ title: "Section divider", background: bg, objects: [
    ...eyebrow(2.75, "01"),
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 3.2, w: 10.8, h: 1.6,
        margin: 0, fontFace: SANS, fontSize: 60, color: INK, align: "left", valign: "top" }, text: "Section" } },
    ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "Title and text", background: bg, objects: [
    ...eyebrow(), title(), body(MX, BODY_Y, 10.4, 4.5), ...shMark(),
  ], ...foot });

  const fy = BODY_Y, fh = 4.25;
  pres.defineSlideMaster({ title: "Figure", background: bg, objects: [
    ...eyebrow(), title(), panel(MX, fy, CW, fh), pic("figure", MX, fy, CW, fh),
    caption("caption", MX, fy + fh + 0.12, CW), ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "Figure (dark panel)", background: bg, objects: [
    ...eyebrow(), title(), panel(MX, fy, CW, fh, true), pic("figure", MX, fy, CW, fh, true),
    caption("caption", MX, fy + fh + 0.12, CW), ...shMark(),
  ], ...foot });

  const lw = 7.35, rx = MX + lw + 0.45;
  pres.defineSlideMaster({ title: "Figure and takeaways", background: bg, objects: [
    ...eyebrow(), title(), panel(MX, fy, lw, fh), pic("figure", MX, fy, lw, fh),
    caption("caption", MX, fy + fh + 0.12, lw),
    body(rx, fy, SW - MX - rx, fh, "Takeaway"), ...shMark(),
  ], ...foot });

  const hw = (CW - 0.45) / 2;
  pres.defineSlideMaster({ title: "Two figures", background: bg, objects: [
    ...eyebrow(), title(),
    panel(MX, fy, hw, fh), pic("figure-left", MX, fy, hw, fh),
    caption("caption-left", MX, fy + fh + 0.12, hw),
    panel(MX + hw + 0.45, fy, hw, fh), pic("figure-right", MX + hw + 0.45, fy, hw, fh),
    caption("caption-right", MX + hw + 0.45, fy + fh + 0.12, hw),
    ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "Statement", background: bg, objects: [
    ...eyebrow(1.9),
    { placeholder: { options: { name: "statement", type: "title", x: MX, y: 2.4, w: 10.6, h: 3.4,
        margin: 0, fontFace: SANS, fontSize: 44, color: INK, align: "left", valign: "top", lineSpacingMultiple: 1.05 },
        text: "One sentence that carries the point" } },
    ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "Title only", background: bg, objects: [
    ...eyebrow(), title(), ...shMark(),
  ], ...foot });

  // Agenda rows are Space Mono on a fixed 46pt pitch (AGENDA), so a band can
  // be dropped behind the current section: see agendaBand().
  pres.defineSlideMaster({ title: "Agenda", background: bg, objects: [
    ...eyebrow(EYEBROW_Y, "OUTLINE"), title(),
    { placeholder: { options: { name: "agenda", type: "body", x: MX, y: BODY_Y, w: 10.4, h: 4.5,
        margin: 0, fontFace: MONO, fontSize: AGENDA.pt, color: INK, valign: "top",
        lineSpacing: AGENDA.line, paraSpaceAfter: AGENDA.pitch - AGENDA.line }, text: "01   Section" } },
    ...shMark(),
  ], ...foot });

  const cw3 = (CW - 2 * 0.45) / 3;
  pres.defineSlideMaster({ title: "Three columns", background: bg, objects: [
    ...eyebrow(), title(),
    ...[0, 1, 2].flatMap((i) => {
      const x = MX + i * (cw3 + 0.45);
      return [
        { placeholder: { options: { name: `head-${i + 1}`, type: "body", x, y: BODY_Y, w: cw3, h: 0.55,
            margin: 0, fontFace: SANS, fontSize: 24, color: INK, valign: "top" }, text: "Heading" } },
        { placeholder: { options: { name: `text-${i + 1}`, type: "body", x, y: BODY_Y + 0.8, w: cw3, h: 3.7,
            margin: 0, fontFace: MONO, fontSize: 14, color: INK, valign: "top",
            lineSpacingMultiple: 1.3, paraSpaceAfter: 6 }, text: "Text" } },
      ];
    }),
    ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "Big number", background: bg, objects: [
    ...eyebrow(1.5, "RESULT"),
    { placeholder: { options: { name: "number", type: "title", x: MX, y: 1.95, w: 7, h: 2.3,
        margin: 0, fontFace: SANS, fontSize: 140, color: INK, align: "left", valign: "top" }, text: "00%" } },
    { placeholder: { options: { name: "label", type: "body", x: MX, y: 4.45, w: 6.6, h: 1,
        margin: 0, fontFace: MONO, fontSize: 18, color: INK_BLUE, valign: "top", lineSpacingMultiple: 1.25 },
        text: "What the number measures" } },
    { placeholder: { options: { name: "context", type: "body", x: 8.4, y: 2.45, w: SW - MX - 8.4, h: 3,
        margin: 0, fontFace: MONO, fontSize: 14, color: INK_DIM, valign: "top",
        lineSpacingMultiple: 1.3, paraSpaceAfter: 6 }, text: "Context" } },
    ...shMark(),
  ], ...foot });

  // Timeline: four stops on an ink rule. Nodes are the LinkedIn banner's: a
  // paper disc, ink ring, ink dot.
  const stops = [0, 1, 2, 3].map((i) => MX + i * 2.95);
  const LINE_Y = 3.9;
  pres.defineSlideMaster({ title: "Timeline", background: bg, objects: [
    ...eyebrow(), title(),
    { line: { x: MX, y: LINE_Y, w: CW, h: 0, line: { color: INK, width: 1, endArrowType: "triangle" } } },
    ...stops.flatMap((x, i) => [
      { text: { text: "", options: { shape: pres.ShapeType.ellipse, x, y: LINE_Y - 0.11, w: 0.22, h: 0.22,
          fill: { color: PAPER }, line: { color: INK, width: 1.25 } } } },
      { text: { text: "", options: { shape: pres.ShapeType.ellipse, x: x + 0.085, y: LINE_Y - 0.025, w: 0.05, h: 0.05,
          fill: { color: INK }, line: { type: "none" } } } },
      { placeholder: { options: { name: `when-${i + 1}`, type: "body", x, y: LINE_Y - 0.6, w: 2.6, h: 0.35,
          margin: 0, fontFace: MONO, fontSize: 14, bold: true, color: INK_BLUE, valign: "bottom" }, text: "Year" } },
      { placeholder: { options: { name: `what-${i + 1}`, type: "body", x, y: LINE_Y + 0.35, w: 2.6, h: 2.2,
          margin: 0, fontFace: MONO, fontSize: 14, color: INK, valign: "top", lineSpacingMultiple: 1.3 },
          text: "What happened" } },
    ]),
    ...shMark(),
  ], ...foot });

  const half = (CW - 0.6) / 2;
  pres.defineSlideMaster({ title: "Acknowledgments", background: bg, objects: [
    ...eyebrow(EYEBROW_Y, "ACKNOWLEDGMENTS"), title(),
    ...[0, 1].flatMap((i) => {
      const x = MX + i * (half + 0.6);
      return [
        { placeholder: { options: { name: `group-${i + 1}`, type: "body", x, y: BODY_Y, w: half, h: 0.3,
            margin: 0, fontFace: MONO, fontSize: 12, charSpacing: 4, color: INK_BLUE, valign: "top" },
            text: "GROUP" } },
        { placeholder: { options: { name: `names-${i + 1}`, type: "body", x, y: BODY_Y + 0.5, w: half, h: 3.9,
            margin: 0, fontFace: MONO, fontSize: 14, color: INK, valign: "top",
            lineSpacingMultiple: 1.3, paraSpaceAfter: 4 }, text: "Names" } },
      ];
    }),
    ...shMark(),
  ], ...foot });

  pres.defineSlideMaster({ title: "References", background: bg, objects: [
    ...eyebrow(EYEBROW_Y, "REFERENCES"), title(),
    { placeholder: { options: { name: "references", type: "body", x: MX, y: BODY_Y, w: CW, h: 4.55,
        margin: 0, fontFace: MONO, fontSize: 12, color: INK, valign: "top",
        lineSpacingMultiple: 1.25, paraSpaceAfter: 8 }, text: "Author, A. (Year). Title. Venue." } },
    ...shMark(),
  ], ...foot });

  // Full bleed: plain paper, no grid, no footer; the picture fills the slide.
  pres.defineSlideMaster({ title: "Full-bleed image", background: { color: PAPER }, objects: [
    { placeholder: { options: { name: "image", type: "pic", x: 0, y: 0, w: SW, h: SH,
        color: INK_DIM, fontFace: MONO, fontSize: 14 }, text: "Drop image here" } },
  ] });

  pres.defineSlideMaster({ title: "Closing", background: bg, objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.3, w: 10.8, h: 1.4,
        margin: 0, fontFace: SANS, fontSize: 60, color: INK, align: "left", valign: "top" }, text: "Thank you" } },
    { placeholder: { options: { name: "contact", type: "body", x: MX, y: 4.15, w: 9, h: 1.6,
        margin: 0, fontFace: MONO, fontSize: 16, color: INK_BLUE, valign: "top", lineSpacingMultiple: 1.5 },
        text: "Contact" } },
  ] });
}

// A highlighter band behind the start of a title, after .hero-highlight: a
// stripe through the lower middle of the letters, padded 0.05em each side.
// `width` is the span's measured width in inches (DM Sans Light, via PIL), so
// the bands fit the sample text; on a real slide, drag the band's ends to fit.
// Google Slides sets DM Sans Light ~5% wider than Keynote and PIL do (measured
// on its PDF export), so the bands are sized for Slides and run a little long
// in Keynote.
const SLIDES_WIDTH = 1.05;
// `drop` is where the stripe starts, in em below the box top: 0.56 suits
// title placeholders; body placeholders set their text higher.
function band(slide, color, top, pt, width, x = MX, drop = 0.56) {
  const em = pt / 72;
  slide.addShape("rect", { x: x - 0.05 * em, y: top + drop * em,
    w: width * SLIDES_WIDTH + 0.1 * em, h: 0.32 * em,
    objectName: "Highlighter band",
    fill: { color: HL[color], transparency: Math.round((1 - HL_ALPHA[color]) * 100) },
    line: { type: "none" } });
}

// Band behind agenda row `i` (0-based) of `chars` characters.
function agendaBand(slide, color, i, chars) {
  const { pt, line, pitch } = AGENDA;
  slide.addShape("rect", {
    x: MX - 0.06, y: BODY_Y + (i * pitch + (line - pt) / 2 + 0.5 * pt) / 72,
    w: (chars * MONO_ADV * pt) / 72 + 0.12, h: (0.36 * pt) / 72,
    objectName: "Highlighter band",
    fill: { color: HL[color], transparency: Math.round((1 - HL_ALPHA[color]) * 100) },
    line: { type: "none" } });
}

function sampleSlides(pres) {
  const sections = new Set();
  const add = (masterName, sectionTitle) => {
    if (!sections.has(sectionTitle)) { pres.addSection({ title: sectionTitle }); sections.add(sectionTitle); }
    return pres.addSlide({ masterName, sectionTitle });
  };
  let s = add("Title", "Opening");
  band(s, "yellow", 2.6, 54, 7.578); // "Your talk title goes here"
  s.addText("Your talk title goes here", { placeholder: "title" });
  s.addText("TALK · VENUE · MONTH YEAR", { placeholder: "eyebrow" });
  s.addText([
    { text: "Shabnam Hakimi, Ph.D.", options: { breakLine: true, color: INK } },
    { text: "Affiliation" },
  ], { placeholder: "byline" });
  s.addNotes("Title layout. The yellow band is a separate shape named 'Highlighter band': drag its ends to sit under the word you want to mark, or delete it.");

  const agenda = ["Background", "Research", "Looking ahead", "Discussion"];
  s = add("Agenda", "Opening");
  agendaBand(s, "yellow", 1, `02   ${agenda[1]}`.length);
  s.addText("OUTLINE", { placeholder: "eyebrow" });
  s.addText("Outline", { placeholder: "title" });
  s.addText(agenda.map((t, i) => ({
    text: `0${i + 1}   ${t}`, options: { breakLine: i < agenda.length - 1 } })), { placeholder: "agenda" });
  s.addNotes("Agenda. Repeat it at each section break and move the band to the current row (it's sized for the row's character count; Space Mono is monospaced, so every character is the same width).");

  s = add("Section divider", "Research");
  band(s, "slate", 3.2, 60, 3.332); // "Research"
  s.addText("01 · RESEARCH", { placeholder: "eyebrow" });
  s.addText("Research", { placeholder: "title" });
  s.addNotes("Section divider. Band colour = the research area's cluster colour (see the palette slide at the end).");

  s = add("Title and text", "Research");
  s.addText("BACKGROUND", { placeholder: "eyebrow" });
  s.addText("A title that states the slide's one message", { placeholder: "title" });
  s.addText([
    { text: "Short points, one idea each", options: { bullet: true, breakLine: true } },
    { text: "Space Mono keeps the site's typewriter voice", options: { bullet: true, breakLine: true } },
    { text: "Three or four is plenty", options: { bullet: true } },
  ], { placeholder: "body" });

  s = add("Three columns", "Research");
  s.addText("PROGRAM", { placeholder: "eyebrow" });
  s.addText("Three threads, one question", { placeholder: "title" });
  const cw3 = (CW - 2 * 0.45) / 3;
  [["slate", "First thread", 1.762], ["red", "Second thread", 2.256], ["lime", "Third thread", 1.872]]
    .forEach(([c, h, w], i) => {
      // 0.6em: Slides sets body-placeholder text lower than Keynote (0.5em there)
      band(s, c, BODY_Y, 24, w, MX + i * (cw3 + 0.45), 0.6);
      s.addText(h, { placeholder: `head-${i + 1}` });
      s.addText("Two or three lines on what this thread asks and what it has found so far.", { placeholder: `text-${i + 1}` });
    });
  s.addNotes("Three columns. Band each heading in its research area's colour so the talk matches the site.");

  s = add("Figure", "Research");
  s.addText("STUDY 1", { placeholder: "eyebrow" });
  s.addText("Full-width figure on a white panel", { placeholder: "title" });
  s.addText("Use the white-background export. Source: Author et al. (Year)", { placeholder: "caption" });

  s = add("Figure (dark panel)", "Research");
  s.addText("STUDY 1", { placeholder: "eyebrow" });
  s.addText("Ink panel for black-background figures", { placeholder: "title" });
  s.addText("Use when a figure only exists with a black background", { placeholder: "caption" });

  s = add("Figure and takeaways", "Research");
  s.addText("STUDY 2", { placeholder: "eyebrow" });
  s.addText("Figure with what to notice", { placeholder: "title" });
  s.addText("Caption or source", { placeholder: "caption" });
  s.addText([
    { text: "The first thing to see", options: { bullet: true, breakLine: true } },
    { text: "Why it matters", options: { bullet: true, breakLine: true } },
    { text: "What it changes", options: { bullet: true } },
  ], { placeholder: "body" });

  s = add("Two figures", "Research");
  s.addText("COMPARISON", { placeholder: "eyebrow" });
  s.addText("Two figures side by side", { placeholder: "title" });
  s.addText("Condition A", { placeholder: "caption-left" });
  s.addText("Condition B", { placeholder: "caption-right" });

  s = add("Big number", "Research");
  band(s, "yellow", 1.95, 140, 3.755); // "42%"
  s.addText("STUDY 2 · RESULT", { placeholder: "eyebrow" });
  s.addText("42%", { placeholder: "number" });
  s.addText("What the number measures, in one line", { placeholder: "label" });
  s.addText("Compared to what, measured how, with what N. Keep the number honest here so the slide can stay simple.", { placeholder: "context" });

  s = add("Title only", "Research");
  s.addText("MODEL", { placeholder: "eyebrow" });
  s.addText("A canvas for diagrams you build by hand", { placeholder: "title" });
  ["Input", "Model", "Output"].forEach((t, i) => {
    const x = MX + 0.6 + i * 3.7;
    s.addText(t, { x, y: 3.6, w: 2.4, h: 1, align: "center", valign: "middle", fontFace: MONO,
      fontSize: 16, color: INK, fill: { color: "FFFFFF" }, line: { color: INK_FAINT, width: 0.75 },
      isTextBox: true, objectName: `Box ${t}` });
    if (i < 2) s.addShape("line", { x: x + 2.5, y: 4.1, w: 1.1, h: 0,
      line: { color: INK_BLUE, width: 1.25, endArrowType: "triangle" }, objectName: "Arrow" });
  });
  s.addNotes("Title only: eyebrow and title on the grid, the rest is yours. White boxes with a faint rule and ink-blue arrows match the figure panels.");

  s = add("Full-bleed image", "Research");
  s.addNotes("Full-bleed image: plain paper, no grid or footer. Click the placeholder to add a photo, screenshot or video; it fills the slide.");

  s = add("Section divider", "Looking ahead");
  band(s, "mint", 3.2, 60, 6.71); // "What comes next"
  s.addText("02 · LOOKING AHEAD", { placeholder: "eyebrow" });
  s.addText("What comes next", { placeholder: "title" });

  s = add("Timeline", "Looking ahead");
  s.addText("ARC", { placeholder: "eyebrow" });
  s.addText("How the work has built", { placeholder: "title" });
  ["Year", "Year", "Year", "Next"].forEach((w, i) => {
    s.addText(w, { placeholder: `when-${i + 1}` });
    s.addText(i < 3 ? "One line on what this step added" : "Where it goes from here", { placeholder: `what-${i + 1}` });
  });

  s = add("Statement", "Looking ahead");
  band(s, "helio", 2.4, 44, 3.733); // "One sentence"
  s.addText("VISION", { placeholder: "eyebrow" });
  s.addText("One sentence that carries the point of this part of the talk", { placeholder: "statement" });

  s = add("Acknowledgments", "Closing");
  s.addText("ACKNOWLEDGMENTS", { placeholder: "eyebrow" });
  s.addText("With thanks", { placeholder: "title" });
  s.addText("COLLABORATORS", { placeholder: "group-1" });
  s.addText(["Name Surname, Institution", "Name Surname, Institution", "Name Surname, Institution"]
    .map((t, i, a) => ({ text: t, options: { breakLine: i < a.length - 1 } })), { placeholder: "names-1" });
  s.addText("FUNDING & SUPPORT", { placeholder: "group-2" });
  s.addText(["Funder, grant number", "Lab or program"]
    .map((t, i, a) => ({ text: t, options: { breakLine: i < a.length - 1 } })), { placeholder: "names-2" });
  s.addNotes("Acknowledgments. Logos, if any, go in a row along the bottom of the slide.");

  s = add("Closing", "Closing");
  band(s, "yellow", 2.3, 60, 3.693); // "Thank you"
  s.addText("Thank you", { placeholder: "title" });
  s.addText([
    { text: "hello@shabnamhakimi.com", options: { breakLine: true } },
    { text: "shabnamhakimi.com" },
  ], { placeholder: "contact" });

  s = add("References", "Appendix");
  s.addText("APPENDIX", { placeholder: "eyebrow" });
  s.addText("References", { placeholder: "title" });
  s.addText([
    "Author, A., & Author, B. (Year). Title of the paper. Journal, Volume(Issue), pages.",
    "Author, A. (Year). Title of the preprint. arXiv.",
    "Author, A., Author, B., & Author, C. (Year). Title of the proceedings paper. In Proceedings of Conference.",
  ].map((t, i, a) => ({ text: t, options: { breakLine: i < a.length - 1 } })), { placeholder: "references" });

  // Reference: all eight cluster colours. The theme only holds six accents,
  // so violet and lime live here for the eyedropper. Delete before presenting.
  s = add("Title and text", "Reference (delete)");
  s.addText("REFERENCE · DELETE BEFORE PRESENTING", { placeholder: "eyebrow" });
  s.addText("Highlighter palette", { placeholder: "title" });
  const names = [
    ["slate", "Motivated learning & self-regulation"], ["helio", "Creativity & design"],
    ["violet", "Psychology-guided generative AI"], ["red", "Intervention science"],
    ["yellow", "Preference elicitation & prediction"], ["cheese", "Social, cognitive, & affective neuroscience"],
    ["mint", "Consumer psychology & forecasting"], ["lime", "Agent state inference"],
  ];
  names.forEach(([k, label], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MX + col * 5.9, y = BODY_Y + row * 1.05;
    s.addShape("rect", { x, y, w: 0.75, h: 0.75, fill: { color: HL[k] },
      line: { color: INK_FAINT, width: 0.75 }, objectName: `Swatch ${k}` });
    s.addText([
      { text: label, options: { breakLine: true, color: INK } },
      { text: `#${HL[k]}  ·  band opacity ${Math.round(HL_ALPHA[k] * 100)}%`, options: { color: INK_DIM, fontSize: 11 } },
    ], { x: x + 0.95, y, w: 4.8, h: 0.75, margin: 0, fontFace: MONO, fontSize: 14,
      valign: "middle", isTextBox: true });
  });
  s.addNotes("Cluster colours match the website (graph, cv, projects). Six of the eight are theme accents; violet and lime are only here, so use the eyedropper. For yellow text on paper use #9A7C00 (dark amber), as the site does.");
}

// pptxgenjs sets the theme fonts but hard-codes Office's colour scheme and theme name; write
// ours into theme1.xml so the colour pickers in Slides/Keynote offer the palette.
// Only six accents fit, so violet and lime are on the palette slide instead.
async function applyColors(file, colors) {
  const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const part = "ppt/theme/theme1.xml";
  const slots = Object.entries(colors)
    .map(([k, v]) => `<a:${k}><a:srgbClr val="${v}"/></a:${k}>`).join("");
  const xml = (await zip.file(part).async("string")).replace(
    /<a:clrScheme name="[^"]*">[\s\S]*?<\/a:clrScheme>/,
    `<a:clrScheme name="Hakimi">${slots}</a:clrScheme>`);
  if (!xml.includes('clrScheme name="Hakimi"')) throw new Error("theme colour scheme not found");
  // Google Slides labels every layout "<theme name> - <layout>"; pptxgenjs
  // calls the theme "Office Theme".
  zip.file(part, xml.replace(/(<a:theme [^>]*name=")[^"]*"/, '$1Hakimi"'));
  // pptxgenjs always adds an empty layout named "DEFAULT" with a white
  // background; make it a usable blank paper slide.
  const blank = "ppt/slideLayouts/slideLayout1.xml";
  zip.file(blank, (await zip.file(blank).async("string"))
    .replace('<p:cSld name="DEFAULT">', '<p:cSld name="Blank">')
    .replace(/<p:bg>[\s\S]*?<\/p:bg>/, `<p:bg><p:bgPr><a:solidFill><a:srgbClr val="${PAPER}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>`));
  // The master has no background of its own, so its thumbnail in Google's
  // theme editor is white; give it paper.
  const master = "ppt/slideMasters/slideMaster1.xml";
  const mxml = await zip.file(master).async("string");
  if (!mxml.includes("<p:bg>")) {
    zip.file(master, mxml.replace(/<p:cSld>/, `<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="${PAPER}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>`));
  }
  // Repack without directory entries; cloud importers have choked on them.
  const out = new JSZip();
  for (const [name, f] of Object.entries(zip.files)) {
    if (!f.dir) out.file(name, await f.async("nodebuffer"), { createFolders: false });
  }
  fs.writeFileSync(file, await out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

async function main() {
  writeGrid(GRID);
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Shabnam Hakimi";
  pres.company = ""; // otherwise pptxgenjs writes its own name here
  pres.title = "Slide template";
  pres.theme = { headFontFace: SANS, bodyFontFace: MONO };
  defineLayouts(pres);
  sampleSlides(pres);
  await pres.writeFile({ fileName: OUT });
  await applyColors(OUT, {
    dk1: INK, lt1: "FFFFFF", dk2: INK_BLUE, lt2: PAPER,
    accent1: HL.yellow, accent2: HL.slate, accent3: HL.helio,
    accent4: HL.red, accent5: HL.cheese, accent6: HL.mint,
    hlink: INK_BLUE, folHlink: INK_BLUE,
  });
  console.log("wrote", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
