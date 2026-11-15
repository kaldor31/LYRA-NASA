// LYRA mirror panel (simulation). REST + WebSocket to lyra/server.py, 3D in body3d.js. Design rules: DESIGN.md
import { createBody } from "./body3d.js";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const reduceMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// ---------------- text hygiene: English, no emoji, no em dashes ----------------
const CYR = /[\u0400-\u04FF]/;
const EMOJI = /[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\u{FE0F}\u{200D}\u{20E3}]/gu;
function clean(s) {
  return String(s ?? "")
    .replace(EMOJI, "")
    .replace(/\s*\u2014\s*/g, ", ")
    .replace(/\s+·\s+/g, ", ")
    .replace(/,\s*,/g, ",")
    .replace(/\s{2,}/g, " ")
    .replace(/^[,\s]+|[,\s]+$/g, "");
}
const esc = (s) => clean(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
/** Backend string if it is already English, otherwise the English fallback. */
const en = (s, fb) => (s && !CYR.test(s) ? s : fb ?? s ?? "");
/** Field lookup that prefers *_en, then the plain name, then *_ru. */
const pick = (o, base) => o?.[`${base}_en`] ?? o?.[base] ?? o?.[`${base}_ru`] ?? "";

const NF = {};
const fmt = (v, d = 1) => {
  if (v == null || isNaN(v)) return "-";
  const k = d;
  NF[k] ||= new Intl.NumberFormat("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  return NF[k].format(v);
};
const sgn = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "±") + fmt(Math.abs(v), d);

// ---------------- icons (Lucide 0.469.0 nodes rendered inline) ----------------
function icon(name, cls = "") {
  const node = window.lucide?.icons?.[name];
  if (!node) return "";
  const kids = Array.isArray(node[2]) ? node[2] : Array.isArray(node[0]) ? node : [];
  const inner = kids.map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(" ")}/>`).join("");
  return `<svg class="ico ${cls}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${inner}</svg>`;
}
const hydrateIcons = (root = document) => $$("[data-icon]", root).forEach((el) => { el.outerHTML = icon(el.dataset.icon, el.dataset.cls || ""); });

// ---------------- vocabulary ----------------
const ST = {
  green: { icon: "CircleCheck", word: "Within baseline" },
  yellow: { icon: "TriangleAlert", word: "Repeat measurement" },
  red: { icon: "OctagonAlert", word: "Refer to specialist" },
  retry: { icon: "RotateCcw", word: "Measurement not confirmed" },
};
const badge = (st, sm = false) => st && ST[st]
  ? `<span class="st ${st} ${sm ? "sm" : ""}">${icon(ST[st].icon)}<span class="word">${ST[st].word}</span></span>`
  : `<span class="st none ${sm ? "sm" : ""}">${icon("CircleDashed")}<span class="word">No data</span></span>`;
const REJECT = { motion: "Too much motion", low_light: "Light too low", light: "Light too low", face_not_visible: "Face not visible",
  face: "Face not visible", pose_not_reached: "Pose not reached", pose: "Pose not reached", weak_signal: "Weak signal", signal: "Weak signal" };
const rejectText = (r) => r ? (REJECT[String(r).toLowerCase().replace(/[\s-]+/g, "_")] || clean(en(r, "Signal check failed"))) : "";
const OVERALL = {
  green: { title: "Within baseline", summary: "All core measurements are within your baseline and NASA's expected adaptation." },
  yellow: { title: "Repeat measurement", steps: ["Follow the action listed under each measurement marked Repeat measurement.", "Repeat the scan tomorrow at the same time of day."] },
  red: { title: "Refer to specialist", steps: ["Stop and secure yourself at the station. Breathe calmly for 5 minutes.",
    "Follow the steps under the measurements marked Refer to specialist.", "Repeat the session in 15 minutes.",
    "The flight surgeon is already receiving the data. If the change persists, call them."] },
  retry: { title: "Measurement not confirmed", steps: ["Fix the issue shown, then repeat the scan."] },
};
const PROV = { team: ["Team recording", "Video"], team_recording: ["Team recording", "Video"], recording: ["Team recording", "Video"],
  open_dataset: ["Open dataset (CameraVitals)", "Database"], dataset: ["Open dataset (CameraVitals)", "Database"], cameravitals: ["Open dataset (CameraVitals)", "Database"],
  nasa: ["NASA material", "BookOpen"], nasa_material: ["NASA material", "BookOpen"], simulation: ["Simulation", "FlaskConical"], simulated: ["Simulation", "FlaskConical"] };
function provenance(p, simulated = true, note = "") {
  const raw = typeof p === "object" && p ? (p.kind || p.type || p.id || p.source) : p;
  const k = String(raw || (simulated ? "simulation" : "")).toLowerCase().replace(/[\s-]+/g, "_");
  const [label, ic] = PROV[k] || (raw ? [clean(en(typeof p === "object" ? (p.label || p.title || raw) : raw, "Data source")), "Database"] : PROV.simulation);
  return `<span class="tag prov" title="Data provenance${note ? `: ${esc(note)}` : ""}">${icon(ic)}${esc(label)}</span>`;
}
/** Environment mode: Earth / microgravity / partial gravity. */
function envMode(st) {
  if (st?.env_mode_label && !CYR.test(st.env_mode_label)) return st.env_mode_label.replace(/\s*\(.*\)$/, "");
  const m = st?.env_mode || st?.gravity_mode;
  if (m) return clean(en(String(m).replace(/_/g, " "), "")).replace(/^./, (c) => c.toUpperCase());
  const g = st?.gravity_g;
  if (g == null) return "";
  return g >= 0.9 ? "Earth" : g <= 0.01 ? "Microgravity" : "Partial gravity";
}
/** Optional contact research module (vertical grips). Excluded from the main status. Fallback when meta lacks research_keys. */
const RESEARCH_KEYS = new Set(["grip_left_kg", "grip_right_kg", "doppler_flow_left_cms", "doppler_flow_right_cms", "flow_asymmetry_pct",
  "hr_palm", "hrv_rmssd_ms", "spo2", "skin_temp", "handgrip_hr_response_bpm", "handgrip_recovery_s"]);
const isResearch = (m) => {
  if (m && typeof m === "object" && m.module) return m.module === "research";
  const k = m?.key ?? m;
  return (S.meta?.research_keys ? S.meta.research_keys.includes(k) : RESEARCH_KEYS.has(k));
};
const SCEN = {
  day1: ["Day 1, ISS", "Fluid shift toward the head has just started. The face reference has not caught up yet, so some crew identify with the NFC card."],
  day40: ["Day 40, ISS", "Expected adaptation: puffier face, thinner calves, height up 2%. Everything sits inside the NASA corridor."],
  mars180: ["Day 180, Mars", "Long mission with up to 20 min signal delay; the crew works autonomously. Slow grip strength loss, as NASA expects."],
  anomaly: ["Anomaly, Moon day 60", "Mira Sato's grip strength and palm blood flow are dropping faster than NASA expects, and facial swelling is above the expected range."],
};
const CREW = { a1: ["Alex Rivera", "Commander", "AR"], a2: ["Mira Sato", "Flight Engineer", "MS"],
  a3: ["Ivan Koval", "Crew Medical Officer", "IK"], a4: ["Leia Okafor", "Mission Specialist", "LO"] };
const ENV = { iss: "ISS, low Earth orbit", moon: "Moon / Gateway", mars: "Mars" };
const ENV_ICON = { iss: "Satellite", moon: "Moon", mars: "Orbit" };
const METRIC = {
  face_volume_ml: "Face volume", periorbital_puffiness_mm: "Puffiness around the eyes", blink_rate: "Blink rate",
  perclos: "Eye closure (PERCLOS)", yawn_count: "Yawns", facial_tension: "Facial tension signs", hr_rppg: "Pulse (camera)",
  leg_volume_ml: "Calf volume", body_volume_l: "Total body volume", height_cm: "Height", head_forward_deg: "Head forward tilt",
  shoulder_asym_deg: "Shoulder asymmetry", grip_left_kg: "Grip strength, left", grip_right_kg: "Grip strength, right",
  doppler_flow_left_cms: "Palm blood flow, left", doppler_flow_right_cms: "Palm blood flow, right",
  flow_asymmetry_pct: "Blood flow asymmetry L/R", hr_palm: "Pulse (palm)", hrv_rmssd_ms: "Heart rate variability (RMSSD)",
  spo2: "Blood oxygen (SpO₂)", skin_temp: "Palm temperature", handgrip_hr_response_bpm: "Pulse response to handgrip test",
  handgrip_recovery_s: "Recovery after handgrip test", sleep_score: "Sleep (self-rated)", wellbeing_score: "Wellbeing (self-rated)",
  symptoms_flag: "Symptoms (self-reported)", back_pain_flag: "Back pain (self-reported)", trunk_tilt_deg: "Trunk tilt",
  pelvis_tilt_deg: "Pelvis tilt", scapula_asym_mm: "Scapula asymmetry", spine_length_mm: "Spine length", pose_return_s: "Time to reach pose", radiation_dose_msv: "Accumulated dose (station dosimeter)",
};
const UNIT = { "\u043C\u043B": "mL", "\u043C\u043C": "mm", "\u043A\u0433": "kg", "\u0441\u043C/\u0441": "cm/s", "\u0443\u0434/\u043C\u0438\u043D": "bpm", "\u043C\u0441": "ms", "\u043B": "L", "\u0441\u043C": "cm",
  "\u043C\u0417\u0432": "mSv", "/\u043C\u0438\u043D": "/min", "\u0440\u0430\u0437": "count", "\u0438\u043D\u0434\u0435\u043A\u0441 0–1": "index 0 to 1", "1–5": "1 to 5", "\u0434\u0430/\u043D\u0435\u0442": "yes/no", "\u0441": "s",
  "% \u043E\u0442 \u0438\u0441\u0445\u043E\u0434\u043D\u043E\u0433\u043E \u043A \u043F\u043B\u0430\u0442\u043E": "% of baseline at plateau", "\u043C\u043C \u043A \u043F\u043B\u0430\u0442\u043E": "mm at plateau", "% \u043A \u043F\u043B\u0430\u0442\u043E": "% at plateau",
  "%/\u043C\u0435\u0441": "%/month", "\u043C\u0417\u0432/\u0441\u0443\u0442 (\u041C\u041A\u0421)": "mSv/day (ISS)" };
const unitEn = (u) => UNIT[u] ?? clean(u);
const mName = (key, fb) => METRIC[key] || clean(en(fb, key));
const GROUPS = [["face", "Face", "IR structured light and RGB camera"], ["body", "Body and posture", "Skeletal keypoints from front, side and back views"],
  ["hands", "Vertical grips", "Load cell, PPG and SpO\u2082"], ["self", "Self-report", "Three-question survey"]];
const LIGHT = { "\u{1F7E2}": "green", "\u{1F7E1}": "yellow", "\u{1F534}": "red" };

const S = { report: null, meta: null, state: null, ref: null, aid: "a1", latest: null, flow: null, chartKey: "face_volume_ml",
  series: null, link: null, linkAt: 0, dose: null, body: null, chartDay: null };

const crewName = (c) => en(c?.name, CREW[c?.id]?.[0]);
const crewRole = (c) => en(c?.role, CREW[c?.id]?.[1]);
const crewInit = (c) => en(c?.initials, CREW[c?.id]?.[2]);

// ---------------- API ----------------
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(clean(en((await r.json().catch(() => ({}))).detail, r.statusText)) || r.statusText);
  return r.json();
}

function toast(text, ico = "Info", ms = 3800) {
  const t = $("#toast");
  t.innerHTML = `${icon(ico)}<span>${esc(text)}</span>`;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, ms);
}

function modal(title, html) {
  $("#modal-title").textContent = clean(title);
  $("#modal-body").innerHTML = html;
  const d = $("#modal");
  if (!d.open) d.showModal();
}
$("#modal-close").innerHTML = icon("X", "ico-20");
$("#modal-close").onclick = () => $("#modal").close();
$("#modal").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

