// Builds docs/presentation/LYRA_deck.pptx (at most 7 slides).
// Run from anywhere: node docs/presentation/_src/build_deck.js
// One-time setup: (cd docs/presentation/_src && npm install)
// All paths are relative to this script.
const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');
const { applyTheme } = require('./theme.js');

const PRES_DIR = path.join(__dirname, '..');                          // docs/presentation
const DRAWINGS = path.join(__dirname, '..', '..', 'drawings', 'png');  // docs/drawings/png
const SHOTS = process.env.LYRA_SCREENSHOTS || path.join(PRES_DIR, 'screenshots'); // app screenshots (optional)
const OUT = path.join(PRES_DIR, 'LYRA_deck.pptx');
const DRAWING_FILES = { 1: '01_general_view.png', 2: '02_front_side_fov.png', 3: '03_handle_section.png', 4: '04_system_diagram.png', 5: '05_compact_config.png' };
const img = n => {
  const p = path.join(DRAWINGS, DRAWING_FILES[n]);
  if (!fs.existsSync(p)) throw new Error('missing drawing: ' + p);
  return p;
};

// Screenshots: prefer 01_overview.png, then the next PNGs by name; use at most 2.
function pickScreenshots() {
  if (!fs.existsSync(SHOTS)) return [];
  const all = fs.readdirSync(SHOTS).filter(f => /\.png$/i.test(f)).sort();
  const first = all.includes('01_overview.png') ? ['01_overview.png'] : [];
  return first.concat(all.filter(f => f !== '01_overview.png')).slice(0, 2).map(f => path.join(SHOTS, f));
}
// PNG size from the IHDR chunk (no extra dependency).
function pngSize(p) {
  const b = fs.readFileSync(p);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
// Fit an image into a box (inches), centered horizontally, top-aligned.
function fit(p, x, y, bw, bh) {
  const { w, h } = pngSize(p);
  const k = Math.min(bw / w, bh / h);
  return { x: x + (bw - w * k) / 2, y, w: w * k, h: h * k };
}

const THEME = { name: 'LYRA Orbit', headFontFace: 'Cambria', bodyFontFace: 'Calibri',
  colors: { dk1: '0B1D33', lt1: 'FFFFFF', dk2: '33475B', lt2: 'EEF3F7',
    accent1: '00A6A6', accent2: '2BA84A', accent3: 'E8A317', accent4: 'D64545', accent5: '5B7DB1', accent6: '8A99A8',
    hlink: '00A6A6', folHlink: '5B7DB1' } };
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'LYRA: 3D health scan for long-duration missions';
pres.author = 'Alina Dmitriyeva, Daniil Shabalin';
const C = pres.SchemeColor;
const W = 13.333;

pres.defineSlideMaster({ title: 'DARK', background: { color: C.text1 },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.5, w: 12.1, h: 0.9, fontSize: 36, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: 'top' }, text: '' } }],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6 } });
pres.defineSlideMaster({ title: 'TITLE', background: { color: C.text1 },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 1.2, w: 6.3, h: 1.3, fontSize: 72, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: 'top', align: 'left', margin: 0 }, text: '' } }] });
pres.defineSlideMaster({ title: 'CONTENT', background: { color: C.background1 },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 32, bold: true, color: C.text1, fontFace: THEME.headFontFace, valign: 'middle' }, text: '' } },
    { text: { text: 'LYRA · NASA Space Apps 2026 · Screening, not a diagnosis', options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.accent6, isTextBox: true } } }],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6 } });

const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, fontSize: 14, color: C.text1, valign: 'top', margin: 0 }, o));
const SI = (s, x, y, w) => T(s, 'Drawing: LYRA concept, SVG drawn with AI (SI) assistance; dimensions approximate', { x, y, w, h: 0.25, fontSize: 10, color: C.accent6, italic: true });

