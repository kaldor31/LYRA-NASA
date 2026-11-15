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
const DRAWING_FILES = { 1: '01_general_view.png', 2: '02_front_side_views.png', 3: '03_doppler_cassette.png', 4: '04_face_pipeline.png', 5: '05_system_ai.png' };
const img = n => {
  const p = path.join(DRAWINGS, DRAWING_FILES[n]);
  if (!fs.existsSync(p)) throw new Error('missing drawing: ' + p);
  return p;
};

// App screenshots (from the frontend agent). Each slot names a preferred file and a drawing fallback,
// so the deck always builds; screenshots are included automatically once they exist.
const shot = name => { const p = path.join(SHOTS, name); return fs.existsSync(p) ? p : null; };
const usedShots = [];
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
pres.title = 'LYRA: Life-signs & Yield-based Readiness Analytics';
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
    { text: { text: 'LYRA · NASA Space Apps 2026 · Detects change, not a diagnosis', options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.accent6, isTextBox: true } } }],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6 } });

const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, fontSize: 14, color: C.text1, valign: 'top', margin: 0 }, o));
const SI = (s, x, y, w, c) => T(s, 'AI (SI) assisted drawing: LYRA concept, dimensions approximate', { x, y, w, h: 0.25, fontSize: 10, color: c || C.accent6, italic: true });

const SHOT_NOTE = 'App screenshot, simulated crew data (app code written with AI (SI) assistance)';
// Place a screenshot (fit, top-aligned) or fall back to a drawing; returns the bottom y of what was placed.
function placeShot(s, name, fallbackDrawing, x, y, w, h, label) {
  const p = shot(name);
  if (p) {
    usedShots.push(name);
    const box = fit(p, x, y, w, h);
    s.addImage(Object.assign({ path: p, objectName: 'App screenshot ' + name }, box));
    T(s, label || SHOT_NOTE, { x, y: box.y + box.h + 0.06, w, h: 0.25, fontSize: 10, color: C.accent6, italic: true });
    return box.y + box.h + 0.31;
  }
  const d = img(fallbackDrawing);
  const box = fit(d, x, y, w, h);
  s.addImage(Object.assign({ path: d, objectName: 'Drawing ' + DRAWING_FILES[fallbackDrawing] }, box));
  SI(s, x, box.y + box.h + 0.06, w);
  return box.y + box.h + 0.31;
}

// 1 Title
pres.addSection({ title: 'Intro' });
let s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'Intro' });
s.addImage({ path: img(1), x: 7.3, y: 0.9, w: 5.5, h: 3.89, objectName: 'General view drawing' });
SI(s, 7.3, 4.85, 5.5);
s.addText('LYRA', { placeholder: 'title' });
T(s, [
  { text: 'Life-signs & Yield-based Readiness Analytics', options: { breakLine: true } },
  { text: 'Lunar-to-orbit Your Readiness Assessment' }
], { x: 0.6, y: 2.55, w: 6.5, h: 0.75, fontSize: 18, color: C.accent1, paraSpaceAfter: 2 });
T(s, 'Step in. Scan. Know.', { x: 0.6, y: 3.45, w: 6.3, h: 0.5, fontSize: 22, italic: true, bold: true, color: C.background1, fontFace: THEME.headFontFace });
T(s, [
  { text: 'Challenge: ', options: { bold: true } }, { text: 'Create Health Monitoring Software for Astronauts on Space Missions', options: { breakLine: true } },
  { text: 'Team: ', options: { bold: true } }, { text: 'LYRA', options: { breakLine: true } },
  { text: 'Members: ', options: { bold: true } }, { text: 'Alina Dmitriyeva, Daniil Shabalin' }
], { x: 0.6, y: 4.6, w: 6.5, h: 1.5, fontSize: 16, color: C.background1, paraSpaceAfter: 6 });
T(s, 'A touch mirror between three camera frames for contactless crew readiness checks. It detects change and checks its own measurement quality; it does not diagnose.', { x: 7.3, y: 5.3, w: 5.5, h: 1.0, fontSize: 15, color: C.background2 });