// ---------------- voice ----------------
const Voice = {
  on: true, listening: false, rec: null, last: "",
  say(text) {
    this.last = clean(text);
    if (!this.on || !("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(this.last);
    u.lang = "en-US";
    const v = speechSynthesis.getVoices().find((x) => x.lang?.toLowerCase().startsWith("en"));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  },
  repeat() { if (this.last) this.say(this.last); },
  toggleMic() {
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) return toast("Speech recognition is not available in this browser. Use the on-screen buttons.", "MicOff");
    if (this.listening) { this.listening = false; this.rec?.stop(); return this.ui(); }
    this.rec = new R();
    this.rec.lang = "en-US"; this.rec.continuous = true; this.rec.interimResults = false;
    this.rec.onresult = (e) => onVoice(e.results[e.results.length - 1][0].transcript.toLowerCase());
    this.rec.onerror = (e) => { if (e.error === "not-allowed") { this.listening = false; this.ui(); toast("Microphone access is blocked. Use the on-screen buttons.", "MicOff"); } };
    this.rec.onend = () => { if (this.listening) try { this.rec.start(); } catch { /* already running */ } };
    this.listening = true;
    try { this.rec.start(); } catch { /* */ }
    this.ui();
    toast("Listening for “start”, “repeat”, “stop”, survey numbers and “yes” or “no”.", "Mic");
  },
  ui() {
    const v = $("#btn-voice"), m = $("#btn-mic");
    v.innerHTML = icon(this.on ? "Volume2" : "VolumeX", "ico-20");
    v.setAttribute("aria-pressed", String(this.on));
    v.setAttribute("aria-label", this.on ? "Voice prompts on" : "Voice prompts off");
    v.title = v.getAttribute("aria-label");
    m.innerHTML = icon(this.listening ? "Mic" : "MicOff", "ico-20");
    m.setAttribute("aria-pressed", String(this.listening));
    m.classList.toggle("listening", this.listening);
    m.setAttribute("aria-label", this.listening ? "Voice commands on" : "Voice commands off");
    m.title = `${m.getAttribute("aria-label")}: start, repeat, stop`;
  },
};
$("#btn-voice").onclick = () => { Voice.on = !Voice.on; if (!Voice.on) window.speechSynthesis?.cancel(); Voice.ui(); };
$("#btn-mic").onclick = () => Voice.toggleMic();

const NUM = { one: 1, won: 1, two: 2, to: 2, too: 2, three: 3, four: 4, for: 4, five: 5 };
function onVoice(t) {
  if (/\b(stop|cancel)\b/.test(t)) return S.flow ? S.flow.stop() : null;
  if (/repeat|again/.test(t)) return Voice.repeat();
  if (/\b(start|begin)\b/.test(t) && !S.flow) return startFlow("daily");
  if (S.flow?.answer) {
    if (/\b(yes|yeah)\b/.test(t)) return S.flow.answer(true, "voice");
    if (/\b(no|nope)\b/.test(t)) return S.flow.answer(false, "voice");
    const d = t.match(/[1-5]/);
    const w = Object.keys(NUM).find((x) => new RegExp(`\\b${x}\\b`).test(t));
    if (d || w) return S.flow.answer(d ? Number(d[0]) : NUM[w], "voice");
  }
  if (/card/.test(t) && S.flow?.nfc) S.flow.nfc();
}

// ---------------- 3D ----------------
function initBody() {
  try {
    S.body = createBody($("#body3d"));
  } catch (e) {
    console.error(e);
    $("#body3d").innerHTML = `<div class="fallback-3d">3D view is not available in this browser</div>`;
    S.body = { setParams() {}, setView() {}, scan() {}, setLabels() {}, setSkeleton() {} };
  }
  $$(".views button").forEach((b) => b.onclick = () => setView(b.dataset.view));
  $("#btn-skel").onclick = () => {
    const on = $("#btn-skel").getAttribute("aria-pressed") !== "true";
    $("#btn-skel").setAttribute("aria-pressed", String(on));
    S.body.setSkeleton?.(on);
  };
}
function setView(v) {
  $$(".views button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.view === v)));
  S.body.setView(v);
}

function showBody(res) {
  const b = res?.body;
  if (!b) { S.body.setParams({ face_pct: 0, legs_pct: 0, body_pct: 0, height_pct: 0, zones: {} }); return S.body.setLabels([]); }
  S.body.setParams(b);
  const z = b.zones || {};
  const L = [];
  if (Math.abs(b.face_pct) >= 0.5) L.push({ zone: "face", text: `Face ${sgn(b.face_pct)}%`, status: z.face || "green" });
  if (Math.abs(b.legs_pct) >= 0.5) L.push({ zone: "legs", text: `Calves ${sgn(b.legs_pct)}%`, status: z.legs || "green" });
  if (Math.abs(b.height_pct) >= 0.3) L.push({ zone: "body", text: `Height ${sgn(b.height_pct)}%`, status: z.body || "green" });
  if (z.hands && z.hands !== "green") L.push({ zone: "hands", text: "Research grips", status: z.hands });
  if (z.posture && z.posture !== "green") L.push({ zone: "posture", text: "Posture", status: z.posture });
  S.body.setLabels(L);
}

function mirror(text) {
  const m = $("#mirror-text");
  m.textContent = clean(text || "");
  m.hidden = !text;
}

// ---------------- header, crew, scenarios ----------------
function renderHeader() {
  const st = S.state;
  $("#scenarios").innerHTML = S.meta.scenarios.map((s) =>
    `<button type="button" data-sc="${s.id}" aria-pressed="${s.id === st.scenario}">${esc(en(s.title, SCEN[s.id]?.[0]))}</button>`).join("");
  $$("#scenarios button").forEach((b) => b.onclick = () => switchScenario(b.dataset.sc));
  const g = st.gravity_g != null ? `, ${fmt(st.gravity_g, st.gravity_g ? 2 : 0)} g` : "";
  const mode = envMode(st);
  $("#env").innerHTML = `${icon(ENV_ICON[st.env] || "Orbit")} <b>${esc(en(st.env_name, ENV[st.env]))}</b>, ${mode ? `${mode.toLowerCase()} ` : ""}${g.replace(/^, /, "")}, mission day <b class="tnum">${st.day}</b>`;
  $("#scenario-sub").textContent = clean(en(st.scenario_subtitle, SCEN[st.scenario]?.[1]));
  renderCrew();
}

function renderCrew() {
  $("#crew").innerHTML = S.state.crew.map((c) => `
    <button type="button" class="member" data-aid="${c.id}" aria-current="${c.id === S.aid}" ${S.flow ? "disabled" : ""}
      aria-label="${esc(crewName(c))}, ${esc(crewRole(c))}, status ${c.status ? ST[c.status]?.word : "no data"}, ${c.streak}-day streak${c.done_today ? ", scanned today" : ""}">
      <span class="avatar" aria-hidden="true">${esc(crewInit(c))}</span>
      <span class="name">${esc(crewName(c))}</span>
      <span class="meta">${badge(c.status, true)}<span class="role">${c.done_today ? "Scanned today" : esc(crewRole(c))}</span></span>
    </button>`).join("");
  $$("#crew .member").forEach((b) => b.onclick = () => selectAstronaut(b.dataset.aid));
}

async function switchScenario(id) {
  if (S.flow) return toast("Finish or stop the session first.", "Info");
  S.state = await api(`/api/scenario/${id}`, {});
  renderHeader();
  await selectAstronaut(S.aid);
  toast(`Scenario: ${en(S.state.scenario_title, SCEN[id]?.[0])}`, "Orbit");
}

async function selectAstronaut(aid) {
  S.aid = aid;
  renderCrew();
  const a = await api(`/api/astronauts/${aid}`);
  S.latest = a.latest;
  S.dose = a.dose;
  showBody(S.latest);
  renderIdle();
  renderScan();
  renderLink();
  loadChart();
  loadReport();
}

// ---------------- tabs (ARIA tabs with arrow keys) ----------------
function tab(name, focus = false) {
  $$(".tabs [role=tab]").forEach((b) => {
    const on = b.dataset.tab === name;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
    if (on && focus) b.focus();
  });
  $$(".tab").forEach((t) => { t.hidden = t.id !== `tab-${name}`; });
  if (name === "chart") drawChart();
  if (name === "scan") paintStages($("#tab-scan"));
}
$$(".tabs [role=tab]").forEach((b) => {
  b.onclick = () => tab(b.dataset.tab);
  b.onkeydown = (e) => {
    const tabs = $$(".tabs [role=tab]"), i = tabs.indexOf(b);
    const j = e.key === "ArrowRight" ? (i + 1) % tabs.length : e.key === "ArrowLeft" ? (i - 1 + tabs.length) % tabs.length
      : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : -1;
    if (j >= 0) { e.preventDefault(); tab(tabs[j].dataset.tab, true); }
  };
});

// ---------------- Today: overview ----------------
const member = () => S.state.crew.find((c) => c.id === S.aid);
const trained = (aid) => { try { return localStorage.getItem(`lyra.trained.${aid}`) === "1"; } catch { return true; } };
const markTrained = (aid) => { try { localStorage.setItem(`lyra.trained.${aid}`, "1"); } catch { /* private mode */ } };

function renderIdle() {
  if (S.flow) return;
  mirror("");
  const m = member();
  const first = !trained(S.aid);
  const box = $("#tab-session");
  box.innerHTML = `
    <div class="who"><h1>${esc(crewName(m))}</h1><span class="role">${esc(crewRole(m))}</span>
      <span class="streak">${icon("CalendarCheck")}<span class="tnum">${m.streak}-day scan streak</span></span></div>
    <div id="overview"></div>
    <div class="start">
      <div class="btn-row">
        <button type="button" class="btn primary lg" data-start="daily">${icon("Play")}Start Daily Scan</button>
        <button type="button" class="btn lg" data-start="weekly">${icon("Activity")}Weekly Full Test</button>
        <button type="button" class="btn quiet lg" data-start="training">${icon("GraduationCap")}Training${first ? " (recommended)" : ""}</button>
      </div>
      <p class="hint">Daily scan takes about 90 s: stand on the marks, face and body scan, three short questions. Grips with Doppler are an optional research module. The weekly test adds a 2 min handgrip hold. Training records nothing.</p>
    </div>
    <div id="last-result"></div>`;
  $$("[data-start]", box).forEach((b) => b.onclick = () => startFlow(b.dataset.start));
  if (S.latest) {
    $("#overview").append(verdictView(S.latest, false));
    $("#last-result").append(metricsView(S.latest));
  } else {
    $("#overview").innerHTML = `<p class="empty">No sessions yet. Start a daily scan to create the first record.</p>`;
  }
}

function overallText(o, res) {
  const title = en(o.title, OVERALL[o.status]?.title);
  let summary = o.summary;
  if (!summary || CYR.test(summary)) {
    const names = (keys) => keys.map((k) => mName(k, res.metrics?.find((x) => x.key === k)?.name)).join(", ");
    const fast = o.faster_than_nasa || [], other = (o.flagged || []).filter((k) => !fast.includes(k));
    summary = o.status === "green" ? OVERALL.green.summary
      : [fast.length ? `Faster than NASA expects: ${names(fast)}.` : "", other.length ? `Off your personal norm: ${names(other)}.` : ""].join(" ").trim();
  }
  let steps = o.steps || [];
  if (steps.some((s) => CYR.test(s))) steps = OVERALL[o.status]?.steps || steps;
  return { title, summary, steps };
}

function verdictView(res, fresh) {
  const o = res.overall, t = overallText(o, res);
  const fast = (o.faster_than_nasa || []).filter((k) => !isResearch(k));
  const offNorm = (o.flagged || []).filter((k) => !fast.includes(k) && !isResearch(k));
  const research = [...new Set([...(o.flagged || []).filter(isResearch), ...(o.research?.flagged || [])])];
  const reasons = (o.flag_reasons || []).filter((r) => r.module !== "research" && !isResearch(r.key));
  const dl = res.downlink;
  const mode = envMode({ ...S.state, ...res });
  const el = document.createElement("section");
  el.className = `verdict ${o.status}`;
  el.setAttribute("aria-label", "Overall status");
  el.innerHTML = `
    <div class="head"><span class="title">${icon(ST[o.status]?.icon || "CircleDashed")}${esc(t.title)}</span>
      <span class="when">${res.live ? (res.training ? "Training result, not recorded" : `Today, mission day ${res.day}`) : `Last session, day ${res.day}`}${res.mode === "weekly" ? ", weekly test" : ""}${mode ? `, ${mode.toLowerCase()}` : ""}</span>
      ${provenance(res.provenance ?? res.data_source, res.simulated !== false, en(res.provenance_note, ""))}</div>
    ${o.status === "green" && t.summary ? `<p class="summary">${esc(t.summary)}</p>` : ""}
    <dl class="facts">
      <dt>Vs NASA expectation</dt>
      <dd>${fast.length ? `Faster than expected: ${fast.map((k) => `<button type="button" class="linkbtn" data-chart="${k}">${esc(mName(k))}</button>`).join(", ")}`
        : "All tracked changes are within NASA's expected adaptation corridor."}</dd>
      ${offNorm.length ? `<dt>Vs your own baseline</dt><dd>Outside your 14-day baseline: ${offNorm.map((k) => `<button type="button" class="linkbtn" data-chart="${k}">${esc(mName(k))}</button>`).join(", ")}</dd>` : ""}
      ${reasons.length ? `<dt>Why flagged</dt><dd>${reasons.map((r) => `<div>${badge(r.status, true)} ${esc(mName(r.key, r.name))}: ${esc(en(r.reason, ST[r.status]?.word || ""))}</div>`).join("")}</dd>` : ""}
      ${t.steps.length ? `<dt>${o.status === "red" ? "Do this now" : "Next step"}</dt><dd><ol class="steps-list">${t.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></dd>`
        : `<dt>Next step</dt><dd>${res.streak != null ? `Keep the streak going: scan again tomorrow.` : "Scan again tomorrow."}</dd>`}
      ${research.length ? `<dt>Research module</dt><dd class="muted">${badge(o.research?.status || "yellow", true)} ${research.map((k) => esc(mName(k))).join(", ")}. Contact grips are shown separately and do not set the main status.</dd>` : ""}
    </dl>
    ${dl ? `<p class="linkline">${icon("SatelliteDish")}Sent to the flight surgeon: <b>${dl.status === "delivered" ? "delivered" : "in transit"}</b>${dl.status !== "delivered" ? `, ${fmtDur(dl.delay_s)} one-way delay` : ""}</p>` : ""}
    ${fresh && res.training ? `<p class="linkline">${icon("GraduationCap")}Training run. Nothing was recorded or sent.</p>` : ""}`;
  $$("[data-chart]", el).forEach((b) => b.onclick = () => openChart(b.dataset.chart));
  return el;
}

function openChart(key) {
  S.chartKey = key;
  loadChart().then(() => tab("chart", true));
}

// ---------------- measurements ----------------
function describeMetric(m) {
  if (m.text && !CYR.test(m.text)) return m.text;
  if (m.status === "retry") return `The reading was rejected${m.reject_reason ? `: ${rejectText(m.reject_reason).toLowerCase()}` : ""}. It is not used for status.`;
  const u = unitEn(m.unit), pre = m.preflight;
  const parts = [];
  if (m.mission_pct != null && m.group !== "self") parts.push(`${sgn(m.mission_pct)}% vs your preflight baseline.`);
  if (m.corridor && pre) {
    const lo = (100 * (m.corridor.lo - pre)) / pre, hi = (100 * (m.corridor.hi - pre)) / pre;
    if (m.faster_than_nasa) parts.push(`Changing faster than NASA expects: about ${sgn(m.expected_pct ?? 0)}% is expected on day ${m.corridor.day} (corridor ${sgn(lo)}% to ${sgn(hi)}%).`);
    else parts.push(`Inside NASA's expected adaptation corridor for day ${m.corridor.day} (${sgn(lo)}% to ${sgn(hi)}%).`);
  } else if (m.norm_mean != null && m.group !== "self") {
    if (m.z_status && m.z_status !== "green") parts.push(`Sharply ${m.z > 0 ? "above" : "below"} your 14-day norm of ${fmt(m.norm_mean, 1)} ${u}.`);
    else parts.push(`Within your personal norm (${fmt(m.norm_mean, 1)} ${u}). NASA publishes no trajectory for this measure.`);
  }
  return parts.join(" ");
}

function valueOf(m) {
  if (m.value == null || m.confirmed === false) return '<span class="faint">-</span>';
  if (m.key === "symptoms_flag" || m.key === "back_pain_flag") return m.value >= 1 ? "Yes" : "No";
  if (m.group === "self") return `${fmt(m.value, 0)}<small>/ 5</small>`;
  const d = m.key === "facial_tension" ? 2 : Math.abs(m.value) >= 100 ? 0 : 1;
  return `${fmt(m.value, d)}<small>${esc(unitEn(m.unit))}</small>`;
}

function gauge(m) {
  const c = m.corridor;
  if (!c || m.value == null) return `<span class="gauge-none">${m.group === "self" ? "" : "Personal norm"}</span>`;
  const w = c.hi - c.lo || 1, pad = w * 0.8;
  const lo = Math.min(c.lo - pad, m.value), hi = Math.max(c.hi + pad, m.value);
  const P = (v) => `${(100 * (v - lo)) / (hi - lo)}%`;
  const dotSt = m.corridor_status && m.corridor_status !== "green" ? m.corridor_status : "";
  return `<span class="gauge" role="img" aria-label="NASA corridor ${fmt(c.lo, 1)} to ${fmt(c.hi, 1)}, today ${fmt(m.value, 1)}" title="NASA expected corridor for day ${c.day}: ${fmt(c.lo, 1)} to ${fmt(c.hi, 1)} ${esc(unitEn(m.unit))}">
    <span class="track"></span><span class="band" style="left:${P(c.lo)};width:calc(${P(c.hi)} - ${P(c.lo)})"></span>
    <span class="mid" style="left:${P(c.center)}"></span><span class="dot ${dotSt}" style="left:${P(m.value)}"></span></span>`;
}

function signalText(sg) {
  if (!sg || typeof sg !== "object") return "";
  const parts = [];
  if (sg.usable_seconds != null && sg.window_seconds != null) parts.push(`${fmt(sg.usable_seconds, 0)} of ${fmt(sg.window_seconds, 0)} s usable`);
  if (sg.motion != null) parts.push(`motion ${typeof sg.motion === "number" ? fmt(sg.motion, 2) : esc(sg.motion)}`);
  if (sg.light != null) parts.push(`light ${typeof sg.light === "number" ? fmt(sg.light, 2) : esc(sg.light)}`);
  return parts.length ? `. ${parts.join(", ")}` : "";
}
const reliability = (q) => q == null ? "" : q >= 0.85 ? "reliable" : q >= 0.6 ? "usable, moderate quality" : "low quality";
function metricAction(m) {
  const steps = (m.steps || []).filter(Boolean);
  const act = m.action || "";
  if (m.status === "retry") return { act: `${rejectText(m.reject_reason) || "Signal check failed"}. Fix it, then repeat the scan.`, steps: [] };
  if (CYR.test(act) || steps.some((x) => CYR.test(x))) {
    if (m.status === "red") return { act: "", steps: ["Repeat the measurement at rest.", "Note any symptoms in the survey.", "The flight surgeon already has the data. Call them if this persists."] };
    if (m.status === "yellow") return { act: "Repeat the measurement tomorrow at the same time of day.", steps: [] };
    return { act: "", steps: [] };
  }
  return { act: m.status === "red" ? "" : act, steps };
}

function mRow(m) {
  const open = m.status === "red" || m.status === "yellow" || m.status === "retry";
  const { act, steps } = metricAction(m);
  const q = m.quality ?? m.signal_quality;
  return `<details class="mrow" ${open ? "open" : ""}>
    <summary>
      <span class="nm">${esc(mName(m.key, m.name))}</span>
      <span class="val vcol">${valueOf(m)}</span>
      <span class="delta dcol">${m.mission_pct != null && m.group !== "self" ? `${sgn(m.mission_pct)}%` : ""}</span>
      <span class="gcol">${gauge(m)}</span>
      <span class="scol">${badge(m.status)}</span>
      <span class="chev">${icon("ChevronDown")}</span>
    </summary>
    <div class="detail">
      <dl class="facts tight">
        <dt>What changed</dt><dd>${esc(describeMetric(m)) || "No change from your baseline."}</dd>
        ${q != null ? `<dt>Signal</dt><dd>${fmt(q * 100, 0)}% quality, ${reliability(q)}${m.reject_reason ? `. Rejected: ${esc(rejectText(m.reject_reason))}` : ""}${signalText(m.signal)}</dd>` : ""}
        <dt>Action</dt><dd>${act ? esc(act) : steps.length ? "" : "No action needed."}${steps.length ? `<ol class="steps-list">${steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}</dd>
      </dl>
      <div class="btn-row">
        <button type="button" class="linkbtn" data-why="${m.key}">${icon("BookOpen")}Why it matters</button>
        ${m.group !== "self" ? `<button type="button" class="linkbtn" data-chart="${m.key}">${icon("ChartSpline")}Open chart</button>` : ""}
        ${m.provenance ? provenance(m.provenance) : ""}
      </div>
    </div>
  </details>`;
}

function metricsView(res) {
  const el = document.createElement("section");
  el.setAttribute("aria-labelledby", "mh");
  const order = { red: 0, yellow: 1, retry: 2, green: 3 };
  const sort = (a, b) => (order[a.status] ?? 4) - (order[b.status] ?? 4);
  let html = `<h2 class="h-section" id="mh">Measurements</h2>
    <div class="colhead" aria-hidden="true"><span>Measure</span><span class="vcol">Today</span><span class="dcol">Vs preflight</span><span class="gcol">NASA corridor</span><span class="scol">Status</span><span></span></div>`;
  for (const [g, title, sensor] of GROUPS) {
    const ms = res.metrics.filter((m) => m.group === g && !isResearch(m)).sort(sort);
    if (!ms.length) continue;
    html += `<h3 class="h-sub">${title} <span class="faint" style="font-weight:400">${sensor}</span></h3><div class="metrics">${ms.map(mRow).join("")}</div>`;
  }
  const rs = res.metrics.filter(isResearch).sort(sort);
  if (rs.length) {
    html += `<section class="research" aria-labelledby="rh"><h3 class="h-sub" id="rh"><span class="tag">${icon("FlaskConical")}Research module</span> Contact grips
      <span class="faint" style="font-weight:400">${esc(en(res.overall?.research?.note, "Optional contact grips in the side posts with a hydrogel cassette. Not part of the main status."))}</span></h3>
      <div class="metrics">${rs.map(mRow).join("")}</div></section>`;
  }
  html += `<p class="small faint" style="margin-top:var(--s4)">${esc(en(res.overall.disclaimer, "This is screening, not a diagnosis."))} Core LYRA is contactless. Values here are simulated along NASA expected-adaptation curves.</p>`;
  el.innerHTML = html;
  $$("[data-why]", el).forEach((b) => b.onclick = () => whyCard(b.dataset.why));
  $$("[data-chart]", el).forEach((b) => b.onclick = () => openChart(b.dataset.chart));
  return el;
}

// ---------------- session flow ----------------
const STEP_NAMES = { position: "Position", identify: "Identify", palms: "Palms", scan: "Face scan", turn: "Body views",
  rest: "Doppler (research)", grip: "Grip (research)", handgrip: "Handgrip (research)", recovery: "Recovery", survey: "Survey", send: "Result" };

class Cancelled extends Error {}

class Flow {
  constructor(mode, training) {
    this.mode = mode; this.training = training; this.stopped = false;
    this.steps = ["position", "identify", "palms", "scan", "turn", "rest", "grip", ...(mode === "weekly" ? ["handgrip", "recovery"] : []), "survey", "send"];
    this.i = 0; this.held = false; this.squeezes = 0; this.answer = null; this.nfc = null;
    const fast = S.meta.fast;
    this.dur = { pose: fast ? 1600 : 3200, view: fast ? 1500 : 3500, scan: fast ? 3600 : 8000, rest: fast ? 3000 : 8000, handgrip: fast ? 8000 : 20000, recovery: fast ? 3000 : 6000 };
  }
  stop() {
    this.stopped = true;
    this._wake?.();
    window.speechSynthesis?.cancel();
  }
  check() { if (this.stopped) throw new Cancelled(); }
  async wait(ms) {
    await new Promise((r) => { this._wake = r; setTimeout(r, ms); });
    this.check();
  }
  /** step timer: tick(fraction 0..1) every 100 ms */
  async timed(ms, tick) {
    const t0 = performance.now();
    for (;;) {
      this.check();
      const p = Math.min((performance.now() - t0) / ms, 1);
      tick?.(p);
      progress(p);
      if (p >= 1) return;
      await this.wait(100);
    }
  }
  frame(step, prompt, sub, body = "", say = prompt) {
    this.i = this.steps.indexOf(step);
    this.prompt = prompt;
    $("#tab-session").innerHTML = `
      ${this.training ? `<p class="notice training">${icon("GraduationCap", "ico-20")}<span><b>Training run.</b> Nothing is recorded or sent.</span></p><div style="height:var(--s4)"></div>` : ""}
      <ol class="stepper" aria-label="Session steps">${this.steps.map((s, k) => `<li class="${k < this.i ? "done" : k === this.i ? "now" : ""}" ${k === this.i ? 'aria-current="step"' : ""}>${STEP_NAMES[s]}</li>`).join("")}</ol>
      <h1 class="prompt" aria-live="polite">${esc(prompt)}</h1>
      <p class="prompt-sub">${sub}</p>
      <div class="progress" role="progressbar" aria-label="Step progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><i id="flow-progress"></i></div>
      <div id="flow-body">${body}</div>
      <div class="btn-row flow-ctl">
        <button type="button" class="btn quiet" id="f-repeat">${icon("Repeat")}Repeat Prompt</button>
        <button type="button" class="btn" id="f-stop">${icon("Square")}Stop Session</button>
      </div>`;
    $("#f-repeat").onclick = () => Voice.repeat();
    $("#f-stop").onclick = () => this.stop();
    mirror(prompt);
    Voice.say(say);
  }
}

function progress(p) {
  const i = $("#flow-progress");
  if (!i) return;
  i.style.transform = `scaleX(${p})`;
  i.parentElement.setAttribute("aria-valuenow", String(Math.round(p * 100)));
}

async function startFlow(kind) {
  if (S.flow) return;
  const training = kind === "training";
  const mode = training ? "weekly" : kind;
  const f = (S.flow = new Flow(mode, training));
  renderCrew();
  tab("session");
  try {
    await stepPosition(f);
    await stepIdentify(f);
    if (!training && !trained(S.aid)) {
      const go = await ask(f, "This looks like your first session. Run the training first? It records nothing.",
        [["Start Training", true], ["Skip to Scan", false]]);
      markTrained(S.aid);
      if (go) { S.flow = null; return startFlow("training"); }
    }
    await stepPalms(f);
    await stepScan(f);
    await stepTurn(f);
    await stepRest(f);
    let handgrip = null;
    if (!f.skipResearch) {
      await stepGrip(f);
      if (mode === "weekly") { handgrip = await stepHandgrip(f); await stepRecovery(f); }
    }
    const survey = await stepSurvey(f);
    f.frame("send", training ? "Training complete" : "Sending your result…", training ? "This is what a real result would look like." : "Data goes to the flight surgeon automatically.");
    const res = await api("/api/sessions", { astronaut_id: S.aid, mode, training, survey, handgrip, include_research: false, skip_research: !!f.skipResearch });
    if (training) markTrained(S.aid);
    finishFlow(res);
  } catch (e) {
    S.flow = null;
    S.body.scan(false);
    S.body.setSkeleton(false); $("#btn-skel")?.setAttribute("aria-pressed", "false");
    if (e instanceof Cancelled) { toast("Session stopped. Nothing was recorded.", "Square"); Voice.say("Session stopped."); }
    else { console.error(e); toast(`Something went wrong: ${e.message}. Try the session again.`, "TriangleAlert", 6000); }
    renderCrew();
    renderIdle();
  }
}

function ask(f, question, options) {
  return new Promise((resolve, reject) => {
    $("#flow-body").innerHTML = `<p class="prompt-sub" style="color:var(--text);font-size:var(--fs-20)">${esc(question)}</p>
      <div class="btn-row" style="margin-top:var(--s4)">${options.map(([l], k) => `<button type="button" class="btn ${k ? "" : "primary"}" data-k="${k}">${esc(l)}</button>`).join("")}</div>`;
    Voice.say(question);
    $$("#flow-body [data-k]").forEach((b) => b.onclick = () => resolve(options[+b.dataset.k][1]));
    const iv = setInterval(() => { if (f.stopped) { clearInterval(iv); reject(new Cancelled()); } }, 200);
  });
}

async function stepIdentify(f) {
  f.frame("identify", "Look at the mirror", "3D face identification: infrared dot projector and infrared camera. Voice is never used for identification.",
    `<div class="readouts"><div><b id="id-conf">…</b><span>Match confidence</span></div><div><b>${fmt(S.meta.face_id_threshold * 100, 0)}%</b><span>Required</span></div></div><div id="id-msg"></div>`);
  setView("front");
  S.body.scan(true);
  await f.timed(1800);
  const r = await api("/api/identify", { astronaut_id: S.aid });
  S.body.scan(false);
  $("#id-conf").textContent = `${fmt(r.confidence * 100, 0)}%`;
  const name = en(r.name, CREW[S.aid]?.[0]);
  if (r.ok) {
    $("#id-msg").innerHTML = `<p class="hello">${icon("ScanFace", "ico-24")}Hello, ${esc(name)}</p>`;
    Voice.say(`Hello, ${name}.`);
    await f.wait(1300);
    return;
  }
  const reason = en(r.reason, "Your face has changed with early-mission swelling, and the reference is still updating.");
  const hint = en(r.hint, "Hold your NFC card to the station reader.");
  $("#id-msg").innerHTML = `<div class="idcard">${icon("Nfc")}
      <div><p><b>Face match is not confident enough.</b> ${esc(reason)}</p>
      <p class="muted">${esc(hint)} The card is kept at the station.</p>
      <div class="btn-row" style="margin-top:var(--s3)"><button type="button" class="btn primary" id="nfc-btn">${icon("Nfc")}Tap NFC Card</button></div></div></div>`;
  $("#nfc-btn").focus();
  mirror(hint);
  Voice.say(`I am not sure who you are. ${hint}`);
  await new Promise((resolve, reject) => {
    f.nfc = resolve;
    $("#nfc-btn").onclick = resolve;
    const iv = setInterval(() => { if (f.stopped) { clearInterval(iv); reject(new Cancelled()); } }, 200);
  });
  f.nfc = null;
  const n = await api("/api/identify/nfc", { astronaut_id: S.aid });
  const nn = en(n.name, CREW[S.aid]?.[0]);
  $("#id-msg").innerHTML = `<p class="hello">${icon("CircleCheck", "ico-24")}NFC card accepted: ${esc(nn)}</p><p class="muted">The face reference will update gradually.</p>`;
  Voice.say(`Card accepted. Hello, ${nn}.`);
  await f.wait(1300);
}

// ---- live quality checks before capture ----
const CHECKS = { feet: ["Footprints", "Feet on the marks"], face: ["ScanFace", "Face visible"], light: ["Sun", "Light level"],
  motion: ["Move", "Holding still"], pose: ["PersonStanding", "Pose reached"], palms: ["Hand", "Both palms on the zones"] };
const checksHTML = (ids) => `<ul class="checks" aria-label="Quality checks">${ids.map((id) =>
  `<li data-check="${id}" class="pending">${icon("CircleDashed")}<span>${CHECKS[id][1]}</span><em class="faint">checking…</em></li>`).join("")}</ul>`;
/** Ticks the checks one by one; "motion" briefly fails once to show the gate is real. */
async function runChecks(f, ids, ms) {
  const per = ms / ids.length;
  for (const id of ids) {
    const li = $(`[data-check="${id}"]`);
    if (id === "motion" && !f._motionShown) {
      f._motionShown = true;
      if (li) { li.className = "fail"; li.innerHTML = `${icon("TriangleAlert")}<span>${CHECKS[id][1]}</span><em>Movement detected, hold still</em>`; }
      mirror("Hold still");
      await f.wait(per * 1.2);
    } else await f.wait(per);
    if (li) { li.className = "ok"; li.innerHTML = `${icon("CircleCheck")}<span>${CHECKS[id][1]}</span><em>OK</em>`; }
  }
  mirror(f.prompt);
}

const FEET_SVG = `<svg class="marks" viewBox="0 0 240 150" role="img" aria-label="Marked standing area with two foot contours">
  <rect x="6" y="6" width="228" height="138" rx="6" class="area"/>
  <g class="foot" id="foot-l"><path d="M92 40c-14 0-20 16-20 34s4 46 18 46 16-20 16-40-2-40-14-40z"/></g>
  <g class="foot" id="foot-r"><path d="M148 40c14 0 20 16 20 34s-4 46-18 46-16-20-16-40 2-40 14-40z"/></g>
  <text x="120" y="138" text-anchor="middle">Marked area, about 1.2 x 1.2 m</text></svg>`;
const PALMS_SVG = `<svg class="marks" viewBox="0 0 240 150" role="img" aria-label="Mirror with two marked palm zones">
  <rect x="6" y="6" width="228" height="138" rx="6" class="area"/>
  <g class="foot" id="palm-l"><rect x="40" y="38" width="60" height="74" rx="14"/></g>
  <g class="foot" id="palm-r"><rect x="140" y="38" width="60" height="74" rx="14"/></g>
  <text x="70" y="80" text-anchor="middle" class="lab">L</text><text x="170" y="80" text-anchor="middle" class="lab">R</text>
  <text x="120" y="138" text-anchor="middle">Palm zones on the mirror, for pose only</text></svg>`;

async function stepPosition(f) {
  f.frame("position", "Step into the marked area", "Place your feet on the two foot contours and secure the foot restraints. The same stance every day makes scans comparable.",
    `<div class="pose-grid">${FEET_SVG}${checksHTML(["feet", "pose"])}</div>`,
    f.training ? "Step into the marked area and put your feet on the two foot contours. In microgravity, secure the foot restraints." : "Step into the marked area.");
  setView("front");
  await f.timed(f.dur.pose, (p) => { $("#foot-l")?.classList.toggle("on", p > 0.3); $("#foot-r")?.classList.toggle("on", p > 0.55); });
  await runChecks(f, ["feet", "pose"], 700);
}

async function stepPalms(f) {
  f.frame("palms", "Place both palms on the marked zones of the mirror", "The palm zones only standardize your pose and shoulder height. They are not a medical sensor.",
    `<div class="pose-grid">${PALMS_SVG}${checksHTML(["palms", "pose"])}</div>`,
    f.training ? "Place both palms flat on the marked zones of the mirror. This only fixes your pose. It does not measure anything." : "Place both palms on the marked zones.");
  await f.timed(f.dur.pose, (p) => { $("#palm-l")?.classList.toggle("on", p > 0.3); $("#palm-r")?.classList.toggle("on", p > 0.55); });
  await runChecks(f, ["palms", "pose"], 700);
}

// ---- face IR pipeline: dot pattern -> depth map -> point cloud -> triangle mesh ----
const FACE_STAGES = [["IR dot pattern", "Projector lights the face with invisible infrared dots"], ["Depth map", "Dot shifts become distance per pixel"],
  ["Point cloud", "Depth pixels become 3D points"], ["Triangle mesh", "Points are joined into a surface; volume is computed"]];
function faceDepth(x, y) { // x, y in -1..1 inside the face ellipse
  const r = x * x + y * y;
  if (r >= 1) return -1;
  const nose = 0.35 * Math.exp(-((x * x) / 0.02 + ((y - 0.05) ** 2) / 0.08));
  const eyes = -0.12 * (Math.exp(-(((x - 0.35) ** 2) + ((y + 0.15) ** 2)) / 0.02) + Math.exp(-(((x + 0.35) ** 2) + ((y + 0.15) ** 2)) / 0.02));
  return Math.sqrt(1 - r) * 0.8 + nose + eyes;
}
function drawStage(canvas, k) {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth || 120, H = canvas.clientHeight || 140;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const c = canvas.getContext("2d"); c.scale(dpr, dpr); c.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H / 2, rx = W * 0.34, ry = H * 0.4;
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const P = (x, y) => [cx + x * rx, cy + y * ry];
  if (k === 0) {
    c.fillStyle = "rgba(143,178,232,0.9)";
    for (let i = 0; i < 900; i++) { const x = rnd() * 2.2 - 1.1, y = rnd() * 2.2 - 1.1, d = faceDepth(x, y); const [px, py] = P(x + (d > 0 ? d * 0.06 : 0), y);
      c.globalAlpha = d > 0 ? 0.9 : 0.25; c.fillRect(px, py, 1.4, 1.4); }
    c.globalAlpha = 1;
  } else if (k === 1) {
    const img = c.createImageData(Math.round(W * dpr), Math.round(H * dpr));
    for (let py = 0; py < img.height; py++) for (let px = 0; px < img.width; px++) {
      const d = faceDepth((px / dpr - cx) / rx, (py / dpr - cy) / ry), o = (py * img.width + px) * 4;
      const v = d > 0 ? 40 + Math.min(1, d) * 200 : 14;
      img.data[o] = v * 0.85; img.data[o + 1] = v * 0.92; img.data[o + 2] = v; img.data[o + 3] = 255;
    }
    c.putImageData(img, 0, 0);
  } else if (k === 2) {
    for (let gy = -1; gy <= 1; gy += 0.07) for (let gx = -1; gx <= 1; gx += 0.07) {
      const x = gx + (rnd() - 0.5) * 0.03, y = gy + (rnd() - 0.5) * 0.03, d = faceDepth(x, y);
      if (d <= 0) continue;
      const [px, py] = P(x * 0.95 + 0.12 * d * 0.4, y);
      const v = Math.round(90 + d * 150);
      c.fillStyle = `rgb(${v * 0.8 | 0},${v * 0.88 | 0},${v})`; c.fillRect(px - 1, py - 1, 2, 2);
    }
  } else {
    const N = 14, pts = [];
    for (let j = 0; j <= N; j++) { pts[j] = []; for (let i = 0; i <= N; i++) { const x = -1 + (2 * i) / N, y = -1 + (2 * j) / N; pts[j][i] = [x, y, faceDepth(x, y)]; } }
    c.lineWidth = 0.8;
    const seg = (a, b) => { if (a[2] <= 0 || b[2] <= 0) return; const v = Math.round(80 + ((a[2] + b[2]) / 2) * 140);
      c.strokeStyle = `rgba(${v * 0.75 | 0},${v * 0.85 | 0},${v},0.9)`; c.beginPath(); c.moveTo(...P(a[0] + a[2] * 0.05, a[1])); c.lineTo(...P(b[0] + b[2] * 0.05, b[1])); c.stroke(); };
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { seg(pts[j][i], pts[j][i + 1]); seg(pts[j][i], pts[j + 1][i]); seg(pts[j][i], pts[j + 1][i + 1]); }
  }
}
const stagesHTML = (active = 4) => `<ol class="stages" aria-label="Face IR pipeline">${FACE_STAGES.map(([t, d], k) =>
  `<li class="${k < active ? "on" : ""}" ${k === active - 1 ? 'aria-current="step"' : ""}><canvas data-stage="${k}" width="120" height="140" aria-hidden="true"></canvas><b>${k + 1}. ${t}</b><span>${d}</span></li>`).join("")}</ol>`;
const paintStages = (root = document) => $$("canvas[data-stage]", root).forEach((cv) => drawStage(cv, +cv.dataset.stage));

async function stepScan(f) {
  f.frame("scan", "Keep your face still and look straight ahead", `IR structured light builds the face surface in four stages. The RGB camera runs as a separate channel: expression, skin tone and pulse from video (rPPG). <span class="faint">A real scan takes 20 s.</span>`,
    `${checksHTML(["face", "light", "motion"])}${stagesHTML(0)}
     <div class="readouts"><div><b id="pts-face">0</b><span>Face points</span></div><div><b id="proj">1 of 3</b><span>Active projector</span></div>
       <div><b id="rppg">-</b><span>RGB channel: rPPG pulse, bpm</span></div><div><b id="rq">-</b><span>rPPG signal quality</span></div></div>`,
    f.training ? "Now the face scan. Look straight ahead and keep still. The projectors use invisible infrared dots. They are safe." : "Keep your face still and look straight ahead.");
  setView("front");
  await runChecks(f, ["face", "light", "motion"], 1400);
  paintStages($("#flow-body"));
  S.body.scan(true);
  const lis = $$("#flow-body .stages li");
  await f.timed(f.dur.scan, (p) => {
    const st = Math.min(4, 1 + Math.floor(p * 4));
    lis.forEach((li, k) => { li.classList.toggle("on", k < st); li.toggleAttribute("aria-current", k === st - 1); });
    $("#pts-face").textContent = fmt(p * 31000, 0);
    $("#proj").textContent = `${1 + (Math.floor(p * 9) % 3)} of 3`;
    if (p > 0.25) { $("#rppg").textContent = fmt(63 + Math.sin(p * 9), 0); $("#rq").textContent = `${fmt(78 + p * 14, 0)}%`; }
  });
  S.body.scan(false);
}

/** Which reference posture is used in this environment (drives the on-screen wording). */
function postureRef(res) {
  const mode = envMode({ ...S.state, ...(res || {}) });
  if (mode === "Earth") return "your standing preflight baseline";
  if (mode === "Microgravity") return "the microgravity neutral body posture (NASA), not the standing posture on Earth";
  return "the partial-gravity upright stance, not the standing posture on Earth";
}

async function stepTurn(f) {
  const views = [["front", "Face the mirror"], ["side", "Turn your right side to the mirror"], ["back", "Turn your back to the mirror"]];
  f.frame("turn", views[0][1], `Three synced views give the skeletal keypoint model: head, shoulders, elbows, pelvis, knees, feet. Posture is compared with ${postureRef()}.`,
    `<ol class="views3" aria-label="Body views">${views.map(([v]) => `<li data-v="${v}">${icon("CircleDashed")}<span>${v[0].toUpperCase() + v.slice(1)}</span></li>`).join("")}</ol>
     ${checksHTML(["light", "motion", "pose"])}
     <div class="readouts"><div><b id="kp">0 of 10</b><span>Keypoints found</span></div><div><b id="bodypts">0</b><span>Body points</span></div></div>`,
    f.training ? "Now three body views. Face the mirror, then turn your right side, then your back, when I ask." : views[0][1]);
  S.body.setSkeleton(true); $("#btn-skel")?.setAttribute("aria-pressed", "true");
  await runChecks(f, ["light", "motion", "pose"], 1200);
  let total = 0;
  for (const [k, [v, say]] of views.entries()) {
    if (k) { $(".prompt").textContent = say; f.prompt = say; mirror(say); Voice.say(say); }
    setView(v);
    const li = $(`[data-v="${v}"]`); li.classList.add("now");
    await f.timed(f.dur.view, (p) => { $("#kp").textContent = `${Math.round(p * 10)} of 10`; $("#bodypts").textContent = fmt(total + p * 71000, 0); });
    total += 71000;
    li.classList.remove("now"); li.classList.add("ok"); const ic = li.querySelector("svg"); if (ic) ic.outerHTML = icon("CircleCheck");
  }
  setView("front");
}

function waveDraw(canvas, t, hr, amp = 1) {
  if (!canvas) return;
  const c = canvas.getContext("2d");
  const w = (canvas.width = canvas.clientWidth * devicePixelRatio), h = (canvas.height = 64 * devicePixelRatio);
  c.clearRect(0, 0, w, h);
  c.strokeStyle = "#8FB2E8"; c.lineWidth = 1.5 * devicePixelRatio;
  c.beginPath();
  for (let x = 0; x < w; x += 2) {
    const ph = ((x / w) * 4 + t * hr / 60) % 1;
    const y = ph < 0.15 ? Math.sin((ph / 0.15) * Math.PI) : 0.25 * Math.exp(-(ph - 0.15) * 5) * Math.sin((ph - 0.15) * 14);
    c.lineTo(x, h * 0.8 - y * h * 0.6 * amp);
  }
  c.stroke();
}

async function stepRest(f) {
  f.frame("rest", "Hold the vertical grips in the side posts", `<span class="tag">${icon("FlaskConical")}Research module</span> Optional contact Doppler ultrasound under the palm arteries, plus PPG, SpO₂ and palm temperature. A fresh hydrogel strip is advanced from the cassette. Excluded from the main status. <span class="faint">A real reading takes 30 s.</span>`,
    `<div class="btn-row" style="margin-bottom:var(--s3)"><button type="button" class="btn quiet" id="skip-rest">${icon("SkipForward")}Skip Research Module</button></div><canvas class="wave" id="wave" aria-hidden="true"></canvas><div class="readouts"><div><b id="hr">-</b><span>Pulse, bpm</span></div><div><b id="spo2">-</b><span>SpO₂, %</span></div><div><b id="tmp">-</b><span>Palm temperature, °C</span></div><div><b id="flow">-</b><span>Blood flow L / R, cm/s</span></div></div>`,
    f.training ? "Rest your palms on the vertical grips. The ultrasound window should sit under your palm, with your index finger on the pulse sensor. Gel is applied automatically." : "Rest both palms on the grips and relax.");
  const t0 = performance.now();
  let skip = false;
  $("#skip-rest").onclick = () => { skip = true; };
  await f.timed(f.dur.rest, (p) => {
    if (skip) throw "skip";
    const t = (performance.now() - t0) / 1000;
    const hr = 62 + Math.sin(t * 0.7) * 2;
    waveDraw($("#wave"), reduceMotion() ? 0 : t, hr);
    if (p > 0.15) {
      $("#hr").textContent = fmt(hr, 0);
      $("#spo2").textContent = "98";
      $("#tmp").textContent = fmt(33.4 + Math.sin(t) * 0.05, 1);
      $("#flow").textContent = `${fmt(21 + Math.sin(t * 2) * 0.6, 0)} / ${fmt(22 + Math.cos(t * 2) * 0.6, 0)}`;
    }
  }).catch((e) => { if (e !== "skip") throw e; });
  if (skip) { f.skipResearch = true; toast("Research module skipped. Nothing from it is recorded. Main status is not affected.", "SkipForward"); }
}

async function stepGrip(f) {
  f.frame("grip", "Squeeze both grips as hard as you can, twice", `<span class="tag">${icon("FlaskConical")}Research module</span> Load cells in the grips measure grip strength. Excluded from the main status. In this demo press <kbd>Space</kbd> or the button.`,
    `<button type="button" class="squeeze" id="sq">${icon("Hand", "ico-24")}Squeeze</button><div class="readouts"><div><b id="sq1">-</b><span>Squeeze 1</span></div><div><b id="sq2">-</b><span>Squeeze 2</span></div></div>`);
  f.squeezes = 0;
  const press = () => {
    if (f.squeezes >= 2) return;
    f.squeezes++;
    $(`#sq${f.squeezes}`).innerHTML = `${icon("Check")}`;
    Voice.say(f.squeezes === 1 ? "Good. Once more." : "Well done.");
    if (f.squeezes === 1) mirror("Once more, as hard as you can");
  };
  f.onSqueeze = press;
  $("#sq").onclick = press;
  await f.timed(12000, () => { if (f.squeezes >= 2) f._done = true; if (f._done) throw "done"; }).catch((e) => { if (e !== "done") throw e; });
  f._done = false;
  if (f.squeezes < 2) { while (f.squeezes < 2) press(); } // the demo never gets stuck here
  f.onSqueeze = null;
  await f.wait(800);
}

async function stepHandgrip(f) {
  const ZONE = [25, 35];
  f.frame("handgrip", "Hold the bar in the green zone", `<span class="tag">${icon("FlaskConical")}Research module</span> Isometric handgrip test at 30% of your maximum. Hold <kbd>Space</kbd> or press and hold the button: the bar rises while you hold and falls when you let go. <span class="faint">The real test lasts 2 min, the demo ${f.dur.handgrip / 1000} s.</span>`,
    `<div class="game"><div class="meter" role="meter" aria-label="Grip force, percent of maximum" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" id="meter">
        <div class="zone" style="bottom:${ZONE[0]}%;height:${ZONE[1] - ZONE[0]}%"></div><div class="fill" id="fill"></div>
        <span class="lbl" style="bottom:${ZONE[1]}%">35%</span><span class="lbl" style="bottom:${ZONE[0] - 7}%">25%</span></div>
      <div><div class="score" id="score">0%</div><div class="muted small">of the time in the green zone</div>
        <div class="rating" id="rating" role="img" aria-label="Rating 0 of 3"><i></i><i></i><i></i></div>
        <div class="zone-state" id="zstate"></div>
        <div class="readouts"><div><b id="ghr">-</b><span>Pulse, bpm</span></div><div><b id="gforce">0</b><span>Force, % of max</span></div></div>
        <button type="button" class="squeeze" id="hold">${icon("Hand", "ico-24")}Hold</button></div></div>`,
    f.training ? "Handgrip test. Keep your grip so the bar stays in the green zone. It is about a third of your maximum, so do not squeeze hard." : "Keep the bar in the green zone.");
  const hold = $("#hold");
  const down = (e) => { e.preventDefault(); f.held = true; hold.classList.add("held"); };
  const up = () => { f.held = false; hold.classList.remove("held"); };
  hold.addEventListener("pointerdown", down);
  ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => hold.addEventListener(ev, up));
  hold.addEventListener("keydown", (e) => { if (e.key === "Enter") down(e); });
  hold.addEventListener("keyup", (e) => { if (e.key === "Enter") up(); });
  let force = 0, inZone = 0, total = 0, last = performance.now(), lastState = "";
  await f.timed(f.dur.handgrip, (p) => {
    const now = performance.now(), dt = (now - last) / 1000; last = now;
    const target = f.held ? 48 : 0;
    force += (target - force) * Math.min(dt * 1.6, 1) + (Math.random() - 0.5) * 0.8;
    force = Math.max(0, Math.min(100, force));
    total += dt;
    const ok = force >= ZONE[0] && force <= ZONE[1];
    if (ok) inZone += dt;
    const fill = $("#fill");
    fill.style.transform = `scaleY(${force / 100})`;
    const state = ok ? "in" : force > ZONE[1] ? "over" : "";
    fill.className = `fill ${state}`;
    $("#meter").setAttribute("aria-valuenow", String(Math.round(force)));
    if (state !== lastState) {
      lastState = state;
      $("#zstate").innerHTML = ok ? `<span class="st green">${icon("CircleCheck")}In the zone</span>`
        : force > ZONE[1] ? `<span class="st red">${icon("ArrowDown")}Too strong, ease off</span>` : `<span class="st none">${icon("ArrowUp")}Squeeze a little more</span>`;
    }
    const frac = total ? inZone / total : 0;
    $("#score").textContent = `${fmt(frac * 100, 0)}%`;
    const stars = frac > 0.8 ? 3 : frac > 0.6 ? 2 : frac > 0.4 ? 1 : 0;
    $$("#rating i").forEach((x, k) => x.classList.toggle("on", k < stars));
    $("#rating").setAttribute("aria-label", `Rating ${stars} of 3`);
    $("#gforce").textContent = fmt(force, 0);
    $("#ghr").textContent = fmt(63 + p * 14 * (force > 10 ? 1 : 0.6), 0);
  });
  f.held = false;
  const frac = total ? inZone / total : 0;
  Voice.say(frac >= 0.5 ? `Well done: ${Math.round(frac * 100)} percent of the time in the green zone.` : "The test did not count: the bar was mostly outside the green zone. Repeat it next time.");
  await f.wait(1500);
  return { in_zone_frac: Math.round(frac * 100) / 100 };
}

async function stepRecovery(f) {
  f.frame("recovery", "Release the grip and keep your palms on the Doppler windows", `Recovery: how fast pulse and blood flow return to rest. <span class="faint">The real recovery lasts 1 min.</span>`,
    `<canvas class="wave" id="wave" aria-hidden="true"></canvas><div class="readouts"><div><b id="rhr">-</b><span>Pulse, bpm</span></div></div>`);
  const t0 = performance.now();
  await f.timed(f.dur.recovery, (p) => {
    const hr = 77 - 13 * p;
    waveDraw($("#wave"), reduceMotion() ? 0 : (performance.now() - t0) / 1000, hr, 1 - p * 0.3);
    $("#rhr").textContent = fmt(hr, 0);
  });
}

async function stepSurvey(f) {
  const Q = [
    ["sleep_score", "How did you sleep? Rate from 1 to 5.", [1, 2, 3, 4, 5], ["Poor", "", "", "", "Great"]],
    ["wellbeing_score", "How do you feel? Rate from 1 to 5.", [1, 2, 3, 4, 5], ["Poor", "", "", "", "Great"]],
    ["symptoms_flag", "Any symptoms: headache, vision changes, stuffy nose, chills?", [true, false], ["", ""]],
    ["back_pain_flag", "Any back pain today? This one is optional.", [true, false, null], ["", "", ""]],
  ];
  const out = {};
  for (const [key, q, opts, hints] of Q) {
    f.frame("survey", q, "Answer by voice (a number, “yes” or “no”) or with a button.",
      `<div class="answers" role="group" aria-label="Answers">${opts.map((o, k) => `<button type="button" data-k="${k}">${o === true ? "Yes" : o === false ? "No" : o === null ? "Skip" : o}${hints[k] ? `<small>${hints[k]}</small>` : ""}</button>`).join("")}</div>`, q);
    progress(Object.keys(out).length / Q.length);
    out[key] = await new Promise((resolve, reject) => {
      f.answer = (v) => {
        const yesNo = key === "symptoms_flag" || key === "back_pain_flag";
        if (typeof v === "boolean" && !yesNo) return;
        if (typeof v === "number" && yesNo) return;
        resolve(v);
      };
      $$("#flow-body [data-k]").forEach((b) => b.onclick = () => resolve(opts[+b.dataset.k]));
      const iv = setInterval(() => { if (f.stopped) { clearInterval(iv); reject(new Cancelled()); } }, 200);
    });
    f.answer = null;
    if (out[key] === null) delete out[key];
  }
  return out;
}

function finishFlow(res) {
  const f = S.flow;
  S.flow = null;
  mirror("");
  if (!f.training) S.latest = res;
  showBody(res);
  S.body.setSkeleton(false); $("#btn-skel")?.setAttribute("aria-pressed", "false");
  renderScan(res);
  if (!f.training) loadReport();
  const box = $("#tab-session");
  const m = member();
  box.innerHTML = `<div class="who"><h1>${esc(crewName(m))}</h1><span class="role">${esc(crewRole(m))}</span>
    ${res.streak != null && !f.training ? `<span class="streak">${icon("CalendarCheck")}<span class="tnum">${res.streak}-day scan streak</span></span>` : ""}</div>`;
  box.append(verdictView(res, true));
  const row = document.createElement("div");
  row.className = "btn-row";
  row.style.marginTop = "var(--s5)";
  row.innerHTML = `<button type="button" class="btn primary" id="to-chart">${icon("ChartSpline")}Compare With NASA</button><button type="button" class="btn" id="again">${icon("RotateCcw")}New Session</button>`;
  box.append(row, metricsView(res));
  $("#again").onclick = () => renderIdle();
  $("#to-chart").onclick = () => openChart(res.overall.faster_than_nasa?.[0] || S.chartKey);
  const o = res.overall, t = overallText(o, res);
  const words = { green: `All stable. ${res.streak} days in a row.`, yellow: `A recheck is needed. ${t.summary}`, red: `Possible deviation. ${t.steps[0] || ""}` };
  Voice.say(words[o.status] || t.title);
  if (!f.training) loadChart();
  renderCrew();
  $(".verdict .title")?.setAttribute("tabindex", "-1");
  $(".verdict .title")?.focus({ preventScroll: true });
}

// ---------------- Scan tab: how LYRA sees you ----------------
const metricOf = (res, key) => res?.metrics?.find((m) => m.key === key);
function stickFromKeypoints(view, kp) {
  const pts = Object.values(kp);
  const xs = pts.map((q) => q[0]), ys = pts.map((q) => q[1]);
  const top = Math.max(...ys) + 140, bottom = Math.min(...ys, 0), span = top - bottom || 1;
  const k = 188 / span, P = (q) => [50 + q[0] * k * (view === "side" ? 1 : -1), 196 - (q[1] - bottom) * k]; // backend back view is already mirrored
  const get = (n) => kp[n] && P(kp[n]);
  const L = (a, b2) => a && b2 ? `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b2[0].toFixed(1)}" y2="${b2[1].toFixed(1)}"/>` : "";
  const head = get("head"), sl = get("shoulder_left"), sr = get("shoulder_right"), pel = get("pelvis");
  const neck = sl && sr ? [(sl[0] + sr[0]) / 2, (sl[1] + sr[1]) / 2] : head;
  const bones = [L(head, neck), L(neck, pel), L(sl, sr), L(sl, get("elbow_left")), L(sr, get("elbow_right")),
    L(pel, get("knee_left")), L(pel, get("knee_right")), L(get("knee_left"), get("foot_left")), L(get("knee_right"), get("foot_right"))];
  const joints = Object.keys(kp).filter((n) => n !== "head").map((n) => { const q = get(n); return `<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="3"/>`; }).join("");
  return `<svg class="stick" viewBox="0 0 100 200" role="img" aria-label="${view} view keypoints">
    <line class="plumb" x1="50" y1="6" x2="50" y2="196"/><g class="bones">${bones.join("")}</g>
    ${head ? `<circle class="headc" cx="${head[0].toFixed(1)}" cy="${(head[1] - 2).toFixed(1)}" r="10"/>` : ""}<g class="joints">${joints}</g></svg>`;
}
function stickFigure(view, b) {
  const kp = b?.skeleton?.views?.[view];
  if (kp && Object.keys(kp).length >= 5) return stickFromKeypoints(view, kp);
  // 2D keypoints for a 100 x 200 box; posture parameters bend the figure.
  const hf = (b?.head_forward_deg || 0) * 1.6, sa = (b?.shoulder_asym_deg || 0) * 2.2;
  const side = view === "side";
  const flip = view === "back" ? -1 : 1;
  const sx = (x) => 50 + x * flip;
  const P = side
    ? { head: [50 + hf * 0.5, 22], neck: [50 + hf * 0.15, 40], sh: [[50, 46], [50, 46]], el: [[46, 82], [46, 82]], wr: [[60, 106], [60, 106]],
        pel: [50, 108], hip: [[50, 110], [50, 110]], kn: [[52, 150], [52, 150]], ft: [[50, 190], [50, 190]] }
    : { head: [50, 22], neck: [50, 40], sh: [[sx(-20), 46 + sa], [sx(20), 46 - sa]], el: [[sx(-27), 78], [sx(27), 78]], wr: [[sx(-30), 104], [sx(30), 104]],
        pel: [50, 108], hip: [[sx(-10), 110], [sx(10), 110]], kn: [[sx(-11), 150], [sx(11), 150]], ft: [[sx(-12), 190], [sx(12), 190]] };
  const L = (a, b2) => `<line x1="${a[0]}" y1="${a[1]}" x2="${b2[0]}" y2="${b2[1]}"/>`;
  const bones = [L(P.head, P.neck), L(P.neck, P.pel), ...[0, 1].flatMap((i) => [L(P.neck, P.sh[i]), L(P.sh[i], P.el[i]), L(P.el[i], P.wr[i]), L(P.pel, P.hip[i]), L(P.hip[i], P.kn[i]), L(P.kn[i], P.ft[i])])];
  if (!side) bones.push(L(P.sh[0], P.sh[1]), L(P.hip[0], P.hip[1]));
  const joints = [P.neck, P.pel, ...P.sh, ...P.el, ...P.wr, ...P.hip, ...P.kn, ...P.ft].map((q) => `<circle cx="${q[0]}" cy="${q[1]}" r="3"/>`).join("");
  return `<svg class="stick" viewBox="0 0 100 200" role="img" aria-label="${view} view keypoints">
    <line class="plumb" x1="50" y1="6" x2="50" y2="196"/>
    <g class="bones">${bones.join("")}</g><circle class="headc" cx="${P.head[0]}" cy="${P.head[1]}" r="11"/><g class="joints">${joints}</g></svg>`;
}

function renderScan(res = S.latest) {
  const el = $("#tab-scan");
  if (!el) return;
  const b = res?.body || {};
  const posture = res?.posture || b.skeleton?.features || {};
  const mode = envMode({ ...S.state, ...(res || {}) });
  const neutralNote = `Posture is compared with ${postureRef(res)}.`;
  const ok = (m) => (m && m.confirmed !== false && m.value != null ? m : null);
  const rppg = ok(metricOf(res, "hr_rppg")), tension = ok(metricOf(res, "facial_tension")), face = ok(metricOf(res, "face_volume_ml"));
  const rppgQ = metricOf(res, "hr_rppg");
  // abs: absolute posture value (no sign); otherwise a change with a sign
  const feat = (label, v, unit, d = 1, abs = false) => `<div><dt>${label}</dt><dd>${v == null || isNaN(v) ? `<span class="faint">not measured in this session</span>` : `${abs ? fmt(v, d) : sgn(v, d)}${unit}`}</dd></div>`;
  el.innerHTML = `
    <h1 style="font-size:var(--fs-20)">How LYRA sees you</h1>
    <p class="muted" style="margin-top:var(--s2);max-width:68ch">Core LYRA is contactless: an IR structured-light face channel, an RGB video channel and a body keypoint model from three synced views.
      ${provenance(res?.provenance ?? res?.data_source, res?.simulated !== false, en(res?.provenance_note, ""))}</p>
    <h2 class="h-section">Face, IR structured light</h2>
    ${stagesHTML(4)}
    <p class="small faint" style="margin-top:var(--s2)">Stylized reconstruction. ${face ? `Face volume today: ${fmt(face.value, 0)} mL (${sgn(face.mission_pct ?? 0)}% vs preflight).` : ""}</p>
    <h2 class="h-section">RGB channel <span class="faint" style="font-weight:400;font-size:var(--fs-13)">separate from IR</span></h2>
    <dl class="kpis">
      <div><dt>${icon("Smile")} Expression</dt><dd>${tension ? `${fmt(tension.value, 2)}<small class="faint"> tension index</small>` : "-"}</dd></div>
      <div><dt>${icon("Droplet")} Skin tone</dt><dd>${res?.skin?.label ? esc(en(res.skin.label, "Stable")) : "Stable"}</dd></div>
      <div><dt>${icon("HeartPulse")} rPPG pulse</dt><dd>${rppg ? `${fmt(rppg.value, 0)}<small class="faint"> bpm</small>` : "-"}</dd></div>
      <div><dt>${icon("Signal")} rPPG signal quality</dt><dd>${rppgQ?.quality != null ? `${fmt(rppgQ.quality * 100, 0)}%<small class="faint"> ${reliability(rppgQ.quality)}</small>` : "-"}</dd></div>
    </dl>
    <h2 class="h-section">Body, skeletal keypoints from three synced views</h2>
    <div class="views3d">${["front", "side", "back"].map((v) => `<figure>${stickFigure(v, b)}<figcaption>${v[0].toUpperCase() + v.slice(1)}</figcaption></figure>`).join("")}</div>
    <p class="small faint">Keypoints: head, shoulders, elbows, pelvis, knees, feet.</p>
    <dl class="kpis" style="margin-top:var(--s4)">
      ${feat("Head tilt forward", posture.head_forward_deg, "°", 1, true)}
      ${feat("Trunk tilt", posture.trunk_tilt_deg, "°", 1, true)}
      ${feat("Shoulder height difference", posture.shoulder_asym_deg, "°", 1, true)}
      ${feat("Pelvis tilt", posture.pelvis_tilt_deg, "°", 1, true)}
    </dl>
    <dl class="kpis" style="margin-top:var(--s3)">
      ${feat("Scapula asymmetry", posture.scapula_asym_mm, " mm", 1, true)}
      ${feat("Height change", b.height_pct, "%")}
      ${feat("Calf volume change", b.legs_pct, "%")}
      <div><dt>Environment mode</dt><dd>${esc(mode || "-")}</dd></div>
    </dl>
    <p class="notice" style="margin-top:var(--s4)">${icon("Info", "ico-20")}<span>${neutralNote}</span></p>
    <h2 class="h-section">Optional research module</h2>
    <p class="notice">${icon("FlaskConical", "ico-20")}<span><b>Doppler ultrasound grips.</b> Vertical grips in the side posts with a hydrogel cassette measure palm blood flow. This is a contact research module, shown separately and excluded from the main status.</span></p>`;
  if (!el.hidden) paintStages(el);
}

// ---------------- Report: medical report for the flight surgeon ----------------
const CORE_REPORT = ["face_volume_ml", "periorbital_puffiness_mm", "leg_volume_ml", "height_cm", "head_forward_deg", "trunk_tilt_deg", "hr_rppg"];
async function loadReport() {
  const res = S.latest, aid = S.aid;
  if (!res) { S.report = null; return renderLink(); }
  const flagged = (res.overall?.flagged || []);
  const keys = [...new Set([...flagged, ...CORE_REPORT])].filter((k) => metricOf(res, k));
  const series = await Promise.all(keys.map((k) => api(`/api/astronauts/${aid}/series/${k}`).catch(() => null)));
  if (aid !== S.aid || res !== S.latest) return; // the user switched astronaut meanwhile
  S.report = { aid, res, rows: keys.map((k, i) => ({ m: metricOf(res, k), s: series[i] })) };
  renderLink();
}
function spark(s) {
  const pts = (s?.points || []).slice(-30);
  if (pts.length < 2) return "";
  const vs = pts.map((p) => p.value), lo = Math.min(...vs), hi = Math.max(...vs), W = 96, H = 24;
  const X = (i) => (i / (pts.length - 1)) * W, Y = (v) => H - 2 - ((v - lo) / ((hi - lo) || 1)) * (H - 4);
  return `<svg class="spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true">
    <polyline points="${pts.map((p, i) => `${X(i)},${Y(p.value)}`).join(" ")}"/><circle cx="${W}" cy="${Y(vs[vs.length - 1])}" r="2.2"/></svg>`;
}
function reportHTML() {
  const R = S.report;
  if (!R || R.aid !== S.aid) return `<p class="empty">Loading the report…</p>`;
  const res = R.res, m0 = member(), mode = envMode({ ...S.state, ...res });
  const row = ({ m, s }) => {
    const pts = s?.points || [];
    const prev = m.previous_value != null ? { value: m.previous_value, day: m.previous_day } : pts.length > 1 ? pts[pts.length - 2] : null;
    const d = m.key === "facial_tension" ? 2 : Math.abs(m.value) >= 100 ? 0 : 1;
    const reason = m.status === "green" ? "" : m.flag_reason && !CYR.test(m.flag_reason) ? m.flag_reason : m.faster_than_nasa ? "Faster than NASA expects" : m.z_status && m.z_status !== "green" ? "Outside personal baseline"
      : m.status === "retry" ? `Not confirmed${m.reject_reason ? `: ${rejectText(m.reject_reason).toLowerCase()}` : ""}` : "Flagged";
    return `<tr>
      <th scope="row">${esc(mName(m.key, m.name))}${isResearch(m) ? ` <span class="tag">Research</span>` : ""}</th>
      <td class="r">${m.confirmed === false ? "-" : fmt(m.value, d)} <small class="faint">${esc(unitEn(m.unit))}</small></td>
      <td class="r">${prev ? `${fmt(prev.value, d)}<small class="faint"> d${prev.day}</small>` : "-"}</td>
      <td class="r">${prev && m.confirmed !== false && m.value != null ? sgn(m.value - prev.value, d) : "-"}</td>
      <td>${spark(s)}</td>
      <td class="r">${m.quality != null ? `${fmt(m.quality * 100, 0)}%` : "-"}</td>
      <td>${badge(m.status, true)}${reason ? `<div class="small faint">${esc(reason)}</div>` : ""}</td></tr>`;
  };
  return `<div class="report-head">
      <div><b>${esc(crewName(m0))}</b> <span class="faint">${esc(crewRole(m0))}</span></div>
      <div class="small muted">Session day ${res.day}${res.mode === "weekly" ? ", weekly test" : ""}. ${esc(en(S.state.env_name, ENV[S.state.env]))}, ${esc((mode || "").toLowerCase())}.
        Overall: ${badge(res.overall.status, true)} ${provenance(res.provenance ?? res.data_source, res.simulated !== false, en(res.provenance_note, ""))}</div></div>
    <div class="table-wrap"><table class="report">
      <thead><tr><th scope="col">Measure</th><th scope="col" class="r">Today</th><th scope="col" class="r">Previous</th><th scope="col" class="r">Change</th><th scope="col">Last 30 days</th><th scope="col" class="r">Signal</th><th scope="col">Status and reason</th></tr></thead>
      <tbody>${R.rows.map(row).join("")}</tbody></table></div>
    <p class="small faint" style="margin-top:var(--s2)">Flagged measures first, then the core set. Signal is the capture quality score. Research module rows do not set the main status.</p>`;
}

// ---------------- why it matters ----------------
function sourceLinks(list) {
  return `<span class="sources">${(list || []).map((s) => s.url
    ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}${icon("ExternalLink")}</a>`
    : `<span>${esc(s.title)} <span class="faint">(link pending)</span></span>`).join("")}</span>`;
}
function srcById(ids) {
  return (ids || []).map((id) => S.ref.sources.find((s) => s.id === id)).filter(Boolean)
    .map((s) => ({ ...s, url: s.url?.startsWith("http") ? s.url : null }));
}
const hazardName = (id) => { const h = S.ref.hazards.find((x) => x.id === id); return h ? en(pick(h, "name"), h.name_en) : id; };
const riskName = (r) => r.name_en || en(pick(r, "name"));
const riskSummary = (r) => pick(r, "summary");
const basisTag = (b) => b ? `<span class="tag ${b === "cited" ? "cited" : ""}">${icon(b === "cited" ? "Quote" : "Calculator")}${b === "cited" ? "Cited" : "Estimated"}</span>` : "";

function whyCard(key) {
  const m = S.ref.metrics[key] || {};
  const exp = m.expected || {};
  const risks = (m.risk_ids || []).map((id) => S.ref.risks.find((r) => r.id === id)).filter(Boolean);
  modal(`Why it matters: ${mName(key, pick(m, "name"))}`, `
    ${pick(m, "why") ? `<p>${esc(pick(m, "why"))}</p>` : ""}
    ${risks.map((r) => `<div class="risk"><span class="hz">Hazard: ${esc(r.hazard_ids.map(hazardName).join(", "))}</span>
      <h3>NASA HRP risk: ${esc(riskName(r))}</h3><p>${esc(riskSummary(r))}</p>${sourceLinks(srcById(r.source_ids))}</div>`).join("")}
    <div class="note" style="margin-top:0"><p><b>NASA expectation.</b> ${exp.model && exp.model !== "none" ? esc(describeExpected(exp)) : "No published trajectory, so LYRA compares with your personal norm."} ${basisTag(exp.basis)}</p>
      ${pick(exp, "note") ? `<p class="small">${esc(pick(exp, "note"))}</p>` : ""}
      ${sourceLinks(srcById(exp.source_ids))}</div>
    <p class="small faint">LYRA is a screening tool, not a diagnosis.</p>`);
}

function describeExpected(e) {
  const r = Number(e.rate), u = unitEn(e.rate_unit || "");
  if (e.model === "linear") return `Linear change of ${sgn(r, 1)} ${u}.`;
  if (e.model === "saturating") return `${sgn(r, 1)} ${u}, reaching a plateau in about ${e.tau_days * 3} days (τ = ${e.tau_days} days)${e.band != null ? `, corridor ±${fmt(e.band, 1)}` : ""}.`;
  return "";
}

// ---------------- "You vs NASA expectation" chart ----------------
async function loadChart() {
  try {
    S.series = await api(`/api/astronauts/${S.aid}/series/${S.chartKey}`);
  } catch { S.chartKey = "face_volume_ml"; S.series = await api(`/api/astronauts/${S.aid}/series/${S.chartKey}`); }
  S.chartDay = null;
  renderChartTab();
}

function lineSwatch(kind) {
  const p = { band: `<rect x="0" y="2" width="22" height="10" fill="#8FB2E8" fill-opacity=".18"/>`,
    personal: `<rect x="0" y="2" width="22" height="10" fill="#7F8B96" fill-opacity=".2"/>`,
    center: `<line x1="0" y1="7" x2="22" y2="7" stroke="#8FB2E8" stroke-width="1.5" stroke-dasharray="5 3"/>`,
    you: `<line x1="0" y1="7" x2="22" y2="7" stroke="#E7ECF0" stroke-width="2"/>`,
    off: `<circle cx="11" cy="7" r="4.5" fill="#F0686A"/>`,
    live: `<circle cx="11" cy="7" r="4.5" fill="#0D1114" stroke="#E7ECF0" stroke-width="2"/>` }[kind];
  return `<svg width="22" height="14" viewBox="0 0 22 14" aria-hidden="true">${p}</svg>`;
}

function renderChartTab() {
  const keys = Object.keys(S.ref.metrics).filter((k) => !["radiation_dose_msv", "sleep_score", "wellbeing_score", "symptoms_flag"].includes(k));
  const modeled = keys.filter((k) => ["linear", "saturating"].includes(S.ref.metrics[k].expected?.model));
  const rest = keys.filter((k) => !modeled.includes(k));
  const opt = (k) => `<option value="${k}" ${k === S.chartKey ? "selected" : ""}>${esc(mName(k, pick(S.ref.metrics[k], "name")))}</option>`;
  const s = S.series;
  const who = member();
  const last = s.points[s.points.length - 1];
  const cLast = last && s.corridor.find((c) => c.day === last.day);
  let verdict = "";
  if (last && s.modeled && cLast) {
    const st = pointStatus(s, last, cLast);
    verdict = `${badge(st)}<span>${st === "green" ? "Day " + last.day + ": inside NASA's expected corridor." : "Day " + last.day + ": changing faster than NASA expects."}</span>`;
  } else if (last) verdict = `<span>No NASA trajectory for this measure. The band shows your preflight norm (±2σ).</span>`;
  const name = mName(s.key, s.name);
  $("#tab-chart").innerHTML = `
    <div class="chart-top">
      <div><h1>${esc(crewName(who))}: you vs NASA expectation</h1></div>
      <label class="field">Measure<select id="metric-sel">
        <optgroup label="With a NASA trajectory">${modeled.map(opt).join("")}</optgroup>
        <optgroup label="Personal norm only">${rest.map(opt).join("")}</optgroup></select></label>
    </div>
    <p class="chart-status">${verdict}</p>
    <div class="legend">
      ${s.modeled ? `<span>${lineSwatch("band")}NASA expected corridor</span><span>${lineSwatch("center")}NASA expected value (dashed)</span>` : `<span>${lineSwatch("personal")}Preflight norm ±2σ</span>`}
      <span>${lineSwatch("you")}You (solid)</span><span>${lineSwatch("off")}Outside the corridor</span><span>${lineSwatch("live")}Today's live session</span>
    </div>
    <div class="chart-wrap" id="chart-wrap">
      <svg class="chart" id="chart" tabindex="0" role="img" aria-describedby="chart-sum" aria-label="${esc(name)} over mission days. Use the left and right arrow keys to read values."></svg>
      <div class="tip" id="tip" hidden></div>
    </div>
    <p class="sr" id="chart-sum" aria-live="polite"></p>
    <div class="note">
      ${s.modeled ? `<p><b>NASA expectation.</b> ${esc(describeExpected(s.expected))} ${basisTag(s.expected.basis)}</p>${pick(s.expected, "note") ? `<p class="small">${esc(pick(s.expected, "note"))}</p>` : ""}`
        : `<p><b>NASA publishes no trajectory for this measure.</b> Status uses your personal norm from the last 14 measurements.</p>`}
      ${s.risks.length ? `<p class="small">Linked NASA risk: ${s.risks.map((r) => esc(riskName(r))).join(", ")}. ${esc(pick(s, "why"))}</p>` : ""}
      ${sourceLinks(s.sources)}
      <p class="small faint">History up to today is simulated along these same curves plus the scenario. Baseline is the mean of 7 preflight days.</p>
    </div>`;
  $("#metric-sel").onchange = (e) => { S.chartKey = e.target.value; loadChart(); };
  drawChart(true);
}

function pointStatus(s, p, c) {
  if (!c || p.day <= 0) return null;
  const half = (c.hi - c.lo) / 2 || 1;
  const up = (p.value - c.hi) / half, dn = (c.lo - p.value) / half;
  const ex = s.direction === "up" ? up : s.direction === "down" ? dn : Math.max(up, dn);
  return ex <= 0 ? "green" : ex < 1 ? "yellow" : "red";
}

function drawChart(animate = false) {
  const s = S.series, svg = $("#chart");
  if (!s || !svg || !svg.isConnected || ($("#tab-chart").hidden && !animate)) return;
  const W = Math.max(svg.parentElement.clientWidth || 600, 280), H = Math.round(Math.min(Math.max(W * 0.48, 220), 360));
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const narrow = W < 480;
  const P = { l: narrow ? 44 : 56, r: narrow ? 12 : 96, t: 22, b: 34 };
  const pts = s.points;
  const corr = s.corridor.filter((c) => c.day <= s.today + 14);
  const x0 = Math.min(-6, ...pts.map((p) => p.day)), x1 = Math.max(s.today + (corr.length ? 14 : 2), ...pts.map((p) => p.day));
  let band = corr;
  if (!s.modeled && s.preflight != null) {
    const pre = pts.filter((p) => p.day <= 0).map((p) => p.value);
    const m = pre.reduce((a, b) => a + b, 0) / (pre.length || 1);
    const sd = Math.sqrt(pre.reduce((a, b) => a + (b - m) ** 2, 0) / Math.max(pre.length - 1, 1)) || 1;
    band = [{ day: x0, lo: m - 2 * sd, hi: m + 2 * sd, center: m }, { day: x1, lo: m - 2 * sd, hi: m + 2 * sd, center: m }];
  }
  const ys = [...pts.map((p) => p.value), ...band.flatMap((c) => [c.lo, c.hi])];
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  const pad = (y1 - y0) * 0.1 || 1; y0 -= pad; y1 += pad;
  const X = (d) => P.l + ((d - x0) / (x1 - x0)) * (W - P.l - P.r);
  const Y = (v) => H - P.b - ((v - y0) / (y1 - y0)) * (H - P.t - P.b);
  const dec = s.decimals ?? 1;
  const unit = unitEn(s.unit);
  const cAt = (d) => corr.find((c) => c.day === d);
  let g = "";
  for (let i = 0; i <= 4; i++) {
    const v = y0 + ((y1 - y0) * i) / 4;
    g += `<line class="grid-l" x1="${P.l}" x2="${W - P.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${P.l - 8}" y="${Y(v) + 4}" text-anchor="end">${fmt(v, dec)}</text>`;
  }
  g += `<text x="${P.l - 8}" y="${P.t - 8}" text-anchor="end">${esc(unit)}</text>`;
  const step = Math.max(5, Math.ceil((x1 - x0) / (narrow ? 5 : 8) / 5) * 5);
  for (let d = Math.ceil(x0 / step) * step; d <= x1; d += step) if (X(d) < W - (narrow ? 40 : 84)) g += `<text x="${X(d)}" y="${H - 12}" text-anchor="middle">${d}</text>`;
  g += `<text x="${W - 2}" y="${H - 12}" text-anchor="end">${narrow ? "Day" : "Mission day"}</text>`;
  if (band.length) {
    const poly = band.map((c) => `${X(c.day)},${Y(c.hi)}`).concat([...band].reverse().map((c) => `${X(c.day)},${Y(c.lo)}`)).join(" ");
    g += `<polygon class="band ${s.modeled ? "" : "personal"}" points="${poly}"/>`;
    if (s.modeled) g += `<polyline class="center" points="${band.map((c) => `${X(c.day)},${Y(c.center)}`).join(" ")}"/>`;
    const lastB = band[band.length - 1];
    if (!narrow) g += `<text class="${s.modeled ? "lab-acc" : "lab"}" x="${X(lastB.day) + 8}" y="${Y(lastB.center) + 4}">${s.modeled ? "NASA corridor" : "Preflight norm"}</text>`;
  }
  g += `<line class="vline" x1="${X(0)}" x2="${X(0)}" y1="${P.t}" y2="${H - P.b}"/><text x="${X(0) + 4}" y="${P.t - 6}">Launch</text>`;
  g += `<line class="vline today" x1="${X(s.today)}" x2="${X(s.today)}" y1="${P.t}" y2="${H - P.b}"/><text class="lab" x="${X(s.today)}" y="${P.t - 6}" text-anchor="middle">Today</text>`;
  const line = pts.map((p) => `${X(p.day)},${Y(p.value)}`).join(" ");
  g += `<polyline class="you ${animate && !reduceMotion() ? "draw" : ""}" id="you-line" points="${line}"/>`;
  g += pts.map((p) => {
    const st = pointStatus(s, p, cAt(p.day));
    const off = st && st !== "green";
    if (p.live) return `<circle class="dot live" cx="${X(p.day)}" cy="${Y(p.value)}" r="5.5"/>`;
    return off ? `<circle class="dot ${st}" cx="${X(p.day)}" cy="${Y(p.value)}" r="4"/><circle class="ring" cx="${X(p.day)}" cy="${Y(p.value)}" r="4"/>`
      : `<circle class="dot" cx="${X(p.day)}" cy="${Y(p.value)}" r="${pts.length > 60 ? 1.6 : 2.2}"/>`;
  }).join("");
  const lastP = pts[pts.length - 1];
  if (lastP && !narrow) g += `<text class="lab" x="${X(lastP.day) + 10}" y="${Y(lastP.value) + 4}">You ${fmt(lastP.value, dec)}</text>`;
  g += `<line class="cross" id="cross" y1="${P.t}" y2="${H - P.b}" visibility="hidden"/><circle id="hov" class="hov" r="7" visibility="hidden"/>`;
  svg.innerHTML = g;
  const path = $("#you-line");
  if (path?.classList.contains("draw")) path.style.setProperty("--len", String(Math.ceil(path.getTotalLength())));

  // summary for screen readers
  if (lastP) {
    const c = cAt(lastP.day);
    $("#chart-sum").textContent = `${mName(s.key, s.name)}: latest ${fmt(lastP.value, dec)} ${unit} on day ${lastP.day}.` +
      (c && s.modeled ? ` NASA expected ${fmt(c.center, dec)}, corridor ${fmt(c.lo, dec)} to ${fmt(c.hi, dec)}.` : "");
  }

  const tip = $("#tip");
  const show = (day) => {
    day = Math.max(x0, Math.min(x1, day));
    S.chartDay = day;
    const pp = pts.find((q) => q.day === day);
    const cc = cAt(day);
    const cross = $("#cross"), hov = $("#hov");
    cross.setAttribute("x1", X(day)); cross.setAttribute("x2", X(day)); cross.setAttribute("visibility", "visible");
    if (pp) { hov.setAttribute("cx", X(day)); hov.setAttribute("cy", Y(pp.value)); hov.setAttribute("visibility", "visible"); } else hov.setAttribute("visibility", "hidden");
    const st = pp && pointStatus(s, pp, cc);
    const pct = pp && s.preflight ? ` (${sgn((100 * (pp.value - s.preflight)) / s.preflight)}%)` : "";
    tip.innerHTML = `<b>Day ${day}${day <= 0 ? ", preflight" : ""}${pp?.live ? ", today" : ""}</b><br>
      ${pp ? `You: <b>${fmt(pp.value, dec)} ${esc(unit)}</b>${pct}<br>` : `<span class="faint">No session this day</span><br>`}
      ${cc && s.modeled ? `NASA expected: ${fmt(cc.center, dec)}<br>Corridor: ${fmt(cc.lo, dec)} to ${fmt(cc.hi, dec)}<br>` : ""}
      ${st ? (st === "green" ? `<span class="st green sm">${icon("CircleCheck")}Inside or better than corridor</span>` : `<span class="st ${st} sm">${icon(ST[st].icon)}Faster than NASA expects</span>`) : ""}
      ${pp?.mode === "weekly" ? `<br><span class="faint">Weekly full test</span>` : ""}`;
    tip.hidden = false;
    const r = svg.getBoundingClientRect(), k = r.width / W;
    const left = X(day) * k;
    tip.style.left = `${left > r.width / 2 || left + 14 + tip.offsetWidth > r.width ? Math.max(left - tip.offsetWidth - 14, 0) : left + 14}px`;
    tip.style.top = `${Math.max((pp ? Y(pp.value) : H / 2) * k - 40, 0)}px`;
    $("#chart-sum").textContent = tip.textContent.replace(/\s+/g, " ").trim();
  };
  const hide = () => { tip.hidden = true; $("#cross")?.setAttribute("visibility", "hidden"); $("#hov")?.setAttribute("visibility", "hidden"); };
  svg.onpointermove = (e) => {
    const r = svg.getBoundingClientRect();
    const mx = ((e.clientX - r.left) / r.width) * W;
    const d = Math.round(x0 + ((mx - P.l) / (W - P.l - P.r)) * (x1 - x0));
    const p = pts.reduce((a, b) => (Math.abs(b.day - d) < Math.abs(a.day - d) ? b : a), pts[0]);
    show(p && Math.abs(p.day - d) <= 1 ? p.day : d);
  };
  svg.onpointerleave = () => { if (document.activeElement !== svg) hide(); };
  svg.onblur = hide;
  svg.onfocus = () => show(S.chartDay ?? lastP?.day ?? s.today);
  svg.onkeydown = (e) => {
    const cur = S.chartDay ?? lastP?.day ?? s.today;
    const map = { ArrowLeft: cur - 1, ArrowRight: cur + 1, Home: x0, End: x1, PageUp: cur - 7, PageDown: cur + 7 };
    if (e.key in map) { e.preventDefault(); show(map[e.key]); }
    else if (e.key === "Escape") hide();
  };
}
let rz;
window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => drawChart(), 150); });

// ---------------- downlink and dose ----------------
function fmtDur(s) {
  if (s == null) return "-";
  if (s < 1) return "under 1 s";
  if (s < 60) return `${fmt(s, 0)} s`;
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m} min${r ? ` ${r} s` : ""}`;
}