// 1 Title
pres.addSection({ title: 'Intro' });
let s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'Intro' });
s.addImage({ path: img(1), x: 7.3, y: 0.9, w: 5.5, h: 3.89, objectName: 'General view drawing' });
s.addText('LYRA', { placeholder: 'title' });
T(s, '3D health scan for long-duration missions', { x: 0.6, y: 2.6, w: 6.3, h: 0.6, fontSize: 24, color: C.accent1 });
T(s, 'Step in. Grip. Know.', { x: 0.6, y: 3.3, w: 6.3, h: 0.5, fontSize: 20, italic: true, color: C.background1 });
T(s, [
  { text: 'Challenge: ', options: { bold: true } }, { text: 'Create Health Monitoring Software for Astronauts on Space Missions', options: { breakLine: true } },
  { text: 'Team: ', options: { bold: true } }, { text: 'LYRA', options: { breakLine: true } },
  { text: 'Members: ', options: { bold: true } }, { text: 'Alina Dmitriyeva, Daniil Shabalin' }
], { x: 0.6, y: 4.9, w: 6.5, h: 1.3, fontSize: 16, color: C.background1, paraSpaceAfter: 6 });
T(s, 'A 90-second daily scan at the station wall. No wearables, no electrodes. Screening, not a diagnosis.', { x: 7.3, y: 5.25, w: 5.5, h: 0.9, fontSize: 16, color: C.background2 });
SI(s, 7.3, 4.85, 5.5);

// 2 Problem
pres.addSection({ title: 'Problem' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problem' });
s.addText('Space changes the body daily, and the doctor is far away', { placeholder: 'title' });
const stats = [
  ['1 to 1.5%', 'bone mineral density lost per month in weight-bearing bones', 'NASA HRP, Gravity Fields', C.accent4],
  ['>2 L', 'of fluid leaves the legs by day 3 ("puffy face, bird legs")', 'NASA Skylab 4 anthropometry (NTRS)', C.accent3],
  ['up to 3%', 'taller as the spine unloads', 'NASA, Spinal Ultrasound', C.accent5],
  ['20 min', 'one-way comm delay to Mars: the crew must self-screen', 'NASA HRP, Distance from Earth', C.accent1]];
stats.forEach((st, i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 2.85, h: 3.3, rectRadius: 0.12, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: 'stat card ' + (i + 1) });
  T(s, st[0], { x: x + 0.25, y: 1.8, w: 2.4, h: 0.9, fontSize: 40, bold: true, color: st[3], fontFace: THEME.headFontFace });
  T(s, st[1], { x: x + 0.25, y: 2.8, w: 2.4, h: 1.3, fontSize: 15 });
  T(s, st[2], { x: x + 0.25, y: 4.25, w: 2.4, h: 0.45, fontSize: 11, color: C.text2, italic: true });
});
T(s, [
  { text: 'NASA HRP risks in scope: ', options: { bold: true } },
  { text: 'bone and muscle loss · headward fluid shift / SANS · cardiovascular adaptations · altered immunity · sleep · behavioral health · radiation (5 Hazards: Gravity, Radiation, Isolation, Distance, Hostile/Closed).', options: { breakLine: true } },
  { text: 'Gap: ', options: { bold: true } },
  { text: 'many checks today are episodic and operator-heavy. A crew needs a fast daily check that knows which changes are expected adaptation and which are not.' }
], { x: 0.6, y: 5.15, w: 12.1, h: 1.6, fontSize: 15, paraSpaceAfter: 8 });