// 2 Problem
pres.addSection({ title: 'Problem' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problem' });
s.addText('Space reshapes the body, and the doctor is far away', { placeholder: 'title' });
const stats = [
  ['1 to 1.5%', 'bone mineral density lost per month in weight-bearing bones', 'NASA HRP, Gravity Fields', C.accent4],
  ['>2 L', 'of fluid leaves the legs by day 3 ("puffy face, bird legs")', 'NASA Skylab 4 anthropometry (NTRS)', C.accent3],
  ['up to 3%', 'taller as the spine elongates; the neutral body posture changes', 'NASA NTRS, neutral body posture', C.accent5],
  ['20 min', 'one-way comm delay to Mars: the crew must check itself', 'NASA HRP, Distance from Earth', C.accent1]];
stats.forEach((st, i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 2.85, h: 3.3, rectRadius: 0.12, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: 'stat card ' + (i + 1) });
  T(s, st[0], { x: x + 0.2, y: 1.8, w: 2.5, h: 0.9, fontSize: 34, bold: true, color: st[3], fontFace: THEME.headFontFace });
  T(s, st[1], { x: x + 0.25, y: 2.8, w: 2.4, h: 1.3, fontSize: 15 });
  T(s, st[2], { x: x + 0.25, y: 4.25, w: 2.4, h: 0.45, fontSize: 11, color: C.text2, italic: true });
});
T(s, [
  { text: 'Gap: ', options: { bold: true } },
  { text: 'checks are episodic and operator-heavy, and an Earth posture is the wrong reference in microgravity. A crew needs a short, repeatable, contactless check that separates expected adaptation from sustained change.', options: { breakLine: true } },
  { text: 'LYRA: ', options: { bold: true, color: C.accent1 } },
  { text: 'compare each person with their own baseline and the environment mode, flag only sustained or repeated change, and say "measurement not confirmed" instead of guessing.' }
], { x: 0.6, y: 5.15, w: 12.1, h: 1.6, fontSize: 15, paraSpaceAfter: 8 });