function renderLink() {
  const L = S.link || S.state.downlink;
  if (!L) return;
  const el = $("#tab-link");
  const scale = L.time_scale;
  const sinceRecv = ((performance.now() - S.linkAt) / 1000) * scale;
  const items = L.items.map((p) => {
    const rem = p.status === "delivered" ? 0 : Math.max(p.remaining_s - (S.linkAt ? sinceRecv : 0), 0);
    const prog = p.delay_s > 0 ? 1 - rem / p.delay_s : 1;
    const st = LIGHT[p.status_light] || (ST[p.status_light] ? p.status_light : null);
    const who = en(p.astronaut_name, CREW[p.astronaut_id]?.[0]);
    return `<li class="${p.status}">
      ${st ? `<span title="${ST[st].word}">${badge(st, true).replace('class="word"', 'class="word sr"')}</span>` : "<span></span>"}
      <span><b>${esc(who)}</b>, ${esc(en(p.title, p.size_kb >= 400 ? "Weekly full test" : p.status === "delivered" && p.day < S.state.day ? "Session (history)" : "Daily scan"))} <span class="pmeta">day ${p.day}, ${p.size_kb} KB${st ? `, ${ST[st].word.toLowerCase()}` : ""}</span></span>
      <span class="pstate ${p.status}">${p.has_report && p.status === "delivered" ? `<button type="button" class="linkbtn" data-report="${esc(p.id)}">${icon("FileText")}Report</button>` : ""}${p.status === "delivered" ? `${icon("Check")}Delivered` : `${icon("Send")}In transit, ${fmtDur(rem)} left`}</span>
      <span class="bar" aria-hidden="true"><i style="transform:scaleX(${Math.max(0, Math.min(1, prog)).toFixed(3)})"></i></span></li>`;
  }).join("");
  const env = en(S.state.env_name, ENV[S.state.env]);
  const [lo, hi] = L.delay_range_s;
  const d = S.dose;
  const focused = document.activeElement?.id === "dose-in" ? $("#dose-in").value : null;
  el.innerHTML = `
    <h1 style="font-size:var(--fs-20)">Report and downlink to the flight surgeon</h1>
    <p class="muted" style="margin-top:var(--s2);max-width:68ch">Every session is queued for Earth automatically. The crew never waits for a reply: “Repeat measurement” and “Refer to specialist” instructions are shown on board right away.</p>
    <dl class="kpis">
      <div><dt>Environment</dt><dd>${esc(env)}</dd></div>
      <div><dt>One-way delay now</dt><dd>${fmtDur(L.delay_s)}</dd></div>
      <div><dt>Range (NASA reference)</dt><dd>${fmtDur(lo)} to ${fmtDur(hi)}</dd></div>
      <div><dt>Earliest reply</dt><dd>${fmtDur(L.round_trip_s)}</dd></div>
    </dl>
    ${scale > 1 && L.delay_s >= 1 ? `<p class="small faint" style="margin-top:var(--s3)">${icon("Clock")} Transfer time is sped up ${fmt(scale, 0)}x for the demo.</p>` : ""}
    <h2 class="h-section">Medical report <span class="faint" style="font-weight:400;font-size:var(--fs-13)">what the flight surgeon receives</span></h2>
    ${reportHTML()}
    <h2 class="h-section">Downlink queue</h2>
    ${items ? `<ul class="packets">${items}</ul>` : `<p class="empty">The queue is empty. Finish a session to send data.</p>`}
    <section class="dose" aria-labelledby="dose-h">
      <h2 class="h-section" id="dose-h" style="margin-bottom:0">${icon("Radiation")} ${esc(en(pick(d, "name"), "Accumulated dose, station dosimeter"))}</h2>
      <p class="muted small">${esc(en(d?.disclaimer, "LYRA does not measure radiation. The value is imported from the station dosimeter."))}</p>
      <div class="big">${d?.last ? `${fmt(d.last.dose_msv, 1)}<small>mSv</small>` : `<span class="faint" style="font-size:var(--fs-20)">No dose imported yet</span>`}</div>
      ${d?.last ? `<p class="small faint">Day ${d.last.day}, ${esc(en(d.last.source, "station dosimeter (simulated)"))}</p>` : ""}
      ${d?.career_limit_msv ? `<p class="small">NASA career limit: ${fmt(d.career_limit_msv, 0)} mSv (${fmt((100 * (d.last?.dose_msv || 0)) / d.career_limit_msv, 1)}% used)</p>` : ""}
      ${d?.rate_msv_day ? `<p class="small faint">Simulated rate: ${fmt(d.rate_msv_day, 2)} mSv/day${CYR.test(d.rate_note || "") ? "" : `, ${esc(d.rate_note)}`}</p>` : ""}
      ${pick(d, "note") ? `<p class="small">${esc(pick(d, "note"))}</p>` : ""}
      ${pick(d, "radiation_note") ? `<p class="small faint">${esc(pick(d, "radiation_note"))}</p>` : ""}
      <form class="dose-form" id="dose-form">
        <label for="dose-in">Dosimeter reading, mSv<input id="dose-in" name="dose_msv" type="number" inputmode="decimal" min="0" step="0.1" placeholder="e.g. 24.5…" autocomplete="off"></label>
        <button class="btn" type="submit">${icon("Download")}Import Reading</button>
      </form>
      ${sourceLinks(d?.sources)}
    </section>`;
  if (focused != null) { $("#dose-in").value = focused; $("#dose-in").focus(); }
  $$("[data-report]", el).forEach((b) => b.onclick = () => openPacketReport(b.dataset.report));
  $("#dose-form").onsubmit = async (e) => {
    e.preventDefault();
    const v = parseFloat($("#dose-in").value);
    if (isNaN(v) || v < 0) { toast("Enter the dose in mSv as a number of 0 or more.", "TriangleAlert"); $("#dose-in").focus(); return; }
    S.dose = await api(`/api/astronauts/${S.aid}/dose`, { dose_msv: v });
    toast("Dose reading imported.", "Check");
    renderLink();
  };
  const n = L.in_transit;
  $("#link-badge").textContent = n;
  $("#link-badge").hidden = !n;
  $("#link-badge").setAttribute("aria-label", `${n} in transit`);
}
setInterval(() => { if (!$("#tab-link").hidden && S.link?.in_transit && document.activeElement?.id !== "dose-in") renderLink(); }, 1000);