// 3 How it works
pres.addSection({ title: 'Solution' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Solution' });
s.addText('Step in, grip, know: a 90-second scan with nothing to wear', { placeholder: 'title' });
s.addImage({ path: img(2), x: 0.6, y: 1.4, w: 6.2, h: 4.38, objectName: 'Front and side view with fields of view' });
SI(s, 0.6, 5.85, 6.2);
const steps = [
  ['20 s', '3D scan', 'Structured light (face, mm-level swelling) + ToF cameras (body volume, legs, height, posture). ToF already flew on ISS in Astrobee (pmd PicoFlexx).'],
  ['30 s', 'Hands on grips', 'Ultrasound Doppler palm blood flow, PPG pulse, HRV, SpO₂, palm temperature. Solid-hydrogel tape cassette: our design.'],
  ['2×', 'Max squeeze', 'Grip strength left/right. Weekly: 2-min isometric hold "keep it in the green" game.'],
  ['15 s', 'Voice check-in', 'Sleep, wellbeing, symptoms. Voice prompts on every step; commands "start", "repeat", "stop".']];
steps.forEach((st, i) => {
  const y = 1.45 + i * 1.2;
  s.addShape(pres.shapes.OVAL, { x: 7.2, y, w: 0.95, h: 0.95, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: 'step ' + (i + 1) });
  T(s, st[0], { x: 7.2, y, w: 0.95, h: 0.95, fontSize: 16, bold: true, color: C.background1, align: 'center', valign: 'middle' });
  T(s, st[1], { x: 8.35, y, w: 4.4, h: 0.35, fontSize: 16, bold: true });
  T(s, st[2], { x: 8.35, y: y + 0.36, w: 4.4, h: 0.8, fontSize: 13, color: C.text2 });
});
T(s, 'Result: Normal / Recheck / Deviation (or Remeasure) + a plain-language instruction, sent to the flight surgeon.', { x: 0.6, y: 6.35, w: 12.1, h: 0.45, fontSize: 15, bold: true, color: C.accent1 });

// 4 NASA data
pres.addSection({ title: 'NASA data' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'NASA data' });
s.addText('You vs. NASA expected adaptation', { placeholder: 'title' });
const days = [0, 1, 2, 3, 5, 7, 10, 14, 21, 28, 35, 42, 49, 56];
const exp = d => -8 * (1 - Math.exp(-d / 2));
const astro = d => d <= 21 ? exp(d) + 0.6 * Math.sin(d) : exp(d) - 0.22 * (d - 21);
const r = v => Math.round(v * 10) / 10;
s.addChart(pres.charts.LINE, [
  { name: 'Expected corridor (upper)', labels: days.map(String), values: days.map(d => r(exp(d) + 3)) },
  { name: 'Expected corridor (lower)', labels: days.map(String), values: days.map(d => r(exp(d) - 3)) },
  { name: 'Astronaut (simulated)', labels: days.map(String), values: days.map(d => r(astro(d))) }],
  { x: 0.6, y: 1.35, w: 7.0, h: 4.6, chartColors: ['8A99A8', '8A99A8', 'D64545'], lineSize: 2, lineDataSymbol: 'none',
    showTitle: true, title: 'Lower-leg volume, % change vs. pre-flight, by mission day', titleFontSize: 13, titleColor: '0B1D33', titleFontFace: '+mn-lt',
    showLegend: true, legendPos: 'b', legendFontSize: 11, legendFontFace: '+mn-lt',
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 11, catAxisLabelColor: '33475B', valAxisLabelColor: '33475B', catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt',
    valAxisMinVal: -20, valAxisMaxVal: 4, valGridLine: { color: 'E1E7ED', size: 0.5 }, catGridLine: { style: 'none' }, objectName: 'NASA corridor chart' });
T(s, 'The simulated astronaut leaves the corridor after about day 21: LYRA shows Recheck, suggests the onboard countermeasure and a re-scan.', { x: 0.6, y: 6.05, w: 7.0, h: 0.7, fontSize: 12, color: C.text2, italic: true });
T(s, [
  { text: 'Published NASA/CSA adaptation data → expected corridor', options: { bold: true, breakLine: true } },
  { text: 'Bone loss 1 to 1.5% per month (NASA, CSA); fluid shift to the head (NASA); >2 L leg fluid by day 3 (Skylab 4); up to +3% height (NASA); ISS dose 0.2 to 0.5 mSv/day (NASA NTRS).', options: { breakLine: true } },
  { text: 'Every metric → HRP risk → hazard', options: { bold: true, breakLine: true } },
  { text: 'On-screen "why it matters" cards cite the NASA risk. 27 metrics, 8 risks, 5 hazards, 36 sources in nasa_reference.json.', options: { breakLine: true } },
  { text: 'Linked HRP studies', options: { bold: true, breakLine: true } },
  { text: 'Thigh Cuff, Venous Haemostasis, Spinal Health, Standard Measures, CIPHER, Brain Fluid Pressure, ARCHeR, Tempus Pro; CSA radiation monitoring (CANS).', options: { breakLine: true } },
  { text: 'Honest labels', options: { bold: true, breakLine: true } },
  { text: 'Each number is tagged "cited" or "estimated" (team estimate). Most corridors are estimates to be calibrated on NASA LSDA/OSDR data.' }
], { x: 8.0, y: 1.4, w: 4.75, h: 5.4, fontSize: 13, paraSpaceAfter: 5 });

// 5 Demo / user experience
pres.addSection({ title: 'Demo' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Demo' });
s.addText('Demo: a clear status for the crew, a queue for the doctor', { placeholder: 'title' });
const shots = pickScreenshots();
if (shots.length === 0) {
  s.addImage({ path: img(4), x: 6.55, y: 1.4, w: 6.2, h: 4.38, objectName: 'System diagram' });
  SI(s, 6.55, 5.85, 6.2);
} else if (shots.length === 1) {
  s.addImage(Object.assign({ path: shots[0], objectName: 'App screenshot 1' }, fit(shots[0], 6.55, 1.4, 6.2, 4.9)));
  T(s, 'Screenshot: LYRA web app running on simulated crew data', { x: 6.55, y: 6.45, w: 6.2, h: 0.25, fontSize: 10, color: C.accent6, italic: true });
} else {
  shots.forEach((p, i) => s.addImage(Object.assign({ path: p, objectName: 'App screenshot ' + (i + 1) }, fit(p, 6.55, 1.4 + i * 2.6, 6.2, 2.45))));
  T(s, 'Screenshots: LYRA web app running on simulated crew data', { x: 6.55, y: 6.5, w: 6.2, h: 0.25, fontSize: 10, color: C.accent6, italic: true });
}
const st3 = [
  ['Normal', C.accent2, 'Within your baseline and the NASA corridor', 'Short summary and a streak of scan days.'],
  ['Recheck', C.accent3, 'Changing faster than NASA expects', 'One onboard action and a re-scan tomorrow.'],
  ['Deviation', C.accent4, 'Strong or multiple deviations', 'Step-by-step guidance; first in the doctor queue.'],
  ['Remeasure', C.accent5, 'Signal quality too low to judge', 'Repeat the measurement; no status is guessed.']];
st3.forEach((q, i) => {
  const y = 1.4 + i * 0.98;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 5.6, h: 0.86, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: 'status ' + q[0] });
  s.addShape(pres.shapes.OVAL, { x: 0.78, y: y + 0.2, w: 0.46, h: 0.46, fill: { color: q[1] }, line: { color: q[1] }, objectName: 'dot ' + q[0] });
  T(s, [{ text: q[0] + ': ', options: { bold: true, color: q[1] } }, { text: q[2], options: { bold: true } }], { x: 1.42, y: y + 0.1, w: 4.68, h: 0.32, fontSize: 14 });
  T(s, q[3], { x: 1.42, y: y + 0.46, w: 4.68, h: 0.32, fontSize: 13, color: C.text2 });
});
T(s, [
  { text: 'Web app (simulation): ', options: { bold: true } },
  { text: '3D point-cloud body, voice-guided daily scan and weekly grip test, you vs. NASA expected adaptation chart, HRP risk cards, doctor queue with ISS / Moon / Mars delay. Scenarios: Day 1, ISS · Day 40, ISS · Day 180, Mars · Anomaly, Lunar Gateway day 60.' }
], { x: 0.6, y: 5.4, w: 5.6, h: 1.4, fontSize: 13 });

// 6 Feasibility
pres.addSection({ title: 'Feasibility' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Feasibility' });
s.addText('Feasible parts, honest limits', { placeholder: 'title' });
s.addImage({ path: img(3), x: 0.6, y: 1.4, w: 5.6, h: 3.96, objectName: 'Handle section drawing' });
SI(s, 0.6, 5.42, 5.6);
const hdr = o => Object.assign({ bold: true, color: 'FFFFFF', fill: { color: '0B1D33' }, fontSize: 12 }, o || {});
const cell = { fontSize: 12, color: '0B1D33' };
s.addTable([
  [{ text: '', options: hdr() }, { text: 'Structured light (face)', options: hdr() }, { text: 'ToF (body)', options: hdr() }],
  [{ text: 'Near 0.5 m', options: cell }, { text: 'sub-mm to mm', options: cell }, { text: 'mm to cm, noisy', options: cell }],
  [{ text: 'Far 1 to 2 m', options: cell }, { text: 'degrades fast', options: cell }, { text: 'almost constant', options: cell }],
  [{ text: 'Interference', options: cell }, { text: 'projectors take turns', options: cell }, { text: 'different modulation freq.', options: cell }],
  [{ text: 'Launch vibration', options: cell }, { text: 'recalibrate on target', options: cell }, { text: 'less sensitive', options: cell }]],
  { x: 6.6, y: 1.45, w: 6.15, colW: [1.55, 2.3, 2.3], border: { type: 'solid', pt: 0.5, color: 'C9D3DD' }, objectName: 'SL vs ToF table' });
T(s, [
  { text: 'Grounded in flight tech: ', options: { bold: true } },
  { text: 'ToF on ISS (Astrobee); solid hydrogel ultrasound coupling (MIT, Science 2022, ≥48 h). The tape cassette and the station are our concept.', options: { breakLine: true } },
  { text: 'LYRA does not: ', options: { bold: true } },
  { text: 'diagnose, measure bone density, eye pressure or vision, measure radiation (it imports the station dosimeter), or determine mental state. Screening trends for the doctor only. Demo data are simulated.' }
], { x: 6.6, y: 4.0, w: 6.15, h: 2.8, fontSize: 13, paraSpaceAfter: 8 });

// 7 Scale & roadmap
pres.addSection({ title: 'Roadmap' });
s = pres.addSlide({ masterName: 'DARK', sectionTitle: 'Roadmap' });
s.addText('From the ISS to Mars, and back to Earth', { placeholder: 'title' });
s.addImage({ path: img(5), x: 7.3, y: 1.5, w: 5.45, h: 3.85, objectName: 'Compact folding configuration' });
T(s, 'Drawing: LYRA concept, SVG drawn with AI (SI) assistance; dimensions approximate', { x: 7.3, y: 5.42, w: 5.45, h: 0.25, fontSize: 10, color: C.accent6, italic: true });
const envs = [['ISS / Gateway / Moon base', 'Full station on module rails'], ['Mars base', 'Autonomous mode, 20-min delay queue'], ['Ship / rover', 'Compact folding kit (sheet 5)'], ['Earth', 'Polar stations, submarines, remote clinics, aging adults (CSA)']];
envs.forEach((e, i) => {
  const y = 1.55 + i * 0.85;
  s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.05, w: 0.3, h: 0.3, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: 'env dot ' + (i + 1) });
  T(s, e[0], { x: 1.1, y, w: 5.8, h: 0.35, fontSize: 16, bold: true, color: C.background1 });
  T(s, e[1], { x: 1.1, y: y + 0.37, w: 5.8, h: 0.4, fontSize: 13, color: C.background2 });
});
T(s, [
  { text: 'Next: ', options: { bold: true, color: C.accent1 } },
  { text: 'calibrate corridors on NASA LSDA/OSDR and Standard Measures → bed-rest and analog tests → handle + hydrogel cassette prototype → parabolic flight.' }
], { x: 0.6, y: 5.1, w: 6.4, h: 1.0, fontSize: 14, color: C.background1 });
T(s, 'Step in. Grip. Know.', { x: 0.6, y: 6.3, w: 6.4, h: 0.5, fontSize: 22, italic: true, bold: true, color: C.accent1, fontFace: THEME.headFontFace });

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('written', path.relative(process.cwd(), OUT));
  console.log(shots.length ? 'demo slide screenshots: ' + shots.map(p => path.basename(p)).join(', ')
    : 'demo slide screenshots: none found in docs/presentation/screenshots (system diagram used)');
})();