// 3 User experience
pres.addSection({ title: 'Experience' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Experience' });
s.addText('Step in, scan, know: a short contactless check', { placeholder: 'title' });
const b3 = placeShot(s, '02_session.png', 2, 0.6, 1.4, 6.2, 3.6);
T(s, 'Palm zones on the mirror standardize the pose; they are not a medical sensor. Voice prompts at every step, a training mode, and "why it matters" cards.', { x: 0.6, y: Math.max(b3 + 0.1, 5.4), w: 6.2, h: 0.9, fontSize: 14, color: C.text2 });
const steps = [
  ['1', 'Position check', 'Feet, torso and palms on the mirror contours. Cameras check pose, light and stillness first.'],
  ['2', 'Face', 'Structured IR dots to depth, point cloud and mesh (key regions). RGB: expression, skin tone, rPPG pulse.'],
  ['3', 'Body in 3 planes', 'Skeleton from the front, side and back frames: shoulder, pelvis, head, trunk, scapulae.'],
  ['4', 'Result', 'One of 3 statuses with what changed, how reliable, what to do. Report queued to Earth.']];
steps.forEach((st, i) => {
  const y = 1.45 + i * 1.2;
  s.addShape(pres.shapes.OVAL, { x: 7.2, y, w: 0.8, h: 0.8, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: 'step ' + (i + 1) });
  T(s, st[0], { x: 7.2, y, w: 0.8, h: 0.8, fontSize: 20, bold: true, color: C.background1, align: 'center', valign: 'middle' });
  T(s, st[1], { x: 8.2, y, w: 4.55, h: 0.35, fontSize: 16, bold: true });
  T(s, st[2], { x: 8.2, y: y + 0.36, w: 4.55, h: 0.8, fontSize: 13, color: C.text2 });
});
T(s, 'Within baseline  ·  Repeat measurement  ·  Refer to specialist', { x: 7.2, y: 6.35, w: 5.55, h: 0.4, fontSize: 15, bold: true, color: C.accent1 });

// 4 How it works: face pipeline + AI modules
pres.addSection({ title: 'How it works' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'How it works' });
s.addText('Five checkable AI modules, one human decision', { placeholder: 'title' });
s.addImage({ path: img(4), x: 0.6, y: 1.35, w: 7.2, h: 5.09, objectName: 'Face pipeline drawing' });
SI(s, 0.6, 6.5, 7.2);
const mods = [
  ['Camera / IR processing', 'Face segmentation, IR dot detection, outlier rejection. The projector does not build the mesh: OpenCV, Open3D or PCL do.'],
  ['RGB + IR fusion', 'Colour, depth geometry and temporal features; one channel covers when the other degrades.'],
  ['rPPG with quality', 'Pulse plus quality, usable duration, motion, light, reject reason. Poor signal: "Measurement not confirmed".'],
  ['Body / posture', 'Three-view skeleton vs personal baseline and environment mode (Earth, microgravity, partial gravity).'],
  ['Change classifier', 'Within baseline, Repeat measurement or Refer to specialist, with the reason. The medical team decides.']];
mods.forEach((m, i) => {
  const y = 1.4 + i * 1.04;
  s.addShape(pres.shapes.OVAL, { x: 8.15, y: y + 0.02, w: 0.42, h: 0.42, fill: { color: C.accent5 }, line: { color: C.accent5 }, objectName: 'module ' + (i + 1) });
  T(s, String(i + 1), { x: 8.15, y: y + 0.02, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.background1, align: 'center', valign: 'middle' });
  T(s, m[0], { x: 8.75, y, w: 4.0, h: 0.3, fontSize: 14, bold: true });
  T(s, m[1], { x: 8.75, y: y + 0.3, w: 4.0, h: 0.7, fontSize: 11, color: C.text2 });
});

// 5 NASA and partner data
pres.addSection({ title: 'Data' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Data' });
s.addText('How NASA and open data make LYRA possible', { placeholder: 'title' });
// Real values from NASA OSDR OSD-575 (Inspiration4), file LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv:
// serum SODIUM, mmol/L. Baseline = mean of L-92, L-44, L-3; R+1 = first day after return. Lab range 135 to 146.
const crew = ['C001', 'C002', 'C003', 'C004'];
s.addChart(pres.charts.BAR, [
  { name: 'Pre-flight baseline (mean of 3)', labels: crew, values: [140.7, 142.0, 138.7, 139.7] },
  { name: 'Day after return (R+1)', labels: crew, values: [138, 137, 137, 140] }],
  { x: 0.6, y: 1.35, w: 5.9, h: 3.75, barDir: 'col', barGrouping: 'clustered', chartColors: ['8A99A8', 'D64545'],
    showTitle: true, title: 'NASA OSDR OSD-575 (Inspiration4): serum sodium, mmol/L', titleFontSize: 12, titleColor: '0B1D33', titleFontFace: '+mn-lt',
    showLegend: true, legendPos: 'b', legendFontSize: 10, legendFontFace: '+mn-lt',
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 9, dataLabelColor: '33475B', dataLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, catAxisLabelColor: '33475B', valAxisLabelColor: '33475B', catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt',
    valAxisMinVal: 130, valAxisMaxVal: 146, valAxisMajorUnit: 4, valGridLine: { color: 'E1E7ED', size: 0.5 }, catGridLine: { style: 'none' }, objectName: 'OSD-575 sodium chart' });
T(s, 'Crew C002: 142.0 before flight, 137 at R+1. Inside the lab range (135 to 146), yet 5 mmol/L below their own baseline. That is the LYRA idea: compare a person with themself. Illustration of the logic, not a clinical reading.', { x: 0.6, y: 5.2, w: 5.9, h: 1.0, fontSize: 12, color: C.text2, italic: true });
T(s, 'Provenance on every result: team recording · open dataset · NASA material · simulation', { x: 0.6, y: 6.3, w: 5.9, h: 0.5, fontSize: 12, bold: true, color: C.accent1 });
const hdr = o => Object.assign({ bold: true, color: 'FFFFFF', fill: { color: '0B1D33' }, fontSize: 11 }, o || {});
const cell = { fontSize: 10, color: '0B1D33', valign: 'top' };
const tag = (t, c) => ({ text: t, options: { fontSize: 10, bold: true, color: c, valign: 'top' } });
s.addTable([
  [{ text: 'Source', options: hdr() }, { text: 'Tag', options: hdr() }, { text: 'Role in LYRA', options: hdr() }],
  [{ text: 'NASA OSDR OSD-575, Inspiration4 metabolic panel: 4 crew, 19 analytes (mg/dL, mmol/L, g/dL, U/L), L-92 to R+194', options: cell }, tag('NASA material', 'B35C00'), { text: 'Our one concrete NASA dataset: personal baseline vs post-flight, on real crew data', options: cell }],
  [{ text: 'NASA Life Sciences Portal (LSDA), NASA Open Data Portal, OSDR', options: cell }, tag('NASA material', 'B35C00'), { text: 'Human research in flight and ground analogs since 1961: context and indicator choice', options: cell }],
  [{ text: 'NASA neutral body posture and anthropometry (HIDH, NASA-STD-3001, NTRS); HRP risks; CSA', options: cell }, tag('NASA / CSA', 'B35C00'), { text: 'Microgravity posture reference, spine elongation, risk cards, expected-adaptation corridors', options: cell }],
  [{ text: 'CameraVitals (COHFACE): RGB video with PPG and breathing, 160 one-minute clips, 40 people', options: cell }, tag('Open dataset', '1F7A3A'), { text: 'rPPG validation on Earth (not microgravity)', options: cell }],
  [{ text: 'Team recordings on a mirror mock-up', options: cell }, tag('Team recording', '2E5AA8'), { text: 'Pose check, face and posture demo', options: cell }],
  [{ text: 'LYRA web app crew', options: cell }, tag('Simulation', '6B3FA0'), { text: 'Live demo time series', options: cell }]],
  { x: 6.85, y: 1.4, w: 5.9, colW: [2.75, 1.0, 2.15], rowH: 0.3, border: { type: 'solid', pt: 0.5, color: 'C9D3DD' }, margin: 0.05, objectName: 'Data provenance table' });
T(s, 'No single NASA dataset holds IR face points, RGB video, 3D posture and medical references together, so LYRA is a prototype that needs validation.', { x: 6.85, y: 6.1, w: 5.9, h: 0.7, fontSize: 12, color: C.text2, italic: true });

// 6 Demo
pres.addSection({ title: 'Demo' });
s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Demo' });
s.addText('Demo: a status with a reason, a report for the medical team', { placeholder: 'title' });
const st3 = [
  ['Within baseline', C.accent2, 'No sustained change vs you and the environment mode', 'Short summary and a scan streak.'],
  ['Repeat measurement', C.accent3, 'A new or unclear change', 'One onboard action and a re-scan.'],
  ['Refer to specialist', C.accent4, 'Sustained or repeated change, or change plus pain or fatigue', 'Step-by-step guidance; first in the report queue.'],
  ['Measurement not confirmed', C.accent5, 'Motion, light or pose made the signal unreliable', 'Repeat; no value is guessed.']];
st3.forEach((q, i) => {
  const y = 1.4 + i * 0.98;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 5.6, h: 0.86, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: 'status ' + q[0] });
  s.addShape(pres.shapes.OVAL, { x: 0.78, y: y + 0.2, w: 0.46, h: 0.46, fill: { color: q[1] }, line: { color: q[1] }, objectName: 'dot ' + q[0] });
  T(s, [{ text: q[0] + ': ', options: { bold: true, color: q[1] } }, { text: q[2], options: { bold: true } }], { x: 1.42, y: y + 0.08, w: 4.68, h: 0.4, fontSize: 12 });
  T(s, q[3], { x: 1.42, y: y + 0.5, w: 4.68, h: 0.3, fontSize: 12, color: C.text2 });
});
T(s, [
  { text: 'Web app (simulation): ', options: { bold: true } },
  { text: '3D body point cloud with three views, voice-guided scan, face pipeline view, "you vs NASA" chart, medical report and a downlink queue with ISS / Moon / Mars delay. Research-module values are shown apart and never set the status.' }
], { x: 0.6, y: 5.4, w: 5.6, h: 1.4, fontSize: 13 });
const b6 = placeShot(s, '01_overview.png', 5, 6.55, 1.4, 6.2, 2.45, 'App screenshots, simulated crew data (app code written with AI (SI) assistance)');
if (shot('06_scan_pipeline.png')) { usedShots.push('06_scan_pipeline.png'); const p = shot('06_scan_pipeline.png'); s.addImage(Object.assign({ path: p, objectName: 'App screenshot scan pipeline' }, fit(p, 6.55, b6 + 0.05, 6.2, 6.85 - b6 - 0.05))); }

// 7 Research module, limits, roadmap
pres.addSection({ title: 'Roadmap' });
s = pres.addSlide({ masterName: 'DARK', sectionTitle: 'Roadmap' });
s.addText('Honest limits, a research option, and what comes next', { placeholder: 'title' });
s.addImage({ path: img(3), x: 7.3, y: 1.5, w: 5.45, h: 3.85, objectName: 'Doppler grip and hydrogel cassette drawing' });
SI(s, 7.3, 5.42, 5.45);
T(s, [
  { text: 'Optional research module: ', options: { bold: true, color: C.accent1 } },
  { text: 'ultrasound Doppler in vertical grips on the side posts, coupled by a 4-part solid hydrogel cassette (holder, thin replaceable pad, soft rim, membrane). Demo: a mock cassette and a signal path diagram. A real transducer only after a phantom or ground test. Not part of the contactless core; no heart or vein claims through the palm.', options: { breakLine: true } },
  { text: 'LYRA does not: ', options: { bold: true, color: C.accent1 } },
  { text: 'diagnose, or measure bone density, discs, muscle strength or radiation. The medical team decides.', options: { breakLine: true } },
  { text: 'Next: ', options: { bold: true, color: C.accent1 } },
  { text: 'mirror mock-up and team recordings, rPPG check on CameraVitals, posture baselines in analogs (bed rest, parabolic flight), then Moon, Mars, rovers, and Earth clinics.' }
], { x: 0.6, y: 1.5, w: 6.4, h: 4.6, fontSize: 14, color: C.background1, paraSpaceAfter: 10 });
T(s, 'Step in. Scan. Know.', { x: 0.6, y: 6.3, w: 6.4, h: 0.5, fontSize: 22, italic: true, bold: true, color: C.accent1, fontFace: THEME.headFontFace });

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('written', path.relative(process.cwd(), OUT));
  console.log(usedShots.length ? 'app screenshots included: ' + usedShots.join(', ')
    : 'app screenshots: none found in docs/presentation/screenshots (drawings used instead)');
})();