async function openPacketReport(id) {
  let d;
  try { d = await api(`/api/downlink/${encodeURIComponent(id)}`); } catch (e) { return toast(`Could not open the report: ${e.message}.`, "TriangleAlert"); }
  const r = d.report;
  if (!r) return toast("This packet has no report attached.", "Info");
  const rows = (r.metrics || []).filter((m) => m.status && m.status !== "green" || ["face_volume_ml", "leg_volume_ml", "height_cm", "hr_rppg"].includes(m.key));
  const row = (m) => {
    const dd = Math.abs(m.value ?? 0) >= 100 ? 0 : 1;
    return `<tr><th scope="row">${esc(mName(m.key, m.name))}${m.module === "research" ? ` <span class="tag">Research</span>` : ""}</th>
      <td class="r">${m.value == null || m.confirmed === false ? "-" : fmt(m.value, dd)} <small class="faint">${esc(unitEn(m.unit))}</small></td>
      <td class="r">${m.previous_value != null ? fmt(m.previous_value, dd) : "-"}</td>
      <td class="r">${m.quality != null ? `${fmt(m.quality * 100, 0)}%` : "-"}</td>
      <td>${badge(m.status, true)}${m.flag_reason ? `<div class="small faint">${esc(en(m.flag_reason, ""))}</div>` : ""}</td></tr>`;
  };
  modal(`Medical report: ${en(r.astronaut?.name, "crew member")}, day ${r.day}`, `
    <p>${badge(r.overall?.status, true)} ${esc(en(r.overall?.summary, ""))}</p>
    <p class="small">${esc(en(r.env_mode_label, envMode(r)))}. ${provenance(r.provenance, true, en(r.provenance_note, ""))}
      ${r.signal_quality?.mean != null ? ` Mean signal quality ${fmt(r.signal_quality.mean * 100, 0)}%.` : ""}</p>
    <div class="table-wrap"><table class="report"><thead><tr><th scope="col">Measure</th><th scope="col" class="r">Value</th><th scope="col" class="r">Previous</th><th scope="col" class="r">Signal</th><th scope="col">Status and reason</th></tr></thead>
      <tbody>${rows.map(row).join("")}</tbody></table></div>
    ${r.research?.note ? `<p class="small faint">${esc(en(r.research.note, ""))}</p>` : ""}`);
}

// ---------------- risks ----------------
function renderRisks() {
  const R = S.ref;
  const metricsFor = (rid) => Object.entries(R.metrics).filter(([, m]) => (m.risk_ids || []).includes(rid)).map(([k, m]) => mName(k, pick(m, "name")));
  $("#tab-risks").innerHTML = `
    <h1 style="font-size:var(--fs-20)">Every measure maps to a NASA risk and hazard</h1>
    <p class="muted" style="margin-top:var(--s2);max-width:68ch">LYRA does not diagnose. It shows whether you are changing faster than NASA expects, and links each measure to a NASA Human Research Program risk.</p>
    <h2 class="h-section">Five hazards of human spaceflight</h2>
    <div class="hazards">${R.hazards.map((h) => `<div><b>${esc(h.name_en || pick(h, "name"))}</b><span>${R.risks.filter((r) => r.hazard_ids?.includes(h.id)).length} linked risks</span></div>`).join("")}</div>
    <h2 class="h-section">Risks LYRA screens for</h2>
    ${R.risks.map((r) => `<article class="risk"><span class="hz">${(r.hazard_ids || []).map((id) => esc(hazardName(id))).join(", ")}</span>
      <h3>${esc(riskName(r))}</h3><p>${esc(riskSummary(r))}</p>
      <p class="mets"><b>LYRA measures:</b> ${metricsFor(r.id).map(esc).join(", ") || "none yet"}</p>
      ${sourceLinks(srcById(r.source_ids))}</article>`).join("")}`;
}

// ---------------- WebSocket ----------------
function connect() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "state") {
      const changed = S.state && m.scenario !== S.state.scenario;
      S.state = m; S.link = m.downlink; S.linkAt = performance.now();
      renderHeader(); renderLink();
      if (changed && !S.flow) selectAstronaut(S.aid);
    } else if (m.type === "downlink") {
      const before = S.link?.items?.filter((p) => p.status === "delivered").length || 0;
      S.link = m; S.linkAt = performance.now();
      const after = m.items.filter((p) => p.status === "delivered").length;
      if (after > before) toast("Packet delivered to the flight surgeon on Earth.", "SatelliteDish");
      renderLink();
    }
  };
  ws.onclose = () => setTimeout(connect, 1500);
}

// ---------------- keyboard ----------------
document.addEventListener("keydown", (e) => {
  if (e.target.matches?.("input, select, textarea")) return;
  if (e.code === "Space" && S.flow) {
    if (e.target.matches?.("button") && !["hold", "sq"].includes(e.target.id)) return;
    e.preventDefault();
    if (e.repeat) return;
    S.flow.held = true; $("#hold")?.classList.add("held");
    S.flow.onSqueeze?.();
  } else if (e.code === "Enter" && !S.flow && !$("#tab-session").hidden && !e.target.matches?.("button, a, summary, svg, [role=tab]")) startFlow("daily");
  else if (e.code === "Escape" && S.flow) S.flow.stop();
});
document.addEventListener("keyup", (e) => {
  if (e.code === "Space" && S.flow) { S.flow.held = false; $("#hold")?.classList.remove("held"); }
});

// ---------------- start ----------------
async function init() {
  hydrateIcons();
  Voice.ui();
  [S.meta, S.state, S.ref] = await Promise.all([api("/api/meta"), api("/api/state"), api("/api/reference")]);
  S.link = S.state.downlink; S.linkAt = performance.now();
  initBody();
  renderHeader();
  renderRisks();
  await selectAstronaut(S.aid);
  connect();
}
init().catch((e) => { console.error(e); toast(`Could not load the station data: ${e.message}. Check that the server is running and reload.`, "TriangleAlert", 10000); });
